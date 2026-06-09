#!/usr/bin/env python3
"""
¿Cuántos cupos comprar en CSC para maximizar la utilidad esperada?

Baja las cuotas de la fase de grupos, construye el modelo de cada partido y
simula la polla (Monte Carlo) para distintos números de cupos, recomendando
el k que maximiza utilidad = premios esperados − costo.

Uso:
    export ODDS_API_KEY=tu_key
    python pollas/CSC/cupos.py --participantes 120

    # sin red, con datos guardados:
    python pollas/CSC/cupos.py --mock /tmp/wc_grupos.json --participantes 120

Recuerda: es SUMA CERO. Solo hay utilidad positiva si nuestro relleno supera
al del participante promedio (parámetro --field-skill). Los resultados son muy
sensibles a --participantes y --field-skill: por eso se muestra sensibilidad.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import cuotas, marcadores, odds_api, simulacion_polla as sp
from pollas.CSC.reglas import RONDAS

PARAMS_GRUPOS = RONDAS["primera"]  # (1, 2, 3)


def matriz_de_evento(c, metodo, linea_pref):
    """Distribución de marcadores de un evento (consenso ya calculado)."""
    p = cuotas.a_probabilidades(c["cuotas_1x2"], metodo)
    p_over = None
    if c["cuotas_ou"]:
        p_over = cuotas.a_probabilidades(c["cuotas_ou"], metodo)[1]
    aj = marcadores.ajustar_lambdas(
        p[0], p[1], p[2], p_over=p_over, linea=c["linea"] or linea_pref)
    return aj["matriz"]


def fmt(x):
    return f"${x:,.0f}".replace(",", ".")


def main(argv=None):
    p = argparse.ArgumentParser(description="Optimizar nº de cupos en CSC")
    p.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    p.add_argument("--mock", help="JSON de eventos (sin red)")
    p.add_argument("--participantes", type=int, default=100,
                   help="total de cupos en la polla (incluye los tuyos)")
    p.add_argument("--precio", type=float, default=100_000)
    p.add_argument("--field-skill", type=float, default=0.3,
                   help="qué tan buenos son los rivales: 0 casual, 1 óptimos")
    p.add_argument("--estrategia", default="evmax",
                   choices=["diversificada", "evmax"],
                   help="evmax (copias idénticas, suele ganar) o diversificada")
    p.add_argument("--casual-concentracion", type=float, default=3.0,
                   help="qué tan 'modal/humano' es el rival casual (>1 más realista)")
    p.add_argument("--T", type=float, default=0.6, help="diversidad (estrategia diversificada)")
    p.add_argument("--max-cupos", type=int, default=12)
    p.add_argument("--sims", type=int, default=3000)
    p.add_argument("--ruido-extra", type=float, default=0.0,
                   help="ruido de eliminatorias sobre el puntaje total (puntos)")
    p.add_argument("--metodo-margen", default="proporcional")
    p.add_argument("--sensibilidad", action="store_true",
                   help="probar varios field-skill")
    args = p.parse_args(argv)

    # 1) eventos
    if args.mock:
        with open(args.mock, encoding="utf-8") as f:
            eventos = json.load(f)
    elif args.api_key:
        eventos = odds_api.bajar_eventos(args.api_key)
    else:
        p.error("se requiere --api-key/ODDS_API_KEY o --mock")

    # 2) matrices por partido
    print(f"Construyendo modelos de {len(eventos)} partidos...", flush=True)
    matrices = []
    for ev in eventos:
        c = odds_api.consenso_evento(ev)
        if c["cuotas_1x2"]:
            matrices.append(matriz_de_evento(c, args.metodo_margen, 2.5))
    print(f"  {len(matrices)} partidos con cuotas. Simulando "
          f"({args.sims} torneos)...\n", flush=True)

    N = args.participantes

    def correr(skill):
        return sp.recomendar_cupos(
            matrices, N, PARAMS_GRUPOS, max_cupos=args.max_cupos,
            field_skill=skill, estrategia=args.estrategia, T=args.T,
            precio=args.precio, S=args.sims, ruido_extra=args.ruido_extra,
            concentracion=args.casual_concentracion, semilla=42)

    skills = [0.1, 0.3, 0.6] if args.sensibilidad else [args.field_skill]

    for skill in skills:
        rec = correr(skill)
        print(f"=== field-skill = {skill}  |  N = {N} cupos  |  "
              f"pot = {fmt(N*args.precio)}  |  estrategia = {args.estrategia} ===")
        print(f"{'cupos':>5} {'costo':>12} {'E[premio]':>14} {'E[utilidad]':>14} "
              f"{'P(premio)':>10} {'slots top5':>11}")
        for r in rec["tabla"]:
            print(f"{r['k']:>5} {fmt(r['costo']):>12} {fmt(r['ganancia_media']):>14} "
                  f"{fmt(r['utilidad_media']):>14} {r['prob_algun_premio']*100:>9.1f}% "
                  f"{r['slots_top5_medio']:>11.2f}")
        m = rec["mejor"]
        signo = "positiva ✅" if m["utilidad_media"] > 0 else "NEGATIVA ⚠️"
        print(f"  → óptimo: {rec['k_optimo']} cupo(s)  |  "
              f"E[utilidad] = {fmt(m['utilidad_media'])} ({signo})\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
