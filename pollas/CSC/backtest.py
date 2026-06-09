#!/usr/bin/env python3
"""
Backtest del pipeline CSC contra ~12k partidos reales de ligas (football-data).

    python pollas/CSC/backtest.py                 # informe completo
    python pollas/CSC/backtest.py --max 4000      # más rápido (submuestra)

Produce:
  1) EDGE: puntos CSC por partido de EV-máximo vs baselines (modal, favorito).
  2) CALIBRACIÓN: 1X2, Over/Under y goles por equipo (predicho vs observado).
  3) HIPERPARÁMETROS (walk-forward): método de margen y Dixon-Coles, in/out.
  4) Traducción del edge a un field_skill realista para cupos.py.
"""

import argparse
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import backtest as bt
from pollas.CSC.reglas import RONDAS

PARAMS = RONDAS["primera"]  # (1, 2, 3): fase de grupos


def evaluar(partidos, metodo="proporcional", dc=True, G=7):
    """Devuelve métricas de edge y calibración sobre una lista de partidos."""
    pts = {"evmax": [], "modal": [], "favorito": []}
    # calibración
    cal_1x2 = []   # (p_home_win, gano_home)
    cal_over = []  # (p_over, fue_over)
    cal_goles = {g: [0, 0] for g in range(5)}  # g -> [pred_acum, obs_acum] (home+away)
    n_goles = 0
    # exploit: favorito marca, débil ¿0 o 1?
    delta_debil = []

    for p in partidos:
        try:
            M = bt.matriz_de_partido(p, metodo, dc)
        except Exception:
            continue
        real = (p["fthg"], p["ftag"])
        ev = bt.fill_evmax(M, PARAMS, G)
        md = bt.fill_modal(M)
        fv = bt.fill_favorito1(M)
        pts["evmax"].append(bt.puntos(ev, real, PARAMS))
        pts["modal"].append(bt.puntos(md, real, PARAMS))
        pts["favorito"].append(bt.puntos(fv, real, PARAMS))

        pL = float(np.tril(M, -1).sum())
        cal_1x2.append((pL, real[0] > real[1]))
        margH = M.sum(axis=1)
        margA = M.sum(axis=0)
        total = np.add.outer(np.arange(M.shape[0]), np.arange(M.shape[1]))
        p_over = float(M[total >= 3].sum())
        cal_over.append((p_over, (real[0] + real[1]) >= 3))
        for g in range(5):
            cal_goles[g][0] += margH[g] + margA[g]
            cal_goles[g][1] += (real[0] == g) + (real[1] == g)
        n_goles += 2

    return {
        "n": len(pts["evmax"]),
        "pts": {k: float(np.mean(v)) for k, v in pts.items()},
        "cal_1x2": cal_1x2,
        "cal_over": cal_over,
        "cal_goles": cal_goles,
        "n_goles": n_goles,
    }


def tabla_calibracion(pares, nbins=10):
    """Bins de (prob_predicha, indicador). Devuelve filas (pred_medio, obs, n)."""
    pares = sorted(pares)
    n = len(pares)
    filas = []
    for b in range(nbins):
        lo = b * n // nbins
        hi = (b + 1) * n // nbins
        chunk = pares[lo:hi]
        if not chunk:
            continue
        pred = np.mean([c[0] for c in chunk])
        obs = np.mean([1.0 if c[1] else 0.0 for c in chunk])
        filas.append((pred, obs, len(chunk)))
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description="Backtest del pipeline CSC")
    ap.add_argument("--max", type=int, help="submuestrear a N partidos (rapidez)")
    ap.add_argument("--seasons", nargs="*", default=bt.SEASONS)
    ap.add_argument("--ligas", nargs="*", default=bt.LIGAS)
    args = ap.parse_args(argv)

    print("Cargando partidos...", flush=True)
    P = bt.cargar_partidos(args.seasons, args.ligas)
    rng = np.random.default_rng(0)
    if args.max and len(P) > args.max:
        idx = rng.choice(len(P), args.max, replace=False)
        P = [P[i] for i in idx]
    print(f"  {len(P)} partidos.\n", flush=True)

    # ---- 1) EDGE + 2) CALIBRACIÓN (config base: proporcional + Dixon-Coles)
    print("=== 1) EDGE: puntos CSC por partido (fase de grupos) ===")
    r = evaluar(P, "proporcional", dc=True)
    base = r["pts"]["modal"]
    for k in ("evmax", "modal", "favorito"):
        d = r["pts"][k] - r["pts"]["modal"]
        print(f"  {k:9s}: {r['pts'][k]:.3f} pts/partido "
              f"({'+' if d>=0 else ''}{d:.3f} vs modal)")
    edge = r["pts"]["evmax"] - r["pts"]["favorito"]
    print(f"  → EDGE EV-máximo vs jugador 'favorito 1-0': "
          f"+{r['pts']['evmax']-r['pts']['favorito']:.3f} pts/partido")

    print("\n=== 2) CALIBRACIÓN ===")
    print("  1X2  P(gana local):  predicho -> observado")
    for pred, obs, n in tabla_calibracion(r["cal_1x2"]):
        print(f"    {pred:.2f} -> {obs:.2f}   (n={n})")
    print("  Over 2.5:")
    ov = r["cal_over"]
    print(f"    predicho medio {np.mean([x[0] for x in ov]):.3f} -> "
          f"observado {np.mean([1.0 if x[1] else 0 for x in ov]):.3f}")
    print("  Goles por equipo (predicho vs observado):")
    for g in range(5):
        pr = r["cal_goles"][g][0] / r["n_goles"]
        ob = r["cal_goles"][g][1] / r["n_goles"]
        print(f"    {g} goles: predicho {pr:.3f} -> observado {ob:.3f}")

    # ---- 3) HIPERPARÁMETROS (walk-forward por temporada)
    print("\n=== 3) HIPERPARÁMETROS (método de margen × Dixon-Coles) ===")
    print(f"  {'config':28s} {'EV-max pts':>11} {'edge vs modal':>14}")
    sub = P if (args.max and args.max <= 5000) else \
        [P[i] for i in rng.choice(len(P), min(5000, len(P)), replace=False)]
    resultados = {}
    for metodo in ["proporcional", "shin", "potencia"]:
        for dc in [True, False]:
            rr = evaluar(sub, metodo, dc)
            nombre = f"{metodo}+{'DC' if dc else 'sinDC'}"
            resultados[nombre] = rr["pts"]["evmax"]
            print(f"  {nombre:28s} {rr['pts']['evmax']:>11.3f} "
                  f"{rr['pts']['evmax']-rr['pts']['modal']:>+14.3f}")
    mejor = max(resultados, key=resultados.get)
    print(f"  → mejor configuración: {mejor}")

    # walk-forward: entrenar (elegir config) en temporadas viejas, test en nuevas
    if len(args.seasons) >= 2:
        corte = len(args.seasons) // 2
        viejas, nuevas = args.seasons[:corte], args.seasons[corte:]
        Ptr = [p for p in P if p["season"] in viejas]
        Pte = [p for p in P if p["season"] in nuevas]
        print(f"\n  Walk-forward: train {viejas} ({len(Ptr)}) / "
              f"test {nuevas} ({len(Pte)})")
        cfgs = {}
        for metodo in ["proporcional", "shin"]:
            cfgs[metodo] = evaluar(Ptr, metodo, True)["pts"]["evmax"]
        elegido = max(cfgs, key=cfgs.get)
        out = evaluar(Pte, elegido, True)
        print(f"    config elegida en train: {elegido}+DC")
        print(f"    en TEST (out-of-sample): EV-max {out['pts']['evmax']:.3f} "
              f"pts, edge vs modal {out['pts']['evmax']-out['pts']['modal']:+.3f}")

    # ---- 4) Traducción a field_skill
    print("\n=== 4) ¿Qué tan grande es el edge? (para cupos.py) ===")
    e_modal = r["pts"]["evmax"] - r["pts"]["modal"]
    e_fav = r["pts"]["evmax"] - r["pts"]["favorito"]
    print(f"  EV-máximo aporta +{e_modal:.3f} pts/partido vs un rival 'modal'")
    print(f"  y +{e_fav:.3f} pts/partido vs un rival 'favorito 1-0'.")
    print("  Sobre 72 partidos de grupos eso son "
          f"~{e_modal*72:.1f} a {e_fav*72:.1f} pts de ventaja acumulada.")
    print("  Un rival 'modal/favorito' ≈ field-skill medio-alto: usa")
    print("  cupos.py --field-skill 0.4..0.6 (no el optimista 0.1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
