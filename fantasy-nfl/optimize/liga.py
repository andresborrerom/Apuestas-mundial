"""SIMULADOR DE LIGA COMPLETA — 16 equipos, 14 titulares, 18 rondas.

Reemplaza a `backtest_liga.py` (que solo tenía los 7 slots ofensivos y por eso
declaraba el sesgo "las victorias tienen más azar del que deberían"). Aquí
está el roster v3 entero:

    QB · RB · WR · WR · TE · flex(RB/WR) · OP(QB/RB/WR/TE)      7 ofensivos
    DT · DE · LB · CB · S · D/ST · K                            7 no ofensivos
    + 4 de banca                                               = 18 rondas

Fuentes de cada pieza — y qué tan buena es cada una (medido, no supuesto):

  OFENSIVA   tablero = ECR superflex real de ese año, condicionado a NUESTRO
             reglamento con la curva posicional. Medido contra puntos reales:
             r = +0.71 a nivel jugador, +0.28 a nivel roster. Es el mejor
             tablero histórico disponible.
  IDP        no existe ECR ni ADP público de IDP. Único insumo posible: los
             puntos del año anterior bajo nuestras reglas.
             ⚠️ SUPUESTO S-IDP declarado. Estabilidad año-a-año MEDIDA:
                DT 0.52 · DE 0.50 · LB 0.58 · CB 0.53 · S 0.46
             (comparar: ofensiva 0.61-0.69). Es peor insumo que el ofensivo.
  K / D/ST   mismo insumo, y es CASI INÚTIL: estabilidad K 0.27, D/ST 0.18.
             Hallazgo con consecuencia directa en el draft: el año anterior no
             dice casi nada de un pateador ni de una defensa. Se toman al
             final porque no hay forma de saber, no por costumbre.

  RIVALES    cada asiento con su personalidad medida (sesgo y ruido contra el
             mercado) + obligación de llenar los slots obligatorios, que es lo
             que genera la corrida tardía de K/DST. 16×7 = 112 picks no
             ofensivos obligatorios sobre 288: la sala NO puede dejarlos todos
             para el final.

  TEMPORADA  14 semanas H2H con calendario aleatorio + playoffs de 8 + la
             planilla real de premios.

CANDADO (optimize/calibrar_liga.py): antes de sacar cualquier conclusión, la
simulación tiene que reproducir lo que se observa en la historia REAL de la
liga (PF por equipo, dispersión, y cuándo se toma cada posición).
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
import numpy as np
from model.scoring import cargar_reglas, puntos
from model.scoring_nflverse import semanas
from model.scoring_kdst import kicker_semanas, dst_semanas
from model.posiciones import POSID, posiciones_desde_db
from optimize.managers import personalidades

RAIZ = Path(__file__).resolve().parent.parent
ECR_PARQUET = ('/tmp/claude-0/-home-user-Apuestas-mundial/'
               'd76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/ecr.parquet')
PAGINA = '/nfl/rankings/ppr-superflex-cheatsheets.php'

SEMANAS_REG = 14
OFE = ('QB', 'RB', 'WR', 'TE')
IDP = ('DT', 'DE', 'LB', 'CB', 'S')
TODAS = OFE + IDP + ('DST', 'K')

SLOTS_2026 = [('QB',), ('RB',), ('WR',), ('WR',), ('TE',), ('RB', 'WR'),
              ('QB', 'RB', 'WR', 'TE'),
              ('DT',), ('DE',), ('LB',), ('CB',), ('S',), ('DST',), ('K',)]
# La app vieja (NFL.com, 2021-2025) tenía 3 slots defensivos, no 5. Para
# comparar contra los drafts reales hay que simular ESA configuración.
SLOTS_NFLCOM = [('QB',), ('RB',), ('RB',), ('WR',), ('WR',), ('TE',),
                ('QB', 'RB', 'WR', 'TE'),
                ('DT', 'DE'), ('LB',), ('CB', 'S'), ('DST',), ('K',)]

# Línea base de VBD = el titular semanal marginal de la liga (optimize/vbd.py,
# baselines de la estructura real con 16 equipos y el slot OP).
BASE = {'QB': 30, 'RB': 26, 'WR': 38, 'TE': 17, 'DT': 17, 'DE': 17, 'LB': 17,
        'CB': 17, 'S': 17, 'DST': 17, 'K': 17}
# Cuántos de cada posición le sirven a un equipo (titulares + banca sana)
MAX_POS = {'QB': 3, 'RB': 5, 'WR': 5, 'TE': 2, 'DT': 2, 'DE': 2, 'LB': 2,
           'CB': 2, 'S': 2, 'DST': 1, 'K': 1}
MIN_POS = {'QB': 1, 'RB': 1, 'WR': 2, 'TE': 1, 'DT': 1, 'DE': 1, 'LB': 1,
           'CB': 1, 'S': 1, 'DST': 1, 'K': 1}


class Config:
    """Configuración de UNA liga. Por defecto, la nuestra de 2026."""

    def __init__(self, equipos=16, rondas=18, mi_asiento=4, slots=None,
                 min_pos=None, max_pos=None, base=None):
        self.equipos, self.rondas, self.mi_asiento = equipos, rondas, mi_asiento
        self.slots = slots or SLOTS_2026
        self.min_pos = dict(min_pos or MIN_POS)
        self.max_pos = dict(max_pos or MAX_POS)
        self.base = dict(base or BASE)

    @staticmethod
    def nflcom(equipos, rondas):
        """La liga como se jugó en NFL.com: 3 slots defensivos, no 5."""
        return Config(equipos=equipos, rondas=rondas, slots=SLOTS_NFLCOM,
                      min_pos={'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'LB': 1,
                               'DST': 1, 'K': 1},
                      max_pos={'QB': 3, 'RB': 6, 'WR': 6, 'TE': 2, 'DT': 2,
                               'DE': 2, 'LB': 2, 'CB': 2, 'S': 2, 'DST': 1,
                               'K': 1},
                      base=dict(BASE, QB=int(equipos*1.9), RB=int(equipos*2.2),
                                WR=int(equipos*2.4), TE=equipos + 1))


CFG = Config()

PREMIOS_STANDINGS = {1: 1610, 2: 900, 3: 700, 4: 550, 5: 400, 6: 325, 7: 275, 8: 200}
PREMIOS_PLAYOFF = {1: 1200, 2: 600, 3: 350, 4: 250}
POR_VICTORIA, HIGH_SCORE, DFL = 20, 50, -200


def orden_snake(cfg=CFG):
    out = []
    for r in range(cfg.rondas):
        out += (list(range(cfg.equipos)) if r % 2 == 0
                else list(reversed(range(cfg.equipos))))
    return out


# --------------------------------------------------------------- PUNTOS REALES
def puntos_semanales(con, año, items, pos_map):
    """{clave: {semana: puntos}} y {clave: (nombre, pos)} para TODAS las posiciones.

    La clave es el gsis_id para jugadores y la abreviatura del equipo para las
    D/ST (no comparten espacio de identificadores, así que no chocan)."""
    pts = defaultdict(dict)
    meta = {}
    W, mw = semanas(año, año)
    for (pid, y, wk), raw in W.items():
        p = pos_map.get(pid)
        if not p or p[0] not in OFE + IDP:
            continue
        pts[pid][wk] = puntos({str(k): v for k, v in raw.items()}, POSID[p[0]], items)
        meta[pid] = (mw[(pid, y, wk)][0], p[0])
    Wk, mk = kicker_semanas(con, año, año)
    for (pid, y, wk), raw in Wk.items():
        pts[pid][wk] = puntos({str(k): v for k, v in raw.items()}, 5, items)
        meta[pid] = (mk[(pid, y, wk)][0], 'K')
    Wd, md = dst_semanas(con, año, año)
    for (eq, y, wk), raw in Wd.items():
        pts[eq][wk] = puntos({str(k): v for k, v in raw.items()}, 16, items)
        meta[eq] = (md[(eq, y, wk)][0], 'DST')
    return pts, meta


def curvas_posicionales(pts_por_año, excluir):
    """Puntos del k-ésimo mejor de cada posición, promediados sobre las OTRAS
    temporadas. Sirve para traducir un rank de mercado a puntos de NUESTRO
    reglamento (corrección de Andrés: un ECR hecho con TD de pase a 4 ordena
    QB vs WR distinto al nuestro con 6)."""
    porpos = defaultdict(lambda: defaultdict(list))
    for y, (pts, meta) in pts_por_año.items():
        if y == excluir:
            continue
        for k, semanas_ in pts.items():
            porpos[meta[k][1]][y].append(sum(semanas_.values()))
    curva = {}
    for pos, años in porpos.items():
        listas = [sorted(v, reverse=True) for v in años.values()]
        n = min(len(l) for l in listas)
        curva[pos] = [sum(l[i] for l in listas) / len(listas) for i in range(n)]
    return curva


# -------------------------------------------------------------------- UNIVERSO
def universo(con, año, items, pts_por_año, n_ofe=200, cfg=CFG):
    """Devuelve (jugadores, valor_vbd, rank_mercado, pts_semanales).

    jugadores = [(clave, nombre, pos)] · el pool del que se draftea.
    """
    pts, meta = pts_por_año[año]
    prev = pts_por_año.get(año - 1)
    curva = curvas_posicionales(pts_por_año, excluir=año)

    # --- OFENSIVA: ECR real de ese año, condicionado a nuestro reglamento
    ecr = con.execute(f"""
        select x.gsis_id, e.player, e.pos, e.ecr
        from read_parquet('{ECR_PARQUET}') e
        join xwalk_ids_nflverse x on cast(e.id as double) = x.fantasypros_id
        where e.fp_page='{PAGINA}' and x.gsis_id is not null
          and e.scrape_date=(select max(scrape_date) from read_parquet('{ECR_PARQUET}')
              where fp_page='{PAGINA}' and year(cast(scrape_date as date))={año}
                and cast(scrape_date as date) < date '{año}-09-10')
        order by e.ecr""").fetchall()
    jug, valor = [], {}
    vistos, porpos = set(), defaultdict(int)
    for g, nom, p, r in ecr:
        if g not in pts or g in vistos:
            continue
        pos = meta[g][1]
        if pos not in OFE:
            continue
        k = porpos[pos]; porpos[pos] += 1
        c = curva.get(pos, [0])
        valor[g] = c[min(k, len(c) - 1)]
        jug.append((g, nom, pos)); vistos.add(g)
        if len(jug) >= n_ofe:
            break
    # Garantía de profundidad: con 16 equipos y 2 TE por roster, un universo
    # con 19 TE (2023) dejaba a un equipo sin poder llenar el slot. Se completa
    # cada posición ofensiva hasta equipos+6 siguiendo el mismo orden del ECR.
    faltantes = {p: cfg.equipos + 6 - porpos[p] for p in OFE
                 if porpos[p] < cfg.equipos + 6}
    if faltantes:
        for g, nom, p, r in ecr:
            if not faltantes:
                break
            if g in vistos or g not in pts or meta[g][1] not in faltantes:
                continue
            pos = meta[g][1]
            c = curva.get(pos, [0])
            valor[g] = c[min(porpos[pos], len(c) - 1)]
            porpos[pos] += 1
            jug.append((g, nom, pos)); vistos.add(g)
            faltantes[pos] -= 1
            if faltantes[pos] <= 0:
                del faltantes[pos]

    # --- IDP / K / D/ST: no hay mercado público. Único insumo: el año anterior.
    #     ⚠️ SUPUESTO S-IDP. Estabilidad medida: IDP ~0.5, K 0.27, D/ST 0.18.
    if prev:
        pprev, mprev = prev
        for pos in IDP + ('DST', 'K'):
            cands = [(sum(v.values()), k) for k, v in pprev.items()
                     if mprev[k][1] == pos and k in pts]
            cands.sort(reverse=True)
            cupo = ({'DST': 20, 'K': 20}.get(pos, 34)
                    if cfg.equipos <= 16 else 40)
            c = curva.get(pos, [0])
            for i, (_, k) in enumerate(cands[:cupo]):
                if k in vistos:
                    continue
                valor[k] = c[min(i, len(c) - 1)]
                jug.append((k, meta[k][0], pos)); vistos.add(k)

    # --- NUESTRO tablero: a VBD con las líneas base de la estructura real
    pp = defaultdict(list)
    for k, nom, pos in jug:
        pp[pos].append(valor[k])
    bl = {}
    for pos, l in pp.items():
        l.sort(reverse=True)
        bl[pos] = l[min(cfg.base[pos], len(l)) - 1]
    vbd = {k: valor[k] - bl[pos] for k, nom, pos in jug}

    # --- EL TABLERO DEL RIVAL NO ES EL NUESTRO. 🚨 Corrección 28-ago: yo tenía
    # a los rivales picando por nuestro VBD y salían 25 QB y dos pateadores
    # dentro de los 112 primeros picks. La sala real toma K en la ronda 13 y
    # los IDP en la 14-15: NO usan VBD, van por el mercado ofensivo y cubren
    # las casillas defensivas cuando la aritmética los obliga.
    #   ofensiva      -> orden del ECR real (el mercado que ellos ven)
    #   no ofensiva   -> nunca por gusto: sólo cuando el forzado la exige,
    #                    y ahí por el mejor de esa posición.
    # Esto NO es una comodidad: es de dónde sale nuestra ventaja. Si la sala
    # ignora a los IDP hasta el final y bajo nuestras reglas un LB vale ~290
    # puntos, tomarlos antes tiene precio medible.
    orden_ofe = [j for j in jug if j[2] in OFE]
    rank = {j[0]: i for i, j in enumerate(orden_ofe)}     # ya venían por ECR
    resto = sorted([j for j in jug if j[2] not in OFE], key=lambda j: -vbd[j[0]])
    for i, j in enumerate(resto):
        rank[j[0]] = 10_000 + i          # inalcanzable salvo por obligación
    return jug, vbd, rank, pts


# ----------------------------------------------------------------------- DRAFT
def draftear(jug, val, politica, personas, rng, rank, cfg=CFG, antic=None):
    antic = antic if antic is not None else [1] * cfg.equipos
    vivos = {k: (nom, pos) for k, nom, pos in jug}
    rosters = [[] for _ in range(cfg.equipos)]
    cnt = [defaultdict(int) for _ in range(cfg.equipos)]
    sec = orden_snake(cfg)
    mis = [i for i, t in enumerate(sec) if t == cfg.mi_asiento]

    def elegibles(t, antic=1):
        """`antic` = con cuántas rondas de anticipación empieza este asiento a
        cubrir sus casillas obligatorias. Medido por asiento, no inventado:
        sale de la avidez de IDP de cada manager en sus drafts reales."""
        faltan = sum(max(0, cfg.min_pos[p] - cnt[t][p]) for p in cfg.min_pos)
        quedan = cfg.rondas - len(rosters[t])
        forz = faltan >= quedan - antic
        out = []
        for k, (nom, pos) in vivos.items():
            if cnt[t][pos] >= cfg.max_pos.get(pos, 0):
                continue
            if forz and cnt[t][pos] >= cfg.min_pos.get(pos, 0):
                continue
            out.append(k)
        if not out:      # nada respeta la restricción: relajarla
            out = [k for k, (nom, pos) in vivos.items()
                   if cnt[t][pos] < cfg.max_pos.get(pos, 0)]
        return out

    for gp, t in enumerate(sec):
        el = elegibles(t, 0 if t == cfg.mi_asiento else antic[t]) or list(vivos)
        if not el:
            break
        if t == cfg.mi_asiento:
            k = politica(el, vivos, val, cnt[t], rosters[t], gp, mis, rank)
        else:
            sesgo, ruido = personas[t]
            k = min(el, key=lambda k: rank[k] + sesgo + rng.normal(0, ruido))
        pos = vivos[k][1]
        rosters[t].append((k, pos)); cnt[t][pos] += 1
        del vivos[k]
    return rosters


def alinear(jugadores, val, cfg=CFG):
    """Mejor alineación posible según un diccionario de valores."""
    disp = sorted(jugadores, key=lambda j: -val.get(j[0], 0))
    usados, tot = set(), 0.0
    for slot in cfg.slots:
        for k, pos in disp:
            if k not in usados and pos in slot:
                usados.add(k); tot += val.get(k, 0); break
    return tot


def valor_roster(jugadores, val, delta=0.0, cfg=CFG):
    """Alineación titular + delta × banca (la banca cubre byes y lesiones)."""
    disp = sorted(jugadores, key=lambda j: -val.get(j[0], 0))
    usados, tot = set(), 0.0
    for slot in cfg.slots:
        for k, pos in disp:
            if k not in usados and pos in slot:
                usados.add(k); tot += val.get(k, 0); break
    # ⚠️ con VBD la banca suele ser NEGATIVA; se pisa en 0 para que `delta`
    # signifique "cuánto suma la profundidad", no "cuánto resta".
    banca = sum(max(0.0, val.get(k, 0)) for k, pos in jugadores if k not in usados)
    return tot + delta * banca


def puntos_reales(ros, pts, semanas_reg=SEMANAS_REG, cfg=CFG):
    tot = 0.0
    for wk in range(1, semanas_reg + 1):
        v = {k: pts.get(k, {}).get(wk, 0.0) for k, pos in ros}
        tot += alinear(ros, v, cfg)
    return tot


# ------------------------------------------------------------------- TEMPORADA
def temporada(rosters, pts, rng, cfg=CFG):
    E = cfg.equipos
    sem = np.zeros((E, 18))
    for t, ros in enumerate(rosters):
        for wk in range(1, 18):
            v = {k: pts.get(k, {}).get(wk, 0.0) for k, pos in ros}
            sem[t, wk] = alinear(ros, v, cfg)
    idx = list(range(E)); rng.shuffle(idx)
    jornadas = []
    for r in range(E - 1):
        rot = [idx[0]] + idx[1:][r:] + idx[1:][:r]
        jornadas.append([(rot[i], rot[E - 1 - i]) for i in range(E // 2)])
    rng.shuffle(jornadas)
    vic = np.zeros(E)
    pf = sem[:, 1:SEMANAS_REG + 1].sum(axis=1)
    dinero = np.zeros(E)
    for wk, jor in enumerate(jornadas[:SEMANAS_REG], 1):
        for a, b in jor:
            if sem[a, wk] > sem[b, wk]: vic[a] += 1
            elif sem[b, wk] > sem[a, wk]: vic[b] += 1
            else: vic[a] += 0.5; vic[b] += 0.5
        dinero[int(np.argmax(sem[:, wk]))] += HIGH_SCORE
    dinero += vic * POR_VICTORIA
    orden = sorted(range(E), key=lambda t: (-vic[t], -pf[t]))
    for puesto, t in enumerate(orden, 1):
        dinero[t] += PREMIOS_STANDINGS.get(puesto, 0)
    dinero[orden[-1]] += DFL
    vivos = orden[:8]
    perdedores = []
    for wk in (SEMANAS_REG + 1, SEMANAS_REG + 2, SEMANAS_REG + 3):
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
    return dinero, puesto, pf, vic, (vivos[0] if vivos else None)


def cargar_todo(y0=2020, y1=2025, db=None):
    """{año: (pts_semanales, meta)} para todas las posiciones."""
    con = duckdb.connect(str(db or RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    items = cargar_reglas()
    pos_map = posiciones_desde_db(con, y0, y1)
    out = {}
    for y in range(y0, y1 + 1):
        out[y] = puntos_semanales(con, y, items, pos_map)
    return con, items, out
