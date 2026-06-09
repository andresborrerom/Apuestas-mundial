#!/usr/bin/env python3
"""
Backtest específico de MUNDIALES (no clubes). Responde: ¿la relación
cuotas↔resultados del Mundial se parece a la de ligas de clubes, o cambia
(sedes neutrales, mismatches de grupos, knockouts de bajo gol)?

Datos: paquete R `oddor` (ikashnitsky/oddor), gratis — 1X2 de cierre + goles
reales de los 4 Mundiales 2010/2014/2018/2022 (256 partidos). Solo hay 1X2
(sin Over/Under), así que el modelo de goles se ajusta solo con el 1X2.

    python pollas/CSC/backtest_mundial.py
"""

import os
import sys
import urllib.request
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import cuotas, marcadores
from motor.simulacion_polla import ev_grid
from motor.backtest import puntos, fill_evmax, fill_modal, fill_favorito1
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
RDA = "/tmp/wc_oddor.rda"
URL = "https://github.com/ikashnitsky/oddor/raw/main/data/soccer_world_cup.rda"

# Calibración de GOLES en clubes (del backtest de ligas), para comparar:
CLUBES_GOLES_OBS = {0: 0.251, 1: 0.346, 2: 0.230, 3: 0.112, 4: 0.042}


def cargar():
    import pyreadr
    if not os.path.exists(RDA):
        urllib.request.urlretrieve(URL, RDA)
    df = list(pyreadr.read_r(RDA).values())[0]
    df = df.dropna(subset=["goals_home", "goals_away",
                           "odds_home", "odds_draw", "odds_away"])
    return df


def main():
    try:
        df = cargar()
    except ImportError:
        print("Falta pyreadr:  pip install pyreadr")
        return 1
    print(f"{len(df)} partidos de Mundial (2010-2022), 1X2 de cierre + goles reales.\n")

    cal_1x2 = []
    obs_goles = np.zeros(8); ng = 0
    pred_goles = np.zeros(8)
    pts = {"evmax": [], "evmax_sesgo": [], "modal": [], "favorito": []}

    for _, row in df.iterrows():
        p = cuotas.a_probabilidades(
            [row.odds_home, row.odds_draw, row.odds_away], "proporcional")
        aj = marcadores.ajustar_lambdas(p[0], p[1], p[2], usar_dixon_coles=True)
        M = aj["matriz"]
        rh, ra = int(row.goals_home), int(row.goals_away)
        real = (rh, ra)

        cal_1x2.append((float(np.tril(M, -1).sum()), rh > ra))
        mh, ma = M.sum(axis=1), M.sum(axis=0)
        for g in range(8):
            pred_goles[g] += (mh[g] if g < len(mh) else 0) + (ma[g] if g < len(ma) else 0)
        obs_goles[min(rh, 7)] += 1; obs_goles[min(ra, 7)] += 1; ng += 2

        pts["evmax"].append(puntos(fill_evmax(M, PARAMS), real, PARAMS))
        Ms = marcadores.aplicar_sesgo_goles(M, 0.05)
        pts["evmax_sesgo"].append(puntos(fill_evmax(Ms, PARAMS), real, PARAMS))
        pts["modal"].append(puntos(fill_modal(M), real, PARAMS))
        pts["favorito"].append(puntos(fill_favorito1(M), real, PARAMS))

    pred_goles /= pred_goles.sum(); obs_goles /= obs_goles.sum()

    print("=== Calibración 1X2 (P(gana equipo1) predicho -> observado) ===")
    pares = sorted(cal_1x2); n = len(pares)
    for b in range(5):
        ch = pares[b*n//5:(b+1)*n//5]
        pr = np.mean([c[0] for c in ch]); ob = np.mean([1.0 if c[1] else 0 for c in ch])
        print(f"  {pr:.2f} -> {ob:.2f}   (n={len(ch)})")

    print("\n=== Goles por equipo: MUNDIAL vs CLUBES (observado) ===")
    print(f"  {'g':>2} {'pred WC':>8} {'obs WC':>7} {'obs clubes':>11}")
    for g in range(5):
        print(f"  {g:>2} {pred_goles[g]:>8.3f} {obs_goles[g]:>7.3f} "
              f"{CLUBES_GOLES_OBS[g]:>11.3f}")

    print("\n=== Edge (pts CSC/partido, params primera) ===")
    for k in ("evmax", "evmax_sesgo", "modal", "favorito"):
        print(f"  {k:12s}: {np.mean(pts[k]):.3f}")
    e = np.mean(pts["evmax"]) - np.mean(pts["modal"])
    es = np.mean(pts["evmax_sesgo"]) - np.mean(pts["evmax"])
    print(f"  → edge EV-máximo vs modal: {e:+.3f} | efecto del sesgo α=0.05: {es:+.3f}")
    print(f"\n  (n={len(df)}; muestra chica, leer como señal direccional, no exacta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
