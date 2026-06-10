#!/usr/bin/env python3
"""
COLFONDOS — COMANDO DIARIO. Baja cuotas en vivo, agrupa por fecha y escupe el
marcador de CADA partido para PLAZA 1 (España, EV-máx) y PLAZA 2 (Inglaterra,
2º mejor = decorrelada). Sirve igual en grupos y en eliminatorias (cuando los
equipos ya se conocen, aparecen solos).

USO DIARIO (cada mañana):
    ODDS_API_KEY=tu_key python pollas/COLFONDOS/dia.py            # todos los próximos
    ODDS_API_KEY=tu_key python pollas/COLFONDOS/dia.py --fecha 2026-06-13
    python pollas/COLFONDOS/dia.py --mock /tmp/wc_grupos.json     # sin gastar API
"""
import argparse, json, os, sys
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta, timezone


def fecha_local(iso, tz_horas):
    """ISO UTC ('...Z') -> fecha YYYY-MM-DD en huso tz_horas (Colombia = -5)."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (dt + timedelta(hours=tz_horas)).strftime("%Y-%m-%d")
    except Exception:
        return str(iso)[:10]
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api
from pollas.CSC.cupos import matriz_de_evento
import pollas.COLFONDOS.marcadores_colfondos as CM


def top2(M):
    """Mejor y 2º mejor marcador COLFONDOS (per-team)."""
    S = CM.matriz_puntos(*M.shape)
    EV = np.einsum("abxy,xy->ab", S, M)
    flat = sorted(((int(i), int(j), EV[i, j]) for i in range(M.shape[0]) for j in range(M.shape[1])),
                  key=lambda x: -x[2])
    return flat[0], flat[1]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--fecha", default="", help="YYYY-MM-DD (vacío = todos los próximos)")
    ap.add_argument("--tz", type=int, default=-5, help="huso horario (Colombia=-5)")
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    pordia = defaultdict(list)
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        dia = fecha_local(e.get("commence_time", ""), args.tz)   # fecha en hora local
        if args.fecha and dia != args.fecha:
            continue
        M = matriz_de_evento(c, "proporcional", 2.5)
        (a1, b1, _), (a2, b2, _) = top2(M)
        pordia[dia].append((c["home"], c["away"], (a1, b1), (a2, b2)))
    if not pordia:
        print("No hay partidos con cuotas para esa fecha (¿aún no abren? ¿ya jugaron?).")
        return 0
    for dia in sorted(pordia):
        print(f"\n===== {dia} =====")
        print(f"{'PARTIDO':40} {'PLAZA1 (ESP)':>13} {'PLAZA2 (ING)':>13}")
        for h, a, p1, p2 in pordia[dia]:
            dec = "" if p1 != p2 else "  (= no hay 2ª opción clara)"
            print(f"{h[:19]:19} vs {a[:17]:17} {p1[0]}-{p1[1]:<10} {p2[0]}-{p2[1]:<10}{dec}")
    print("\nPlaza1 = marcador EV-máx. Plaza2 = 2º mejor (decorrelado, cuesta poco EV).")
    print("Outrights/premios solo se ponen UNA vez (ya están). Esto es solo marcadores del día.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
