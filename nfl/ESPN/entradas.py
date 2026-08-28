"""
Genera las entradas ESPN de la semana (para hermano y sobrino, 10 c/u).

Diseño (validado en backtest_espn.py):
  - CONFIDENCE (el modo con más edge): UNA entrada "pura" por persona con
    el ranking óptimo (peso 16 al favorito más seguro, ..., 1 al más
    parejo). Es la apuesta a los premios de temporada/consistencia.
  - STANDARD: las 20 entradas con patrones de flips escalonados sobre los
    partidos más parejos (entrada 1 = favoritos puros; el resto caza la
    semana 15+/16, que con 20 entradas aparece en ~15% de las semanas).

Uso:  python nfl/ESPN/entradas.py [--week N]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402
from nfl.ESPN.backtest_espn import patrones_20  # noqa: E402

TEMPORADA = 2026


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None)
    args = ap.parse_args()

    temporada = datos.cargar_partidos(temporadas={TEMPORADA},
                                      solo_jugados=False)
    semanas = {w: js for (_s, w), js in datos.por_semana(temporada).items()}
    if args.week:
        w = args.week
    else:
        w = min(wk for wk, js in semanas.items()
                if any(j["result"] is None and j["ml_home"] for j in js))
    juegos = [j for j in semanas[w] if j["ml_home"] is not None]

    filas = []
    for j in juegos:
        ph = prob.p_local_moneyline(j["ml_home"], j["ml_away"])
        fav, p = (j["home"], ph) if ph >= 0.5 else (j["away"], 1 - ph)
        dog = j["away"] if fav == j["home"] else j["home"]
        filas.append((p, fav, dog, j))
    filas.sort(key=lambda x: -x[0])          # más seguro primero

    print(f"ESPN NFL Pick'em — SEMANA {w} ({len(filas)} partidos)")
    print("\n== CONFIDENCE (1 entrada por persona, la misma: es el óptimo)")
    print("   peso = puntos si acierta; ESPN pide asignar 1..N único")
    for i, (p, fav, _d, j) in enumerate(filas):
        peso = len(filas) - i
        print(f"  peso {peso:>2}: {fav:<3} ({100 * p:.0f}%)  "
              f"[{j['away']} @ {j['home']}]")

    print("\n== STANDARD (20 entradas: 10 hermano + 10 sobrino)")
    print("   base = favoritos; cada entrada voltea los partidos marcados")
    parejos = sorted(filas, key=lambda x: x[0])   # más parejo primero
    for e, pat in enumerate(patrones_20(len(filas)), 1):
        flips = [parejos[k][2] for k in pat]      # pick al underdog
        etiqueta = " + ".join(flips) if flips else "favoritos puros"
        quien = "hermano" if e <= 10 else "sobrino"
        print(f"  E{e:>2} ({quien}): {etiqueta}")
    print("\n(Spread y Pick 5: llenarlos con el pick del spread de Vegas tal"
          "\n cual — sin edge, pero habilita el bono de $5K por llenar todo.)")


if __name__ == "__main__":
    main()
