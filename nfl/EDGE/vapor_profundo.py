"""
E4 — Anatomía del vapor: qué más hay en el movimiento apertura->cierre.

E2/E3 mostraron: seguir el vapor cubre la apertura 57-59%, y un Elo tosco
lo huele. Esta batería explora la estructura del movimiento (SBRO
2013-2020 + nflverse). K=8 hipótesis/preguntas declaradas antes de mirar:

  V1 dosis-respuesta: cover vs apertura por magnitud del movimiento
     (¿lineal? ¿satura?)
  V2 asimetría: ¿vapor hacia el UNDERDOG cubre más que hacia el favorito?
     (el público empuja favoritos; el dinero sharp suele ir al dog)
  V3 números clave: movimiento que CRUZA 3 o 7 vs movimiento que no
  V4 vapor en TOTALES: ¿el movimiento del total predice over/under vs la
     apertura igual que el spread?
  V5 ¿queda algo al CIERRE? cover del lado del vapor contra la línea de
     cierre (si ~50%, el cierre absorbe todo: hay que ser temprano)
  V6 overshoot: en movimientos grandes (>=2.5), ¿el lado del vapor cubre
     el CIERRE por debajo de 50%? (valor de contra-apostar el exceso)
  V7 estación: ¿las aperturas de las semanas 1-4 son más blandas?
     (más movimiento y mejor cover del vapor que semanas 5+)
  V8 vapor vs Elo: cuando el movimiento va CONTRA el lado del Elo,
     ¿quién cubre la apertura? (¿el dinero informado le gana al modelo?)

Split-half 2013-2016 / 2017-2020 en los candidatos.

Uso:  python nfl/EDGE/vapor_profundo.py
"""

import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402
from nfl.EDGE.apertura_cierre import cargar_sbro  # noqa: E402


def cover_stats(pares):
    """pares = [(cubre_bool)] -> (n, %, SE en pp)."""
    n = len(pares)
    if n == 0:
        return 0, 0.0, 0.0
    c = 100 * np.mean(pares)
    return n, c, 50 / math.sqrt(n)


def cruza_clave(a, b):
    """¿el intervalo [min,max] de |spread| cruza 3 o 7?"""
    lo, hi = sorted((abs(a), abs(b)))
    return any(lo < k < hi for k in (3.0, 7.0))


def main():
    juegos = cargar_sbro()

    # semana de temporada vía nflverse (fecha+equipos)
    semana = {}
    for r in csv.DictReader(open(datos.RUTA_GAMES)):
        if r["game_type"] == "REG" and r["result"]:
            semana[(r["gameday"], r["home_team"], r["away_team"])] = \
                int(r["week"])

    # Elo walk-forward (pendiente 2002-2012, igual que E3)
    todos = sorted(datos.cargar_partidos(),
                   key=lambda x: (x["season"], x["week"], x["gameday"]))
    train = [p for p in todos if p["season"] <= 2012
             and p["spread_line"] is not None and not p["empate"]]
    b = prob.ajustar_pendiente_spread(
        [p["spread_line"] for p in train],
        [1.0 if p["result"] > 0 else 0.0 for p in train])
    elo = prob.Elo()
    p_elo = {}
    for p in todos:
        p_elo[(p["gameday"], p["home"], p["away"])] = \
            elo.p_local(p["home"], p["away"])
        elo.actualizar(p)

    for j in juegos:
        j["mov"] = j["sp_close"] - j["sp_open"]     # >0 = hacia el local
        j["resid_ap"] = j["margen"] - j["sp_open"]
        j["resid_ci"] = j["margen"] - j["sp_close"]
        j["week"] = semana.get((j["fecha"], j["home"], j["away"]))
        j["pe"] = p_elo.get((j["fecha"], j["home"], j["away"]))

    con_mov = [j for j in juegos if abs(j["mov"]) >= 1
               and j["resid_ap"] != 0]

    def cubre_vapor(j, contra="ap"):
        r = j["resid_ap"] if contra == "ap" else j["resid_ci"]
        if r == 0:
            return None
        return (r > 0) if j["mov"] > 0 else (r < 0)

    print(f"juegos: {len(juegos)}; con movimiento >=1: {len(con_mov)}\n")

    print("V1 dosis-respuesta (cover del vapor vs APERTURA):")
    for lo, hi in [(0.5, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 99)]:
        sub = [cubre_vapor(j) for j in juegos
               if lo <= abs(j["mov"]) < hi and cubre_vapor(j) is not None]
        n, c, se = cover_stats(sub)
        print(f"  mov {lo}-{hi if hi < 99 else '+'}: n={n:>4}  "
              f"cubre {c:.1f}% (±{se:.1f})")

    print("\nV2 asimetría (mov>=1): hacia dónde va el vapor")
    hacia_dog = [cubre_vapor(j) for j in con_mov
                 if (j["mov"] > 0) == (j["sp_open"] < 0)]
    hacia_fav = [cubre_vapor(j) for j in con_mov
                 if (j["mov"] > 0) == (j["sp_open"] > 0)]
    for nombre, sub in [("hacia el underdog", hacia_dog),
                        ("hacia el favorito", hacia_fav)]:
        n, c, se = cover_stats([x for x in sub if x is not None])
        print(f"  {nombre:<18} n={n:>4}  cubre {c:.1f}% (±{se:.1f})")

    print("\nV3 números clave (mov>=1):")
    for nombre, cond in [("cruza 3 o 7", True), ("no cruza", False)]:
        sub = [cubre_vapor(j) for j in con_mov
               if cruza_clave(j["sp_open"], j["sp_close"]) == cond]
        n, c, se = cover_stats([x for x in sub if x is not None])
        print(f"  {nombre:<12} n={n:>4}  cubre {c:.1f}% (±{se:.1f})")

    print("\nV4 vapor en TOTALES (mov total >=1): ¿el lado del movimiento "
          "acierta vs apertura?")
    for lo, hi in [(1.0, 2.0), (2.0, 99)]:
        acierta = []
        for j in juegos:
            mt = j["tot_close"] - j["tot_open"]
            if not (lo <= abs(mt) < hi) or j["total_real"] == j["tot_open"]:
                continue
            acierta.append((j["total_real"] > j["tot_open"]) if mt > 0
                           else (j["total_real"] < j["tot_open"]))
        n, c, se = cover_stats(acierta)
        print(f"  mov {lo}-{hi if hi < 99 else '+'}: n={n:>4}  "
              f"acierta {c:.1f}% (±{se:.1f})")

    print("\nV5 ¿queda algo al CIERRE? (vapor >=1, contra la línea de "
          "cierre):")
    sub = [cubre_vapor(j, "ci") for j in con_mov
           if cubre_vapor(j, "ci") is not None]
    n, c, se = cover_stats(sub)
    print(f"  n={n}  cubre {c:.1f}% (±{se:.1f})  "
          f"[~50% = el cierre absorbió todo]")

    print("\nV6 overshoot (mov>=2.5, contra el CIERRE):")
    sub = [cubre_vapor(j, "ci") for j in juegos
           if abs(j["mov"]) >= 2.5 and cubre_vapor(j, "ci") is not None]
    n, c, se = cover_stats(sub)
    print(f"  n={n}  cubre {c:.1f}% (±{se:.1f})  [<50% = el mercado se "
          f"pasó de largo]")

    print("\nV7 estación (vapor >=1 vs apertura):")
    for nombre, cond in [("semanas 1-4", lambda w: w and w <= 4),
                         ("semanas 5+", lambda w: w and w > 4)]:
        sub = [cubre_vapor(j) for j in con_mov if cond(j["week"])
               and cubre_vapor(j) is not None]
        movs = [abs(j["mov"]) for j in juegos if cond(j["week"])]
        n, c, se = cover_stats(sub)
        print(f"  {nombre:<12} n={n:>4}  cubre {c:.1f}% (±{se:.1f})  "
              f"|mov| medio={np.mean(movs):.2f}")

    print("\nV8 vapor vs Elo (mov>=1 y |gap|>=0.2): ¿quién cubre la "
          "apertura?")
    def gap(j):
        if j["pe"] is None:
            return None
        po = 1 / (1 + math.exp(-b * j["sp_open"]))
        return math.log(j["pe"] / (1 - j["pe"])) - math.log(po / (1 - po))
    acuerdo, choque_vapor, choque_elo = [], [], []
    for j in con_mov:
        g = gap(j)
        if g is None or abs(g) < 0.2:
            continue
        cv = cubre_vapor(j)
        if cv is None:
            continue
        if (g > 0) == (j["mov"] > 0):
            acuerdo.append(cv)
        else:
            choque_vapor.append(cv)          # cubre el lado del vapor
            choque_elo.append(not cv)        # cubre el lado del Elo
    for nombre, sub in [("acuerdo (mismo lado)", acuerdo),
                        ("choque: gana vapor", choque_vapor),
                        ("choque: gana Elo", choque_elo)]:
        n, c, se = cover_stats(sub)
        print(f"  {nombre:<22} n={n:>4}  cubre {c:.1f}% (±{se:.1f})")

    # split-half del headline (V1 total)
    print("\nsplit-half del vapor>=1 vs apertura:")
    for nombre, cond in [("2013-2016", lambda s: s <= 2016),
                         ("2017-2020", lambda s: s > 2016)]:
        sub = [cubre_vapor(j) for j in con_mov if cond(j["season"])
               and cubre_vapor(j) is not None]
        n, c, se = cover_stats(sub)
        print(f"  {nombre}: n={n:>4}  cubre {c:.1f}% (±{se:.1f})")


if __name__ == "__main__":
    main()
