"""Proyección v2 — overlay de PARTIDOS JUGADOS sobre la base de mercado.

Sesgo del mercado MEDIDO (19-ago, corpus 2026): ~100% de los jugadores
relevantes proyectados a 17 juegos (statId 210). Realidad 2021-2025
(nflverse): élite ~14 juegos, P(16+) ~50%.

Factor VALIDADO por walk-forward (2023/24/25, n=675): predecir total con
per-juego × E[g|pos,tier,edad] reduce el MAE 21.9% vs per-juego × 17,
mejora consistente los 3 años.

Modelo de valor: mientras tu titular juega ganas su ventaja sobre el
reemplazo; cuando falta, alineas reemplazo (neto ~0 vs baseline). →
    VBD2 = E[g] × (pts_por_juego − pts_por_juego_del_baseline)
Como el scoring es LINEAL en los crudos, pts_por_juego = total_mercado /
g_proyectados, exacto.

SUPUESTOS DECLARADOS:
- S4: eficiencia por-juego del mercado insesgada (sin archivo histórico de
  proyecciones no es testeable; solo corregimos el componente PROBADO
  sesgado: los juegos).
- S5: E[g] por (posición, tier producción previa, edad≥29). Tier desde el
  2025 REAL del corpus bajo NUESTRAS reglas. Rookies sin NFL 2025: QB por
  ronda de draft (R1 13.3 / R2-3 7.2 / R4+ 5.1), resto media rookie de su
  posición. Sin datos → tier B joven.
- S6: D/ST sin ajuste (no se lesiona); K default 16 si no hay data.
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
    """E[g] por (pos_nflverse, tier, edad) con TODO 2021-2025 (método ya
    validado walk-forward; el modelo final usa la muestra completa)."""
    rows = con.execute("""
    with juegos as (
      select player_id, position, season, count(distinct week) g,
             sum(coalesce(fantasy_points_ppr,0)) fp,
             sum(coalesce(def_tackles_solo,0)+coalesce(def_tackle_assists,0)) tkl
      from fact_player_week where season_type='REG' group by 1,2,3),
    rel as (select *, lag(g) over w g_prev, lag(fp) over w fp_prev,
                   lag(tkl) over w tkl_prev
            from juegos window w as (partition by player_id order by season)),
    t as (select r.*, rank() over (partition by r.position, r.season
                                   order by r.fp_prev desc) rk_prev, x.birthdate
          from rel r left join xwalk_ids_nflverse x on r.player_id=x.gsis_id
          where r.g_prev >= 8)
    select position, g, rk_prev, tkl_prev,
           case when birthdate is null then null
                else season - year(birthdate::date) end edad
    from t where season between 2022 and 2025
    """).fetchall()
    from collections import defaultdict
    acc = defaultdict(list)
    for pos, g, rk, tkl, edad in rows:
        acc[(pos, _tier(pos, rk, tkl), 'v' if (edad or 0) >= 29 else 'j')].append(g)
    return {k: sum(v) / len(v) for k, v in acc.items() if len(v) >= 8}


def _tier(pos, rk, tkl):
    if pos == 'QB':
        return 'A' if (rk or 99) <= 12 else 'B'
    if pos in ('RB', 'WR'):
        return 'A' if (rk or 99) <= 24 else ('B' if (rk or 99) <= 48 else 'C')
    if pos == 'TE':
        return 'A' if (rk or 99) <= 12 else 'B'
    return 'A' if (tkl or 0) >= 100 else 'B'


ROOKIE_QB = {1: 13.3, 2: 7.2, 3: 7.2}          # por ronda draft NFL; 4+: 5.1


def eg_de(pos, tier, viejo, EG):
    for p in ([pos] if isinstance(NVPOS.get(pos, pos), str) else NVPOS[pos]):
        k = (p if isinstance(p, str) else p, tier, 'v' if viejo else 'j')
        if k in EG:
            return EG[k]
    # fallback: mismo pos sin edad, luego default posicional
    for p in ([pos] if isinstance(NVPOS.get(pos, pos), str) else NVPOS[pos]):
        for e in ('j', 'v'):
            if (p, tier, e) in EG:
                return EG[(p, tier, e)]
    return 16.0 if pos == 'K' else 14.0


def proyectar_v2():
    todos = json.load(open(RAIZ / 'data' / 'espn_applied_2025.json'))
    items = cargar_reglas()
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    EG = tabla_eg(con)
    xw = {int(e): (b, dy, dr) for e, b, dy, dr in con.execute(
        "select espn_id, birthdate, draft_year, draft_round from xwalk_ids_nflverse "
        "where espn_id is not null").fetchall()}
    # rank 2025 real por posición bajo NUESTRAS reglas (para el tier)
    prev = {}
    for pw in todos:
        p = pw['player']
        for s in p.get('stats') or []:
            if (s.get('seasonId'), s.get('statSourceId'), s.get('statSplitTypeId')) == (2025, 0, 0):
                raw = s.get('stats') or {}
                g25 = raw.get('210', raw.get(210)) or 0
                prev[p['id']] = (s.get('appliedTotal', 0), g25)
    rk25 = {}
    from collections import defaultdict
    porpos = defaultdict(list)
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if pos and p['id'] in prev:
            porpos[pos].append((prev[p['id']][0], p['id']))
    for pos, lst in porpos.items():
        for i, (_, pid) in enumerate(sorted(lst, reverse=True)):
            rk25[pid] = i + 1
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
        if pos == 'DST':
            eg = 17.0
        elif p['id'] in prev and prev[p['id']][1] >= 8:
            eg = eg_de(pos, _tier(pos, rk25.get(p['id']), None) if pos in
                       ('QB', 'RB', 'WR', 'TE') else _tier(pos, None, prev[p['id']][0] / 2.5),
                       (edad or 0) >= 29, EG)
        elif dy == 2026 and pos == 'QB':
            eg = ROOKIE_QB.get(dr or 9, 5.1)
        else:
            eg = eg_de(pos, 'B', (edad or 0) >= 29, EG)
        out.append(dict(nombre=p['fullName'], pos=pos, espn_id=p['id'], edad=edad,
                        proj_mercado=round(tot_mkt, 1), g_proj=g_proj,
                        pg=round(pg, 2), eg=round(eg, 1),
                        total_v2=round(pg * eg, 1)))
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
