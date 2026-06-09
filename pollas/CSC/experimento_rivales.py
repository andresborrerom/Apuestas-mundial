#!/usr/bin/env python3
"""
Modelo de rivales realista (idea del usuario): generar ~100 rivales muestreando
su marcador de la distribución por partido, y testear ROBUSTEZ de nuestras
conclusiones (perturbación > copias idénticas; cuántos cupos) ante varios
"mundos" posibles de rivales.

Cada rival es de un arquetipo (ver motor.generar_field_mix):
  - "cal": muestrea de M (la idea del usuario: distribución implícita).
  - "hum": cerca del marcador modal (humano sesgado, no afina goles).
  - "opt": juega EV-máximo (rival sharp).

Probamos 3 mezclas y, en cada una, evmax vs perturbada (k=4, N=100).

    python pollas/CSC/experimento_rivales.py --mock /tmp/wc_grupos.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, simulacion_polla as sp
from pollas.CSC.cupos import matriz_de_evento
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]

MEZCLAS = {
    "calibrado puro (tu idea)": {"cal": 1.0, "hum": 0.0, "opt": 0.0},
    "humano-pesado":            {"cal": 0.3, "hum": 0.6, "opt": 0.1},
    "mixto realista":           {"cal": 0.4, "hum": 0.3, "opt": 0.3},
    "sharp-pesado":             {"cal": 0.3, "hum": 0.2, "opt": 0.5},
}


def fmt(x):
    return f"${x/1000:,.0f}k".replace(",", ".")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--mock")
    ap.add_argument("--participantes", type=int, default=100)
    ap.add_argument("--cupos", type=int, default=4)
    ap.add_argument("--sims", type=int, default=8000)
    args = ap.parse_args(argv)

    eventos = (json.load(open(args.mock, encoding="utf-8")) if args.mock
               else odds_api.bajar_eventos(args.api_key))
    matrices = [matriz_de_evento(c, "proporcional", 2.5)
                for c in (odds_api.consenso_evento(e) for e in eventos)
                if c["cuotas_1x2"]]
    N, k = args.participantes, args.cupos
    print(f"{len(matrices)} partidos · N={N} rivales · k={k} cupos · "
          f"{args.sims} torneos\n")

    print(f"{'mezcla de rivales':26} {'estrategia':12} {'E[util]':>9} "
          f"{'P(1º)':>7} {'P(premio)':>10}")
    print("-" * 70)
    for nombre, pesos in MEZCLAS.items():
        for estr, kw in [("evmax", {}), ("perturbada", {"n_swaps": 15, "pool": 40})]:
            r = sp.simular_utilidad(matrices, k, N, PARAMS, field=pesos,
                                    estrategia=estr, S=args.sims, semilla=7, **kw)
            etq = nombre if estr == "evmax" else ""
            print(f"{etq:26} {estr:12} {fmt(r['utilidad_media']):>9} "
                  f"{r['prob_primera']*100:>6.1f}% {r['prob_algun_premio']*100:>9.1f}%")
        print()
    print("Lectura: ¿la perturbación le gana a las copias idénticas en P(1º)/util\n"
          "en TODAS las mezclas de rivales? Si sí, la conclusión es robusta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
