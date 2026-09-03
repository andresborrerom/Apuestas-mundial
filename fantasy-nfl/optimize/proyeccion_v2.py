"""Proyección v2.1 — overlay de PARTIDOS JUGADOS, historia 2010-2025.

Sesgo del mercado MEDIDO: ~100% de relevantes proyectados a 17 juegos.
Factor VALIDADO walk-forward en 12 años de test (2014-2025, n=2,771):
mejora +12% a +28% TODOS los años vs asumir temporada llena; estacionario
(la ventana histórica no cambia el resultado: se usa toda la muestra).

Modelo JERÁRQUICO (pedido de Andrés: "condicionado a quiénes se parecían
a ellos"): celda fina (pos, tier POR-JUEGO, lesión previa) si n>=8;
respaldo (pos, tier por total, edad); respaldo final: posición.
Pareado 2014-2025 n=2,727: fino 55.7-55.8 vs grueso 56.0 MAE — no pierde
en agregado y corrige los casos élite-lesionado (QB A+les: 13.7 juegos,
n=21; vs B+les: 8.6, n=130 — la celda que contaminaba a Lamar/Burrow).

Pre-2021 la temporada era de 16: todo se estima como FRACCIÓN perdida y
se re-escala a 17.

Modelo de valor: VBD2 = E[g] × (pg − pg_baseline). Motor lineal → exacto.

SUPUESTOS: S4 eficiencia por-juego del mercado insesgada. S5 rookies QB
por ronda draft (13.3/7.2/5.1), resto media rookie posicional; sin data →
celda B sana. S6 D/ST E[g]=17; K sin celda → 16.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
from model.scoring import cargar_reglas, puntos
from optimize.vbd import POS, BASE

RAIZ = Path(__file__).resolve().parent.parent
NVPOS = {'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'K': 'K', 'LB': 'LB',
         'DT': 'DT', 'DE': 'DE', 'CB': 'CB',
         'S': ('S', 'FS', 'SS'), 'DB': ('DB',)}


def tabla_eg(con):
    """E[fracción perdida] jerárquico con 2010-2025 (transiciones 2011+)."""
    rows = con.execute("""
    with juegos as (
      select player_id, position, season, count(distinct week) g,
             sum(coalesce(fantasy_points_ppr,0)) fp,
             sum(coalesce(def_tackles_solo,0)+coalesce(def_tackle_assists,0)) tkl
      from fact_player_week where season_type='REG' group by 1,2,3),
    rel as (select *, lag(g) over w g_prev, lag(fp) over w fp_prev,
                   lag(tkl) over w tkl_prev, lag(season) over w s_prev
            from juegos window w as (partition by player_id order by season)),
    t as (select r.*,
            rank() over (partition by r.position, r.season order by r.fp_prev desc) rk_tot,
            rank() over (partition by r.position, r.season
                         order by r.fp_prev/nullif(r.g_prev,0) desc) rk_pg,
            x.birthdate
          from rel r left join xwalk_ids_nflverse x on r.player_id=x.gsis_id
          where r.g_prev >= 8 and r.s_prev = r.season-1)
    select position, season, g, g_prev, rk_tot, rk_pg, tkl_prev,
           case when birthdate is null then null
                else season - year(birthdate::date) end edad
    from t where season >= 2011
    """).fetchall()
    from collections import defaultdict
    fino, grueso, porpos = defaultdict(list), defaultdict(list), defaultdict(list)
    for pos, ss, g, gp, rkt, rkpg, tklp, edad in rows:
        sg, sgp = (17 if ss >= 2021 else 16), (17 if ss - 1 >= 2021 else 16)
        miss = 1 - g / sg
        les = 'les' if gp <= sgp - 4 else 'ok'
        v = 'v' if (edad or 0) >= 29 else 'j'
        fino[(pos, _tier(pos, rkpg, tklp), les)].append(miss)
        grueso[(pos, _tier(pos, rkt, tklp), v)].append(miss)
        porpos[pos].append(miss)
    # celda 'corto': jugó 1-7 juegos el año previo con per-juego de titular
    # (QB>=15, resto >=8 ppr/j). Auditoría 19-ago: el fallback "sano" era
    # demasiado generoso justo para la población más riesgosa.
    corto_rows = con.execute("""
    with juegos as (
      select player_id, position, season, count(distinct week) g,
             sum(coalesce(fantasy_points_ppr,0)) fp
      from fact_player_week where season_type='REG' group by 1,2,3),
    rel as (select *, lag(g) over w g_prev, lag(fp) over w fp_prev,
                   lag(season) over w s_prev
            from juegos window w as (partition by player_id order by season))
    select position, season, g, fp_prev/g_prev pgp
    from rel where s_prev=season-1 and g_prev between 1 and 7 and season>=2011
    """).fetchall()
    corto = defaultdict(list)
    for pos, ss, g, pgp in corto_rows:
        if pgp and pgp >= (15 if pos == 'QB' else 8):
            corto[pos].append(1 - g / (17 if ss >= 2021 else 16))
    prom = lambda d: {k: sum(v) / len(v) for k, v in d.items() if len(v) >= 8}
    return prom(fino), prom(grueso), prom(porpos), prom(corto)


def _tier(pos, rk, tkl):
    if pos == 'QB':
        return 'A' if (rk or 99) <= 12 else 'B'
    if pos in ('RB', 'WR'):
        return 'A' if (rk or 99) <= 24 else ('B' if (rk or 99) <= 48 else 'C')
    if pos == 'TE':
        return 'A' if (rk or 99) <= 12 else 'B'
    return 'A' if (tkl or 0) >= 100 else 'B'


ROOKIE_QB = {1: 13.3, 2: 7.2, 3: 7.2}          # por ronda draft NFL; 4+: 5.1


def eg_de(pos, rk_pg, rk_tot, tkl, les, viejo, EG):
    FINO, GRUESO, POR, _ = EG
    alias = NVPOS.get(pos, pos)
    for p in ([alias] if isinstance(alias, str) else alias):
        k = (p, _tier(p, rk_pg, tkl), les)
        if k in FINO:
            return 17 * (1 - FINO[k])
    for p in ([alias] if isinstance(alias, str) else alias):
        k = (p, _tier(p, rk_tot, tkl), 'v' if viejo else 'j')
        if k in GRUESO:
            return 17 * (1 - GRUESO[k])
    for p in ([alias] if isinstance(alias, str) else alias):
        if p in POR:
            return 17 * (1 - POR[p])
    return 16.0


def proyectar_v2():
    todos = json.load(open(RAIZ / 'data' / 'espn_applied_2025.json'))
    items = cargar_reglas()
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    EG = tabla_eg(con)
    xw = {int(e): (b, dy, dr) for e, b, dy, dr in con.execute(
        "select espn_id, birthdate, draft_year, draft_round from xwalk_ids_nflverse "
        "where espn_id is not null").fetchall()}
    # 2025 real por posición bajo NUESTRAS reglas: total, juegos, tacleadas
    prev = {}
    for pw in todos:
        p = pw['player']
        for s in p.get('stats') or []:
            if (s.get('seasonId'), s.get('statSourceId'), s.get('statSplitTypeId')) == (2025, 0, 0):
                raw = s.get('stats') or {}
                g25 = raw.get('210', raw.get(210)) or 0
                tkl25 = raw.get('109', raw.get(109)) or 0
                prev[p['id']] = (s.get('appliedTotal', 0), g25, tkl25)
    rk25_tot, rk25_pg = {}, {}
    from collections import defaultdict
    porpos = defaultdict(list)
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if pos and p['id'] in prev:
            tot, g25, _ = prev[p['id']]
            porpos[pos].append((tot, tot / g25 if g25 >= 8 else 0, p['id']))
    for pos, lst in porpos.items():
        for i, (_, _, pid) in enumerate(sorted(lst, key=lambda x: -x[0])):
            rk25_tot[pid] = i + 1
        for i, (_, _, pid) in enumerate(sorted(lst, key=lambda x: -x[1])):
            rk25_pg[pid] = i + 1
    out = []
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if not pos:
            continue
        ent = [s for s in (p.get('stats') or [])
               if (s.get('seasonId'), s.get('statSourceId'), s.get('statSplitTypeId')) == (2026, 1, 0)]
        if not ent:
            continue
        raw = ent[0].get('stats') or {}
        tot_mkt = puntos(raw, p.get('defaultPositionId'), items)
        if tot_mkt <= 0:
            continue
        g_proj = raw.get('210', raw.get(210)) or 17
        pg = tot_mkt / g_proj
        bd, dy, dr = xw.get(p['id'], (None, None, None))
        edad = 2026 - int(str(bd)[:4]) if bd else None
        CORTO = EG[3]
        tot25, g25, tkl25 = prev.get(p['id'], (0, 0, 0))
        if pos == 'DST':
            eg = 17.0
        elif g25 >= 8:
            les = 'les' if g25 <= 13 else 'ok'
            eg = eg_de(pos, rk25_pg.get(p['id']), rk25_tot.get(p['id']),
                       tkl25, les, (edad or 0) >= 29, EG)
        elif 1 <= g25 < 8 and pos in CORTO and \
                tot25 / g25 >= (15 if pos == 'QB' else 8):
            eg = 17 * (1 - CORTO[pos])       # jugó poco siendo titular: celda propia
        elif dy == 2026 and pos == 'QB':
            eg = ROOKIE_QB.get(dr or 9, 5.1)
        else:
            # sin 2025 útil: celda B sana de su posición
            eg = eg_de(pos, 999, 999, 0, 'ok', (edad or 0) >= 29, EG)
        # diagnóstico de celda (para la capa de distribuciones)
        if pos == 'DST':
            celda = 'dst'
        elif g25 >= 8:
            celda = ('fino', pos, _tier(pos, rk25_pg.get(p['id']), tkl25),
                     'les' if g25 <= 13 else 'ok')
        elif 1 <= g25 < 8 and pos in EG[3] and tot25 / g25 >= (15 if pos == 'QB' else 8):
            celda = ('corto', pos)
        else:
            celda = ('fallback', pos)
        out.append(dict(nombre=p['fullName'], pos=pos, espn_id=p['id'], edad=edad,
                        proj_mercado=round(tot_mkt, 1), g_proj=g_proj,
                        pg=round(pg, 2), eg=round(eg, 1),
                        total_v2=round(pg * eg, 1), celda=celda))
    return out


def vbd2(proys):
    porpos = {}
    for r in proys:
        porpos.setdefault(r['pos'], []).append(r)
    todos = []
    for pos, lst in porpos.items():
        n = BASE.get(pos)
        if not n or len(lst) < 2:
            continue
        lst.sort(key=lambda r: -r['pg'])
        pg_base = lst[min(n, len(lst)) - 1]['pg']
        for i, r in enumerate(lst):
            r['rank_pos'] = i + 1
            r['vbd2'] = round(r['eg'] * (r['pg'] - pg_base), 1)
        todos += lst
    todos.sort(key=lambda r: -r['vbd2'])
    return todos


if __name__ == '__main__':
    import csv
    rk = vbd2(proyectar_v2())
    with open(RAIZ / 'data' / 'vbd_v2.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['nombre', 'pos', 'rank_pos', 'edad',
                                          'proj_mercado', 'g_proj', 'pg', 'eg',
                                          'total_v2', 'vbd2', 'espn_id'])
        w.writeheader()
        for r in rk:
            w.writerow({k: r.get(k) for k in w.fieldnames})
    print(f"jugadores: {len(rk)}  ->  data/vbd_v2.csv")
    print(f"{'#':>3} {'jugador':24}{'pos':>4}{'edad':>5}{'pg':>7}{'E[g]':>6}{'tot_v2':>8}{'VBD2':>7}")
    for i, r in enumerate(rk[:40]):
        print(f"{i+1:>3} {r['nombre'][:24]:24}{r['pos']:>4}{str(r['edad'] or '?'):>5}"
              f"{r['pg']:>7}{r['eg']:>6}{r['total_v2']:>8}{r['vbd2']:>7}")
