"""
ANTICROWD INFORMADO vs m3 — el backtest que pedía la semana 6 de 2026.

Datos: NFL Pickwatch (via repo sarviinageelen/pickwatch-analysis, cacheado
en nfl/datos/pickwatch_nfl.csv): % de FANS que pickeó cada lado (~5-6k
votantes/juego), cuotas decimales y resultado real, 2020-2025 REG
completas. Semana via join con nflverse (fecha+equipos; AZ->ARI, LAR->LA).

Políticas comparadas (planilla semanal de Pick'em):
  fav      : favorito del mercado en todo.
  m3       : favoritos + flip en los 3 más cercanos a 50% (la política
             oficial, validada contra field SINTÉTICO).
  anti-k   : favoritos + flip en los k partidos con mayor EXCESO del
             público (fans% sobre el favorito − prob de mercado del
             favorito), exigiendo p_mercado del underdog >= 0.35.
  anti20   : flip donde exceso >= 20pp y p_dog >= 0.40 (máx 3).

Field: 13 rivales; cada uno pickea cada juego según la distribución REAL
de fans de ese juego (independencia entre juegos). Resultados = ground
truth. Métrica de la Batalla: P(1º único) promedio por semana; costo:
E[aciertos]. Split-half 2020-2022 / 2023-2025.

Uso:  python nfl/EDGE/anticrowd_informado.py
"""

import csv
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from motor import cuotas  # noqa: E402

MAPA = {"AZ": "ARI", "LAR": "LA"}
SIMS = 400
N_RIV = 13


def cargar():
    semana_de = {}
    for p in datos.cargar_partidos(temporadas=set(range(2020, 2026))):
        semana_de[(p["gameday"], p["home"], p["away"])] = \
            (p["season"], p["week"])
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "datos", "pickwatch_nfl.csv")
    semanas = defaultdict(list)
    for r in csv.DictReader(open(ruta)):
        if (r["game_type_std"] != "REGULAR" or not r["su_home_pct_fans"]
                or not r["home_odds_dec"] or not r["home_score"]):
            continue
        home = MAPA.get(r["home_team"], r["home_team"])
        road = MAPA.get(r["road_team"], r["road_team"])
        fecha = r["game_start"][:10]
        clave = semana_de.get((fecha, home, road))
        if clave is None:
            # partidos de lunes caen a veces un dia corrido por zona horaria
            continue
        try:
            ph = float(cuotas.a_probabilidades(
                [float(r["home_odds_dec"]), float(r["road_odds_dec"])])[0])
        except Exception:
            continue
        semanas[clave].append({
            "p_home": ph,
            "fans_home": float(r["su_home_pct_fans"]) / 100.0,
            "gano_home": int(r["home_score"]) > int(r["road_score"]),
            "empate": int(r["home_score"]) == int(r["road_score"]),
        })
    return {k: v for k, v in semanas.items() if len(v) >= 12}


def planillas(juegos):
    """Devuelve dict política -> vector bool pick_home por juego."""
    p = np.array([j["p_home"] for j in juegos])
    fans = np.array([j["fans_home"] for j in juegos])
    fav_home = p >= 0.5
    p_fav = np.where(fav_home, p, 1 - p)
    fans_fav = np.where(fav_home, fans, 1 - fans)
    exceso = fans_fav - p_fav
    pols = {"fav": fav_home.copy()}
    # m3: voltear los 3 mas parejos
    m3 = fav_home.copy()
    for i in np.argsort(np.abs(p - 0.5))[:3]:
        m3[i] = ~m3[i]
    pols["m3"] = m3
    # anti-k: voltear mayor exceso, p_dog >= 0.35
    for k in (1, 2, 3):
        ak = fav_home.copy()
        cand = [i for i in np.argsort(-exceso) if 1 - p_fav[i] >= 0.35][:k]
        for i in cand:
            ak[i] = ~ak[i]
        pols[f"anti{k}"] = ak
    # anti20: exceso>=20pp y p_dog>=0.40, max 3
    a20 = fav_home.copy()
    cand = [i for i in np.argsort(-exceso)
            if exceso[i] >= 0.20 and 1 - p_fav[i] >= 0.40][:3]
    for i in cand:
        a20[i] = ~a20[i]
    pols["anti20"] = a20
    return pols


def main():
    semanas = cargar()
    print(f"semanas con >=12 juegos cubiertos: {len(semanas)}")
    rng = np.random.default_rng(7)

    res = defaultdict(lambda: defaultdict(list))
    for (s, w), juegos in sorted(semanas.items()):
        gano_home = np.array([j["gano_home"] for j in juegos])
        empate = np.array([j["empate"] for j in juegos])
        fans = np.array([j["fans_home"] for j in juegos])
        pick_f = rng.random((SIMS, N_RIV, len(juegos))) < fans[None, None, :]
        hits_f = np.where(pick_f, gano_home[None, None, :],
                          (~gano_home & ~empate)[None, None, :]).sum(axis=2)
        mejor = hits_f.max(axis=1)
        mitad = "20-22" if s <= 2022 else "23-25"
        for nombre, pick_home in planillas(juegos).items():
            mios = np.where(pick_home, gano_home, ~gano_home & ~empate).sum()
            res[nombre]["hits"].append((mios, len(juegos)))
            res[nombre][mitad].append(100 * np.mean(mios > mejor))
            res[nombre]["solo"].append(100 * np.mean(mios > mejor))

    print(f"\n{'política':<8} {'aciertos/sem':>13} {'P(1º único)':>12} "
          f"{'20-22':>7} {'23-25':>7}")
    for nombre in ["fav", "m3", "anti1", "anti2", "anti3", "anti20"]:
        h = res[nombre]["hits"]
        media_h = np.mean([a for a, _n in h])
        print(f"{nombre:<8} {media_h:>13.2f} "
              f"{np.mean(res[nombre]['solo']):>11.1f}% "
              f"{np.mean(res[nombre]['20-22']):>6.1f}% "
              f"{np.mean(res[nombre]['23-25']):>6.1f}%")


if __name__ == "__main__":
    main()
