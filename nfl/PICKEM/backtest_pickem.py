"""
Backtest walk-forward del Pick'em (1 pt por acierto, sin marcadores).

Dos preguntas separadas, porque las 4 apuestas tienen estructuras opuestas:

1. POTS ACUMULADOS (Small 1, Small 2, Big): maratón de E[puntos].
   El pick EV-máx es EL FAVORITO EN TODO — cualquier desvío cuesta puntos
   esperados. Acá medimos cuánto rinde el favorito y cuánto cuesta desviarse.

2. BATALLA SEMANAL (winner-take-all, con acumulación): la media no importa,
   importa P(quedar 1º ÚNICO en la semana). Contra un field que también
   toma favoritos, ir idéntico = empatar siempre (el pozo rueda y se
   reparte). La idea de perturbación mínima de CSC: voltear los partidos
   MÁS parejos (p≈50%) cuesta casi nada de E[pts] y te decorrelaciona.
   Acá medimos P(ganar solo la semana) según cuántos coin-flips volteas.

FIELD MODEL (supuesto explícito): N rivales; cada uno acierta el pick del
favorito con prob q_j fija por rival, q_j ~ U(0.75, 0.95) (entre casual y
afilado). Sensibilidad incluida porque el resultado depende de esto.

Uso:  python nfl/PICKEM/backtest_pickem.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402

TEMPORADAS = range(2011, 2026)
N_FIELD = [9, 19]
FLIPS = [0, 1, 2, 3]     # cuántos partidos ~50/50 volteamos al underdog
SIMS = 2000


def semanas_con_probs(partidos):
    """{(season, week): [(p_favorito_local?, fav_gano, p_fav)]}."""
    sem = defaultdict(list)
    for p in partidos:
        if p["ml_home"] is None or p["empate"]:
            continue
        ph = prob.p_local_moneyline(p["ml_home"], p["ml_away"])
        fav_es_local = ph >= 0.5
        p_fav = ph if fav_es_local else 1 - ph
        fav_gano = (p["result"] > 0) == fav_es_local
        sem[(p["season"], p["week"])].append((p_fav, fav_gano))
    return dict(sorted(sem.items()))


def main():
    partidos = datos.cargar_partidos(temporadas=set(TEMPORADAS))
    semanas = semanas_con_probs(partidos)
    rng = np.random.default_rng(11)

    # ---------- 1. el favorito como baseline de E[puntos] ----------------
    aciertos_fav = [np.mean([g for _p, g in js]) for js in semanas.values()]
    n_juegos = [len(js) for js in semanas.values()]
    print("=" * 72)
    print("1. POTS ACUMULADOS — el favorito en todo (2011-2025)")
    print("=" * 72)
    print(f"acierto del favorito: {100 * np.mean(aciertos_fav):.1f}% "
          f"(~{np.mean(aciertos_fav) * np.mean(n_juegos):.1f} de "
          f"{np.mean(n_juegos):.1f} pts/semana)")
    costo = []
    for js in semanas.values():
        ordenados = sorted(js, key=lambda x: x[0])
        costo.append(sum(2 * p - 1 for p, _g in ordenados[:1]))
    print(f"costo E[pts] de voltear el partido más parejo: "
          f"{np.mean(costo):.3f} pts/semana "
          f"({17 * np.mean(costo):.1f} pts/temporada de 17-18 sem.)")

    # ---------- 2. batalla semanal: P(ganar SOLO) ------------------------
    print()
    print("=" * 72)
    print("2. BATALLA SEMANAL — P(quedar 1º único) vs field de favoritos")
    print(f"   field: q_j ~ U(0.75, 0.95) por rival, {SIMS} sims/semana")
    print("=" * 72)
    lista_semanas = list(semanas.values())

    for nf in N_FIELD:
        q = rng.uniform(0.75, 0.95, size=nf)
        print(f"\n--- pool de N={nf + 1} (nosotros + {nf} rivales) ---")
        print(f"{'flips':>6} {'E[pts] semana':>14} {'P(1º único)':>12} "
              f"{'P(empate 1º)':>13}")
        for m in FLIPS:
            solos, empates, pts = [], [], []
            for js in lista_semanas:
                orden = np.argsort([abs(p - 0.5) for p, _g in js])
                nuestro = np.array([g for _p, g in js], dtype=float)
                for k in orden[:m]:
                    nuestro[k] = 1 - nuestro[k]     # volteamos al underdog
                n_pts = nuestro.sum()
                pts.append(n_pts)
                fav_gano = np.array([g for _p, g in js], dtype=float)
                # field: (SIMS, nf, juegos) — acierta el pick del favorito
                # con prob q_j; si no, tomó al underdog
                pick_fav = (rng.random((SIMS, nf, len(js)))
                            < q[None, :, None])
                hits = np.where(pick_fav, fav_gano[None, None, :],
                                1 - fav_gano[None, None, :]).sum(axis=2)
                mejor_field = hits.max(axis=1)
                solos.append(np.mean(n_pts > mejor_field))
                empates.append(np.mean(n_pts == mejor_field))
            print(f"{m:>6} {np.mean(pts):>14.2f} "
                  f"{100 * np.mean(solos):>11.1f}% "
                  f"{100 * np.mean(empates):>12.1f}%")

    # ---------- 3. pots acumulados: P(ganar la maratón) ------------------
    print()
    print("=" * 72)
    print("3. POTS ACUMULADOS — P(1º en la suma de 9 / 18 semanas)")
    print("=" * 72)
    por_temp = defaultdict(list)
    for (s, _w), js in semanas.items():
        por_temp[s].append(js)
    for nf in N_FIELD:
        q = rng.uniform(0.75, 0.95, size=nf)
        for m in [0, 1]:
            g_mitad, g_full = [], []
            for s, sems_t in sorted(por_temp.items()):
                nuestros, field = [], []
                for js in sems_t:
                    orden = np.argsort([abs(p - 0.5) for p, _g in js])
                    nu = np.array([g for _p, g in js], dtype=float)
                    for k in orden[:m]:
                        nu[k] = 1 - nu[k]
                    nuestros.append(nu.sum())
                    fav = np.array([g for _p, g in js], dtype=float)
                    pf = (rng.random((SIMS // 4, nf, len(js)))
                          < q[None, :, None])
                    field.append(np.where(pf, fav[None, None, :],
                                          1 - fav[None, None, :])
                                 .sum(axis=2))
                nuestros = np.array(nuestros)
                field = np.array(field)          # (semanas, sims, nf)
                mitad = len(nuestros) // 2
                for corte, acc in [(slice(0, mitad), g_mitad),
                                   (slice(None), g_full)]:
                    nos = nuestros[corte].sum()
                    ellos = field[corte].sum(axis=0)   # (sims, nf)
                    acc.append(np.mean(nos > ellos.max(axis=1))
                               + 0.5 * np.mean(nos == ellos.max(axis=1)))
            print(f"N={nf + 1}, flips={m}: P(1º Small Pot ~9 sem.)="
                  f"{100 * np.mean(g_mitad):.0f}%  "
                  f"P(1º Big Pot temporada)={100 * np.mean(g_full):.0f}%")

    print("\n=> La MISMA planilla juega las 4 apuestas: los flips que ganan"
          "\n   la Batalla Semanal cuestan ~1 pt/temporada en los pots."
          "\n   Con la ventaja estructural del favorito, ese costo es chico.")


if __name__ == "__main__":
    main()
