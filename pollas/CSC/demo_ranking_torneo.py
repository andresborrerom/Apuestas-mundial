#!/usr/bin/env python3
"""
Libro mayor del TORNEO COMPLETO (grupos + eliminatorias, puntos que escalan) +
la distribución de la utilidad rota por DECILES. Así se ve de dónde sale el
E[util]: casi todo de los deciles altos (premio top-heavy).

    python pollas/CSC/demo_ranking_torneo.py --mock /tmp/wc_grupos.json
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, torneo
from pollas.CSC.cupos import matriz_de_evento

FIELD = {"cal": 0.4, "hum": 0.3, "opt": 0.3}
SCHEDULE = {"primera": 12, "dieciseisavos": 8, "octavos": 5, "cuartos": 3,
            "semis": 2, "tercer_puesto": 1, "final": 1}


def money(x):
    s = f"${abs(x):,.0f}".replace(",", ".")
    return ("-" + s) if x < 0 else s


def correr(matrices, N, k, precio, S, muestra):
    rng = np.random.default_rng(0)
    rondas = torneo.construir_rondas(matrices, rng)
    r = torneo.simular_torneo(rondas, N, k, SCHEDULE, FIELD, precio=precio,
                              S=S, semilla=7, detalle=True)
    util, gan, mejor, rk = (r["util"], r["ganancia"], r["mejor_rango"],
                            r["rangos_nuestros"])

    print(f"\n{'='*70}\n{k} CUPOS · {N} participantes · pot {money(r['pot'])} "
          f"· {S} simulaciones (torneo completo)")

    print(f"\nMuestra del libro mayor (puesto FINAL de cada cupo):")
    cab = " ".join(f"c{c+1:>2}" for c in range(k))
    print(f" {'sim':>4} | {cab} | {'mejor':>5} | {'premio':>12} | utilidad")
    print("-" * (9 + 4 * k + 34))
    for s in range(muestra):
        cols = " ".join(f"{rk[c, s]:>3}" for c in range(k))
        prem = money(gan[s]) if gan[s] > 0 else "—"
        print(f" {'#'+str(s+1):>4} | {cols} | {mejor[s]:>4}º | {prem:>12} | "
              f"{money(util[s])}")

    # --- distribución de la utilidad por DECILES ---
    orden = np.sort(util)
    print(f"\nDISTRIBUCIÓN DE LA UTILIDAD por deciles (10% de las sims c/u):")
    print(f"  {'decil':>5} | {'util media':>13} | {'desde':>12} {'hasta':>12}")
    print("  " + "-" * 50)
    medias = []
    for d in range(10):
        chunk = orden[d * S // 10:(d + 1) * S // 10]
        medias.append(chunk.mean())
        print(f"  {d+1:>4}º | {money(chunk.mean()):>13} | "
              f"{money(chunk[0]):>12} {money(chunk[-1]):>12}")
    print(f"\n  E[util] = {money(util.mean())}  (= promedio de las 10 medias)")
    print(f"  El decil 10 aporta {medias[9]/10:,.0f} al E[util]; "
          f"los deciles que pierden: {sum(1 for m in medias if m<0)}/10.")
    print(f"  quedó 1º en {(mejor==1).mean()*100:.1f}% · con premio en "
          f"{(gan>0).mean()*100:.1f}% · pierde (util<0) en {(util<0).mean()*100:.1f}%")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--cupos", type=int, default=4)
    ap.add_argument("--precio", type=float, default=100_000)
    ap.add_argument("--sims", type=int, default=8000)
    ap.add_argument("--muestra", type=int, default=12)
    ap.add_argument("--Ns", type=int, nargs="*", default=[80, 100])
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))
    matrices = [matriz_de_evento(c, "proporcional", 2.5)
                for c in (odds_api.consenso_evento(e) for e in eventos)
                if c["cuotas_1x2"]]
    for N in args.Ns:
        correr(matrices, N, args.cupos, args.precio, args.sims, args.muestra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
