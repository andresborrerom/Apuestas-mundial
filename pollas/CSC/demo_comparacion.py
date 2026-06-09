#!/usr/bin/env python3
"""
Head-to-head sobre RESULTADOS REALES de Mundial (256 partidos, paquete oddor):
¿cuánto mejora NUESTRO modelo (EV-máximo + sesgo) frente a los métodos "a mano"
con los que se suele jugar (poner el marcador más probable, o un marcador
plausible muestreado)?

Puntaje exacto por método (params fase de grupos):
  - modal       : el marcador más probable (argmax M).
  - muestreado  : marcador plausible sorteado de M -> puntos ESPERADOS exactos
                  = sum_{a,b} M[a,b]·puntos((a,b), real).  (tu método clásico)
  - EV-máximo   : el relleno que maximiza puntos esperados.
  - EV-máx+sesgo: con el sesgo a gol=1 validado (α=0.05).

    python pollas/CSC/demo_comparacion.py
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import cuotas, marcadores
from motor.backtest import puntos, fill_evmax, fill_modal
from pollas.CSC.backtest_mundial import cargar
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]


def pts_muestreado(M, real):
    """Puntos ESPERADOS de poner un marcador plausible sorteado de M (exacto)."""
    n = M.shape[0]
    tot = 0.0
    for a in range(n):
        for b in range(n):
            if M[a, b] > 0:
                tot += M[a, b] * puntos((a, b), real, PARAMS)
    return tot


def main():
    try:
        df = cargar()
    except ImportError:
        print("Falta pyreadr:  pip install pyreadr")
        return 1

    acc = {"modal": [], "muestreado": [], "evmax": [], "evmax_sesgo": []}
    gana_vs_modal = gana_vs_muestreado = 0
    for _, row in df.iterrows():
        p = cuotas.a_probabilidades(
            [row.odds_home, row.odds_draw, row.odds_away], "proporcional")
        M = marcadores.ajustar_lambdas(p[0], p[1], p[2])["matriz"]
        real = (int(row.goals_home), int(row.goals_away))

        pm = puntos(fill_modal(M), real, PARAMS)
        ps = pts_muestreado(M, real)
        pe = puntos(fill_evmax(M, PARAMS), real, PARAMS)
        pes = puntos(fill_evmax(marcadores.aplicar_sesgo_goles(M, 0.05), PARAMS),
                     real, PARAMS)
        acc["modal"].append(pm); acc["muestreado"].append(ps)
        acc["evmax"].append(pe); acc["evmax_sesgo"].append(pes)
        gana_vs_modal += pe >= pm
        gana_vs_muestreado += pe >= ps

    n = len(df)
    print(f"{n} partidos reales de Mundial (2010-2022)\n")
    print(f"{'método':16} {'pts/partido':>12} {'proy. 72 partidos':>18}")
    base = np.mean(acc["muestreado"])
    for k in ("modal", "muestreado", "evmax", "evmax_sesgo"):
        m = np.mean(acc[k])
        etq = "  <- tu método clásico" if k == "muestreado" else \
              ("  <- NUESTRO modelo" if k == "evmax_sesgo" else "")
        print(f"{k:16} {m:>12.3f} {m*72:>18.1f}{etq}")

    g = np.mean(acc["evmax_sesgo"]) - base
    print(f"\nNUESTRO modelo vs tu método clásico (muestreado):")
    print(f"  +{g:.3f} pts/partido  →  ~+{g*72:.1f} pts en 72 partidos de grupos")
    print(f"  EV-máximo iguala o supera al modal en {gana_vs_modal/n*100:.0f}% "
          f"de los partidos, y al muestreado en {gana_vs_muestreado/n*100:.0f}%.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
