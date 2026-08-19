"""
Temporada completa del Pick'em con las REGLAS DE PLATA oficiales, N=14.

Hasta ahora la Batalla Semanal se midió por semana suelta. Acá se simula la
temporada entera con la contabilidad real del reglamento:

  - Batalla: $50k/jugador/semana. Ganador único recibe el pozo acumulado de
    cada rival. Empate en el 1º → no hay ganador, el pozo rueda (máx 2
    acumulaciones; en la 3ª semana se reparte entre los empatados de esa
    semana). Liquidación FORZADA en los cortes (semana 9 y última): si hay
    empate ahí, se reparte entre los empatados de esa semana.
  - Small Pots ($100k c/u): más puntos en la 1ª / 2ª mitad. Empate divide.
  - Big Pot ($200k): más puntos de toda la temporada. Empate divide.

Políticas nuestras (los flips = coin-flips volteados al underdog):
  estáticas m=0..3, y DINÁMICA: 2 flips por defecto; en las 2 semanas
  previas a cada corte, si lideramos el pot en juego por >=3 pts -> 0 flips
  (proteger); si vamos a >=4 detrás -> 3 flips (comprar varianza).

Field: 13 rivales, q_j ~ U(0.75, 0.95) re-sorteado por simulación.

Uso:  python nfl/PICKEM/temporada.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from nfl.PICKEM.backtest_pickem import (  # noqa: E402
    TEMPORADAS, semanas_con_probs)

N_RIV = 13
SIMS = 300
AP_BATALLA, AP_SMALL, AP_BIG = 50_000, 100_000, 200_000
POLITICAS = ["m0", "m1", "m2", "m3", "m4", "m5", "dinamica"]


def hits_nuestros(js, m):
    """Puntos reales de favoritos con los m coin-flips más parejos volteados."""
    orden = np.argsort([abs(p - 0.5) for p, _g in js])
    pts = np.array([g for _p, g in js], dtype=float)
    for k in orden[:m]:
        pts[k] = 1 - pts[k]
    return float(pts.sum())


def flips_dinamica(w, n_sem, delta_pot):
    """Política dinámica: proteger liderando cerca del corte, arriesgar detrás."""
    corte1, corte2 = 9, n_sem
    cerca = (corte1 - 1 <= w <= corte1) or (corte2 - 1 <= w <= corte2)
    if cerca:
        if delta_pot >= 3:
            return 0
        if delta_pot <= -4:
            return 3
    return 2


def liquidar_batalla(nuestro, field_hits, pozo_pp, n_acum, forzar):
    """Una semana de Batalla. Devuelve (neto_nuestro, pozo_pp, n_acum).

    field_hits: (n_riv,) puntos de los rivales esa semana (una sim).
    """
    tope = max(field_hits.max(), nuestro)
    lideres_riv = int((field_hits == tope).sum())
    nosotros_top = nuestro == tope
    n_top = lideres_riv + int(nosotros_top)
    if n_top == 1:                               # ganador único: cobra
        neto = 13 * pozo_pp if nosotros_top else -pozo_pp
        return neto, 1, 0
    # empate en el 1º
    if n_acum >= 2 or forzar:                    # tope o corte: se reparte
        neto = (14 * pozo_pp / n_top - pozo_pp) if nosotros_top else -pozo_pp
        return neto, 1, 0
    return 0.0, pozo_pp + 1, n_acum + 1          # rueda


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=23)
    args = ap.parse_args()

    partidos = datos.cargar_partidos(temporadas=set(TEMPORADAS))
    semanas = semanas_con_probs(partidos)
    por_temp = defaultdict(list)
    for (s, _w), js in sorted(semanas.items()):
        por_temp[s].append(js)
    rng = np.random.default_rng(args.seed)

    tot = {p: [] for p in POLITICAS}
    des = {p: defaultdict(list) for p in POLITICAS}
    for s, sems_t in sorted(por_temp.items()):
        n_sem = len(sems_t)
        nuestros = {m: [hits_nuestros(js, m) for js in sems_t]
                    for m in range(6)}
        favs = [np.array([g for _p, g in js], dtype=float) for js in sems_t]

        for _ in range(SIMS):
            q = rng.uniform(0.75, 0.95, size=N_RIV)
            fh = []                              # field hits por semana
            for js, fav in zip(sems_t, favs):
                pf = rng.random((N_RIV, len(js))) < q[:, None]
                fh.append(np.where(pf, fav[None, :],
                                   1 - fav[None, :]).sum(axis=1))
            fh = np.array(fh)                    # (semanas, rivales)
            acum_f = fh.cumsum(axis=0)

            for pol in POLITICAS:
                bat, pozo_pp, n_ac = 0.0, 1, 0
                mis = np.empty(n_sem)
                mi_acum = 0.0
                for w in range(1, n_sem + 1):
                    if pol == "dinamica":
                        # standing del pot en juego ANTES de esta semana
                        if w <= 9:
                            base_n = sum(mis[:w - 1][max(0, 0):])
                            base_f = acum_f[w - 2].max() if w > 1 else 0
                        else:
                            base_n = sum(mis[9:w - 1])
                            base_f = ((acum_f[w - 2] - acum_f[8]).max()
                                      if w > 10 else 0)
                        m = flips_dinamica(w, n_sem, base_n - base_f)
                    else:
                        m = int(pol[1])
                    mis[w - 1] = nuestros[m][w - 1]
                    neto, pozo_pp, n_ac = liquidar_batalla(
                        mis[w - 1], fh[w - 1], pozo_pp, n_ac,
                        forzar=(w == 9 or w == n_sem))
                    bat += neto
                mi_acum = mis.cumsum()

                pots = 0.0
                mitades = [(0, 9, AP_SMALL), (9, n_sem, AP_SMALL),
                           (0, n_sem, AP_BIG)]
                for ini, fin, ap in mitades:
                    nos = mi_acum[fin - 1] - (mi_acum[ini - 1] if ini else 0)
                    ellos = (acum_f[fin - 1]
                             - (acum_f[ini - 1] if ini else 0))
                    tope = max(ellos.max(), nos)
                    n_top = int((ellos == tope).sum()) + int(nos == tope)
                    if nos == tope:
                        pots += 14 * ap / n_top - ap
                    else:
                        pots -= ap
                tot[pol].append(bat * AP_BATALLA + pots)
                des[pol]["batalla"].append(bat * AP_BATALLA)
                des[pol]["pots"].append(pots)

    print(f"POOL DE 14 — E[$ NETO POR TEMPORADA], {SIMS} sims x 15 temp.")
    print(f"{'política':<10} {'E[batalla]':>12} {'E[pots]':>12} "
          f"{'E[TOTAL]':>12} {'P(total>0)':>11}")
    for pol in POLITICAS:
        t = np.array(tot[pol])
        print(f"{pol:<10} {np.mean(des[pol]['batalla']) / 1e6:>+10.2f}M "
              f"{np.mean(des[pol]['pots']) / 1e6:>+10.2f}M "
              f"{np.mean(t) / 1e6:>+10.2f}M {100 * np.mean(t > 0):>10.1f}%")


if __name__ == "__main__":
    main()
