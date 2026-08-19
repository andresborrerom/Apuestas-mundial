"""
Pick'em con N=14 y alianza de 2: flips complementarios en la Batalla Semanal.

La pareja controla 2 planillas. En la Batalla (winner-take-all semanal,
$50k por cabeza → el que gana solo recibe $650k), ir idénticos es regalar
una planilla. La jugada: A voltea el coin-flip #1 de la semana y B voltea
el #2 — cubren rutas distintas y NUNCA empatan entre sí en el 1º puesto
con el mismo puntaje... (sí pueden empatar en puntos; se mide todo).

Flujo neto de la banca por semana (aportes de $50k):
  gana uno de la pareja SOLO  → +12  (recibe 13, uno es del aliado: lavado)
  gana un rival SOLO          → −2   (pagan ambos)
  empate en el 1º             → 0 esa semana (el pozo rueda; a la larga se
                                 liquida en proporciones parecidas)

También: efecto de la alianza en los pots acumulados (Small/Big) con N=14.

Field model: 12 rivales, aciertan el pick del favorito con q_j~U(0.75,0.95).

Uso:  python nfl/PICKEM/alianza.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl.PICKEM.backtest_pickem import (  # noqa: E402
    TEMPORADAS, semanas_con_probs)
from nfl import datos  # noqa: E402

N_RIVALES = 12
SIMS = 2000
APORTE = 50_000

# (flips de A, flips de B) — B voltea juegos DISTINTOS a los de A
CONFIGS = [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)]


def puntos_con_flips(js, indices_flip):
    """Puntos reales de una planilla = favoritos con esos juegos volteados."""
    pts = np.array([g for _p, g in js], dtype=float)
    for k in indices_flip:
        pts[k] = 1 - pts[k]
    return pts.sum()


def main():
    partidos = datos.cargar_partidos(temporadas=set(TEMPORADAS))
    semanas = semanas_con_probs(partidos)
    rng = np.random.default_rng(11)
    q = rng.uniform(0.75, 0.95, size=N_RIVALES)

    print("=" * 72)
    print(f"BATALLA SEMANAL, POOL DE 14 — banca de 2, {SIMS} sims/semana")
    print(f"(gana solo un aliado: +12 aportes = +${12 * APORTE / 1e3:.0f}k "
          f"a la banca; gana solo un rival: −2)")
    print("=" * 72)
    print(f"{'(A,B) flips':>12} {'P(banca 1º única)':>18} "
          f"{'P(rival 1º único)':>18} {'E[neto banca]/sem':>18}")

    resultados_flujo = {}
    for ma, mb in CONFIGS:
        p_banca, p_rival = [], []
        for js in semanas.values():
            orden = np.argsort([abs(p - 0.5) for p, _g in js])
            pa = puntos_con_flips(js, orden[:ma])
            pb = puntos_con_flips(js, orden[ma:ma + mb])
            fav = np.array([g for _p, g in js], dtype=float)
            pick_fav = rng.random((SIMS, N_RIVALES, len(js))) < q[None, :, None]
            hits = np.where(pick_fav, fav[None, None, :],
                            1 - fav[None, None, :]).sum(axis=2)
            mejor_rival = hits.max(axis=1)
            n_mejor_rival = (hits == mejor_rival[:, None]).sum(axis=1)
            nuestro_max = max(pa, pb)
            unicos_nuestros = (pa == nuestro_max) + (pb == nuestro_max)
            gana_banca = (nuestro_max > mejor_rival) & (unicos_nuestros == 1)
            gana_rival = (mejor_rival > nuestro_max) & (n_mejor_rival == 1)
            p_banca.append(np.mean(gana_banca))
            p_rival.append(np.mean(gana_rival))
        eb, er = np.mean(p_banca), np.mean(p_rival)
        neto = 12 * eb - 2 * er
        resultados_flujo[(ma, mb)] = neto
        print(f"{str((ma, mb)):>12} {100 * eb:>17.1f}% {100 * er:>17.1f}% "
              f"{neto:>+11.2f} ap. (${neto * APORTE / 1e3:+.0f}k)")

    # ---------------- pots acumulados con banca de 2 ---------------------
    print()
    print("=" * 72)
    print("POTS ACUMULADOS, POOL DE 14 — P(alguno de la banca queda 1º)")
    print("=" * 72)
    por_temp = defaultdict(list)
    for (s, _w), js in semanas.items():
        por_temp[s].append(js)
    for ma, mb in [(0, 0), (1, 1), (1, 2)]:
        g_mitad, g_full = [], []
        for s, sems_t in sorted(por_temp.items()):
            pa_l, pb_l, field_l = [], [], []
            for js in sems_t:
                orden = np.argsort([abs(p - 0.5) for p, _g in js])
                pa_l.append(puntos_con_flips(js, orden[:ma]))
                pb_l.append(puntos_con_flips(js, orden[ma:ma + mb]))
                fav = np.array([g for _p, g in js], dtype=float)
                pf = (rng.random((SIMS // 4, N_RIVALES, len(js)))
                      < q[None, :, None])
                field_l.append(np.where(pf, fav[None, None, :],
                                        1 - fav[None, None, :]).sum(axis=2))
            pa_l, pb_l = np.array(pa_l), np.array(pb_l)
            field_l = np.array(field_l)      # (semanas, sims, rivales)
            mitad = len(pa_l) // 2
            for corte, acc in [(slice(0, mitad), g_mitad),
                               (slice(None), g_full)]:
                nos = max(pa_l[corte].sum(), pb_l[corte].sum())
                ellos = field_l[corte].sum(axis=0).max(axis=1)
                acc.append(np.mean(nos > ellos) + 0.5 * np.mean(nos == ellos))
        print(f"  (A,B)=({ma},{mb}): P(Small Pot)={100 * np.mean(g_mitad):.0f}%"
              f"  P(Big Pot)={100 * np.mean(g_full):.0f}%"
              f"   [premios: ${1.3:.1f}M / ${2.6:.1f}M al ganador]")

    print("\n=> La banca compara su MEJOR planilla contra el mejor rival;"
          "\n   los flips de B son gratis para los pots si A va limpio (0 o"
          "\n   1 flip) y B asume la varianza de la Batalla.")


if __name__ == "__main__":
    main()
