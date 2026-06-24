#!/usr/bin/env python3
"""
CSC — ELIMINATORIAS. Un solo comando, consciente del deadline, que genera los 5
cupos descorrelacionados de la ronda de knockout que viene.

A diferencia de grupos (donde se reparte 1 punto por ganador), en eliminatorias
los puntos suben fuerte por ronda (ver reglas.py: final = 8 por ganador, goles
base 16). Por eso aquí cada acierto vale oro y la estrategia cambia:
  - modelo ENRIQUECIDO por defecto (--rico): curva O/U + O/U por equipo, gratis.
  - más DISPERSIÓN entre cupos (n_swaps mayor) para descorrelacionar: con pocos
    partidos de mucho valor, separar las 5 planillas cubre más escenarios.

Importante (reglamento CSC): en eliminatorias cuenta el resultado tras los 120
min (los penales NO), y SE PUEDE apostar al empate. La cuota 1X2 de tiempo
reglamentario es una buena aproximación del marcador a 120'.

Uso:
    export ODDS_API_KEY=tu_key
    python pollas/CSC/eliminatorias.py                 # ronda que viene, si ya hay cuotas
    python pollas/CSC/eliminatorias.py --round octavos # forzar ronda
    python pollas/CSC/eliminatorias.py --csv r32.csv   # guardar para llenar el form
    python pollas/CSC/eliminatorias.py --dias-antes 5  # ventana de aviso

Pensado para correr a mano o desde el GitHub Action (eliminatorias-aviso.yml),
que lo dispara en los días previos a cada deadline y publica los cupos en un issue.
"""
import argparse
import os
import sys
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import pollas.CSC.llenar as L

# Rondas de eliminatoria en orden (excluye 'primera'); cada una con su deadline.
RONDAS_KO = [r for r in L.CALENDARIO if r[2] != "primera"]


def deadline_dt(texto, tz):
    """'28/06/2026 1:59 PM' -> datetime con tz."""
    return datetime.strptime(texto, "%d/%m/%Y %I:%M %p").replace(tzinfo=tz)


def ronda_que_viene(hoy_dt, tz):
    """Primera ronda KO cuyo deadline aún no pasó. (nombre, deadline_dt) o None."""
    for ini, fin, nombre, dl in RONDAS_KO:
        d = deadline_dt(dl, tz)
        if d >= hoy_dt:
            return nombre, d
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generar los 5 cupos CSC de la ronda KO que viene")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--round", default="auto", help="ronda KO o 'auto' (la que viene)")
    ap.add_argument("--cupos", type=int, default=5)
    ap.add_argument("--dias-antes", type=int, default=4,
                    help="solo genera si faltan <= estos días para el deadline")
    ap.add_argument("--tz", default="America/Bogota")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--mock", default=None, help="JSON de eventos (sin red)")
    ap.add_argument("--simple", action="store_true",
                    help="apaga --rico (no hace 1 llamada API por partido)")
    ap.add_argument("--force", action="store_true",
                    help="genera aunque falte más que --dias-antes o ya pasó el deadline")
    args = ap.parse_args(argv)

    tz = ZoneInfo(args.tz)
    ahora = datetime.now(tz)

    if args.round != "auto":
        ronda = args.round
        txt = L.deadline_de_ronda(ronda)
        dl = deadline_dt(txt, tz) if txt else None
    else:
        nxt = ronda_que_viene(ahora, tz)
        if not nxt:
            print("✅ No quedan rondas de eliminatoria por enviar (o ya terminó el Mundial).")
            return 0
        ronda, dl = nxt

    faltan = (dl - ahora) if dl else timedelta(0)
    dias = faltan.total_seconds() / 86400
    print(f"⚔️  Próxima ronda CSC: {ronda.upper()}  |  deadline: "
          f"{dl.strftime('%d/%m/%Y %I:%M %p') if dl else 's/d'}  |  "
          f"faltan {dias:.1f} días")

    if not args.force and dias > args.dias_antes:
        print(f"\n⏳ Aún no es momento (genero cuando falten ≤ {args.dias_antes} días).")
        print(f"   Cuando se definan los cruces y haya cuotas, corre:")
        print(f"   ODDS_API_KEY=... python pollas/CSC/eliminatorias.py --round {ronda} --csv {ronda}.csv")
        return 0

    # delega en llenar.py con los ajustes correctos de eliminatoria
    argv2 = ["--all", "--round", ronda, "--cupos", str(args.cupos)]
    if not args.simple:
        argv2.append("--rico")
    if args.csv:
        argv2 += ["--csv", args.csv]
    if args.mock:
        argv2 += ["--mock", args.mock]
    if args.api_key:
        argv2 += ["--api-key", args.api_key]
    print()
    rc = L.main(argv2)
    if rc == 0 and not args.csv:
        print("\n💡 Tip: agrega  --csv " + ronda + ".csv  para guardar y llenar un form por cupo.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
