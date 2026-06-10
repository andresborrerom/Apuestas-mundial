#!/usr/bin/env python3
"""
LEMAITRE — clasificación de grupos (Monte Carlo CONJUNTO).

Mejora sobre la primera versión:
  - Simula los 12 grupos a la vez (mismo índice de sim) para poder rankear los
    12 TERCEROS y elegir los 8 mejores correctamente (formato 2026).
  - Usa las distribuciones REALES sin sesgo (el sesgo a gol=1 de CSC NO se usa
    aquí: la clasificación va de RESULTADOS, no de optimizar un pago de goles).
  - Desempate de grupo por (puntos, dif. de gol, goles a favor).

    python pollas/LEMAITRE/clasificacion.py --mock /tmp/wc_grupos.json
"""

import argparse
import json
import os
import sys
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api
from pollas.CSC.cupos import matriz_de_evento


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=20000)
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))

    partidos = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if c["cuotas_1x2"]:
            partidos.append((c["home"], c["away"],
                             matriz_de_evento(c, "proporcional", 2.5)))

    # equipos y grupos (por rivales)
    opp = defaultdict(set)
    for h, a, _ in partidos:
        opp[h].add(a); opp[a].add(h)
    grupos, vistos = [], set()
    for t in opp:
        if t in vistos:
            continue
        g = frozenset({t} | opp[t])
        if len(g) == 4 and not (g & vistos):
            grupos.append(sorted(g)); vistos |= g
    grupos.sort()
    teams = sorted(vistos); tid = {t: i for i, t in enumerate(teams)}
    NT, S = len(teams), args.sims

    # simular TODOS los partidos a la vez
    rng = np.random.default_rng(0)
    pts = np.zeros((NT, S)); gd = np.zeros((NT, S)); gf = np.zeros((NT, S))
    for h, a, M in partidos:
        fl = M.ravel() / M.sum()
        k = rng.choice(fl.size, size=S, p=fl)
        gh, ga = k // M.shape[1], k % M.shape[1]
        ih, ia = tid[h], tid[a]
        pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[ih] += gh - ga; gd[ia] += ga - gh; gf[ih] += gh; gf[ia] += ga

    clave = pts * 1e6 + gd * 1e3 + gf + rng.random((NT, S)) * 1e-3

    # posición dentro de cada grupo + capturar el 3º de cada grupo por sim
    Ppos = {}                      # team -> [P1,P2,P3,P4]
    tercer_key = np.zeros((12, S)) # clave del 3º de cada grupo
    tercer_tid = np.zeros((12, S), dtype=int)
    for gi, g in enumerate(grupos):
        ids = [tid[t] for t in g]
        sub = clave[ids]                       # (4,S)
        orden = np.argsort(-sub, axis=0)       # (4,S) índices locales por puesto
        for local, t in enumerate(g):
            Ppos[t] = [float(np.mean(orden[pos] == local)) for pos in range(4)]
        loc3 = orden[2]                        # local del 3º por sim
        tercer_tid[gi] = np.array(ids)[loc3]
        tercer_key[gi] = sub[loc3, np.arange(S)]

    # mejores 8 terceros: por sim, rankear los 12 terceros, top 8 avanzan
    avanza3 = np.zeros(NT)
    orden3 = np.argsort(-tercer_key, axis=0)   # (12,S) grupos ordenados
    for s in range(S):
        for gi in orden3[:8, s]:
            avanza3[tercer_tid[gi, s]] += 1
    Pavanza3 = avanza3 / S

    GRP = "ABCDEFGHIJKL"
    print(f"{len(grupos)} grupos · {len(partidos)} partidos · {S} sims "
          f"(SIN sesgo de goles)\n")
    for gi, g in enumerate(grupos):
        print(f"Grupo (auto {GRP[gi]}):")
        for t in sorted(g, key=lambda t: -Ppos[t][0]):
            p = Ppos[t]
            extra = f" · 3º-avanza {Pavanza3[tid[t]]*100:3.0f}%" if p[2] > 0.15 else ""
            print(f"   {t[:16]:16}  1º:{p[0]*100:3.0f}% 2º:{p[1]*100:3.0f}% "
                  f"3º:{p[2]*100:3.0f}% 4º:{p[3]*100:3.0f}%  (clasif top2 {(p[0]+p[1])*100:3.0f}%){extra}")

    print("\n8 MEJORES TERCEROS más probables (P de avanzar como 3º):")
    for t in sorted(teams, key=lambda t: -Pavanza3[tid[t]])[:8]:
        print(f"   {t:18} {Pavanza3[tid[t]]*100:4.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
