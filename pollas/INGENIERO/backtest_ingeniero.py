#!/usr/bin/env python3
"""
Backtest del pipeline para las reglas de INGENIERO (Polla Mundial 2026 de Pato).
Mismo harness de ground truth que CSC (~miles de partidos reales de
football-data.co.uk: cuotas de cierre 1X2 + O/U y resultado real).

Responde, con datos reales (no con el modelo):
  1) ¿El relleno EV-máximo BAJO LAS REGLAS DE INGENIERO gana puntos reales vs
     baselines humanos (modal, favorito 2-1, favorito 3-0)?
  2) ¿De verdad conviene 3-0 a favoritos fuertes, o es un espejismo del modelo?
     (estratificado por fuerza del favorito).
  3) Walk-forward: ¿ayuda recalibrar la distribución de goles (aprendida en
     train) fuera de muestra? ¿con qué intensidad?
  4) Sensibilidad a la interpretación ambigua "marcador de un equipo" (por equipo
     vs total).

    python pollas/INGENIERO/backtest_ingeniero.py --max 6000

Reglas INGENIERO por partido (todas suman): marcador exacto 3 · ganador/empate 2
· marcador de un equipo 1 · total de goles 1 · goles de un equipo ≥3 (exacto) 5.
(El ×5 de Colombia y el +8 de "único acertante" NO se backtestean aquí: no hay
Colombia en clubes y la unicidad depende del campo; se razonan aparte.)
"""
import argparse, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from motor import backtest as bt


def puntos_ing(pred, real, un_equipo="or"):
    """Puntaje INGENIERO de un relleno vs resultado real (sin Colombia/unicidad).
    un_equipo: 'or' = 1 pt si aciertas al menos un equipo; 'cada' = 1 pt por equipo."""
    pa, pv = pred; ra, rv = real; s = 0
    if pa == ra and pv == rv: s += 3                 # marcador completo
    if np.sign(pa - pv) == np.sign(ra - rv): s += 2  # ganador o empate
    if un_equipo == "cada": s += (pa == ra) + (pv == rv)
    else: s += 1 if (pa == ra or pv == rv) else 0    # marcador de un equipo
    if pa + pv == ra + rv: s += 1                    # total de goles
    if pa >= 3 and pa == ra: s += 5                  # ≥3 goles local (exacto)
    if pv >= 3 and pv == rv: s += 5                  # ≥3 goles visita
    return s


def fill_evmax_ing(M, un_equipo="or", G=6):
    """Relleno que maximiza el puntaje INGENIERO esperado sobre la matriz M."""
    n, m = M.shape
    best, bev = (0, 0), -1.0
    for h in range(G + 1):
        for a in range(G + 1):
            ev = 0.0
            for gh in range(n):
                row = M[gh]
                for ga in range(m):
                    p = row[ga]
                    if p > 1e-12:
                        ev += p * puntos_ing((h, a), (gh, ga), un_equipo)
            if ev > bev:
                bev, best = ev, (h, a)
    return best


def fill_fav(M, fg, wg):
    """Relleno 'favorito fg - débil wg', orientado al lado favorecido."""
    pL = float(np.tril(M, -1).sum()); pV = float(np.triu(M, 1).sum())
    return (fg, wg) if pL >= pV else (wg, fg)


def p_fav(M):
    return max(float(np.tril(M, -1).sum()), float(np.triu(M, 1).sum()))


def evaluar(partidos, metodo="proporcional", dc=True, un_equipo="or",
            recal=None):
    """Puntos INGENIERO reales/partido de cada estrategia."""
    acc = {k: [] for k in ["evmax", "modal", "fav21", "fav30", "fav20"]}
    n3_ev = n3_hit = 0
    for p in partidos:
        try:
            M = bt.matriz_de_partido(p, metodo, dc)
        except Exception:
            continue
        if recal is not None:
            M = bt.matriz_recalibrada(M, recal)
        real = (p["fthg"], p["ftag"])
        ev = fill_evmax_ing(M, un_equipo)
        acc["evmax"].append(puntos_ing(ev, real, un_equipo))
        acc["modal"].append(puntos_ing(bt.fill_modal(M), real, un_equipo))
        acc["fav21"].append(puntos_ing(fill_fav(M, 2, 1), real, un_equipo))
        acc["fav30"].append(puntos_ing(fill_fav(M, 3, 0), real, un_equipo))
        acc["fav20"].append(puntos_ing(fill_fav(M, 2, 0), real, un_equipo))
        if max(ev) >= 3:
            n3_ev += 1
            if (ev[0] >= 3 and ev[0] == real[0]) or (ev[1] >= 3 and ev[1] == real[1]):
                n3_hit += 1
    return {k: float(np.mean(v)) for k, v in acc.items()}, (n3_ev, n3_hit, len(acc["evmax"]))


def matrices_y_reales(partidos, metodo, dc):
    Ms, R = [], []
    for p in partidos:
        try:
            Ms.append(bt.matriz_de_partido(p, metodo, dc)); R.append((p["fthg"], p["ftag"]))
        except Exception:
            pass
    return Ms, R


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=6000)
    ap.add_argument("--seasons", nargs="*", default=bt.SEASONS)
    ap.add_argument("--ligas", nargs="*", default=bt.LIGAS)
    args = ap.parse_args(argv)

    print("Cargando partidos reales...", flush=True)
    P = bt.cargar_partidos(args.seasons, args.ligas)
    rng = np.random.default_rng(0)
    if args.max and len(P) > args.max:
        P = [P[i] for i in rng.choice(len(P), args.max, replace=False)]
    print(f"  {len(P)} partidos.\n", flush=True)

    # 1) EDGE: puntos INGENIERO reales por estrategia
    print("=== 1) EDGE: puntos INGENIERO reales / partido ===")
    r, (n3e, n3h, N) = evaluar(P, "proporcional", True, "or")
    orden = sorted(r.items(), key=lambda x: -x[1])
    for k, v in orden:
        d = v - r["modal"]
        print(f"  {k:8s}: {v:.3f}  ({'+' if d>=0 else ''}{d:.3f} vs modal)")
    print(f"  → EV-máximo pone ≥3 a un equipo en {n3e/N*100:.0f}% de partidos; "
          f"de esos acierta el ≥3 exacto en {(n3h/n3e*100) if n3e else 0:.0f}%.")

    # 2) ¿conviene 3-0 a FAVORITOS FUERTES? (estratificado)
    print("\n=== 2) ¿3-0 a favoritos fuertes paga? (estratificado por P(favorito)) ===")
    Ms, R = matrices_y_reales(P, "proporcional", True)
    pf = np.array([p_fav(M) for M in Ms])
    for lo, hi, et in [(0.0, 0.5, "parejo  <50%"), (0.5, 0.65, "favorito 50-65%"),
                       (0.65, 0.8, "fuerte 65-80%"), (0.8, 1.01, "aplastante >80%")]:
        idx = [i for i in range(len(Ms)) if lo <= pf[i] < hi]
        if not idx:
            continue
        sc = {et2: 0.0 for et2 in ["evmax", "fav21", "fav30", "fav20", "modal"]}
        for i in idx:
            M = Ms[i]
            sc["evmax"] += puntos_ing(fill_evmax_ing(M), R[i])
            sc["fav21"] += puntos_ing(fill_fav(M, 2, 1), R[i])
            sc["fav30"] += puntos_ing(fill_fav(M, 3, 0), R[i])
            sc["fav20"] += puntos_ing(fill_fav(M, 2, 0), R[i])
            sc["modal"] += puntos_ing(bt.fill_modal(M), R[i])
        n = len(idx)
        print(f"  {et:16s} (n={n:4d}): " +
              "  ".join(f"{k} {sc[k]/n:.2f}" for k in ["evmax", "fav30", "fav21", "fav20", "modal"]))

    # 3) Walk-forward: recalibración de goles (train -> test)
    print("\n=== 3) Walk-forward: recalibrar goles (train viejas / test nuevas) ===")
    if len(args.seasons) >= 2:
        corte = len(args.seasons) // 2
        viejas, nuevas = args.seasons[:corte], args.seasons[corte:]
        Ptr = [p for p in P if p["season"] in viejas]
        Pte = [p for p in P if p["season"] in nuevas]
        Mtr, Rtr = matrices_y_reales(Ptr, "proporcional", True)
        recal = bt.aprender_recalibracion(Mtr, Rtr)
        base_te, _ = evaluar(Pte, "proporcional", True, "or", recal=None)
        rec_te, _ = evaluar(Pte, "proporcional", True, "or", recal=recal)
        print(f"  train {viejas} ({len(Ptr)}) / test {nuevas} ({len(Pte)})")
        print(f"  factores r_g aprendidos: " +
              " ".join(f"{g}:{recal[g]:.2f}" for g in range(min(5, len(recal)))))
        print(f"  EV-máx en TEST:  sin recal {base_te['evmax']:.3f}  ->  "
              f"con recal {rec_te['evmax']:.3f}  (Δ {rec_te['evmax']-base_te['evmax']:+.3f})")

    # 4) Sensibilidad a la interpretación de "marcador de un equipo"
    print("\n=== 4) Sensibilidad: 'marcador de un equipo' = OR vs por-equipo ===")
    for ue in ["or", "cada"]:
        rr, _ = evaluar(P[:min(3000, len(P))], "proporcional", True, ue)
        print(f"  un_equipo='{ue}': evmax {rr['evmax']:.3f} · fav30 {rr['fav30']:.3f} "
              f"· fav21 {rr['fav21']:.3f} · modal {rr['modal']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
