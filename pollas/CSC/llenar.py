#!/usr/bin/env python3
"""
Comando para CSC: baja las cuotas del Mundial, calcula el relleno ÓPTIMO de
cada partido de un día y lo imprime (y opcionalmente lo guarda en CSV) listo
para copiar al formulario de la Super Polla de los Pollos.

Uso típico (rellenar los partidos de mañana):
    export ODDS_API_KEY=tu_key_de_the-odds-api.com
    python pollas/CSC/llenar.py

Otros ejemplos:
    python pollas/CSC/llenar.py --date 2026-06-12 --round primera
    python pollas/CSC/llenar.py --csv marcadores.csv
    python pollas/CSC/llenar.py --list-sports          # ver claves de torneo
    python pollas/CSC/llenar.py --mock pollas/CSC/ejemplo_odds.json  # sin red

Recordatorio: CSC exige enviar TODA una ronda antes de su primer partido (ver
tabla de deadlines del reglamento). El comando avisa el deadline de la ronda.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import numpy as np
from motor import analizar_partido
from motor import odds_api, cuotas, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS


# Dispersión recomendada por ronda (n_swaps): poca en grupos (la ley de grandes
# números ya protege), mucha en eliminatorias (pocos partidos, mucho valor →
# cada swap descorrelaciona más). Validado en experimento_dispersion_rondas.py.
DISPERSION_POR_RONDA = {
    "primera": 12, "dieciseisavos": 8, "octavos": 5,
    "cuartos": 3, "semis": 2, "tercer_puesto": 1, "final": 1,
}


# Calendario oficial Mundial 2026 -> ronda CSC y deadline de envío (hora Col).
# (inicio_ronda, fin_ronda, nombre_ronda, deadline_texto)
CALENDARIO = [
    (date(2026, 6, 11), date(2026, 6, 27), "primera",       "11/06/2026 1:59 PM"),
    (date(2026, 6, 28), date(2026, 7, 3),  "dieciseisavos", "28/06/2026 1:59 PM"),
    (date(2026, 7, 4),  date(2026, 7, 7),  "octavos",       "04/07/2026 11:59 AM"),
    (date(2026, 7, 9),  date(2026, 7, 11), "cuartos",       "09/07/2026 2:59 PM"),
    (date(2026, 7, 14), date(2026, 7, 15), "semis",         "14/07/2026 1:59 PM"),
    (date(2026, 7, 18), date(2026, 7, 18), "tercer_puesto", "18/07/2026 3:59 PM"),
    (date(2026, 7, 19), date(2026, 7, 19), "final",         "19/07/2026 1:59 PM"),
]

# Traducción de nombres para mostrar (la API los da en inglés). Solo display.
ES = {
    "United States": "Estados Unidos", "Mexico": "México", "Canada": "Canadá",
    "Brazil": "Brasil", "South Korea": "Corea del Sur", "Japan": "Japón",
    "Saudi Arabia": "Arabia Saudita", "South Africa": "Sudáfrica",
    "Morocco": "Marruecos", "Croatia": "Croacia", "Switzerland": "Suiza",
    "Germany": "Alemania", "Spain": "España", "England": "Inglaterra",
    "France": "Francia", "Belgium": "Bélgica", "Netherlands": "Países Bajos",
    "Wales": "Gales", "Ivory Coast": "Costa de Marfil", "Egypt": "Egipto",
}


def inferir_ronda(d):
    for ini, fin, nombre, _ in CALENDARIO:
        if ini <= d <= fin:
            return nombre
    return None


def deadline_de_ronda(nombre):
    for _, _, n, dl in CALENDARIO:
        if n == nombre:
            return dl
    return None


def es(nombre):
    return ES.get(nombre, nombre)


def main(argv=None):
    p = argparse.ArgumentParser(description="Relleno óptimo de marcadores CSC")
    p.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"),
                   help="API key de the-odds-api.com (o variable ODDS_API_KEY)")
    p.add_argument("--sport", default=odds_api.SPORT_MUNDIAL,
                   help=f"clave del torneo (default {odds_api.SPORT_MUNDIAL})")
    p.add_argument("--date", help="fecha objetivo YYYY-MM-DD (default: mañana)")
    p.add_argument("--all", action="store_true",
                   help="volcar TODA la fase de grupos (ignora --date)")
    p.add_argument("--tz", default="America/Bogota", help="zona horaria")
    p.add_argument("--round", default="auto",
                   help="ronda CSC o 'auto' para inferir por fecha")
    p.add_argument("--regions", default="us,uk,eu,au")
    p.add_argument("--line", type=float, default=2.5, help="línea Over/Under preferida")
    p.add_argument("--metodo-margen", default="proporcional",
                   choices=["proporcional", "aditivo", "potencia", "shin"])
    p.add_argument("--sesgo-goles", type=float, default=0.05,
                   help="sesgo hacia gol=1 (validado: ~+0.03 pts/partido). 0 lo apaga")
    p.add_argument("--rico", action="store_true",
                   help="modelo enriquecido (curva O/U + O/U por equipo, gratis). "
                        "1 llamada API por partido; recomendado en eliminatorias")
    p.add_argument("--cupos", type=int, default=1,
                   help="generar K planillas perturbadas (descorrelacionadas)")
    p.add_argument("--n-swaps", type=int, default=-1,
                   help="partidos a perturbar por cupo extra (-1 = auto por ronda: "
                        "poco en grupos, mucho en eliminatorias)")
    p.add_argument("--csv", help="guardar resultado en este archivo CSV")
    p.add_argument("--mock", help="leer JSON de eventos de un archivo (sin red)")
    p.add_argument("--list-sports", action="store_true",
                   help="listar claves de torneo y salir")
    args = p.parse_args(argv)

    tz = ZoneInfo(args.tz)

    if args.list_sports:
        if not args.api_key:
            p.error("se requiere --api-key o ODDS_API_KEY")
        for s in odds_api.listar_deportes(args.api_key):
            if "soccer" in s.get("key", ""):
                print(f"  {s['key']:32s} {s.get('title','')}")
        return 0

    # 1) obtener eventos (red o mock)
    if args.mock:
        with open(args.mock, encoding="utf-8") as f:
            eventos = json.load(f)
    else:
        if not args.api_key:
            p.error("se requiere --api-key o ODDS_API_KEY (o usa --mock)")
        eventos = odds_api.bajar_eventos(
            args.api_key, sport=args.sport,
            regions=args.regions, markets="h2h,totals")

    # 2) fecha objetivo (o toda la fase de grupos con --all)
    if args.all:
        objetivo = None
        print(f"\n📅 TODA LA FASE DE GRUPOS  |  deadline envío: "
              f"{deadline_de_ronda('primera')}")
    else:
        objetivo = (datetime.strptime(args.date, "%Y-%m-%d").date() if args.date
                    else (datetime.now(tz) + timedelta(days=1)).date())
        ronda = inferir_ronda(objetivo) if args.round == "auto" else args.round
        if ronda not in RONDAS:
            p.error(f"no pude determinar la ronda para {objetivo}; pásala con "
                    f"--round (opciones: {list(RONDAS)})")
        print(f"\n📅 Partidos del {objetivo}  |  ronda: {ronda.upper()}  "
              f"|  deadline envío: {deadline_de_ronda(ronda) or 's/d'}")
    print(f"   Cuotas: consenso de casas (mediana) · margen quitado por "
          f"método '{args.metodo_margen}'\n")

    # 3) filtrar y calcular
    filas = []
    mats = []  # matrices alineadas con filas (para perturbar múltiples cupos)
    for ev in eventos:
        inicio = ev.get("commence_time")
        if not inicio:
            continue
        dt_local = datetime.fromisoformat(inicio.replace("Z", "+00:00")).astimezone(tz)
        if objetivo is not None and dt_local.date() != objetivo:
            continue
        ronda_ev = (inferir_ronda(dt_local.date()) if args.round == "auto"
                    else args.round)
        if ronda_ev not in RONDAS:
            continue
        c = odds_api.consenso_evento(ev, linea_pref=args.line)
        if not c["cuotas_1x2"]:
            continue
        matriz_rica = None
        if args.rico and args.api_key and ev.get("id"):
            try:  # modelo enriquecido: curva O/U + O/U por equipo (gratis)
                rc = odds_api.consenso_rico(
                    odds_api.bajar_evento_mercados(args.api_key, ev["id"]))
                pp = cuotas.a_probabilidades(rc["cuotas_1x2"], args.metodo_margen)
                matriz_rica = marcadores.ajustar_lambdas_rico(
                    pp[0], pp[1], pp[2], totales=rc["totales"],
                    team_local=rc["team_local"], team_visita=rc["team_visita"])["matriz"]
            except Exception:
                matriz_rica = None
        r = analizar_partido(
            cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda(ronda_ev),
            cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or args.line,
            metodo_margen=args.metodo_margen, max_goles_relleno=7,
            sesgo_goles=args.sesgo_goles, matriz=matriz_rica)
        gh, ga = r["relleno_optimo"]
        pr = r["prob_1x2"]
        filas.append({
            "fecha": dt_local.strftime("%Y-%m-%d"),
            "hora": dt_local.strftime("%H:%M"),
            "local": es(c["home"]), "visita": es(c["away"]),
            "marcador": f"{gh}-{ga}",
            "gl": gh, "gv": ga,
            "p_local": round(pr["local"], 3),
            "p_empate": round(pr["empate"], 3),
            "p_visita": round(pr["visita"], 3),
            "ev_pts": round(r["puntos_esperados"], 2),
            "n_casas": c["n_casas"],
        })
        mats.append(r["matriz"])

    if not filas:
        print("No encontré partidos con cuotas para esa fecha.")
        print("Revisa --date, la --tz, o la clave del torneo con --list-sports.")
        return 0

    # 3b) múltiples cupos: perturbación mínima (cupo 1 = EV-máximo; los demás
    # cambian al 2º mejor en n_swaps partidos casi-empatados). Descorrelaciona
    # sin alejarse del modelo (ver experimento_colas.py / DECISIONES.md).
    if args.cupos > 1:
        ronda_param = "primera" if args.all else (
            inferir_ronda(objetivo) if args.round == "auto" else args.round)
        Msesgo = [marcadores.aplicar_sesgo_goles(M, args.sesgo_goles) for M in mats]
        ns = (args.n_swaps if args.n_swaps >= 0
              else DISPERSION_POR_RONDA.get(ronda_param, 12))
        ns_usado = ns
        ph, pa = sp.generar_nuestras(
            Msesgo, args.cupos, RONDAS[ronda_param], estrategia="perturbada",
            rng=np.random.default_rng(7), n_swaps=ns, pool=max(40, 2 * ns + 1))
        for idx, f in enumerate(filas):
            f["cupos"] = [f"{ph[c, idx]}-{pa[c, idx]}" for c in range(args.cupos)]

    filas.sort(key=lambda x: (x["fecha"], x["hora"]))
    ancho = max(len(f"{f['local']} vs {f['visita']}") for f in filas)
    col_f = 11 if objetivo is None else 0
    cab_f = f"{'Fecha':11}" if objetivo is None else ""
    if args.cupos > 1:
        cab_c = " ".join(f"cupo{c+1:>2}" for c in range(args.cupos))
        print(f"{cab_f}{'Hora':6} {'Partido':{ancho}}  {cab_c}")
        print("-" * (col_f + 6 + ancho + 8 * args.cupos))
        for f in filas:
            partido = f"{f['local']} vs {f['visita']}"
            pref = f"{f['fecha']:11}" if objetivo is None else ""
            cols = " ".join(f"{m:>6}" for m in f["cupos"])
            print(f"{pref}{f['hora']:6} {partido:{ancho}}  {cols}")
    else:
        print(f"{cab_f}{'Hora':6} {'Partido':{ancho}}  {'Marcador':8} "
              f"{'P(L/E/V)':18} {'E[pts]':>6}  casas")
        print("-" * (col_f + 6 + ancho + 8 + 18 + 8 + 10))
        for f in filas:
            partido = f"{f['local']} vs {f['visita']}"
            plev = f"{f['p_local']:.2f}/{f['p_empate']:.2f}/{f['p_visita']:.2f}"
            pref = f"{f['fecha']:11}" if objetivo is None else ""
            print(f"{pref}{f['hora']:6} {partido:{ancho}}  {f['marcador']:8} "
                  f"{plev:18} {f['ev_pts']:6.2f}  {f['n_casas']}")

    print(f"\nTotal: {len(filas)} partidos · E[pts] suma = "
          f"{sum(f['ev_pts'] for f in filas):.2f}")
    if args.cupos > 1:
        print(f"Cupo 1 = relleno EV-máximo; cupos 2..{args.cupos} perturbados "
              f"(n_swaps={ns_usado}). Llena un formulario por cupo.")

    if args.csv:
        if args.cupos > 1:
            for f in filas:
                for c in range(args.cupos):
                    f[f"cupo_{c+1}"] = f["cupos"][c]
                del f["cupos"]
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)
        print(f"💾 Guardado en {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
