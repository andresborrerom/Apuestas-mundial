"""
ESPN NFL Pick'em nacional — ¿Standard o Confidence? Medir el edge por modo.

Contexto: hermano y sobrino del usuario en Seattle (elegibles), 10 entradas
cada uno. Contra un pool nacional enorme NO se compite por la media: se
compite por las COLAS (semanas casi perfectas) y por los premios de
temporada (consistencia). Este backtest mide, con ground truth 2011-2025:

  STANDARD (1 pt por acierto):
    - Distribución semanal de aciertos de nuestros favoritos.
    - P(semana 15+/16) — el territorio donde se ganan premios semanales —
      con 1 entrada y con 20 entradas descorrelacionadas (favoritos + j
      flips en los partidos más parejos, patrones disjuntos).
  CONFIDENCE (aciertas y ganas el peso 1..N que le pusiste al partido):
    - Nuestro score: ranking por P calibrada del moneyline (el óptimo
      teórico: E[score] = sum p_(i) * peso_i se maximiza ordenando por p).
    - vs público sintético: mismo acierto de favoritos, pero ranking con
      ruido (la gente ordena "a ojo": sesgo a equipos populares, errores).
    - El edge de ORDENAR bien es nuestro; en Standard no existe.

Público sintético (supuesto explícito): acierta el pick del favorito con
q ~ U(0.72, 0.95) y ordena la confianza por p + ruido N(0, sigma=0.08).

Uso:  python nfl/ESPN/backtest_espn.py
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

SIMS_PUB = 400          # públicos simulados por semana
SIGMA_RANK = 0.08       # ruido del ranking del público
N_ENTRADAS = 20         # hermano + sobrino, 10 c/u


def patrones_20(n_juegos):
    """20 patrones de flips disjuntos/escalonados sobre los más parejos.

    Entrada 0 = favoritos puros; 1-3 = 1 flip (juegos 1º/2º/3º más
    parejos); 4-9 = 2 flips (parejas distintas); 10-19 = 3 flips (tríos
    distintos). Diseño a priori, sin mirar resultados.
    """
    from itertools import combinations
    pats = [()]
    pats += [(i,) for i in range(3)]
    pats += list(combinations(range(4), 2))
    pats += list(combinations(range(5), 3))
    return [p for p in pats if max(p, default=0) < n_juegos][:N_ENTRADAS]


def main():
    partidos = datos.cargar_partidos(temporadas=set(TEMPORADAS))
    semanas = semanas_con_probs(partidos)
    rng = np.random.default_rng(31)

    hits_sem, hits15_1, hits15_20 = [], 0, 0
    conf_nuestro, conf_pub, conf_gana = [], [], []
    std_max_frac = []
    n_sem = 0

    for js in semanas.values():
        n = len(js)
        if n < 12:
            continue
        n_sem += 1
        orden_parejos = np.argsort([abs(p - 0.5) for p, _g in js])
        p_fav = np.array([p for p, _g in js])
        gano_fav = np.array([g for _p, g in js], dtype=float)

        # ---- STANDARD ----
        h = gano_fav.sum()
        hits_sem.append(h / n)
        if h >= n - 1:
            hits15_1 += 1
        for pat in patrones_20(n):
            pts = gano_fav.copy()
            for k in pat:
                pts[orden_parejos[k]] = 1 - pts[orden_parejos[k]]
            if pts.sum() >= n - 1:
                hits15_20 += 1
                break

        # ---- CONFIDENCE ----
        # nuestro: peso n al de mayor p, ..., 1 al más parejo
        rank_n = np.argsort(np.argsort(p_fav)) + 1     # 1..n por p asc
        nuestro = float((rank_n * gano_fav).sum())
        maximo = n * (n + 1) / 2
        conf_nuestro.append(nuestro / maximo)
        # público: mismo favorito con prob q, ranking por p + ruido
        q = rng.uniform(0.72, 0.95, size=SIMS_PUB)
        pick_fav = rng.random((SIMS_PUB, n)) < q[:, None]
        correcto = np.where(pick_fav, gano_fav[None, :],
                            1 - gano_fav[None, :])
        p_ruido = p_fav[None, :] + rng.normal(0, SIGMA_RANK, (SIMS_PUB, n))
        rank_p = np.argsort(np.argsort(p_ruido, axis=1), axis=1) + 1
        pub = (rank_p * correcto).sum(axis=1)
        conf_pub.append(pub.mean() / maximo)
        conf_gana.append((nuestro > pub).mean() + 0.5 * (nuestro == pub).mean())
        # standard 1-vs-1 para comparar la naturaleza del edge
        std_pub = correcto.sum(axis=1)
        std_max_frac.append((h > std_pub).mean() + 0.5 * (h == std_pub).mean())

    print("=" * 70)
    print(f"ESPN — STANDARD vs CONFIDENCE, {n_sem} semanas 2011-2025")
    print("=" * 70)
    print(f"\nSTANDARD (favoritos): {100 * np.mean(hits_sem):.1f}% de "
          f"aciertos/semana")
    print(f"  P(semana 15+/16) con 1 entrada:  "
          f"{100 * hits15_1 / n_sem:.1f}% de las semanas")
    print(f"  P(semana 15+/16) con 20 entradas descorrelacionadas: "
          f"{100 * hits15_20 / n_sem:.1f}%")
    print(f"  P(ganarle a UN público en la semana): "
          f"{100 * np.mean(std_max_frac):.1f}%")

    print(f"\nCONFIDENCE (ranking por p calibrada):")
    print(f"  nuestro score medio:  {100 * np.mean(conf_nuestro):.1f}% del "
          f"máximo")
    print(f"  público medio:        {100 * np.mean(conf_pub):.1f}% del máximo")
    print(f"  P(ganarle a UN público en la semana): "
          f"{100 * np.mean(conf_gana):.1f}%")

    e_std, e_conf = np.mean(std_max_frac), np.mean(conf_gana)
    print(f"\n=> Edge por rival y semana (sobre el 50% neutro): "
          f"Standard +{100 * (e_std - 0.5):.1f} pts, "
          f"Confidence +{100 * (e_conf - 0.5):.1f} pts.")
    print("   En pool gigante el premio semanal lo definen las COLAS; el de"
          "\n   temporada, la consistencia — donde el edge por semana compone.")


if __name__ == "__main__":
    main()
