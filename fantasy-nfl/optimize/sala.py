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
EQUIPOS = 16
RONDAS = 18                     # 14 titulares + 4 banca (IR no se draftea)
MI_PICK = 5                     # sorteo 27-ago: Pocho = 5
ORDEN = ['Ferchos', 'Jaime', 'Nich', 'Luisca', 'POCHO', 'Diego', 'Santi A',
         'Sergio', 'Brian', 'Rodrigo', 'Gabriel', 'SteveO', 'Esguerra',
         'Kike', 'James B', 'Santi Gut']
# cuántos de cada posición son ÚTILES para un equipo (titulares + banca sana)
MAX_UTIL = {'QB': 3, 'RB': 5, 'WR': 5, 'TE': 2, 'DT': 2, 'DE': 2, 'LB': 2,
            'CB': 2, 'S': 2, 'DST': 1, 'K': 1}
OBLIG = {'QB': 2, 'RB': 2, 'WR': 2, 'TE': 1, 'DT': 1, 'DE': 1, 'LB': 1,
         'CB': 1, 'S': 1, 'DST': 1, 'K': 1}    # QB2 = el slot OP


def orden_snake():
    """Lista de (pick_global, indice_equipo)."""
    out = []
    for r in range(RONDAS):
        seq = range(EQUIPOS) if r % 2 == 0 else reversed(range(EQUIPOS))
        for t in seq:
            out.append(t)
    return out


def cargar():
    dist = {r['nombre']: r for r in csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv'))}
    todos = json.load(open(RAIZ / 'data' / 'espn_applied_2025.json'))
    adp = {}
    for pw in todos:
        p = pw['player']
        o = p.get('ownership') or {}
        a = o.get('averageDraftPosition')
        if a and a > 0:
            adp[p['fullName']] = a
    jug = []
    for n, r in dist.items():
        if r['pos'] == 'DB':
            continue
        jug.append(dict(nombre=n, pos=r['pos'], vbd=float(r['vbd2']),
                        proj=float(r['total_v2']), p10=float(r['p10']),
                        p50=float(r['p50']), p90=float(r['p90']),
                        adp=adp.get(n)))
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


def valor_roster(roster, campo='vbd'):
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
