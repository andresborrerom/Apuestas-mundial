#!/usr/bin/env python3
"""
Demo pedagógico (parte 2): cómo el EV-MÁXIMO elige NUESTRO relleno.

A diferencia de demo_modelo.py (que SORTEA marcadores de la distribución), aquí
NO se sortea: para cada partido se calcula, para cada marcador candidato (a-b),
los PUNTOS ESPERADOS bajo las reglas CSC (fase de grupos) y se elige el máximo.
Ese es el marcador que escribimos en el formulario.

Puntos esperados de predecir (a, b):
  EV = P(acertar tendencia 1X2)·res
     + P(local marque a)·valor(a)
     + P(visita marque b)·valor(b)
donde valor(0)=2 (cero) y valor(g>0)=g+3 (base), res=1 (ronda "primera").

    python pollas/CSC/demo_evmax.py [--mock /tmp/wc_grupos.json]
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, cuotas, marcadores
from motor.simulacion_polla import ev_grid
from pollas.CSC.reglas import RONDAS

RES, CERO, BASE = RONDAS["primera"]   # (1, 2, 3)


def abr(n):
    return n.split()[0][:3].upper()


def valor(g):
    return CERO if g == 0 else g + BASE


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))

    modelos = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        p = cuotas.a_probabilidades(c["cuotas_1x2"], "proporcional")
        po = cuotas.a_probabilidades(c["cuotas_ou"], "proporcional")[1] if c["cuotas_ou"] else None
        aj = marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=po)
        modelos.append((c["home"], c["away"], aj))
    modelos.sort(key=lambda m: marcadores.prob_1x2(m[2]["matriz"])[0])
    idx = [1, len(modelos)//4, len(modelos)//2, 3*len(modelos)//4, len(modelos)-2]

    for i in idx:
        home, away, aj = modelos[i]
        M = aj["matriz"]
        margH, margA = M.sum(1), M.sum(0)
        pL, pD, pV = marcadores.prob_1x2(M)
        EV = ev_grid(M, (RES, CERO, BASE), 7)
        cands = sorted(((EV[a, b], a, b) for a in range(7) for b in range(7)),
                       reverse=True)[:5]
        modal = np.unravel_index(np.argmax(M), M.shape)
        evmax = (cands[0][1], cands[0][2])
        # con sesgo 0.05
        Ms = marcadores.aplicar_sesgo_goles(M, 0.05)
        EVs = ev_grid(Ms, (RES, CERO, BASE), 7)
        evmax_s = np.unravel_index(np.argmax(EVs), EVs.shape)

        print(f"\n{'='*72}\n{abr(home)}-{abr(away)}  ({home} vs {away})")
        print(f"  λ {aj['lambda_local']:.2f}-{aj['lambda_visita']:.2f} | "
              f"P(L/E/V)={pL*100:.0f}/{pD*100:.0f}/{pV*100:.0f} | "
              f"marcador MÁS PROBABLE (modal) = {modal[0]}-{modal[1]} "
              f"(P={M[modal]*100:.0f}%)")
        print(f"  {'pred':>5} | {'tendencia':>18} | {'gol '+abr(home):>14} | "
              f"{'gol '+abr(away):>14} | {'EV':>5}")
        for ev, a, b in cands:
            psign = pL if a > b else (pD if a == b else pV)
            res_p = RES * psign
            gh = valor(a) * margH[a]
            ga = valor(b) * margA[b]
            tend = "L" if a > b else ("E" if a == b else "V")
            etq = " <- EV-MÁX" if (a, b) == evmax else ""
            etq += " (modal)" if (a, b) == tuple(modal) else ""
            print(f"  {a}-{b:>3} | {tend} P={psign*100:>3.0f}% -> {res_p:>4.2f} | "
                  f"P{a}={margH[a]*100:>3.0f}% x{valor(a)} = {gh:>4.2f} | "
                  f"P{b}={margA[b]*100:>3.0f}% x{valor(b)} = {ga:>4.2f} | "
                  f"{ev:>5.2f}{etq}")
        msg = f"  -> RELLENO: {evmax[0]}-{evmax[1]}"
        if tuple(modal) != evmax:
            msg += f"  (¡distinto del modal {modal[0]}-{modal[1]}!)"
        if tuple(evmax_s) != evmax:
            msg += f"  | con sesgo 0.05 -> {evmax_s[0]}-{evmax_s[1]}"
        print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
