#!/usr/bin/env python3
"""
LEMAITRE — equipo que marca el gol número N del torneo (25/50/75/100/125/150).

Modela de verdad (no adivina): ordena los partidos por calendario, usa los
resultados REALES de los ya jugados y simula los demás desde las cuotas; lleva la
cuenta acumulada de goles y atribuye el gol N al equipo que lo marca (dentro del
partido donde cae, repartido por los goles de cada equipo). Toma la moda sobre
muchas sims. Todos los N pedidos caen en fase de grupos.
"""
import argparse, json, os, sys, urllib.request
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api
from pollas.CSC.cupos import matriz_de_evento

OBJ = [25, 50, 75, 100, 125, 150]


def bajar_scores(api_key, days=3):
    url = (f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/scores/"
           f"?apiKey={api_key}&daysFrom={days}")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=40000)
    args = ap.parse_args(argv)
    odds = json.load(open(args.mock, encoding="utf-8"))
    # matrices + orden por calendario, desde las cuotas
    info = {}
    for e in odds:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        info[(c["home"], c["away"])] = dict(ct=e.get("commence_time", ""),
                                            M=matriz_de_evento(c, "proporcional", 2.5))
    # resultados reales (fija los jugados)
    reales = {}
    if args.api_key:
        try:
            for e in bajar_scores(args.api_key):
                if e.get("completed") and e.get("scores"):
                    sc = {x["name"]: int(x["score"]) for x in e["scores"]}
                    reales[(e["home_team"], e["away_team"])] = (sc.get(e["home_team"]), sc.get(e["away_team"]))
        except Exception as ex:
            print(f"(aviso: sin resultados en vivo: {ex})")
    orden = sorted(info, key=lambda k: info[k]["ct"])
    S = args.sims; rng = np.random.default_rng(0)
    NT = orden
    # acumulado de goles por sim y equipo que marca el gol N
    cum = np.zeros(S, dtype=int)
    quien = {n: np.empty(S, dtype=object) for n in OBJ}
    pendiente = {n: np.ones(S, dtype=bool) for n in OBJ}
    for (h, a) in orden:
        M = info[(h, a)]["M"]
        if (h, a) in reales and None not in reales[(h, a)]:
            gh = np.full(S, reales[(h, a)][0]); ga = np.full(S, reales[(h, a)][1])
        else:
            fl = M.ravel() / M.sum(); k = rng.choice(fl.size, size=S, p=fl)
            gh, ga = k // M.shape[1], k % M.shape[1]
        tot = gh + ga
        nuevo = cum + tot
        for n in OBJ:
            cae = pendiente[n] & (cum < n) & (nuevo >= n)   # el gol N cae en este partido
            if cae.any():
                # ¿lo marca local o visita? repartido por sus goles en el partido
                pa = np.where(tot > 0, gh / np.maximum(tot, 1), 0.5)
                local = rng.random(S) < pa
                quien[n][cae] = np.where(local[cae], h, a)
                pendiente[n][cae] = False
        cum = nuevo

    print(f"Equipo que marca el gol N (moda sobre {S} sims; {len(reales)} partidos ya reales)\n")
    for n in OBJ:
        c = Counter(x for x in quien[n] if x is not None)
        if not c:
            print(f"  Gol #{n:3}: (no alcanzado en grupos)"); continue
        top = c.most_common(4)
        s = sum(c.values())
        det = "  ".join(f"{t}({v/s*100:.0f}%)" for t, v in top)
        marca = "  <-- NUEVO" if n in (25, 75, 125, 150) else ""
        print(f"  Gol #{n:3}: {top[0][0]:14} {top[0][1]/s*100:4.0f}%   | {det}{marca}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
