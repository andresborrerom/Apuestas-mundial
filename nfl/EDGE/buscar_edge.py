"""
Caza de edge REAL contra la línea de cierre — hipótesis situacionales.

La pregunta: ¿hay situaciones donde el resultado real se desvía
sistemáticamente de la probabilidad del mercado? y−p_mercado por bucket.
"El mercado es eficiente" es una hipótesis; acá se testea con ground truth.

PROTOCOLO DE HONESTIDAD (contra el sesgo de multiplicidad):
  - K hipótesis declaradas ANTES de mirar (las 15 de abajo, ideas del
    usuario + clásicos de la literatura: viento, frío, descanso, viajes,
    home dogs, primetime).
  - Con K=15 tests, esperamos ~1-2 |z|>2 POR PURO AZAR. Un candidato solo
    se toma en serio si: |z|>=2 en el total Y el signo se mantiene en las
    dos mitades (2002-2013 vs 2014-2025).
  - Baseline: moneyline de-vig (2010+) o spread->logística (2002-2009).

Uso:  python nfl/EDGE/buscar_edge.py
"""

import csv
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402

# huso horario de la casa de cada equipo (offset vs ET)
TZ = {}
for eq in ("BUF MIA NE NYJ NYG PHI PIT BAL CIN CLE WAS ATL CAR JAX TB IND "
           "DET").split():
    TZ[eq] = 0
for eq in "CHI GB MIN DAL HOU TEN NO KC STL".split():
    TZ[eq] = 1
for eq in "DEN ARI".split():
    TZ[eq] = 2
for eq in "SEA SF LA LAC LV SD OAK".split():
    TZ[eq] = 3

CALIDOS = {"MIA", "TB", "JAX", "ARI", "LAC", "SD", "LA"}  # ciudades cálidas


def cargar():
    """Partidos REG 2002-2025 con features y p_mercado del local."""
    filas = []
    with open(datos.RUTA_GAMES) as f:
        rows = [r for r in csv.DictReader(f)
                if r["game_type"] == "REG" and r["result"]
                and 2002 <= int(r["season"]) <= 2025]
    # pendiente global del spread (solo para 2002-2009, 1 parámetro)
    con_sp = [(float(r["spread_line"]), int(r["result"]) > 0)
              for r in rows if r["spread_line"] and int(r["result"]) != 0]
    b = prob.ajustar_pendiente_spread([s for s, _ in con_sp],
                                      [1.0 * g for _, g in con_sp])
    # techo de la casa de cada equipo por temporada (inferido de sus locales)
    techo = defaultdict(lambda: defaultdict(list))
    for r in rows:
        techo[int(r["season"])][r["home_team"]].append(r["roof"])
    techo_eq = {(s, eq): max(set(v), key=v.count)
                for s, d in techo.items() for eq, v in d.items()}

    for r in rows:
        res = int(r["result"])
        if res == 0:
            continue
        if r["home_moneyline"]:
            p = prob.p_local_moneyline(
                datos.americano_a_decimal(r["home_moneyline"]),
                datos.americano_a_decimal(r["away_moneyline"]))
        elif r["spread_line"]:
            p = prob.p_local_spread(float(r["spread_line"]), b)
        else:
            continue
        s = int(r["season"])
        away, home = r["away_team"], r["home_team"]
        hora = int(r["gametime"][:2]) + int(r["gametime"][3:5]) / 60
        filas.append({
            "season": s, "week": int(r["week"]), "home": home, "away": away,
            "p": p, "y": 1.0 if res > 0 else 0.0,
            "wind": float(r["wind"]) if r["wind"] else None,
            "temp": float(r["temp"]) if r["temp"] else None,
            "outdoor": r["roof"] in ("outdoors", "open"),
            "rest_h": int(r["home_rest"]), "rest_a": int(r["away_rest"]),
            "div": r["div_game"] == "1", "weekday": r["weekday"],
            "hora": hora,
            "tz_h": TZ.get(home, 0), "tz_a": TZ.get(away, 0),
            "away_dome": techo_eq.get((s, away)) in ("dome", "closed"),
            "away_calido": away in CALIDOS,
        })
    return filas


def resid(sub, lado="home"):
    """(n, esperado, real, residual, z) para el lado dado del bucket."""
    if not sub:
        return 0, 0, 0, 0, 0
    if lado == "home":
        ps = np.array([f["p"] for f in sub])
        ys = np.array([f["y"] for f in sub])
    elif lado == "fav":
        ps = np.array([max(f["p"], 1 - f["p"]) for f in sub])
        ys = np.array([f["y"] if f["p"] >= 0.5 else 1 - f["y"]
                       for f in sub])
    else:                                    # dog / away
        ps = np.array([min(f["p"], 1 - f["p"]) if lado == "dog"
                       else 1 - f["p"] for f in sub])
        ys = np.array([(f["y"] if f["p"] < 0.5 else 1 - f["y"])
                       if lado == "dog" else 1 - f["y"] for f in sub])
    n = len(ps)
    r = ys.mean() - ps.mean()
    se = math.sqrt(np.sum(ps * (1 - ps))) / n
    return n, ps.mean(), ys.mean(), r, r / se


HIPOTESIS = [
    ("H1  home dog", lambda f: f["p"] < 0.5, "home"),
    ("H2  home dog grande (p<.35)", lambda f: f["p"] < 0.35, "home"),
    ("H3  home dog divisional", lambda f: f["p"] < 0.5 and f["div"], "home"),
    ("H4  local tras bye (rest>=10)", lambda f: f["rest_h"] >= 10, "home"),
    ("H5  visita en semana corta (<=5d)", lambda f: f["rest_a"] <= 5, "home"),
    ("H6  ventaja descanso local >=4d",
     lambda f: f["rest_h"] - f["rest_a"] >= 4, "home"),
    ("H7  partido de jueves", lambda f: f["weekday"] == "Thursday", "home"),
    ("H8  viento >=15mph (favorito)",
     lambda f: f["outdoor"] and f["wind"] is not None and f["wind"] >= 15,
     "fav"),
    ("H9  viento >=20mph (favorito)",
     lambda f: f["outdoor"] and f["wind"] is not None and f["wind"] >= 20,
     "fav"),
    ("H10 frio<=25F y visita domo/calida",
     lambda f: f["temp"] is not None and f["temp"] <= 25
     and (f["away_dome"] or f["away_calido"]), "home"),
    ("H11 oeste viaja este, juego 1pm (visita)",
     lambda f: f["tz_a"] - f["tz_h"] >= 2 and f["hora"] <= 13.6
     and f["weekday"] == "Sunday", "away"),
    ("H12 este viaja oeste, juego nocturno (visita)",
     lambda f: f["tz_h"] - f["tz_a"] >= 2 and f["hora"] >= 20, "away"),
    ("H13 dog en primetime (>=20:15)", lambda f: f["hora"] >= 20.25, "dog"),
    ("H14 semana>=15 outdoor frio<=32 (local)",
     lambda f: f["week"] >= 15 and f["outdoor"]
     and f["temp"] is not None and f["temp"] <= 32, "home"),
    ("H15 favorito grande (p>=.80)",
     lambda f: max(f["p"], 1 - f["p"]) >= 0.80, "fav"),
]


def main():
    filas = cargar()
    print(f"partidos 2002-2025 con línea y sin empate: {len(filas)}")
    print(f"K = {len(HIPOTESIS)} hipótesis declaradas — con K=15 esperamos "
          f"~1-2 |z|>2 por azar\n")
    print(f"{'hipótesis':<38} {'n':>5} {'E[p]':>6} {'real':>6} "
          f"{'resid':>7} {'z':>6}  mitades")
    candidatos = []
    for nombre, cond, lado in HIPOTESIS:
        sub = [f for f in filas if cond(f)]
        n, ep, real, r, z = resid(sub, lado)
        m1 = [f for f in sub if f["season"] <= 2013]
        m2 = [f for f in sub if f["season"] > 2013]
        _, _, _, r1, z1 = resid(m1, lado)
        _, _, _, r2, z2 = resid(m2, lado)
        consist = "==" if r1 * r2 > 0 else "!="
        print(f"{nombre:<38} {n:>5} {ep:>6.3f} {real:>6.3f} "
              f"{r:>+7.3f} {z:>+6.2f}  {r1:+.3f}/{r2:+.3f} {consist}")
        if abs(z) >= 2 and r1 * r2 > 0:
            candidatos.append((nombre, n, r, z))

    print("\nCANDIDATOS (|z|>=2 Y mismo signo en ambas mitades):")
    if not candidatos:
        print("  ninguno — la línea de cierre absorbe estas situaciones.")
    for nombre, n, r, z in candidatos:
        print(f"  {nombre}: resid {r:+.3f} (n={n}, z={z:+.2f}) -> "
              f"validar walk-forward antes de usar")


if __name__ == "__main__":
    main()
