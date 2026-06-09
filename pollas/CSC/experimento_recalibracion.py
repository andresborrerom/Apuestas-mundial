#!/usr/bin/env python3
"""
Experimento: ¿recalibrar la distribución de goles mejora los puntos?

El modelo predice "0 goles" de más y "1" de menos. Aprendemos el sesgo en
temporadas de TRAIN y medimos en TEST (walk-forward) si recomputar el relleno
EV-máximo sobre la distribución corregida gana puntos CSC. Comparamos:

  - ninguna        : EV-máximo sobre la distribución del modelo (baseline)
  - empírica       : corrección con el % observado de sub-predicción (train)
  - manual_suave   : corrección manual leve (3 distribuciones de sanity check)
  - manual_fuerte  : corrección manual exagerada
  - solo_1         : solo mueve masa de 0 a 1

Uso:  python pollas/CSC/experimento_recalibracion.py --max 6000
"""

import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import backtest as bt
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
G = 7


def puntos_variante(matrices, reales, r):
    tot = 0
    for M, real in zip(matrices, reales):
        M2 = bt.matriz_recalibrada(M, r) if r is not None else M
        tot += bt.puntos(bt.fill_evmax(M2, PARAMS, G), real, PARAMS)
    return tot / len(matrices)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=6000)
    ap.add_argument("--seasons", nargs="*", default=bt.SEASONS)
    ap.add_argument("--ligas", nargs="*", default=bt.LIGAS)
    args = ap.parse_args(argv)

    print("Cargando partidos...", flush=True)
    P = bt.cargar_partidos(args.seasons, args.ligas)
    rng = np.random.default_rng(0)
    if args.max and len(P) > args.max:
        P = [P[i] for i in rng.choice(len(P), args.max, replace=False)]

    # split temporal: train = temporadas viejas, test = nuevas
    corte = len(args.seasons) // 2
    viejas = set(args.seasons[:corte])
    Ptr = [p for p in P if p["season"] in viejas]
    Pte = [p for p in P if p["season"] not in viejas]
    print(f"  train {len(Ptr)} / test {len(Pte)} partidos. "
          f"Construyendo modelos (lento)...", flush=True)

    def construir(lst):
        Ms, reales = [], []
        for p in lst:
            try:
                Ms.append(bt.matriz_de_partido(p))
                reales.append((p["fthg"], p["ftag"]))
            except Exception:
                pass
        return Ms, reales

    Mtr, Rtr = construir(Ptr)
    Mte, Rte = construir(Pte)

    # aprender corrección empírica en TRAIN
    r_emp = bt.aprender_recalibracion(Mtr, Rtr, G)
    print("\nCorrección empírica aprendida en train (r_g por # de goles):")
    print("  g:   " + "  ".join(f"{g}" for g in range(6)))
    print("  r_g: " + "  ".join(f"{r_emp[g]:.2f}" for g in range(6)))

    # variantes (vectores r de longitud G+1)
    def vec(d):
        r = np.ones(G + 1)
        for g, v in d.items():
            r[g] = v
        return r

    variantes = {
        "ninguna": None,
        "empírica (train)": r_emp,
        "manual_suave": vec({0: 0.93, 1: 1.06, 2: 1.02, 4: 0.95}),
        "manual_fuerte": vec({0: 0.82, 1: 1.14, 2: 1.06, 4: 0.88}),
        "solo_0_a_1": vec({0: 0.88, 1: 1.10}),
    }

    print(f"\n=== Puntos CSC/partido en TEST (out-of-sample, n={len(Mte)}) ===")
    base = puntos_variante(Mte, Rte, None)
    filas = []
    for nombre, r in variantes.items():
        pv = puntos_variante(Mte, Rte, r)
        filas.append((nombre, pv, pv - base))
    for nombre, pv, d in filas:
        flag = "  ← baseline" if nombre == "ninguna" else \
               ("  ✅ mejor" if d == max(f[2] for f in filas) and d > 0 else "")
        print(f"  {nombre:18s} {pv:.4f}  ({d:+.4f}){flag}")

    mejor = max(filas, key=lambda x: x[1])
    if mejor[2] > 0:
        print(f"\n  → La recalibración '{mejor[0]}' gana "
              f"{mejor[2]:+.4f} pts/partido fuera de muestra "
              f"(~{mejor[2]*72:+.2f} pts en 72 partidos de grupos).")
    else:
        print("\n  → Ninguna recalibración mejora el baseline fuera de muestra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
