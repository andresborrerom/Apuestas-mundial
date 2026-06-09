#!/usr/bin/env python3
"""
Experimento de COLAS: ¿una aleatoriedad mínima sube la probabilidad de que UNA
de nuestras entradas quede de primera, sin alejarnos del modelo? ¿Y cómo queda
el modelo vs rellenos hechos a mano en los peores escenarios?

Simula el ranking de la polla (Monte Carlo) y compara, para k cupos:
  - evmax        : k copias idénticas del EV-máximo (correlación total)
  - perturbada-S : EV-máximo + cambiar al 2º mejor en S partidos casi empatados
  - diversificada: muestreo softmax (referencia de "demasiado azar")
  - hechos a mano (k copias): siempre 2-1, agresivo (goles altos), modal

Métricas: E[utilidad], utilidad p10 (peor 10% = cola), P(1º), P(top3), P(premio).

Uso:
    python pollas/CSC/experimento_colas.py --mock /tmp/wc_grupos.json \
        --participantes 120 --field-skill 0.5 --cupos 3
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.cupos import matriz_de_evento
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]
G = 7


def fills_constante(gh, ga, k, Mn):
    return (np.full((k, Mn), gh), np.full((k, Mn), ga))


def fills_modal(matrices, k):
    h = [int(np.unravel_index(np.argmax(M), M.shape)[0]) for M in matrices]
    a = [int(np.unravel_index(np.argmax(M), M.shape)[1]) for M in matrices]
    return (np.tile(h, (k, 1)), np.tile(a, (k, 1)))


def fills_evmax_sesgo(matrices, alpha, k):
    Ms = [marcadores.aplicar_sesgo_goles(M, alpha) for M in matrices]
    h, a = sp.fill_evmax(Ms, PARAMS, G)
    return (np.tile(h, (k, 1)), np.tile(a, (k, 1)))


def fmt(x):
    return f"${x:,.0f}".replace(",", ".")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--mock")
    ap.add_argument("--participantes", type=int, default=120)
    ap.add_argument("--field-skill", type=float, default=0.5)
    ap.add_argument("--cupos", type=int, default=3)
    ap.add_argument("--sims", type=int, default=8000)
    ap.add_argument("--precio", type=float, default=100_000)
    args = ap.parse_args(argv)

    if args.mock:
        eventos = json.load(open(args.mock, encoding="utf-8"))
    elif args.api_key:
        eventos = odds_api.bajar_eventos(args.api_key)
    else:
        ap.error("se requiere --api-key/ODDS_API_KEY o --mock")

    print(f"Construyendo modelos de {len(eventos)} partidos...", flush=True)
    matrices = []
    for ev in eventos:
        c = odds_api.consenso_evento(ev)
        if c["cuotas_1x2"]:
            matrices.append(matriz_de_evento(c, "proporcional", 2.5))
    Mn = len(matrices)
    k, N = args.cupos, args.participantes
    print(f"  {Mn} partidos. k={k} cupos, N={N}, field-skill={args.field_skill}, "
          f"{args.sims} torneos.\n", flush=True)

    comun = dict(field_skill=args.field_skill, precio=args.precio,
                 S=args.sims, semilla=7)

    def correr(nombre, **kw):
        r = sp.simular_utilidad(matrices, k, N, PARAMS, **comun, **kw)
        return (nombre, r)

    resultados = [
        correr("evmax (idénticas)", estrategia="evmax"),
        correr("perturbada n=5", estrategia="perturbada", n_swaps=5),
        correr("perturbada n=10", estrategia="perturbada", n_swaps=10),
        correr("perturbada n=18", estrategia="perturbada", n_swaps=18),
        correr("diversificada", estrategia="diversificada", T=0.6),
    ]
    # hechos a mano (k copias idénticas)
    for nombre, fills in [
        ("mano: siempre 2-1", fills_constante(2, 1, k, Mn)),
        ("mano: modal", fills_modal(matrices, k)),
        ("mano: agresivo (α=0.4)", fills_evmax_sesgo(matrices, 0.4, k)),
    ]:
        r = sp.simular_utilidad(matrices, k, N, PARAMS, **comun, fills=fills)
        resultados.append((nombre, r))

    print(f"{'estrategia':24} {'E[util]':>12} {'util p10':>12} "
          f"{'P(1º)':>7} {'P(top3)':>8} {'P(premio)':>10} {'slots':>6}")
    print("-" * 84)
    for nombre, r in resultados:
        print(f"{nombre:24} {fmt(r['utilidad_media']):>12} "
              f"{fmt(r['utilidad_p10']):>12} "
              f"{r['prob_primera']*100:>6.1f}% {r['prob_top3']*100:>7.1f}% "
              f"{r['prob_algun_premio']*100:>9.1f}% {r['slots_top5_medio']:>6.2f}")

    print("\nLectura: 'util p10' = peor 10% (cola). 'P(1º)' = prob. de que al "
          "menos un cupo\nquede de primero. Buscamos subir P(1º)/cola sin "
          "bajar E[util].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
