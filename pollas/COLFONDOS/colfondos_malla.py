#!/usr/bin/env python3
"""
COLFONDOS — MALLA MENOS VENCIDA (menos goles encajados EN TOTAL en el torneo).

Punto fino (del usuario): NO es goles/partido, es el TOTAL. El campeón juega 7
partidos contra rivales duros -> acumula. Una defensa sólida que sale temprano
(o por penales, que no suman goles) puede encajar MENOS en total. Aquí se cuenta
los goles en contra de cada equipo en TODOS sus partidos (grupos + eliminatorias,
90'/120'; penales no cuentan) y se mide P(equipo tenga el MÍNIMO).

    python pollas/COLFONDOS/colfondos_malla.py --mock /tmp/wc_grupos.json
"""
import argparse, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.COLFONDOS.competencia_colfondos as CC


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=20000)
    args = ap.parse_args(argv)
    realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv = CC.construir(args)
    S = realiz["S"]; NT = len(teams)
    idx = np.arange(S)

    # goles en contra TOTALES = grupos + eliminatorias
    gc_tot = realiz["gc"].copy().astype(float)        # (NT,S) grupos
    n_part = np.full((NT, S), 3.0)                     # partidos jugados (grupos=3)
    for sl, (A, B) in realiz["occ"].items():
        gA, gB = realiz["score"][sl]
        mA = A >= 0; mB = B >= 0
        np.add.at(gc_tot, (A[mA], idx[mA]), gB[mA])    # A encaja los goles de B
        np.add.at(gc_tot, (B[mB], idx[mB]), gA[mB])
        np.add.at(n_part, (A[mA], idx[mA]), 1.0)
        np.add.at(n_part, (B[mB], idx[mB]), 1.0)

    # P(cada equipo tenga el MÍNIMO de goles en contra del torneo)
    minrow = gc_tot == gc_tot.min(axis=0, keepdims=True)
    pmin = minrow.sum(axis=1) / S / np.maximum(minrow.sum(axis=0).mean(), 1) * 0 + minrow.mean(axis=1)
    # (si hay empate en el mínimo, cuenta a todos los empatados)
    pmin = minrow.mean(axis=1)
    orden = np.argsort(-pmin)
    print("=== MALLA MENOS VENCIDA: P(tener el MÍNIMO de goles en contra) ===")
    print(f"{'equipo':16} {'P(min)':>7} {'E[GC tot]':>9} {'E[part]':>7} {'GC/part':>8} {'P(campeón)':>10}")
    pcamp = np.array([Counter(realiz['campeon'].tolist()).get(i, 0) / S for i in range(NT)])
    for i in orden[:12]:
        gcm = gc_tot[i].mean(); npm = n_part[i].mean()
        print(f"{inv[i]:16} {pmin[i]*100:6.1f}% {gcm:9.2f} {npm:7.2f} {gcm/npm:8.2f} {pcamp[i]*100:9.1f}%")
    print("\nLectura: el ganador suele NO ser el campeón (juega más partidos y encaja")
    print("más en total), sino una defensa sólida que cae en octavos/cuartos con poco")
    print("acumulado. Compara Argentina vs España abajo.")
    for t in ("Argentina", "Spain", "France", "England", "Brazil", "Belgium", "Croatia", "Morocco"):
        if t in tid:
            i = tid[t]
            print(f"  {t:12} P(min)={pmin[i]*100:4.1f}%  E[GC]={gc_tot[i].mean():.2f}  "
                  f"E[part]={n_part[i].mean():.2f}  P(camp)={pcamp[i]*100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
