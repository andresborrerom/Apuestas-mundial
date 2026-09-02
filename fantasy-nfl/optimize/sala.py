"""Simulador de SALA + optimizador del draft (16 equipos, snake, pick 5).

Modelo de la sala (declarado, no inventado):
- Tablero del rival = lo que VE en la app ESPN: mezcla de ADP (mercado) y
  PROYECCIÓN puntuada con las reglas de la liga (la app la muestra). Los
  IDP no tienen ADP → van por proyección pura, que es justo lo que hace
  que la sala los tome tarde (proyectan menos que los ofensivos... salvo
  bajo NUESTRAS reglas de tackles).
- Necesidad por slot: nadie draftea 2 K; y al final se fuerza el llenado
  de slots obligatorios (esto genera solo la corrida tardía de DST/K/IDP).
- Ruido humano Gumbel(σ): reaches y caídas.
- Estructura clave MEDIDA: 14 titulares de los cuales 7 son IDP/DST/K.
  16×7 = 112 picks obligatorios no-ofensivos de 288 totales; las rondas
  13-18 solo dan 96 → la sala NO puede dejar todo para el final.

Mi política: greedy con LOOKAHEAD — en cada pick mío elijo la posición
que maximiza VBD2(mejor disponible ahora) − E[VBD2(mejor disponible en mi
próximo turno)], estimando la supervivencia por Monte Carlo de la sala.

Uso: python fantasy-nfl/optimize/sala.py [--sims 300]
"""
import argparse, csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
import os
# ── SELECTOR DE LIGA (1-sep): LIGA=cs → Fantasy Cheap-Sheet (draft 2-sep).
# Default: Peace and Love. El pick propio en cs se pasa por env LIGA_PICK.
LIGA = os.environ.get('LIGA', 'pl')
if LIGA == 'cs':
    EQUIPOS = 14
    RONDAS = 14                 # 10 titulares + 4 banca
    MI_PICK = int(os.environ.get('LIGA_PICK', '1'))   # pickOrder: team 1 = yo
else:
    EQUIPOS = 16
    RONDAS = 18                 # 14 titulares + 4 banca (IR no se draftea)
    MI_PICK = 5                 # sorteo 27-ago: Pocho = 5
ORDEN = ['Ferchos', 'Jaime', 'Nich', 'Luisca', 'POCHO', 'Diego', 'Santi A',
         'Sergio', 'Brian', 'Rodrigo', 'Gabriel', 'SteveO', 'Esguerra',
         'Kike', 'James B', 'Santi Gut']
# cuántos de cada posición son ÚTILES para un equipo (titulares + banca sana)
# Cuántos de cada posición son ÚTILES *para la sala* (titulares + banca sana).
MAX_UTIL = {'QB': 3, 'RB': 5, 'WR': 5, 'TE': 2, 'DT': 2, 'DE': 2, 'LB': 2,
            'CB': 2, 'S': 2, 'DST': 1, 'K': 1}
# 🔒 REGLA DE ANDRÉS (28-ago): "un IDP por posición. No quiero IDP en mi banca
# nunca." Vale para MI equipo, no para los rivales — ellos siguen haciendo lo
# que hacen. No es una preferencia contra los datos: el backtest de 4
# temporadas × 300 simulaciones mostró que las políticas que ganan toman
# exactamente 1.0 de cada IDP y meten la profundidad en RB/WR, y que la que se
# llena de IDP (greedy, 1.7-2.0 por posición) es la peor de todas por lejos
# (−$469 por temporada, t = −16.8). La regla y la medición coinciden.
MAX_UTIL_MIO = dict(MAX_UTIL, DT=1, DE=1, LB=1, CB=1, S=1)
if LIGA == 'cs':                # sin IDP; banca ofensiva
    MAX_UTIL = {'QB': 2, 'RB': 7, 'WR': 7, 'TE': 2, 'DST': 1, 'K': 1}
    MAX_UTIL_MIO = dict(MAX_UTIL)
# ✅ VERIFICADO en eligibleSlots: el slot 7 (OP) admite QB/RB/WR/TE — NO es un
# superflex que obligue a un 2º QB. Mínimos duros por posición + un mínimo de
# 7 ofensivos totales (QB, RB, WR×2, TE, flex RB/WR y OP).
OBLIG = {'QB': 1, 'RB': 1, 'WR': 2, 'TE': 1, 'DT': 1, 'DE': 1, 'LB': 1,
         'CB': 1, 'S': 1, 'DST': 1, 'K': 1}
# 🔒 GUARDARRAÍL QB≥2 (1-sep, OK de Andrés: "sano para el piso"): en superflex
# un roster con UN QB tiene margen ~0 si ese QB cae y el modelo de temporada
# no cobra ese riesgo. Solo para MI asiento; entra a la aritmética de forzado
# como cualquier casilla obligatoria (el motor lo toma por valor cuando
# quiere; esto solo garantiza que nunca salga con 1).
OBLIG_MIO = dict(OBLIG, QB=2)
OFE = ('QB', 'RB', 'WR', 'TE')
OFE_MIN = 7
if LIGA == 'cs':
    OBLIG = {'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'DST': 1, 'K': 1}
    OBLIG_MIO = dict(OBLIG, QB=2)       # guardarraíl QB>=2 también aquí
    OFE_MIN = 12                        # 14 rondas − DST − K


def orden_snake():
    """Lista de (pick_global, indice_equipo)."""
    out = []
    for r in range(RONDAS):
        seq = range(EQUIPOS) if r % 2 == 0 else reversed(range(EQUIPOS))
        for t in seq:
            out.append(t)
    return out


def cargar_cs():
    """Pool Cheap-Sheet: proyección FRESCA puntuada por ESPN bajo SUS reglas
    (optimize/cheapsheet.py). Lesión ya aplicada allí; DST vale 0 (real)."""
    byes = {}
    for r in csv.DictReader(open(RAIZ / 'data' / 'archivo' / '2026-08-28' /
                                 'ffc_2qb_adp.csv')):
        if r.get('bye'):
            byes[r['name']] = int(r['bye'])
    adp = {}
    for pw in json.load(open(RAIZ / 'data' / 'espn_applied_2025.json')):
        p = pw['player']
        a = (p.get('ownership') or {}).get('averageDraftPosition')
        if a and a > 0:
            adp[p['id']] = a
    jug = []
    for r in csv.DictReader(open(RAIZ / 'data' / 'cheapsheet_tablero.csv')):
        pid = int(r['espn_id'])
        pr = float(r['proj'])
        jug.append(dict(nombre=r['nombre'], pos=r['pos'], vbd=float(r['vbd']),
                        proj=pr, p10=float(r['p10']) if r['p10'] else pr * .6,
                        p50=pr, p90=float(r['p90']) if r['p90'] else pr * 1.4,
                        espn_id=pid, adp=adp.get(pid),
                        bye=byes.get(r['nombre'], 0)))
    con_adp = sorted([j for j in jug if j['adp']], key=lambda j: j['adp'])
    for i, j in enumerate(con_adp):
        j['rk_adp'] = i + 1
    for j in jug:
        j.setdefault('rk_adp', None)
    porpos = {}
    for j in jug:
        porpos.setdefault(j['pos'], []).append(j)
    for lst in porpos.values():
        lst.sort(key=lambda j: -j['proj'])
        for i, j in enumerate(lst):
            j['rk_pos_proj'] = i + 1
    for i, j in enumerate(sorted(jug, key=lambda j: -j['proj'])):
        j['rk_proj'] = i + 1
    return jug


def cargar():
    if LIGA == 'cs':
        return cargar_cs()
    """⚠️ Se une por espn_id, NUNCA por nombre: el corpus tiene 8 homónimos
    (Justin Jefferson WR/LB, Lamar Jackson QB/CB, Chris Jones DT/CB...) y
    indexar por nombre sobreescribía el ADP del bueno con el del homónimo
    (Jefferson 12.2 -> 170.5), volviéndolos invisibles para la sala."""
    dist = list(csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv')))
    todos = json.load(open(RAIZ / 'data' / 'espn_applied_2025.json'))
    adp = {}
    for pw in todos:
        p = pw['player']
        a = (p.get('ownership') or {}).get('averageDraftPosition')
        if a and a > 0:
            adp[p['id']] = a
    # semana de bye por nombre (FFC; ofensiva — IDP/K/DST quedan en 0 y el
    # desempate de byes simplemente no les aplica)
    byes = {}
    for r in csv.DictReader(open(RAIZ / 'data' / 'archivo' / '2026-08-28' /
                                 'ffc_2qb_adp.csv')):
        if r.get('bye'):
            byes[r['name']] = int(r['bye'])
    jug = []
    for r in dist:
        if r['pos'] == 'DB':
            continue
        pid = int(r['espn_id'])
        jug.append(dict(nombre=r['nombre'], pos=r['pos'], vbd=float(r['vbd2']),
                        proj=float(r['total_v2']), p10=float(r['p10']),
                        p50=float(r['p50']), p90=float(r['p90']),
                        espn_id=pid, adp=adp.get(pid),
                        bye=byes.get(r['nombre'], 0)))
    # 🚑 RECORTE POR LESIÓN VIVA (1-sep, lo cazó Andrés con Charbonnet: OUT
    # en la API y aun así el motor lo tomaba de titular R7). El estado viene
    # de data/injury_vivo.json (ingest/lesiones.py — refrescar antes de usar).
    # Factores = fracción esperada de temporada disponible; ⚠️ SUPUESTO con
    # ficha en el Libro (rango declarado, sensibilidad abajo):
    #   OUT (PUP/semanas)  ×0.55 · INJURY_RESERVE ×0.30 · SUSPENSION ×0.65
    #   DOUBTFUL ×0.90 · QUESTIONABLE/DAY_TO_DAY sin recorte (ruido de agosto)
    REC = {'OUT': 0.55, 'INJURY_RESERVE': 0.30, 'SUSPENSION': 0.65,
           'DOUBTFUL': 0.90}
    try:
        inj = json.load(open(RAIZ / 'data' / 'injury_vivo.json'))
    except Exception:
        inj = {}
    for j in jug:
        st = (inj.get(str(j['espn_id'])) or {}).get('inj')
        f = REC.get(st)
        if f:
            j['vbd'] -= j['proj'] * (1 - f)     # vbd cae lo que caen los puntos
            for c in ('proj', 'p10', 'p50', 'p90'):
                j[c] *= f
            j['inj'] = st
    # tablero de la sala: rank por ADP donde existe; los demás por proyección
    con_adp = sorted([j for j in jug if j['adp']], key=lambda j: j['adp'])
    for i, j in enumerate(con_adp):
        j['rk_adp'] = i + 1
    sin_adp = [j for j in jug if not j['adp']]
    porpos = {}
    for j in jug:
        porpos.setdefault(j['pos'], []).append(j)
    for pos, lst in porpos.items():
        lst.sort(key=lambda j: -j['proj'])
        for i, j in enumerate(lst):
            j['rk_pos_proj'] = i + 1
    # rank global por proyección (lo que muestra la app)
    for i, j in enumerate(sorted(jug, key=lambda j: -j['proj'])):
        j['rk_proj'] = i + 1
    for j in sin_adp:
        j['rk_adp'] = None
    return jug


def score_sala(j, alpha):
    """Menor = antes lo toma la sala. Mezcla ADP (mercado) y proyección (app)."""
    rp = j['rk_proj']
    ra = j['rk_adp'] if j['rk_adp'] else rp * 1.6 + 40   # sin ADP: castigo
    return alpha * ra + (1 - alpha) * rp


def simular(jug, mi_policy, rng, alpha=0.55, sigma=12.0, mi_equipo=MI_PICK - 1,
            registrar=None):
    disp = {j['nombre']: j for j in jug}
    base = {n: score_sala(j, alpha) for n, j in disp.items()}
    rosters = [dict() for _ in range(EQUIPOS)]
    picks = orden_snake()
    mis_picks = []
    for gp, t in enumerate(picks, 1):
        ronda = (gp - 1) // EQUIPOS + 1
        if t == mi_equipo:
            elegido = mi_policy(disp, rosters[t], ronda, gp, rng)
            mis_picks.append((gp, ronda, elegido))
        else:
            elegido = pick_rival(disp, base, rosters[t], ronda, rng, sigma)
        if elegido is None:
            continue
        rosters[t][elegido['nombre']] = elegido
        del disp[elegido['nombre']]
        if registrar is not None:
            registrar.append((gp, t, elegido['nombre'], elegido['pos']))
    return rosters, mis_picks


def pick_rival(disp, base, roster, ronda, rng, sigma):
    cnt = {}
    for j in roster.values():
        cnt[j['pos']] = cnt.get(j['pos'], 0) + 1
    faltan_oblig = sum(max(0, OBLIG[p] - cnt.get(p, 0)) for p in OBLIG)
    quedan = RONDAS - len(roster)
    forzado = faltan_oblig >= quedan            # ya no cabe: llenar obligatorios
    mejor, mejor_s = None, 1e18
    for n, j in disp.items():
        p = j['pos']
        if cnt.get(p, 0) >= MAX_UTIL.get(p, 3):
            continue
        if forzado and cnt.get(p, 0) >= OBLIG.get(p, 0):
            continue
        s = base[n] + rng.gumbel(0, sigma)
        # la sala no toma K/DST temprano (medido: K ronda ~13)
        if p in ('K', 'DST') and ronda < 11:
            s += 400
        if s < mejor_s:
            mejor, mejor_s = j, s
    return mejor


def slots_libres(roster):
    """Titulares que faltan por cubrir (QB, RB, RBWR×2, WR, TE, OP, IDP...)."""
    cnt = {}
    for j in roster.values():
        cnt[j['pos']] = cnt.get(j['pos'], 0) + 1
    need = {}
    for p, k in OBLIG.items():
        need[p] = max(0, k - cnt.get(p, 0))
    # los 2 flex RB/WR
    flex = max(0, 2 - max(0, cnt.get('RB', 0) - 1) - max(0, cnt.get('WR', 0) - 1))
    return need, flex, cnt


def valor_roster_cs(roster, campo='vbd'):
    porpos = {}
    for j in roster.values():
        porpos.setdefault(j['pos'], []).append(j)
    for v in porpos.values():
        v.sort(key=lambda j: -j[campo])
    tot, usados = 0.0, set()
    for p, k in (('QB', 1), ('RB', 2), ('WR', 2), ('TE', 1), ('DST', 1), ('K', 1)):
        for j in porpos.get(p, [])[:k]:
            tot += j[campo]; usados.add(j['nombre'])
    def libres(poss):
        return sorted((j for p in poss for j in porpos.get(p, [])
                       if j['nombre'] not in usados), key=lambda j: -j[campo])
    for j in libres(('RB', 'WR'))[:1]:                    # flex RB/WR
        tot += j[campo]; usados.add(j['nombre'])
    for j in libres(('RB', 'WR', 'TE'))[:1]:              # FLEX RB/WR/TE
        tot += j[campo]; usados.add(j['nombre'])
    return tot


def valor_roster(roster, campo='vbd'):
    if LIGA == 'cs':
        return valor_roster_cs(roster, campo)
    """Σ del mejor titular posible (14 slots). Asignación por JUGADOR (no por
    valor: los empates rompían la exclusión). Slots dedicados → OP (pool
    QB/RB/WR/TE, el mayor) → 2 flex RB/WR; greedy del pool mayor al menor es
    óptimo porque flex ⊂ OP."""
    porpos = {}
    for j in roster.values():
        porpos.setdefault(j['pos'], []).append(j)
    for v in porpos.values():
        v.sort(key=lambda j: -j[campo])
    tot, usados = 0.0, set()
    # roster v3 (19-ago): WR lleva DOS slots dedicados y el flex bajó a UNO
    for p, k in (('QB', 1), ('RB', 1), ('WR', 2), ('TE', 1), ('DT', 1), ('DE', 1),
                 ('LB', 1), ('CB', 1), ('S', 1), ('DST', 1), ('K', 1)):
        for j in porpos.get(p, [])[:k]:
            tot += j[campo]; usados.add(j['nombre'])
    def libres(poss):
        return sorted((j for p in poss for j in porpos.get(p, [])
                       if j['nombre'] not in usados), key=lambda j: -j[campo])
    for j in libres(('QB', 'RB', 'WR', 'TE'))[:1]:        # OP (superflex)
        tot += j[campo]; usados.add(j['nombre'])
    for j in libres(('RB', 'WR'))[:1]:                    # 1 flex RB/WR
        tot += j[campo]; usados.add(j['nombre'])
    return tot


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=200)
    args = ap.parse_args()
    jug = cargar()
    print(f'universo: {len(jug)} jugadores · mi pick: {MI_PICK} ({ORDEN[MI_PICK-1]})')
    mis = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
    print('mis picks globales:', mis)
