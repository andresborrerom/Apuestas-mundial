#!/usr/bin/env python3
"""
COLFONDOS (Pollaya) — picks de TORNEO (outrights), una sola vez al inicio.

Reúsa el motor calibrado de LEMAITRE (sim de grupos + ratings calibrados a las
cuotas de campeón). Outrights de COLFONDOS y sus puntos:
  campeón 20 · subcampeón 15 · tercer puesto 10 · clasificados 2da ronda 4 c/u ·
  malla menos vencida 7.
(Goleador/MVP/portero/joven: ver investigación de mercados de jugador aparte.)

    python pollas/COLFONDOS/modelo_colfondos.py --mock /tmp/wc_grupos.json
"""
import argparse, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.LEMAITRE.modelo_lemaitre as M
import pollas.LEMAITRE.competencia_lemaitre as C


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=20000)
    args = ap.parse_args(argv)
    realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv = C.construir(args)
    S = realiz["S"]

    def topc(arr, n):
        return [(inv[i], v / S) for i, v in Counter(arr.tolist()).most_common(n)]

    print("=== CAMPEÓN (20 pts) ===")
    for t, p in topc(realiz["campeon"], 6): print(f"   {t:14} {p*100:4.1f}%")
    print("=== SUBCAMPEÓN (15 pts) ===")
    for t, p in topc(realiz["subcampeon"], 5): print(f"   {t:14} {p*100:4.1f}%")
    print("=== TERCER PUESTO (10 pts) — ganador del partido por el 3º ===")
    for t, p in topc(realiz["tercero"], 5): print(f"   {t:14} {p*100:4.1f}%")

    # P(avanzar a 2da ronda = ronda de 32): aparece como ocupante en algún slot R32
    NT = len(teams); adv = np.zeros(NT)
    for sl in M.R32:
        a, b = realiz["ent_r32"][sl[0]]
        for arr in (a, b):
            valido = arr[arr >= 0]          # ignorar slots de 3º sin asignar (-1)
            np.add.at(adv, valido, 1)
    Padv = adv / S
    print("\n=== CLASIFICADOS 2da RONDA (4 pts c/u) — P(avanzar), top 24 ===")
    orden = np.argsort(-Padv)
    for k, i in enumerate(orden[:24]):
        marca = "  <- pick seguro" if Padv[i] > 0.6 else (" (burbuja)" if Padv[i] > 0.4 else "")
        print(f"   {inv[i]:16} {Padv[i]*100:4.0f}%{marca}")

    # Malla menos vencida (7 pts): defensa fuerte que va lejos.
    # E[GC por partido de grupo] como calidad defensiva; ponderar por P(ir lejos).
    gc = realiz["gc"]; gc_pp = gc.mean(axis=1) / 3.0       # goles en contra por partido (grupos)
    # "ir lejos" ~ P(avanzar) * fuerza; usar P(semifinal) como proxy de muchos partidos
    semis = np.zeros(NT)
    for sl in (97, 98, 99, 100):                            # ganadores de cuartos = semifinalistas
        np.add.at(semis, realiz["ganador"][sl], 1)
    Psemi = semis / S
    # candidato malla: minimiza GC/partido entre los que tienen P(semi) decente
    cand = [(inv[i], gc_pp[i], Psemi[i]) for i in range(NT) if Psemi[i] > 0.08]
    cand.sort(key=lambda x: x[1])
    print("\n=== MALLA MENOS VENCIDA (7 pts) — mejor defensa entre los que van lejos ===")
    for t, g, ps in cand[:6]:
        print(f"   {t:14} {g:.2f} GC/partido · P(semi) {ps*100:.0f}%")
    print(f"   -> pick sugerido: {cand[0][0]} (aprox; depende de cuántos partidos juegue)")
    print("\n(Goleador/MVP/portero/joven: pendientes del agente de mercados de jugador.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
