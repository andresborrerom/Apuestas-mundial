"""
Backtest walk-forward de los 3 proxies de P(gana) contra ground truth.

Protocolo (el mismo rigor de CSC/LEMAITRE):
  - Para cada temporada de test Y (2011-2025):
      * MONEYLINE: sin ajuste (el mercado ya viene "entrenado"); se evalúa
        directo sobre Y. Se comparan métodos de de-vig (proporcional/shin).
      * SPREAD: la pendiente b se ajusta SOLO con temporadas < Y (desde 1999)
        y se evalúa en Y. Nada del futuro contamina el pasado.
      * ELO: corre cronológicamente desde 1999; para cada partido predice
        ANTES de actualizar. (Auto-walk-forward por construcción.)
  - Métricas sobre partidos con moneyline (2011-2025): Brier, log-loss,
    % acierto del favorito, y calibración por bucket de probabilidad.
  - Empates: excluidos de las métricas de "ganó/perdió" (son ~0.4%);
    su frecuencia se reporta aparte porque en Survival cuestan vida.

Uso:  python nfl/backtest_probabilidades.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfl import datos, probabilidades as prob  # noqa: E402


def metricas(p_pred, gano):
    """Brier, log-loss y acierto del favorito para predicciones P(local)."""
    p = np.asarray(p_pred, dtype=float)
    y = np.asarray(gano, dtype=float)
    eps = 1e-12
    brier = float(np.mean((p - y) ** 2))
    logloss = float(-np.mean(y * np.log(p + eps)
                             + (1 - y) * np.log(1 - p + eps)))
    pick = (p >= 0.5).astype(float)
    acierto = float(np.mean(pick == y))
    return brier, logloss, acierto


def main():
    partidos = datos.cargar_partidos()  # REG jugados, todas las temporadas

    # --- Elo cronológico (predice antes de actualizar) -------------------
    elo = prob.Elo()
    p_elo = {}
    for p in sorted(partidos, key=lambda x: (x["season"], x["week"],
                                             x["gameday"])):
        clave = (p["season"], p["week"], p["home"], p["away"])
        p_elo[clave] = elo.p_local(p["home"], p["away"])
        elo.actualizar(p)

    # --- walk-forward por temporada de test ------------------------------
    filas = defaultdict(lambda: defaultdict(list))  # proxy -> campo -> vals
    buckets = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    n_emp, n_tot = 0, 0

    for anio in range(2011, 2026):
        train = [p for p in partidos
                 if p["season"] < anio and p["spread_line"] is not None
                 and not p["empate"]]
        b = prob.ajustar_pendiente_spread(
            [p["spread_line"] for p in train],
            [1.0 if p["result"] > 0 else 0.0 for p in train])

        test = [p for p in partidos
                if p["season"] == anio and p["ml_home"] is not None]
        n_emp += sum(1 for p in test if p["empate"])
        n_tot += len(test)
        test = [p for p in test if not p["empate"]]

        gano = [1.0 if p["result"] > 0 else 0.0 for p in test]
        pred = {
            "moneyline": [prob.p_local_moneyline(p["ml_home"], p["ml_away"])
                          for p in test],
            "moneyline_shin": [prob.p_local_moneyline(p["ml_home"],
                                                      p["ml_away"], "shin")
                               for p in test],
            "spread": [prob.p_local_spread(p["spread_line"], b)
                       for p in test],
            "elo": [p_elo[(p["season"], p["week"], p["home"], p["away"])]
                    for p in test],
        }
        for nombre, ps in pred.items():
            br, ll, ac = metricas(ps, gano)
            filas[nombre]["brier"].append(br)
            filas[nombre]["logloss"].append(ll)
            filas[nombre]["acierto"].append(ac)
            # calibración: bucket por P del EQUIPO PREDICHO como ganador
            for pi, yi in zip(ps, gano):
                pw = pi if pi >= 0.5 else 1 - pi
                yw = yi if pi >= 0.5 else 1 - yi
                bk = min(int(pw * 10) / 10, 0.9)
                buckets[nombre][bk][0] += yw
                buckets[nombre][bk][1] += 1

    print("=" * 72)
    print("WALK-FORWARD 2011-2025 (test año a año, partidos REG con moneyline)")
    print("=" * 72)
    print(f"\n{'proxy':<16} {'Brier':>8} {'log-loss':>9} {'% favorito':>11}")
    for nombre in ["moneyline", "moneyline_shin", "spread", "elo"]:
        f = filas[nombre]
        print(f"{nombre:<16} {np.mean(f['brier']):>8.4f} "
              f"{np.mean(f['logloss']):>9.4f} "
              f"{100 * np.mean(f['acierto']):>10.1f}%")

    print(f"\nempates: {n_emp} de {n_tot} partidos "
          f"({100 * n_emp / n_tot:.2f}%) — en Survival cuestan vida")

    print("\nCALIBRACIÓN (P predicha del favorito vs frecuencia real):")
    print(f"{'bucket':<8}", end="")
    for nombre in ["moneyline", "spread", "elo"]:
        print(f"{nombre:>18}", end="")
    print()
    for bk in [0.5, 0.6, 0.7, 0.8, 0.9]:
        print(f"{bk:.1f}-{bk + 0.1:.1f} ", end="")
        for nombre in ["moneyline", "spread", "elo"]:
            w, n = buckets[nombre][bk]
            print(f"{100 * w / n:>9.1f}% (n={n:>4})" if n else " " * 18,
                  end="")
        print()

    print("\nPor temporada (Brier moneyline vs elo):")
    for i, anio in enumerate(range(2011, 2026)):
        print(f"  {anio}: ml={filas['moneyline']['brier'][i]:.4f} "
              f"elo={filas['elo']['brier'][i]:.4f} "
              f"fav_ml={100 * filas['moneyline']['acierto'][i]:.1f}%")


if __name__ == "__main__":
    main()
