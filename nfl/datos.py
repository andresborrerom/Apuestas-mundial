"""
Carga de datos NFL: partidos históricos con líneas de cierre y resultados.

Fuente: nflverse/nfldata `games.csv` (Lee Sharpe). Un CSV con TODO lo que
necesitamos: resultados 1999-hoy, spread de cierre desde 1999, moneylines de
cierre completos desde 2010, y las líneas ya publicadas de la temporada
entrante (sirve también como fuente "en vivo" para los picks de 2026).

Snapshot cacheado en `nfl/datos/games.csv`. Para refrescar:
    curl -sSL -o nfl/datos/games.csv \
        https://github.com/nflverse/nfldata/raw/master/data/games.csv

Convenciones del CSV (verificadas contra 2024 sem. 1):
  - `spread_line` es el margen esperado del LOCAL: positivo = local favorito.
  - `away_moneyline`/`home_moneyline` en formato americano (+124 / -148).
  - `result` = home_score - away_score (0 = empate). Vacío = no jugado aún.
"""

import csv
import os

RUTA_GAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "datos", "games.csv")


def americano_a_decimal(ml):
    """Moneyline americano -> cuota decimal (+124 -> 2.24, -148 -> 1.676)."""
    ml = float(ml)
    if ml > 0:
        return 1.0 + ml / 100.0
    return 1.0 + 100.0 / (-ml)


def cargar_partidos(temporadas=None, tipo="REG", solo_jugados=True,
                    ruta=RUTA_GAMES):
    """Lee games.csv y devuelve una lista de dicts limpios.

    Cada partido: season, week, home, away, home_score, away_score, result
    (home-away; None si no jugado), spread_line (margen esperado del local;
    None si no hay), ml_home/ml_away (cuotas DECIMALES; None si no hay),
    empate (bool), gameday.
    """
    partidos = []
    with open(ruta, newline="") as f:
        for r in csv.DictReader(f):
            if tipo and r["game_type"] != tipo:
                continue
            season = int(r["season"])
            if temporadas is not None and season not in temporadas:
                continue
            jugado = r["result"] != ""
            if solo_jugados and not jugado:
                continue
            p = {
                "season": season,
                "week": int(r["week"]),
                "away": r["away_team"],
                "home": r["home_team"],
                "gameday": r["gameday"],
                "away_score": int(r["away_score"]) if jugado else None,
                "home_score": int(r["home_score"]) if jugado else None,
                "result": int(r["result"]) if jugado else None,
                "empate": (int(r["result"]) == 0) if jugado else None,
                "spread_line": (float(r["spread_line"])
                                if r["spread_line"] else None),
                "ml_home": (americano_a_decimal(r["home_moneyline"])
                            if r["home_moneyline"] else None),
                "ml_away": (americano_a_decimal(r["away_moneyline"])
                            if r["away_moneyline"] else None),
            }
            partidos.append(p)
    return partidos


def por_semana(partidos):
    """Agrupa en dict {(season, week): [partidos]} ordenado."""
    semanas = {}
    for p in partidos:
        semanas.setdefault((p["season"], p["week"]), []).append(p)
    return dict(sorted(semanas.items()))


if __name__ == "__main__":
    ps = cargar_partidos()
    con_ml = [p for p in ps if p["ml_home"]]
    print(f"partidos REG jugados: {len(ps)}  con moneyline: {len(con_ml)}")
    print(f"temporadas con ML completo: "
          f"{sorted({p['season'] for p in con_ml if p['season'] >= 2010})}")
    empates = [p for p in ps if p["empate"]]
    print(f"empates históricos: {len(empates)} "
          f"({100 * len(empates) / len(ps):.2f}% de los partidos)")
