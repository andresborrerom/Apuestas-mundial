#!/usr/bin/env python3
"""
Demo: el "libro mayor" de las simulaciones, para entender de dónde sale E[util].

En cada simulación (un Mundial posible) se calcula el puntaje total de los ~90
participantes, se ordenan, y se ve en qué PUESTO quedó cada uno de NUESTROS
cupos, qué premio ganamos y la utilidad de esa simulación. E[util] = promedio
de la columna 'utilidad' sobre miles de simulaciones.

Esto es FASE DE GRUPOS (lo que pediste, "primera fase"). Nota: grupos solo da
cifras optimistas; el torneo completo baja la P(1º) (ver experimento_rivales).

    python pollas/CSC/demo_ranking.py --mock /tmp/wc_grupos.json --cupos 4
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, simulacion_polla as sp
from motor.simulacion_polla import PREMIOS
from pollas.CSC.cupos import matriz_de_evento
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
FIELD = {"cal": 0.4, "hum": 0.3, "opt": 0.3}


def money(x):
    return f"${x:,.0f}".replace(",", ".")


def correr(matrices, k, N, precio, S, n_muestra, semilla=7):
    rng = np.random.default_rng(semilla)
    Ef = N - k
    gh, ga = sp.muestrear_torneos(matrices, S, rng)
    fh, fa = sp.generar_field_mix(matrices, Ef, FIELD, PARAMS, rng)
    oh, oa = sp.generar_nuestras(matrices, k, PARAMS, estrategia="perturbada",
                                 rng=rng, n_swaps=12, pool=40)
    pf = sp._puntos(fh, fa, gh, ga, PARAMS)
    po = sp._puntos(oh, oa, gh, ga, PARAMS)
    todo = np.vstack([pf, po]) + rng.random((N, S)) * 1e-6  # jitter = rifa

    pot = N * precio
    premio_val = PREMIOS * pot                      # $ por puesto 1..5
    rangos = np.argsort(np.argsort(-todo, axis=0), axis=0) + 1   # puesto 1..N
    nuestros = rangos[Ef:, :]                        # (k, S) puesto de cada cupo
    mejor = nuestros.min(axis=0)                     # mejor puesto por sim
    # premio ganado por sim = suma de premios de los cupos que cayeron en top5
    gan = np.where(nuestros <= 5,
                   premio_val[np.clip(nuestros, 1, 5) - 1], 0.0).sum(axis=0)
    util = gan - k * precio

    print(f"\n=== {k} CUPOS · {N} participantes · pot {money(pot)} ===")
    print("Premios: " + " · ".join(f"{i+1}º {money(premio_val[i])}"
                                    for i in range(5)))
    cab = " ".join(f"cupo{c+1:>2}" for c in range(k))
    print(f"\n {'sim':>4} | {cab} | {'mejor':>5} | {'premio':>12} | utilidad")
    print("-" * (9 + 7 * k + 32))
    for s in range(n_muestra):
        cols = " ".join(f"{nuestros[c, s]:>5}" for c in range(k))
        prem = money(gan[s]) if gan[s] > 0 else "—"
        print(f" {'#'+str(s+1):>4} | {cols} | {mejor[s]:>4}º | {prem:>12} | "
              f"{('+' if util[s]>=0 else '')+money(util[s])}")

    print(f"\nResumen sobre {S} simulaciones:")
    print(f"  E[utilidad] = {money(util.mean())}   ← promedio de la columna 'utilidad'")
    print(f"  quedó 1º en {(mejor==1).mean()*100:.1f}% · en premio (top5) en "
          f"{(mejor<=5).mean()*100:.1f}% · sin premio en {(mejor>5).mean()*100:.1f}%")
    # reparto del mejor puesto
    bins = [(1,1,"1º"),(2,5,"2º-5º"),(6,20,"6º-20º"),(21,N,">20º")]
    rep = " · ".join(f"{et}:{((mejor>=a)&(mejor<=b)).mean()*100:.0f}%" for a,b,et in bins)
    print(f"  reparto del MEJOR puesto:  {rep}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--participantes", type=int, default=90)
    ap.add_argument("--precio", type=float, default=100_000)
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--muestra", type=int, default=15)
    ap.add_argument("--cupos", type=int, nargs="*", default=[4, 5])
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))
    matrices = [matriz_de_evento(c, "proporcional", 2.5)
                for c in (odds_api.consenso_evento(e) for e in eventos)
                if c["cuotas_1x2"]]
    for k in args.cupos:
        correr(matrices, k, args.participantes, args.precio, args.sims, args.muestra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
