"""
Tramo de 9 semanas del Pick'em (Batalla semanal + Small Pot) con field REAL.

Complementa temporada.py (que usaba un field sintético q~U(.75,.95)): acá cada
rival pickea cada juego según la distribución real de fans de Pickwatch
(2020-2025), como en nfl/EDGE/anticrowd_informado.py, y se simula la plata de
un tramo completo con la contabilidad del reglamento:

  - Batalla: $50k/jugador/semana, ganador único cobra el pozo acumulado,
    empate rueda (máx 2), liquidación forzada en la última semana del tramo.
  - Small Pot: $100k, más puntos del tramo; empate divide.

Política fija durante todo el tramo: fav, m3, anti1, anti2, anti3.
Pickwatch solo cubre ~68 semanas sueltas (ninguna temporada completa), así
que cada tramo es un REMUESTREO de 9 semanas reales distintas (con su
distribución de fans y su resultado de verdad). Métrica: E[neto] por tramo
(batalla + small pot) y P(ganar el pot).

Uso:  python3.13 nfl/PICKEM/temporada_anti3.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl.EDGE.anticrowd_informado import cargar, planillas, N_RIV  # noqa: E402
from nfl.PICKEM.temporada import liquidar_batalla  # noqa: E402

SIMS = 150
TRAMOS = 400
LARGO = 9
AP_BATALLA, AP_SMALL = 50_000, 100_000
POLITICAS = ["fav", "m3", "anti1", "anti2", "anti3", "anti4", "anti5"]


def planillas_k(juegos):
    """planillas() + anti4/anti5 (mismo criterio: mayor exceso, p_dog>=.35)."""
    pols = planillas(juegos)
    p = np.array([j["p_home"] for j in juegos])
    fans = np.array([j["fans_home"] for j in juegos])
    fav_home = p >= 0.5
    p_fav = np.where(fav_home, p, 1 - p)
    exceso = np.where(fav_home, fans, 1 - fans) - p_fav
    for k in (4, 5):
        ak = fav_home.copy()
        for i in [i for i in np.argsort(-exceso)
                  if 1 - p_fav[i] >= 0.35][:k]:
            ak[i] = ~ak[i]
        pols[f"anti{k}"] = ak
    return pols


def main():
    semanas = cargar()
    claves = sorted(semanas)
    rng = np.random.default_rng(11)
    pre = {}
    for k in claves:
        juegos = semanas[k]
        gh = np.array([j["gano_home"] for j in juegos])
        em = np.array([j["empate"] for j in juegos])
        fans = np.array([j["fans_home"] for j in juegos])
        pl = planillas_k(juegos)
        pre[k] = (gh, em, fans, {p: int(np.where(pl[p], gh, ~gh & ~em).sum())
                                 for p in POLITICAS})

    res = {p: defaultdict(list) for p in POLITICAS}
    for _ in range(TRAMOS):
        idx = rng.choice(len(claves), size=LARGO, replace=False)
        ws = [claves[i] for i in idx]
        fh = []
        for k in ws:
            gh, em, fans, _m = pre[k]
            pf = rng.random((SIMS, N_RIV, len(gh))) < fans
            fh.append(np.where(pf, gh, (~gh & ~em)).sum(axis=2))
        fh = np.stack(fh, axis=1)                   # (SIMS, semanas, riv)
        acum_f = fh.sum(axis=1)
        for p in POLITICAS:
            m = np.array([pre[k][3][p] for k in ws])
            nos = m.sum()
            ini = len(res[p]["bat"])
            for j in range(SIMS):
                bat, pozo, n_ac = 0.0, 1, 0
                for i in range(LARGO):
                    neto, pozo, n_ac = liquidar_batalla(
                        m[i], fh[j, i], pozo, n_ac, forzar=(i == LARGO - 1))
                    bat += neto
                tope = max(acum_f[j].max(), nos)
                n_top = int((acum_f[j] == tope).sum()) + int(nos == tope)
                pot = (14 * AP_SMALL / n_top - AP_SMALL
                       if nos == tope else -AP_SMALL)
                res[p]["bat"].append(bat * AP_BATALLA)
                res[p]["pot"].append(pot)
                res[p]["pts"].append(nos)
                res[p]["gana_pot"].append(nos == tope and n_top == 1)
                res[p]["gana_bat"].append(bat > 0)
            res[p]["tramo_tot"].append(
                np.mean(res[p]["bat"][ini:]) + np.mean(res[p]["pot"][ini:]))

    print(f"TRAMO DE {LARGO} SEMANAS (remuestreo de {len(claves)} semanas "
          f"reales; {TRAMOS}x{SIMS} sims; pool de 14)")
    print(f"{'política':<8} {'pts/tramo':>10} {'E[batalla]':>11} "
          f"{'E[pot]':>9} {'E[total]':>10} {'P(gana pot)':>12} "
          f"{'P(bat>0)':>9} {'±EE total':>10}")
    for p in POLITICAS:
        r = res[p]
        tot = np.array(r["bat"]) + np.array(r["pot"])
        print(f"{p:<8} {np.mean(r['pts']):>10.1f} "
              f"{np.mean(r['bat']) / 1e3:>+10.0f}k "
              f"{np.mean(r['pot']) / 1e3:>+8.0f}k "
              f"{np.mean(tot) / 1e3:>+9.0f}k "
              f"{100 * np.mean(r['gana_pot']):>11.1f}% "
              f"{100 * np.mean(r['gana_bat']):>8.1f}% "
              f"{np.std(r['tramo_tot']) / np.sqrt(TRAMOS) / 1e3:>8.0f}k")


if __name__ == "__main__":
    main()
