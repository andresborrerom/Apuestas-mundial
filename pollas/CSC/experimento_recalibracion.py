#!/usr/bin/env python3
"""
Experimento: ¿sesgar la distribución de goles hacia "1" mejora los puntos?

Hallazgo: como la regla premia más acertar gol≠0 (1+base) que el 0 (cero), el
sesgo óptimo PARA PUNTOS es más agresivo que la calibración. Para no
autoengañarnos, TUNEAMOS la magnitud del sesgo en TRAIN (maximizando puntos
CSC) y medimos UNA sola vez en TEST (walk-forward).

Contrastamos con la corrección "empírica" (calibración pura), que NO maximiza
puntos.

Uso:  python pollas/CSC/experimento_recalibracion.py --max 6000
"""

import argparse
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


def r_sesgo(alpha):
    """Familia de 1 parámetro: baja P(0), sube P(1)/P(2), baja colas altas."""
    r = np.ones(G + 1)
    r[0] = 1 - alpha
    r[1] = 1 + alpha
    r[2] = 1 + alpha / 2
    if G >= 5:
        r[5:] = 1 - alpha / 2
    return r


def puntos_variante(matrices, reales, r):
    tot = 0
    for M, real in zip(matrices, reales):
        M2 = bt.matriz_recalibrada(M, r) if r is not None else M
        tot += bt.puntos(bt.fill_evmax(M2, PARAMS, G), real, PARAMS)
    return tot / len(matrices)


def construir(lst):
    Ms, reales = [], []
    for p in lst:
        try:
            Ms.append(bt.matriz_de_partido(p))
            reales.append((p["fthg"], p["ftag"]))
        except Exception:
            pass
    return Ms, reales


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=6000)
    ap.add_argument("--seasons", nargs="*", default=bt.SEASONS)
    ap.add_argument("--ligas", nargs="*", default=bt.LIGAS)
    ap.add_argument("--rebuild", action="store_true", help="ignorar caché")
    args = ap.parse_args(argv)

    cache = f"/tmp/recal_cache_{args.max}.pkl"
    if os.path.exists(cache) and not args.rebuild:
        print("Usando caché de matrices...", flush=True)
        with open(cache, "rb") as f:
            Mtr, Rtr, Mte, Rte = pickle.load(f)
    else:
        print("Cargando partidos y construyendo modelos (lento)...", flush=True)
        P = bt.cargar_partidos(args.seasons, args.ligas)
        rng = np.random.default_rng(0)
        if args.max and len(P) > args.max:
            P = [P[i] for i in rng.choice(len(P), args.max, replace=False)]
        corte = len(args.seasons) // 2
        viejas = set(args.seasons[:corte])
        Mtr, Rtr = construir([p for p in P if p["season"] in viejas])
        Mte, Rte = construir([p for p in P if p["season"] not in viejas])
        with open(cache, "wb") as f:
            pickle.dump((Mtr, Rtr, Mte, Rte), f)
    print(f"  train {len(Mtr)} / test {len(Mte)} partidos.\n")

    # --- Contraste: corrección de calibración pura (no optimiza puntos) ---
    r_emp = bt.aprender_recalibracion(Mtr, Rtr, G)
    base_te = puntos_variante(Mte, Rte, None)
    emp_te = puntos_variante(Mte, Rte, r_emp)
    print(f"Baseline (sin corrección)         TEST: {base_te:.4f} pts/partido")
    print(f"Corrección de calibración pura    TEST: {emp_te:.4f} "
          f"({emp_te-base_te:+.4f})  → calibrar ≠ maximizar puntos\n")

    # --- Tuneo correcto: elegir alpha en TRAIN por PUNTOS, medir en TEST ---
    alphas = np.round(np.linspace(0.0, 0.40, 21), 3)
    pts_train = [puntos_variante(Mtr, Rtr, r_sesgo(a)) for a in alphas]
    a_star = float(alphas[int(np.argmax(pts_train))])
    print(f"Tuneo del sesgo α en TRAIN (maximizando puntos):  α* = {a_star}")

    # curva en TEST (solo diagnóstico: confirmar que train-óptimo ≈ test-óptimo)
    pts_test = [puntos_variante(Mte, Rte, r_sesgo(a)) for a in alphas]
    a_test = float(alphas[int(np.argmax(pts_test))])
    print(f"   (diagnóstico: α óptimo en TEST = {a_test}; deben parecerse)\n")

    test_en_astar = pts_test[int(np.where(alphas == a_star)[0][0])]
    print("=== RESULTADO walk-forward (honesto) ===")
    print(f"  Baseline                TEST: {base_te:.4f}")
    print(f"  Sesgo α*={a_star} (de train) TEST: {test_en_astar:.4f} "
          f"({test_en_astar-base_te:+.4f})")
    g72 = (test_en_astar - base_te) * 72
    print(f"  → Ganancia out-of-sample: {test_en_astar-base_te:+.4f} pts/partido "
          f"(~{g72:+.2f} pts en 72 partidos de grupos)")

    print("\n  Curva (α : train / test):")
    for a, tr, te in zip(alphas, pts_train, pts_test):
        marca = " <- α*" if a == a_star else ""
        print(f"    {a:.2f} : {tr:.4f} / {te:.4f}{marca}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
