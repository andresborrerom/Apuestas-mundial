"""
Robustez de la heurística marrano a sus 2 parámetros.

Los valores del backtest principal (umbral=0.70, bottom-5) se eligieron a
priori, SIN probar alternativas. Este experimento barre la vecindad para
verificar que el resultado no es un pico afinado de chiripa: si la ventaja
sobre greedy aparece en TODA la malla, es estructural; si solo aparece en
una celda, es sobreajuste y no hay que creerla.

Uso:  python nfl/SURVIVAL/experimento_robustez_marrano.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from nfl.SURVIVAL import estrategias as est, simulador as sim  # noqa: E402
from nfl.SURVIVAL.backtest_survival import (  # noqa: E402
    TEMPORADAS, preparar_temporada)

THETA, N_RIVALES, SIMS = 25, 19, 200


def main():
    partidos = datos.cargar_partidos()
    rng = np.random.default_rng(7)

    prep, field = {}, {}
    for t in TEMPORADAS:
        prep[t] = preparar_temporada(partidos, t)
        sj, so = prep[t][0], prep[t][1]
        trays = [sim.trayectoria_field(so, sj, THETA, rng)
                 for _ in range(SIMS)]
        field[t] = np.array([np.inf if e is None else e for e in trays])

    print(f"field theta={THETA}, pool N={N_RIVALES + 1}, "
          f"{SIMS} sims — E[ganancia] en aportes / semanas medias")
    print(f"{'umbral':>8} " + "".join(f"{'bottom-' + str(k):>18}"
                                      for k in (3, 5, 7)))
    for umbral in (0.65, 0.70, 0.75):
        fila = f"{umbral:>8} "
        for k in (3, 5, 7):
            est.UMBRAL_MARRANO, est.N_MARRANOS = umbral, k
            gan, sems = [], []
            for t in TEMPORADAS:
                sj, so, elo_w, fz_w = prep[t]
                elim, _ = sim.trayectoria_estrategia(
                    "marrano", so, sj, sj, elo_w, fz_w)
                e_n = np.inf if elim is None else elim
                sems.append(19 if elim is None else elim)
                for _ in range(SIMS // 4):
                    muestra = rng.choice(field[t], size=N_RIVALES,
                                         replace=True)
                    gan.append(sim.repartir_pozo(e_n, muestra))
            fila += f"  {np.mean(gan):+6.2f} / {np.mean(sems):4.1f}s"
        print(fila)
    est.UMBRAL_MARRANO, est.N_MARRANOS = 0.70, 5  # restaurar


if __name__ == "__main__":
    main()
