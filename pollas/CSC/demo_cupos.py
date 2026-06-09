#!/usr/bin/env python3
"""
Demo: NUESTRA metodología (EV-máximo + sesgo) con 5 cupos = lo que escribimos.

Filas = partidos, columnas = los 5 cupos. NO se sortea nada: el cupo 1 es el
relleno EV-máximo+sesgo, y los cupos 2..5 lo COPIAN salvo en los partidos
casi-empatados (donde se cambia al 2º mejor relleno, que cuesta casi 0 puntos
esperados). Así se ve la "aleatoriedad mínima": casi todo idéntico, variación
solo donde da igual.

    python pollas/CSC/demo_cupos.py [--mock /tmp/wc_grupos.json]
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, cuotas, marcadores, simulacion_polla as sp
from motor.simulacion_polla import ev_grid
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
K = 5


def abr(n):
    return n.split()[0][:3].upper()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))

    nombres, Msesgo, gaps = [], [], []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        p = cuotas.a_probabilidades(c["cuotas_1x2"], "proporcional")
        po = cuotas.a_probabilidades(c["cuotas_ou"], "proporcional")[1] if c["cuotas_ou"] else None
        M = marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=po)["matriz"]
        Ms = marcadores.aplicar_sesgo_goles(M, 0.05)
        nombres.append(f"{abr(c['home'])}-{abr(c['away'])}")
        Msesgo.append(Ms)
        ev = ev_grid(Ms, PARAMS, 7).ravel()
        o = np.sort(ev)[::-1]
        gaps.append(o[0] - o[1])   # brecha EV entre 1º y 2º mejor relleno

    # generar los 5 cupos con perturbación mínima
    ph, pa = sp.generar_nuestras(Msesgo, K, PARAMS, estrategia="perturbada",
                                 rng=np.random.default_rng(7), n_swaps=15, pool=40)
    fills = [[f"{ph[c, i]}-{pa[c, i]}" for c in range(K)] for i in range(len(nombres))]
    distintos = [len(set(f)) for f in fills]
    varian = [i for i, d in enumerate(distintos) if d > 1]
    fijos = [i for i, d in enumerate(distintos) if d == 1]

    # mostrar 10: hasta 5 que varían + completar con fijos
    rng = np.random.default_rng(1)
    sel_v = sorted(rng.choice(varian, min(5, len(varian)), replace=False)) if varian else []
    sel_f = sorted(rng.choice(fijos, min(10 - len(sel_v), len(fijos)), replace=False))
    sel = list(sel_v) + list(sel_f)

    print(f"\n{len(varian)} de {len(nombres)} partidos VARÍAN entre los 5 cupos; "
          f"los otros {len(fijos)} son IDÉNTICOS (alta confianza).\n")
    print(f"{'partido':>9} | " + " ".join(f"cupo{c+1}" for c in range(K)) + " |  brecha-EV  tipo")
    print("-" * 64)
    for i in sel:
        row = " ".join(f"{fills[i][c]:>5}" for c in range(K))
        tipo = "PERTURBADO" if distintos[i] > 1 else "fijo"
        print(f"{nombres[i]:>9} | {row} | {gaps[i]:>9.2f}  {tipo}")

    g_var = np.mean([gaps[i] for i in varian]) if varian else 0
    g_fij = np.mean([gaps[i] for i in fijos]) if fijos else 0
    print(f"\nBrecha-EV media: partidos perturbados={g_var:.2f} (casi empate) vs "
          f"fijos={g_fij:.2f} (claros).")
    print("Es decir: solo perturbamos donde el 2º mejor cuesta casi nada → "
          "aleatoriedad MÍNIMA, sin alejarnos del modelo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
