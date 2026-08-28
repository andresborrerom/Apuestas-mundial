"""
E3 — ¿Podemos PRONOSTICAR el vapor? Elo vs la línea de apertura.

E2 mostró que seguir el movimiento de la línea cubre la apertura 57-59%.
Pero el vapor solo es apostable si lo ves ANTES. Test honesto: nuestro
Elo (puro resultados, cero mercado, walk-forward) discrepa de la apertura
en algunos juegos. En esos:
  a) ¿la línea se mueve hacia el lado del Elo? (¿olemos el vapor?)
  b) ¿el lado del Elo cubre la apertura por encima del break-even 52.4%?

La pendiente spread->prob se ajusta SOLO con 2002-2012 (test = 2013-2020).

Uso:  python nfl/EDGE/predecir_vapor.py
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402
from nfl.EDGE.apertura_cierre import cargar_sbro  # noqa: E402


def main():
    juegos = cargar_sbro()

    # Elo cronológico hasta la víspera de cada juego
    todos = sorted(datos.cargar_partidos(),
                   key=lambda x: (x["season"], x["week"], x["gameday"]))
    train = [p for p in todos
             if p["season"] <= 2012 and p["spread_line"] is not None
             and not p["empate"]]
    b = prob.ajustar_pendiente_spread(
        [p["spread_line"] for p in train],
        [1.0 if p["result"] > 0 else 0.0 for p in train])
    elo = prob.Elo()
    p_elo = {}
    for p in todos:
        p_elo[(p["gameday"], p["home"], p["away"])] = \
            elo.p_local(p["home"], p["away"])
        elo.actualizar(p)

    def logit(x):
        return math.log(x / (1 - x))

    filas = []
    for j in juegos:
        pe = p_elo.get((j["fecha"], j["home"], j["away"]))
        if pe is None:
            continue
        po = 1 / (1 + math.exp(-b * j["sp_open"]))
        gap = logit(pe) - logit(po)          # >0: Elo quiere al local
        mov = j["sp_close"] - j["sp_open"]   # >0: mercado se movió al local
        resid = j["margen"] - j["sp_open"]   # >0: local cubrió la apertura
        filas.append((gap, mov, resid))
    print(f"juegos con Elo y apertura: {len(filas)}")

    print(f"\n{'|gap| >=':>9} {'n':>5} {'mov hacia Elo':>14} "
          f"{'cubre Elo vs AP':>16} {'SE':>5}")
    for umbral in (0.1, 0.2, 0.3, 0.5):
        sub = [(g, m, r) for g, m, r in filas if abs(g) >= umbral]
        if not sub:
            continue
        hacia = [np.sign(g) == np.sign(m) for g, m, r in sub if m != 0]
        cubre = [(r > 0) if g > 0 else (r < 0) for g, m, r in sub if r != 0]
        n = len(cubre)
        print(f"{umbral:>9} {n:>5} {100 * np.mean(hacia):>13.1f}% "
              f"{100 * np.mean(cubre):>15.1f}% {50 / math.sqrt(n):>4.1f}pp")
    print("\n(break-even -110 = 52.4%. 'mov hacia Elo' >50% = sí olemos"
          "\n hacia dónde va la línea; 'cubre' > 52.4% = es apostable)")


if __name__ == "__main__":
    main()
