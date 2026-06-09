#!/usr/bin/env python3
"""
TEORÍA (mía, aprobada): el sesgo hacia gol=1 debería depender del total
esperado de goles del partido. En partidos de BAJO gol, empujar más hacia "1"
(el 0 se sobre-predice más); en goleadas esperadas, menos.

α(partido) = clip( α_base + α_slope · (2.6 − E[goles totales]) , 0, 0.5 )
  - α_slope > 0  → más sesgo en partidos cerrados/de bajo gol.
  - α_slope = 0  → recupera el sesgo CONSTANTE ya validado.

Honesto: tuneamos (α_base, α_slope) en TRAIN por puntos y medimos en TEST.
Usa la caché de matrices de experimento_recalibracion.py.

    python pollas/CSC/experimento_sesgo_lambda.py
"""

import os
import pickle
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import backtest as bt
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
CENTRO = 2.6  # total de goles "típico"


def r_sesgo(alpha, n):
    r = np.ones(n)
    r[0] = 1 - alpha
    r[1] = 1 + alpha
    r[2] = 1 + alpha / 2
    if n > 5:
        r[5:] = 1 - alpha / 2
    return r


def total_esperado(M):
    n = M.shape[0]
    tot = np.add.outer(np.arange(n), np.arange(n))
    return float((M * tot).sum())


def puntos(matrices, reales, etots, a_base, a_slope):
    tot = 0
    for M, real, et in zip(matrices, reales, etots):
        a = min(0.5, max(0.0, a_base + a_slope * (CENTRO - et)))
        M2 = bt.matriz_recalibrada(M, r_sesgo(a, M.shape[0])) if a else M
        tot += bt.puntos(bt.fill_evmax(M2, PARAMS, 7), real, PARAMS)
    return tot / len(matrices)


def main():
    cache = "/tmp/recal_cache_6000.pkl"
    if not os.path.exists(cache):
        print("No hay caché; corre experimento_recalibracion.py primero.")
        return 1
    with open(cache, "rb") as f:
        Mtr, Rtr, Mte, Rte = pickle.load(f)
    Etr = [total_esperado(M) for M in Mtr]
    Ete = [total_esperado(M) for M in Mte]
    print(f"train {len(Mtr)} / test {len(Mte)}.  "
          f"E[goles] medio train={np.mean(Etr):.2f}\n")

    base_te = puntos(Mte, Rte, Ete, 0.0, 0.0)

    # referencia: constante (slope=0), tuneado en train
    bases = [0.0, 0.04, 0.08, 0.12, 0.16, 0.20]
    slopes = [0.0, 0.03, 0.06, 0.10, 0.15, 0.20]
    cte = max(bases, key=lambda b: puntos(Mtr, Rtr, Etr, b, 0.0))
    cte_te = puntos(Mte, Rte, Ete, cte, 0.0)

    # λ-dependiente: grid (base, slope) tuneado en train
    mejor = (-1, 0, 0)
    for b in bases:
        for s in slopes:
            p = puntos(Mtr, Rtr, Etr, b, s)
            if p > mejor[0]:
                mejor = (p, b, s)
    _, b_star, s_star = mejor
    lam_te = puntos(Mte, Rte, Ete, b_star, s_star)

    print("=== TEST (out-of-sample, pts CSC/partido) ===")
    print(f"  Baseline (sin sesgo)              {base_te:.4f}")
    print(f"  Constante  α={cte:.2f}                {cte_te:.4f} ({cte_te-base_te:+.4f})")
    print(f"  λ-dependiente base={b_star:.2f} slope={s_star:.2f}  {lam_te:.4f} "
          f"({lam_te-base_te:+.4f})")
    print(f"\n  ¿La λ-dependencia supera al sesgo constante? "
          f"{'SÍ' if lam_te > cte_te + 1e-9 else 'NO'} ({lam_te-cte_te:+.4f})")
    if s_star > 0:
        print("  (slope>0 → conviene empujar más a '1' en partidos de bajo gol)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
