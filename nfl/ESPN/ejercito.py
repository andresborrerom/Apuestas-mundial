"""
El ejército: ¿cuánto valen 20 / 100 / 500 entradas ESPN descorrelacionadas?

Con ~50 personas en USA (10 entradas c/u) el juego de colas cambia de
escala. Acá no hay que "encontrar" edge: el edge es ESTRUCTURAL — cubrir
sistemáticamente los caminos de upsets que el público no cubre, con
probabilidad de mercado como guía.

Diseño de entradas (a priori): favoritos + combinaciones de flips sobre
los J partidos más parejos de la semana, ordenadas por P(patrón) =
prod(p de lo que pide el patrón). Las primeras 20 son las de siempre;
100 y 500 agregan combos más profundos (3-5 flips). Métrica con ground
truth 2011-2025: P(alguna entrada 15+/16) y P(alguna 16/16) por semana.

Uso:  python nfl/ESPN/ejercito.py
"""

import os
import sys
from itertools import combinations

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from nfl.PICKEM.backtest_pickem import (  # noqa: E402
    TEMPORADAS, semanas_con_probs)

TAMANOS = [20, 100, 500]
J = 12                       # profundidad: los 12 partidos más parejos


def patrones(p_fav_ordenada, n_max):
    """Patrones de flips ordenados por P(acertar el patrón completo).

    p_fav_ordenada: p del favorito en los J partidos más parejos (asc).
    P(patrón) = prod(1-p en los volteados) * prod(p en el resto).
    """
    pats = [()]
    for k in range(1, 6):
        pats += list(combinations(range(min(J, len(p_fav_ordenada))), k))
    def prob(pat):
        pr = 1.0
        for i, p in enumerate(p_fav_ordenada[:J]):
            pr *= (1 - p) if i in pat else p
        return pr
    pats.sort(key=prob, reverse=True)
    return pats[:n_max]


def main():
    partidos = datos.cargar_partidos(temporadas=set(TEMPORADAS))
    semanas = semanas_con_probs(partidos)

    exitos = {t: [0, 0] for t in TAMANOS}    # [15+, 16 perfecto]
    n_sem = 0
    for js in semanas.values():
        n = len(js)
        if n < 14:
            continue
        n_sem += 1
        orden = np.argsort([abs(p - 0.5) for p, _g in js])
        p_ord = [js[k][0] for k in orden]
        gano = np.array([g for _p, g in js], dtype=float)
        gano_ord = gano[orden]
        base = gano.sum()
        pats = patrones(p_ord, max(TAMANOS))
        for t in TAMANOS:
            top15, perfecto = False, False
            for pat in pats[:t]:
                pts = base
                for i in pat:
                    pts += (1 - gano_ord[i]) - gano_ord[i]
                if pts >= n - 1:
                    top15 = True
                if pts == n:
                    perfecto = True
                if top15 and perfecto:
                    break
            exitos[t][0] += top15
            exitos[t][1] += perfecto

    print(f"STANDARD ESPN — colas por semana, {n_sem} semanas 2011-2025")
    print(f"(entradas = favoritos + flips en los {J} más parejos, "
          f"ordenadas por P(patrón))")
    print(f"\n{'entradas':>9} {'P(alguna 15+/16)':>18} {'P(alguna PERFECTA)':>20}")
    for t in TAMANOS:
        print(f"{t:>9} {100 * exitos[t][0] / n_sem:>17.1f}% "
              f"{100 * exitos[t][1] / n_sem:>19.1f}%")
    print("\nNota: pegar 15-16/16 pone la entrada en la pelea del premio"
          "\nsemanal; ganarlo depende de cuántos más lo lograron y del"
          "\ntiebreaker de ESPN (verlo en la app). En Confidence el ejército"
          "\nusa pocos: 1 entrada óptima por persona ya es el tope teórico.")


if __name__ == "__main__":
    main()
