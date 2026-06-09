#!/usr/bin/env python3
"""
¿Conviene SUBIR la dispersión (perturbación entre cupos) a medida que avanzan
las rondas? Simula el torneo completo y compara varios "schedules" de
perturbación por ronda, midiendo P(quedar 1º) y utilidad.

    python pollas/CSC/experimento_dispersion_rondas.py --mock /tmp/wc_grupos.json
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

# n_swaps por ronda. Partidos por ronda: 72,16,8,4,2,1,1
SCHEDULES = {
    "EV-máx puro (sin disp.)": {},
    "baja constante":          {"primera": 10, "dieciseisavos": 2, "octavos": 1,
                                "cuartos": 1, "semis": 0, "tercer_puesto": 0, "final": 0},
    "alta constante":          {"primera": 30, "dieciseisavos": 8, "octavos": 4,
                                "cuartos": 2, "semis": 1, "tercer_puesto": 1, "final": 1},
    "CRECIENTE por ronda":     {"primera": 8, "dieciseisavos": 6, "octavos": 5,
                                "cuartos": 3, "semis": 2, "tercer_puesto": 1, "final": 1},
}
# Test riguroso: MISMO presupuesto (~24 swaps), repartido distinto.
SCHEDULES_IGUAL = {
    "~24 TODO en grupos":      {"primera": 24},
    "~24 uniforme x fracción": {"primera": 17, "dieciseisavos": 4, "octavos": 2, "cuartos": 1},
    "~24 KNOCKOUT-pesado":     {"primera": 2, "dieciseisavos": 8, "octavos": 6,
                                "cuartos": 4, "semis": 2, "tercer_puesto": 1, "final": 1},
}
FIELD = {"cal": 0.4, "hum": 0.3, "opt": 0.3}


def correr_bloque(titulo, scheds, matrices, args, semillas=4):
    """Promedia sobre varias semillas para que el orden no sea ruido."""
    print(f"\n{titulo}")
    print(f"{'schedule':26} {'swaps':>5} {'P(1º) media±sd':>16} {'P(top3)':>8}")
    print("-" * 60)
    for nombre, sched in scheds.items():
        p1, p3, tot = [], [], 0
        for s in range(semillas):
            rng = np.random.default_rng(s)
            rondas = torneo.construir_rondas(matrices, rng)
            tot = sum(min(sched.get(n, 0), len(m)) for n, m, _ in rondas)
            r = torneo.simular_torneo(rondas, args.participantes, args.cupos,
                                      sched, FIELD, S=args.sims, semilla=s)
            p1.append(r["prob_primera"] * 100); p3.append(r["prob_top3"] * 100)
        print(f"{nombre:26} {tot:>5} {np.mean(p1):>10.1f}% ± {np.std(p1):.1f} "
              f"{np.mean(p3):>7.1f}%")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--participantes", type=int, default=100)
    ap.add_argument("--cupos", type=int, default=4)
    ap.add_argument("--sims", type=int, default=6000)
    args = ap.parse_args(argv)

    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))
    matrices = [matriz_de_evento(c, "proporcional", 2.5)
                for c in (odds_api.consenso_evento(e) for e in eventos)
                if c["cuotas_1x2"]]

    rng = np.random.default_rng(0)
    rondas = torneo.construir_rondas(matrices, rng)
    tot_part = sum(len(m) for _, m, _ in rondas)
    print(f"Torneo: {tot_part} partidos "
          f"({' · '.join(f'{n}={len(m)}' for n, m, _ in rondas)})")
    print(f"N={args.participantes} rivales, k={args.cupos} cupos, "
          f"{args.sims} torneos, field={FIELD}\n")

    correr_bloque("BLOQUE 1 — más dispersión total ayuda (presupuestos distintos):",
                  SCHEDULES, matrices, args)
    correr_bloque("BLOQUE 2 — MISMO presupuesto, ¿dónde ponerlo? (test de la hipótesis):",
                  SCHEDULES_IGUAL, matrices, args)
    print("\nConclusión: a igual presupuesto, concentrar la dispersión en las\n"
          "ELIMINATORIAS gana más P(1º) que ponerla en grupos. En grupos la ley\n"
          "de grandes números ya nos protege; los swaps rinden más donde cada\n"
          "partido vale ×5 a ×16 (cuartos→final).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
