"""
Captura un snapshot de las líneas NFL (spread, total, moneyline) de todas
las casas que sirve The Odds API, y lo APILA en un CSV histórico propio.

Por qué: E2-E4 mostraron que el edge vive en el movimiento apertura->
cierre, pero solo tenemos open/close históricos (SBRO). Capturando 2
snapshots diarios durante la temporada construimos NUESTRO dataset
intra-semana — el insumo del pronosticador de vapor v2 — gratis
(2 snapshots/día x ~120 días ≈ 240 requests; el plan free da 500/mes).

Uso:  ODDS_API_KEY=... python nfl/EDGE/snapshot_odds.py
Apila en nfl/datos/snapshots/lineas_nfl.csv (una fila por casa-partido-
mercado-lado, con timestamp UTC del snapshot).
"""

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "datos", "snapshots", "lineas_nfl.csv")
URL = ("https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
       "?regions=us&markets=h2h,spreads,totals&oddsFormat=decimal"
       "&apiKey={key}")

CAMPOS = ["snapshot_utc", "commence", "home", "away", "casa", "mercado",
          "lado", "punto", "cuota"]


def main():
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("falta ODDS_API_KEY")
        sys.exit(1)
    with urllib.request.urlopen(URL.format(key=key), timeout=60) as r:
        eventos = json.loads(r.read())
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    filas = []
    for ev in eventos:
        base = {"snapshot_utc": ahora, "commence": ev["commence_time"],
                "home": ev["home_team"], "away": ev["away_team"]}
        for casa in ev.get("bookmakers", []):
            for m in casa.get("markets", []):
                for o in m.get("outcomes", []):
                    filas.append({**base, "casa": casa["key"],
                                  "mercado": m["key"],
                                  "lado": o.get("name", ""),
                                  "punto": o.get("point", ""),
                                  "cuota": o.get("price", "")})
    if not filas:
        print("sin eventos (fuera de temporada?)")
        return
    os.makedirs(os.path.dirname(RUTA), exist_ok=True)
    nuevo = not os.path.exists(RUTA)
    with open(RUTA, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()
        w.writerows(filas)
    print(f"snapshot {ahora}: {len(eventos)} partidos, "
          f"{len(filas)} filas apiladas")


if __name__ == "__main__":
    main()
