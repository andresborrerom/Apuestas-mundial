"""FASE B — drafts históricos completos, calificados con lo que REALMENTE pasó.

Diseñado con Andrés (28-ago). Por cada temporada 2021-2025:

  1. DRAFT: 16 equipos, 9 rondas, solo ofensiva (QB/RB/WR/TE). Los rivales
     pican por el ECR superflex REAL de ese año, cada uno con SU personalidad
     medida (sesgo y ruido contra el mercado, de sus drafts históricos).
     Yo pico con la POLÍTICA que se está probando, sobre el TABLERO que se
     está probando.
  2. TEMPORADA: 14 semanas de enfrentamientos cara a cara con calendario
     aleatorio (round-robin barajado). Cada semana, cada equipo alinea lo
     mejor que tenga — con información posterior, igual para todos: es una
     medida de POTENCIAL del roster, no de habilidad para alinear.
  3. PLAYOFFS: 8 equipos, siembra por récord (desempate: puntos a favor),
     tres rondas de una semana con re-siembra.
  4. DINERO: la planilla real de premios de la liga.

Métrica principal: DINERO esperado y distribución del puesto final. No
puntos totales — como dijo Andrés, "no es al que más puntos haga sino al que
más partidos gane".

⚠️ SESGO DECLARADO: sin IDP/K/DST los puntajes semanales son más bajos y
parejos que en la liga real, así que las victorias tienen más azar. Si las
políticas salen indistinguibles, puede ser esto y no la verdad.
   Medido (28-ago): los 7 slots ofensivos son ~71% de los puntos de la liga
   y los 5 IDP ~29%. Los ~1400 pts/equipo de esta simulación (7 slots, 14
   semanas) reconcilian con los 2258-2585 de PF real 2025 al agregar IDP+K+
   DST y las 17 semanas. La simulación NO está baja por un bug: le faltan
   slots a propósito.

🚨 CORRECCIÓN 28-ago — QUÉ TABLERO USAR. Medido sobre el universo de 260
jugadores que de verdad se draftean, contra puntos reales (2021-2025):

    tablero                        jugador r     ROSTER r
    ESPN pretemporada + reglas       +0.750       +0.335   (solo 2025)
    mercado ECR (curva condicionada) +0.706       +0.280
    mío (proxy: ppg del año pasado)  +0.639       +0.040

El tablero `mio`/`hibrido` de este archivo es un PROXY reconstruido (puntos
por juego del año anterior × E[juegos]) porque no existen proyecciones ESPN
archivadas de 2021-2024. Ese proxy NO predice el resultado de un roster.
El default pasa a `mercado`. El tablero real del 7-sep (optimize/vbd.py) usa
proyección ESPN de pretemporada re-puntuada con nuestras reglas — el que
mide mejor — y por eso este defecto NO contamina el draft.
"""
import argparse, csv, json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
import numpy as np
from model.scoring import cargar_reglas, puntos
from model.scoring_nflverse import semanas, temporadas, POSID
from optimize.managers import personalidades

RAIZ = Path(__file__).resolve().parent.parent
ECR_PARQUET = ('/tmp/claude-0/-home-user-Apuestas-mundial/'
               'd76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/ecr.parquet')
PAGINA = '/nfl/rankings/ppr-superflex-cheatsheets.php'
OFE = ('QB', 'RB', 'WR', 'TE')
EQUIPOS, RONDAS, MI_ASIENTO = 16, 9, 4        # asiento 5 (0-indexado)
SEMANAS_REG = 14
# titulares ofensivos de la liga: QB, RB, WR, WR, TE, flex(RB/WR), OP(cualquiera)
SLOTS = [('QB',), ('RB',), ('WR',), ('WR',), ('TE',), ('RB', 'WR'),
         ('QB', 'RB', 'WR', 'TE')]
MAX_POS = {'QB': 3, 'RB': 4, 'WR': 4, 'TE': 2}
MIN_POS = {'QB': 1, 'RB': 1, 'WR': 2, 'TE': 1}
PREMIOS_STANDINGS = {1: 1610, 2: 900, 3: 700, 4: 550, 5: 400, 6: 325, 7: 275, 8: 200}
PREMIOS_PLAYOFF = {1: 1200, 2: 600, 3: 350, 4: 250}
POR_VICTORIA, HIGH_SCORE = 20, 50


def orden_snake():
    out = []
    for r in range(RONDAS):
        out += list(range(EQUIPOS)) if r % 2 == 0 else list(reversed(range(EQUIPOS)))
    return out


def curvas_posicionales(T, items, excluir):
    """Puntos reales del k-ésimo mejor de cada posición, promediados sobre las
    temporadas DISTINTAS a la que se está probando. Sirve para condicionar el
    ranking del mercado a NUESTRO reglamento (corrección de Andrés: un ECR
    hecho con TD de pase a 4 ordena QB vs WR distinto al nuestro con 6)."""
    porpos = defaultdict(lambda: defaultdict(list))
    for (pid, y), (nom, pos, raw) in T.items():
        if pos in OFE and y != excluir:
            porpos[pos][y].append(puntos({str(k): v for k, v in raw.items()},
                                         POSID[pos], items))
    curva = {}
    for pos, años in porpos.items():
        listas = [sorted(v, reverse=True) for v in años.values()]
        n = min(len(l) for l in listas)
        curva[pos] = [sum(l[i] for l in listas) / len(listas) for i in range(n)]
    return curva


def cargar_anio(con, año, items, T):
    """Universo del año: ECR de mercado, puntos semanales reales y tableros."""
    ecr = con.execute(f"""
        select x.gsis_id, e.player, e.pos, e.ecr
        from read_parquet('{ECR_PARQUET}') e
        join xwalk_ids_nflverse x on cast(e.id as double) = x.fantasypros_id
        where e.fp_page='{PAGINA}' and x.gsis_id is not null
          and e.scrape_date=(select max(scrape_date) from read_parquet('{ECR_PARQUET}')
              where fp_page='{PAGINA}' and year(cast(scrape_date as date))={año}
                and cast(scrape_date as date) < date '{año}-09-10')
        order by e.ecr""").fetchall()
    W, meta = semanas(año, año)
    pts_sem = defaultdict(dict)
    for (pid, y, wk), raw in W.items():
        pos = meta[(pid, y, wk)][1]
        if pos in OFE and wk <= 17:
            pts_sem[pid][wk] = puntos({str(k): v for k, v in raw.items()},
                                      POSID[pos], items)
    # universo: los del ECR que existen en la temporada
    univ = [(g, n, p, r) for g, n, p, r in ecr if g in pts_sem][:260]
    # --- TABLERO MERCADO condicionado a nuestro reglamento
    curva = curvas_posicionales(T, items, excluir=año)
    porpos = defaultdict(int)
    val_mk = {}
    for g, n, p, r in univ:
        k = porpos[p]; porpos[p] += 1
        c = curva.get(p, [0])
        val_mk[g] = c[min(k, len(c) - 1)]
    # --- TABLERO MÍO: proyección con datos de año-1 (puntos por juego × E[g])
    prev = {}
    for (pid, y), (nom, pos, raw) in T.items():
        if y == año - 1 and pos in OFE and raw.get(210, 0) >= 8:
            pts = puntos({str(k): v for k, v in raw.items()}, POSID[pos], items)
            prev[pid] = (pos, pts / raw[210], raw[210])
    val_mio, val_hib = {}, {}
    sg = 17 if año - 1 >= 2021 else 16
    for g, n, p, r in univ:
        if g in prev:
            _, pg, gj = prev[g]
            frac = 0.88 if gj > sg - 4 else 0.72
            val_mio[g] = pg * 17 * frac
        val_hib[g] = val_mio.get(g, val_mk[g])
    # ⚠️ Los tableros deben estar en VBD, no en puntos crudos: en crudos el QB
    # domina y una política greedy acumula QBs que no puede alinear (el mismo
    # sesgo que ya nos había engañado en la Fase A). Línea base = titulares
    # semanales de la liga por posición (16 equipos).
    TITULARES = {'QB': 21, 'RB': 26, 'WR': 42, 'TE': 18}

    def a_vbd(v):
        pp = defaultdict(list)
        for g, x in v.items():
            pp[dict((gg, p) for gg, n, p, r in univ)[g]].append(x)
        bl = {}
        for pos, l in pp.items():
            l.sort(reverse=True)
            bl[pos] = l[min(TITULARES[pos], len(l)) - 1]
        posde = dict((gg, p) for gg, n, p, r in univ)
        return {g: x - bl[posde[g]] for g, x in v.items()}

    return univ, pts_sem, {'mercado': a_vbd(val_mk), 'mio': a_vbd(val_mio),
                           'hibrido': a_vbd(val_hib)}


def valor_alineacion(jugadores, val):
    """Mejor alineación posible (7 slots) según un diccionario de valores."""
    disp = sorted(jugadores, key=lambda j: -val.get(j[0], 0))
    usados, tot = set(), 0.0
    for slot in SLOTS:
        for g, pos in disp:
            if g not in usados and pos in slot:
                usados.add(g); tot += val.get(g, 0); break
    return tot


def draftear(univ, val, politica, personas, rng, ecr_rank):
    """Un draft completo. Devuelve la lista de rosters (16 listas de (gsis,pos))."""
    vivos = {g: (n, p) for g, n, p, r in univ}
    rosters = [[] for _ in range(EQUIPOS)]
    cnt = [defaultdict(int) for _ in range(EQUIPOS)]
    sec = orden_snake()
    mis_picks = [i for i, t in enumerate(sec) if t == MI_ASIENTO]

    def elegibles(t):
        faltan = sum(max(0, MIN_POS[p] - cnt[t][p]) for p in MIN_POS)
        quedan = RONDAS - len(rosters[t])
        forz = faltan >= quedan
        out = []
        for g, (n, p) in vivos.items():
            if cnt[t][p] >= MAX_POS[p]:
                continue
            if forz and cnt[t][p] >= MIN_POS[p]:
                continue
            out.append(g)
        return out

    for gp, t in enumerate(sec):
        el = elegibles(t)
        if not el:
            el = list(vivos)
        if t == MI_ASIENTO:
            g = politica(el, vivos, val, cnt[t], rosters[t], gp, mis_picks, ecr_rank)
        else:
            sesgo, ruido = personas[t]
            g = min(el, key=lambda g: ecr_rank[g] + sesgo + rng.normal(0, ruido))
        pos = vivos[g][1]
        rosters[t].append((g, pos)); cnt[t][pos] += 1
        del vivos[g]
    return rosters


def temporada_liga(rosters, pts_sem, rng):
    """14 semanas H2H + playoffs. Devuelve dinero y puesto por equipo."""
    # puntos semanales de cada equipo con su mejor alineación (info posterior)
    sem = np.zeros((EQUIPOS, 18))
    for t, ros in enumerate(rosters):
        for wk in range(1, 18):
            val = {g: pts_sem[g].get(wk, 0.0) for g, p in ros}
            sem[t, wk] = valor_alineacion(ros, val)
    # calendario: round-robin barajado, 14 de las 15 jornadas
    idx = list(range(EQUIPOS)); rng.shuffle(idx)
    jornadas = []
    for r in range(EQUIPOS - 1):
        rot = [idx[0]] + idx[1:][r:] + idx[1:][:r]
        jornadas.append([(rot[i], rot[EQUIPOS - 1 - i]) for i in range(EQUIPOS // 2)])
    rng.shuffle(jornadas)
    vic = np.zeros(EQUIPOS); pf = sem[:, 1:SEMANAS_REG + 1].sum(axis=1)
    dinero = np.zeros(EQUIPOS)
    for wk, jor in enumerate(jornadas[:SEMANAS_REG], 1):
        for a, b in jor:
            if sem[a, wk] > sem[b, wk]: vic[a] += 1
            elif sem[b, wk] > sem[a, wk]: vic[b] += 1
            else: vic[a] += 0.5; vic[b] += 0.5
        dinero[int(np.argmax(sem[:, wk]))] += HIGH_SCORE
    dinero += vic * POR_VICTORIA
    orden = sorted(range(EQUIPOS), key=lambda t: (-vic[t], -pf[t]))
    for puesto, t in enumerate(orden, 1):
        dinero[t] += PREMIOS_STANDINGS.get(puesto, 0)
    # playoffs: 8 equipos, 3 rondas de 1 semana, con re-siembra
    vivos = orden[:8]
    ronda_wk = [SEMANAS_REG + 1, SEMANAS_REG + 2, SEMANAS_REG + 3]
    perdedores = []
    for wk in ronda_wk:
        if len(vivos) == 1:
            break
        vivos = sorted(vivos, key=lambda t: orden.index(t))
        nxt, out = [], []
        for i in range(len(vivos) // 2):
            a, b = vivos[i], vivos[len(vivos) - 1 - i]
            gana, pierde = (a, b) if sem[a, wk] >= sem[b, wk] else (b, a)
            nxt.append(gana); out.append(pierde)
        perdedores.append(out); vivos = nxt
    if vivos:
        dinero[vivos[0]] += PREMIOS_PLAYOFF[1]
        if perdedores:
            dinero[perdedores[-1][0]] += PREMIOS_PLAYOFF[2]
        if len(perdedores) >= 2:
            for t in perdedores[-2][:2]:
                dinero[t] += (PREMIOS_PLAYOFF[3] + PREMIOS_PLAYOFF[4]) / 2
    puesto = {t: i + 1 for i, t in enumerate(orden)}
    campeon = vivos[0] if vivos else None
    return dinero, puesto, pf, vic, campeon


# ---------------------------------------------------------------------------
# POLÍTICAS (todas reciben el mismo tablero `val`; lo que cambia es CÓMO deciden)
SIGMA_SUP = 22.0     # dispersión efectiva para la supervivencia analítica


def _surv(r, pick):
    """P(un jugador de rank de mercado r siga vivo en el pick global `pick`)."""
    from math import erf, sqrt
    return 0.5 * (1 + erf(((r - pick) / SIGMA_SUP) / sqrt(2)))


def _mejor_por_pos(el, vivos, val):
    d = defaultdict(list)
    for g in el:
        d[vivos[g][1]].append(g)
    for p in d:
        d[p].sort(key=lambda g: -val.get(g, 0))
    return d


def pol_greedy(el, vivos, val, cnt, roster, gp, mis, ecr_rank):
    return max(el, key=lambda g: val.get(g, 0))


def pol_motor(el, vivos, val, cnt, roster, gp, mis, ecr_rank):
    """Ganancia marginal a UN turno: valor ahora − E[valor en mi próximo pick]."""
    sig = next((p for p in mis if p > gp), None)
    if sig is None:
        return pol_greedy(el, vivos, val, cnt, roster, gp, mis, ecr_rank)
    mejor, mejor_g = None, -1e18
    for p, gs in _mejor_por_pos(el, vivos, val).items():
        ahora = val.get(gs[0], 0)
        luego, q = 0.0, 1.0
        for g in gs[:25]:
            s = _surv(ecr_rank[g], sig)
            luego += val.get(g, 0) * s * q
            q *= (1 - s)
            if q < 1e-3:
                break
        if ahora - luego > mejor_g:
            mejor, mejor_g = gs[0], ahora - luego
    return mejor


def pol_regla(el, vivos, val, cnt, roster, gp, mis, ecr_rank):
    """Versión sin escala de la regla validada para 2026: R1 el mejor WR;
    R2 un QB si el mejor QB vivo vale al menos tanto como el mejor WR vivo."""
    k = len([1 for p in mis if p < gp])
    d = _mejor_por_pos(el, vivos, val)
    if k == 0 and d.get('WR'):
        return d['WR'][0]
    if k == 1:
        qb, wr = d.get('QB'), d.get('WR')
        if qb and (not wr or val.get(qb[0], 0) >= val.get(wr[0], 0)):
            return qb[0]
        if wr:
            return wr[0]
    return pol_motor(el, vivos, val, cnt, roster, gp, mis, ecr_rank)


def pol_nomiope(el, vivos, val, cnt, roster, gp, mis, ecr_rank, rollouts=10, cand=5):
    """Para cada candidato simula TODO el resto del draft y se queda con el que
    termina con mejor alineación proyectada. Mira hasta el final, no un turno.

    ⚠️ La CONTINUACIÓN de cada simulación usa el MOTOR, no greedy. Un rollout
    vale lo que valga su política de continuación: con greedy (que resultó ser
    la peor) evaluaba todos los futuros con un jugador tonto y por eso perdía
    contra el motor en la primera corrida."""
    if not [p for p in mis if p > gp]:
        return pol_greedy(el, vivos, val, cnt, roster, gp, mis, ecr_rank)
    cands = sorted(el, key=lambda g: -val.get(g, 0))[:cand]
    for p, gs in _mejor_por_pos(el, vivos, val).items():
        if gs and gs[0] not in cands:
            cands.append(gs[0])
    rng = np.random.default_rng(gp * 7919 + 13)
    mejor, mejor_v = None, -1e18
    for c in cands:
        tot = 0.0
        for _ in range(rollouts):
            vv = dict(vivos); vv.pop(c, None)
            mi = list(roster) + [(c, vivos[c][1])]
            cc = defaultdict(int)
            for _g, _p in mi:
                cc[_p] += 1
            for pk in range(gp + 1, EQUIPOS * RONDAS):
                if not vv:
                    break
                if pk in mis:
                    faltan = sum(max(0, MIN_POS[p] - cc[p]) for p in MIN_POS)
                    quedan = RONDAS - len(mi)
                    ok = [g for g in vv if cc[vv[g][1]] < MAX_POS[vv[g][1]]
                          and (faltan < quedan or cc[vv[g][1]] < MIN_POS[vv[g][1]])]
                    if not ok:
                        continue
                    g = pol_motor(ok, vv, val, cc, mi, pk, mis, ecr_rank)
                    mi.append((g, vv[g][1])); cc[vv[g][1]] += 1
                else:
                    g = min(vv, key=lambda g: ecr_rank[g] + rng.normal(0, 20))
                vv.pop(g, None)
            tot += valor_alineacion(mi, val)
        if tot / rollouts > mejor_v:
            mejor, mejor_v = c, tot / rollouts
    return mejor


POLITICAS = {'greedy': pol_greedy, 'motor': pol_motor, 'regla': pol_regla,
             'no-miope': pol_nomiope}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=100)
    ap.add_argument('--anios', default='2021,2022,2023,2024,2025')
    ap.add_argument('--tableros', default='mercado')   # ver 🚨 del encabezado
    ap.add_argument('--politicas', default='greedy,motor,regla,no-miope')
    a = ap.parse_args()
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    items = cargar_reglas()
    print('cargando temporadas reales...', flush=True)
    T = temporadas(2019, 2025)
    personas = personalidades()
    res = defaultdict(lambda: defaultdict(list))
    for anio in [int(x) for x in a.anios.split(',')]:
        univ, pts_sem, tableros = cargar_anio(con, anio, items, T)
        ecr_rank = {g: i for i, (g, n, p, r) in enumerate(univ)}
        print(f"\n=== {anio} · universo {len(univ)} jugadores ===", flush=True)
        for tb in a.tableros.split(','):
            val = tableros[tb]
            for pol in a.politicas.split(','):
                fn = POLITICAS[pol]
                for s in range(a.sims):
                    rng = np.random.default_rng(1000 + s)      # PAREADO
                    rosters = draftear(univ, val, fn, personas, rng, ecr_rank)
                    dinero, puesto, pf, vic, camp = temporada_liga(
                        rosters, pts_sem, np.random.default_rng(5000 + s))
                    k = f'{tb}/{pol}'
                    res[k]['dinero'].append(dinero[MI_ASIENTO])
                    res[k]['puesto'].append(puesto[MI_ASIENTO])
                    res[k]['vic'].append(vic[MI_ASIENTO])
                    res[k]['campeon'].append(1 if camp == MI_ASIENTO else 0)
                d = res[f'{tb}/{pol}']
                print(f"  {tb}/{pol:9} E[$]={np.mean(d['dinero']):>7.0f}"
                      f" · puesto {np.mean(d['puesto']):>4.1f}"
                      f" · vict {np.mean(d['vic']):>4.1f}"
                      f" · top8 {np.mean([p<=8 for p in d['puesto']])*100:>3.0f}%"
                      f" · campeon {np.mean(d['campeon'])*100:>3.0f}%", flush=True)
    print("\n===== AGREGADO =====")
    print(f"  {'tablero/politica':22}{'E[$]':>9}{'sd':>8}{'puesto':>8}{'top8':>7}"
          f"{'campeon':>9}{'p10 $':>8}{'p90 $':>8}")
    for k, d in sorted(res.items(), key=lambda kv: -np.mean(kv[1]['dinero'])):
        print(f"  {k:22}{np.mean(d['dinero']):>9.0f}{np.std(d['dinero']):>8.0f}"
              f"{np.mean(d['puesto']):>8.1f}{np.mean([p<=8 for p in d['puesto']])*100:>6.0f}%"
              f"{np.mean(d['campeon'])*100:>8.0f}%"
              f"{np.percentile(d['dinero'],10):>8.0f}{np.percentile(d['dinero'],90):>8.0f}")


def valor_roster(jugadores, val, delta=0.0):
    """Valor de un roster = ALINEACIÓN TITULAR + delta × la banca.

    Corrección de Andrés (28-ago): "no pienses solo en titular, dale un valor
    a la banca que te puede dar trades, lesiones, bye weeks y demás". Un
    tercer QB vale cero para la alineación proyectada y sin embargo cubre el
    bye y la lesión del titular — sin este término las políticas construían
    rosters sin profundidad. `delta` NO se inventa: se calibra midiendo qué
    peso predice mejor los puntos REALES (ver calibrar_delta)."""
    disp = sorted(jugadores, key=lambda j: -val.get(j[0], 0))
    usados, tot = set(), 0.0
    for slot in SLOTS:
        for g, pos in disp:
            if g not in usados and pos in slot:
                usados.add(g); tot += val.get(g, 0); break
    banca = sum(val.get(g, 0) for g, pos in jugadores if g not in usados)
    return tot + delta * banca


def puntos_reales_roster(ros, pts_sem, semanas_reg=SEMANAS_REG):
    """Puntos REALES de un roster: cada semana su mejor alineación posible."""
    tot = 0.0
    for wk in range(1, semanas_reg + 1):
        v = {g: pts_sem[g].get(wk, 0.0) for g, p in ros}
        tot += valor_alineacion(ros, v)
    return tot


def calibrar_delta(univ, pts_sem, val, personas, ecr_rank, n=60, deltas=None):
    """¿Cuánto vale la banca? Se mide: se generan rosters variados, se calcula
    su valor proyectado con distintos deltas y se ve cuál correlaciona mejor
    con los PUNTOS REALES que produjeron."""
    deltas = deltas or [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]
    rosters = []
    for s in range(n):
        rng = np.random.default_rng(9000 + s)
        pol = POLITICAS[['greedy', 'motor', 'regla'][s % 3]]
        rs = draftear(univ, val, pol, personas, rng, ecr_rank)
        for t in range(EQUIPOS):
            rosters.append(rs[t])
    reales = np.array([puntos_reales_roster(r, pts_sem) for r in rosters])
    out = {}
    for d in deltas:
        proy = np.array([valor_roster(r, val, d) for r in rosters])
        out[d] = float(np.corrcoef(proy, reales)[0, 1])
    return out, len(rosters)
