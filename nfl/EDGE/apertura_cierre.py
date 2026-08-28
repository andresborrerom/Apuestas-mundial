"""
E2 — Apertura vs cierre (SBRO 2013-2020): ¿dónde vive el movimiento?

Nadie apuesta contra el cierre: se apuesta cuando el número está
disponible. Tres preguntas con datos de apertura Y cierre:

  1. ¿El cierre predice mejor que la apertura? (la "closing line value"
     de los sharps: si sí, mover plata temprano hacia donde cerrará = edge)
  2. SEGUIR EL VAPOR: cuando la línea se mueve >=1 punto, ¿el lado hacia
     el que se movió cubre la APERTURA más del 52.4% (break-even -110)?
     Eso mide cuánta información llega entre lunes y domingo.
  3. VIENTO: ¿el total se mueve a la baja apertura->cierre con viento?
     (empalme con nflverse). Si el mercado ajusta tarde, el under con
     viento hay que apostarlo TEMPRANO; si ajusta desde la apertura, el
     edge del cierre (E1) es todo lo que hay.

Formato SBRO: 2 filas por juego (V y H); en las columnas Open/Close una
fila trae el TOTAL (número grande) y la otra el SPREAD (número chico, en
la fila del favorito). 'pk' = 0.

Uso:  python nfl/EDGE/apertura_cierre.py
"""

import csv
import glob
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "datos", "sbro")

EQ = {"GreenBay": "GB", "Chicago": "CHI", "Atlanta": "ATL",
      "Minnesota": "MIN", "Washington": "WAS", "Philadelphia": "PHI",
      "Buffalo": "BUF", "NYJets": "NYJ", "NYGiants": "NYG",
      "Dallas": "DAL", "KansasCity": "KC", "Jacksonville": "JAX",
      "Baltimore": "BAL", "Miami": "MIA", "Cleveland": "CLE",
      "Tennessee": "TEN", "LARams": "LA", "StLouis": "STL",
      "Carolina": "CAR", "TampaBay": "TB", "NewEngland": "NE",
      "Pittsburgh": "PIT", "Cincinnati": "CIN", "Indianapolis": "IND",
      "Oakland": "OAK", "Denver": "DEN", "LAChargers": "LAC",
      "SanDiego": "SD", "Seattle": "SEA", "SanFrancisco": "SF",
      "Arizona": "ARI", "NewOrleans": "NO", "Houston": "HOU",
      "Detroit": "DET", "LasVegas": "LV"}


def num(v):
    v = str(v).strip().lower()
    if v in ("pk", "p"):
        return 0.0
    try:
        return float(v)
    except ValueError:
        return None


def cargar_sbro():
    juegos = []
    for ruta in sorted(glob.glob(os.path.join(RUTA, "nfl_odds_*.csv"))):
        season = int(os.path.basename(ruta)[9:13])
        rows = list(csv.DictReader(open(ruta)))
        for i in range(0, len(rows) - 1, 2):
            v, h = rows[i], rows[i + 1]
            if v["VH"] not in ("V", "N") or h["VH"] not in ("H", "N"):
                continue
            fecha = int(float(v["Date"]))
            mes, dia = divmod(fecha, 100)
            anio = season if mes >= 8 else season + 1
            par = {}
            ok = True
            for col in ("Open", "Close"):
                a, b = num(v[col]), num(h[col])
                if a is None or b is None:
                    ok = False
                    break
                spread, total = min(a, b), max(a, b)
                if total < 30:            # sin total real (dato raro)
                    ok = False
                    break
                # el spread va en la fila del favorito ->
                # sp_home = margen esperado del LOCAL
                sp_home = spread if b < a else -spread
                par[col] = (sp_home, total)
            if not ok:
                continue
            try:
                fv, fh = float(v["Final"]), float(h["Final"])
            except ValueError:
                continue
            juegos.append({
                "season": season,
                "fecha": f"{anio}-{mes:02d}-{dia:02d}",
                "away": EQ.get(v["Team"]), "home": EQ.get(h["Team"]),
                "margen": fh - fv, "total_real": fh + fv,
                "sp_open": par["Open"][0], "tot_open": par["Open"][1],
                "sp_close": par["Close"][0], "tot_close": par["Close"][1],
            })
    return juegos


def main():
    juegos = cargar_sbro()
    print(f"juegos SBRO parseados 2013-2020: {len(juegos)}")

    # 1 --- ¿el cierre predice mejor? -----------------------------------
    mae_o = np.mean([abs(j["margen"] - j["sp_open"]) for j in juegos])
    mae_c = np.mean([abs(j["margen"] - j["sp_close"]) for j in juegos])
    mto = np.mean([abs(j["total_real"] - j["tot_open"]) for j in juegos])
    mtc = np.mean([abs(j["total_real"] - j["tot_close"]) for j in juegos])
    print(f"\n1) error absoluto medio del SPREAD: apertura {mae_o:.2f} vs "
          f"cierre {mae_c:.2f}")
    print(f"   error absoluto medio del TOTAL:  apertura {mto:.2f} vs "
          f"cierre {mtc:.2f}")

    # 2 --- seguir el vapor contra la apertura ---------------------------
    print("\n2) SEGUIR EL VAPOR (línea se movió >=1): ¿cubre la apertura?")
    for umbral in (0.5, 1.0, 1.5, 2.0):
        cubre, n = 0, 0
        for j in juegos:
            mov = j["sp_close"] - j["sp_open"]
            if abs(mov) < umbral:
                continue
            # el vapor favoreció al local si mov>0: apostar local -sp_open
            resultado = j["margen"] - j["sp_open"]
            if resultado == 0:
                continue
            n += 1
            cubre += (resultado > 0) if mov > 0 else (resultado < 0)
        if n:
            se = 50 / math.sqrt(n)
            print(f"   mov>={umbral}: n={n:>4}, cubre {100 * cubre / n:.1f}%"
                  f" (SE {se:.1f}pp; break-even -110 = 52.4%)")

    # 3 --- ¿el total se mueve con el viento apertura->cierre? -----------
    viento = {}
    for p in datos.cargar_partidos(temporadas=set(range(2013, 2021))):
        # cargar viento crudo del csv
        pass
    import csv as _csv
    vmap = {}
    for r in _csv.DictReader(open(datos.RUTA_GAMES)):
        if r["game_type"] == "REG" and r["wind"] and \
                r["roof"] in ("outdoors", "open"):
            vmap[(r["gameday"], r["home_team"], r["away_team"])] = \
                float(r["wind"])
    print("\n3) VIENTO y el TOTAL (empalme nflverse, solo outdoor):")
    print(f"{'viento':>8} {'n':>5} {'mov total ap->ci':>17} "
          f"{'under vs AP':>12} {'under vs CI':>12}")
    for lo, hi in [(0, 10), (10, 15), (15, 99)]:
        movs, u_ap, u_ci, n = [], 0, 0, 0
        for j in juegos:
            w = vmap.get((j["fecha"], j["home"], j["away"]))
            if w is None or not (lo <= w < hi):
                continue
            movs.append(j["tot_close"] - j["tot_open"])
            if j["total_real"] != j["tot_open"]:
                u_ap += j["total_real"] < j["tot_open"]
            if j["total_real"] != j["tot_close"]:
                u_ci += j["total_real"] < j["tot_close"]
            n += 1
        if n:
            print(f"{lo:>3}-{hi if hi < 99 else '+':>3} {n:>6} "
                  f"{np.mean(movs):>+17.2f} {100 * u_ap / n:>11.1f}% "
                  f"{100 * u_ci / n:>11.1f}%")
    print("\n(si 'mov total' apenas baja con viento, el mercado NO ajusta"
          "\n entre semana: el under ventoso vale igual temprano que tarde)")


if __name__ == "__main__":
    main()
