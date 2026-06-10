#!/usr/bin/env python3
"""
LEMAITRE — clasificación de grupos (Monte Carlo).

La polla LEMAITRE puntúa sobre todo PREDECIR QUIÉN CLASIFICA y en qué ORDEN
(no marcadores de grupos). Esto simula cada grupo (round-robin de 6 partidos)
miles de veces usando nuestros modelos de partido, y devuelve:
  - P(cada equipo termine 1º/2º/3º/4º) en su grupo,
  - el orden más probable por grupo,
  - los 8 mejores terceros (para la fase de 32).

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


def detectar_grupos(partidos):
    """Agrupa equipos por sus rivales (cada equipo juega a los otros 3 del grupo)."""
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
    return grupos


def simular_grupo(equipos, partidos_idx, partidos, S, rng):
    """Devuelve matriz P[equipo, posición] (4x4) para un grupo."""
    idx = {e: i for i, e in enumerate(equipos)}
    pts = np.zeros((4, S)); gd = np.zeros((4, S)); gf = np.zeros((4, S))
    for h, a, M in [partidos[k] for k in partidos_idx]:
        flat = M.ravel() / M.sum()
        k = rng.choice(flat.size, size=S, p=flat)
        gh, ga = k // M.shape[1], k % M.shape[1]
        ih, ia = idx[h], idx[a]
        pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[ih] += gh - ga; gd[ia] += ga - gh
        gf[ih] += gh; gf[ia] += ga
    # ranking por (pts, gd, gf, ruido) por simulación
    clave = pts * 1e6 + gd * 1e3 + gf + rng.random((4, S)) * 1e-3
    orden = np.argsort(-clave, axis=0)             # orden[pos, s] = equipo
    P = np.zeros((4, 4))
    for pos in range(4):
        for e in range(4):
            P[e, pos] = np.mean(orden[pos] == e)
    # info de terceros: pts/gd para comparar mejores terceros
    return P, pts, gd, gf, orden


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
            partidos.append((c["home"], c["away"], matriz_de_evento(c, "proporcional", 2.5)))
    grupos = detectar_grupos(partidos)
    # partidos por grupo
    pidx = {tuple(g): [] for g in grupos}
    setg = [set(g) for g in grupos]
    for k, (h, a, _) in enumerate(partidos):
        for g, s in zip(grupos, setg):
            if h in s and a in s:
                pidx[tuple(g)].append(k); break

    rng = np.random.default_rng(0)
    print(f"{len(grupos)} grupos · {len(partidos)} partidos · {args.sims} sims\n")
    terceros = []  # (E[pts del 3º], grupo, equipo más probable 3º)
    GRP = "ABCDEFGHIJKL"
    for gi, g in enumerate(sorted(grupos, key=lambda x: x)):
        P, pts, gd, gf, orden = simular_grupo(g, pidx[tuple(g)], partidos, args.sims, rng)
        # orden más probable: asignar por P(1º) desc (greedy)
        print(f"Grupo {GRP[gi]}:")
        for e in sorted(range(4), key=lambda e: -P[e, 0]):
            print(f"   {g[e][:16]:16}  1º:{P[e,0]*100:4.0f}%  2º:{P[e,1]*100:4.0f}%  "
                  f"3º:{P[e,2]*100:4.0f}%  4º:{P[e,3]*100:4.0f}%  (clasifica {(P[e,0]+P[e,1])*100:3.0f}%)")
        # equipo más probable de quedar 3º y su "fuerza de tercero"
        e3 = max(range(4), key=lambda e: P[e, 2])
        # E[pts] del que quede 3º (proxy de fuerza): media de pts del tercero
        pts_tercero = np.mean([pts[orden[2, s], s] for s in range(0, args.sims, 50)])
        terceros.append((pts_tercero, GRP[gi], g[e3]))
    terceros.sort(reverse=True)
    print("\nMejores 8 terceros (proxy por pts esperados del 3º del grupo):")
    for pt, gl, eq in terceros[:8]:
        print(f"   Grupo {gl}: {eq}  (pts~{pt:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
