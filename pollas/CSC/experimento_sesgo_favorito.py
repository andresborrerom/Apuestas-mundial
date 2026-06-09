#!/usr/bin/env python3
"""
TEORÍA (idea del usuario): el 1X2 debería condicionar el sesgo de goles —
ponerle "un gol extra" al FAVORITO más que al débil. Probamos un sesgo
ASIMÉTRICO: alpha_fav en el eje del favorito, alpha_dog en el del débil.

Honesto: tuneamos (alpha_fav, alpha_dog) en TRAIN por puntos CSC y medimos UNA
vez en TEST (walk-forward). Comparamos contra el sesgo SIMÉTRICO ya validado.

Usa la caché de matrices de experimento_recalibracion.py (/tmp/recal_cache_*).

    python pollas/CSC/experimento_sesgo_favorito.py
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
G = 7


def r_sesgo(alpha, n):
    r = np.ones(n)
    r[0] = 1 - alpha
    r[1] = 1 + alpha
    r[2] = 1 + alpha / 2
    if n > 5:
        r[5:] = 1 - alpha / 2
    return r


def matriz_asim(M, alpha_fav, alpha_dog):
    """Sesgo distinto según quién es favorito (por prob. de ganar)."""
    n = M.shape[0]
    pL = float(np.tril(M, -1).sum())
    pV = float(np.triu(M, 1).sum())
    if pL >= pV:  # local favorito -> filas
        r_h, r_w = r_sesgo(alpha_fav, n), r_sesgo(alpha_dog, n)
    else:         # visitante favorito -> columnas
        r_h, r_w = r_sesgo(alpha_dog, n), r_sesgo(alpha_fav, n)
    M2 = M * np.outer(r_h, r_w)
    s = M2.sum()
    return M2 / s if s > 0 else M


def puntos(matrices, reales, af, ad):
    tot = 0
    for M, real in zip(matrices, reales):
        M2 = matriz_asim(M, af, ad) if (af or ad) else M
        tot += bt.puntos(bt.fill_evmax(M2, PARAMS, G), real, PARAMS)
    return tot / len(matrices)


def main():
    cache = "/tmp/recal_cache_6000.pkl"
    if not os.path.exists(cache):
        print("No hay caché. Corre primero experimento_recalibracion.py")
        return 1
    with open(cache, "rb") as f:
        Mtr, Rtr, Mte, Rte = pickle.load(f)
    print(f"train {len(Mtr)} / test {len(Mte)} partidos (ground truth real)\n")

    base_tr = puntos(Mtr, Rtr, 0, 0)
    base_te = puntos(Mte, Rte, 0, 0)

    # referencia: simétrico (mismo alpha a ambos), tuneado en train
    rejilla = [0.0, 0.04, 0.08, 0.12, 0.16, 0.20, 0.25, 0.30]
    sim = [(a, puntos(Mtr, Rtr, a, a)) for a in rejilla]
    a_sim = max(sim, key=lambda x: x[1])[0]
    sim_te = puntos(Mte, Rte, a_sim, a_sim)

    # asimétrico: grid (alpha_fav, alpha_dog) tuneado en train
    mejor = (-1, 0, 0)
    for af in rejilla:
        for ad in rejilla:
            p = puntos(Mtr, Rtr, af, ad)
            if p > mejor[0]:
                mejor = (p, af, ad)
    _, af_star, ad_star = mejor
    asim_te = puntos(Mte, Rte, af_star, ad_star)

    print("=== TEST (out-of-sample, pts CSC/partido) ===")
    print(f"  Baseline (sin sesgo)                 {base_te:.4f}")
    print(f"  Simétrico  α={a_sim:.2f}                  {sim_te:.4f} "
          f"({sim_te-base_te:+.4f})")
    print(f"  Asimétrico fav={af_star:.2f} dog={ad_star:.2f}        {asim_te:.4f} "
          f"({asim_te-base_te:+.4f})")
    print(f"\n  ¿La asimetría (condicionar por 1X2) supera al simétrico? "
          f"{'SÍ' if asim_te > sim_te + 1e-9 else 'NO'} "
          f"({asim_te-sim_te:+.4f} vs simétrico)")
    print(f"\n  (α* favorito={af_star}, α* débil={ad_star} elegidos en TRAIN; "
          f"si fav>dog, conviene empujar más goles al favorito)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
