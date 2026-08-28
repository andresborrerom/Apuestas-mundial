"""
E1 — Viento vs TOTALES: el edge climático documentado, probado en serio.

En la batería 1 probamos viento contra el GANADOR (nada). Pero el hallazgo
clásico de la literatura es en el TOTAL: el viento mata el juego aéreo de
los dos equipos y el mercado históricamente lo descontaba de menos →
apostar UNDER con viento fuerte. games.csv trae total_line, under/over
odds (completos 2010-2025) y viento por partido outdoor. HIPÓTESIS
DECLARADA (una sola): con viento >=15 mph el under rinde por encima de su
probabilidad implícita, con efecto monótono en el viento.

Tres métricas:
  a) puntos reales − total_line por bucket de viento (¿la línea descuenta
     de menos?), con SE.
  b) frecuencia real del under vs su probabilidad implícita de-vig
     (empujes excluidos), residual y z por bucket.
  c) ROI de apostar under a la cuota real (con el vig incluido) cuando
     viento >= umbral — split-half 2010-2017 / 2018-2025 para consistencia.

Uso:  python nfl/EDGE/viento_totales.py
"""

import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from motor import cuotas  # noqa: E402

BUCKETS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 99)]


def cargar():
    filas = []
    with open(datos.RUTA_GAMES) as f:
        for r in csv.DictReader(f):
            if (r["game_type"] != "REG" or not r["result"]
                    or not r["total_line"] or not r["under_odds"]
                    or not r["over_odds"] or not r["wind"]
                    or r["roof"] not in ("outdoors", "open")
                    or int(r["season"]) < 2010):
                continue
            total = int(r["home_score"]) + int(r["away_score"])
            linea = float(r["total_line"])
            cu = datos.americano_a_decimal(r["under_odds"])
            co = datos.americano_a_decimal(r["over_odds"])
            p_under = float(cuotas.a_probabilidades([cu, co])[0])
            filas.append({
                "season": int(r["season"]), "wind": float(r["wind"]),
                "total": total, "linea": linea,
                "under": total < linea, "push": total == linea,
                "cuota_under": cu, "p_under": p_under,
            })
    return filas


def main():
    filas = cargar()
    print(f"partidos outdoor con viento y cuotas de total 2010-2025: "
          f"{len(filas)}\n")

    print("a) PUNTOS REALES − LÍNEA por bucket de viento:")
    print(f"{'viento':>8} {'n':>5} {'línea media':>12} {'real medio':>11} "
          f"{'resid':>7} {'SE':>5}")
    for lo, hi in BUCKETS:
        sub = [f for f in filas if lo <= f["wind"] < hi]
        if not sub:
            continue
        d = np.array([f["total"] - f["linea"] for f in sub])
        li = np.mean([f["linea"] for f in sub])
        print(f"{lo:>3}-{hi if hi < 99 else '+':>3} {len(sub):>6} "
              f"{li:>12.1f} {li + d.mean():>11.1f} {d.mean():>+7.2f} "
              f"{d.std() / math.sqrt(len(d)):>5.2f}")

    print("\nb) UNDER real vs implícito (sin empujes):")
    print(f"{'viento':>8} {'n':>5} {'P impl.':>8} {'real':>7} "
          f"{'resid':>7} {'z':>6}")
    for lo, hi in BUCKETS:
        sub = [f for f in filas if lo <= f["wind"] < hi and not f["push"]]
        if not sub:
            continue
        ps = np.array([f["p_under"] for f in sub])
        ys = np.array([1.0 * f["under"] for f in sub])
        r = ys.mean() - ps.mean()
        se = math.sqrt(np.sum(ps * (1 - ps))) / len(ps)
        print(f"{lo:>3}-{hi if hi < 99 else '+':>3} {len(sub):>6} "
              f"{ps.mean():>8.3f} {ys.mean():>7.3f} {r:>+7.3f} "
              f"{r / se:>+6.2f}")

    print("\nc) ROI apostando UNDER a cuota real (viento >= umbral):")
    print(f"{'umbral':>7} {'n':>5} {'ROI total':>10} "
          f"{'2010-17':>9} {'2018-25':>9}")
    for umbral in (10, 15, 20):
        sub = [f for f in filas if f["wind"] >= umbral]
        def roi(ff):
            if not ff:
                return 0.0, 0
            u = [(f["cuota_under"] - 1) if f["under"]
                 else (0.0 if f["push"] else -1.0) for f in ff]
            return float(np.mean(u)), len(ff)
        r_tot, n = roi(sub)
        r1, n1 = roi([f for f in sub if f["season"] <= 2017])
        r2, n2 = roi([f for f in sub if f["season"] > 2017])
        print(f"{umbral:>7} {n:>5} {100 * r_tot:>+9.1f}% "
              f"{100 * r1:>+8.1f}% {100 * r2:>+8.1f}%")

    print("\n(criterio: solo se cree si b) es monótono con z decente Y c)"
          "\n es positivo en AMBAS mitades después del vig)")


if __name__ == "__main__":
    main()
