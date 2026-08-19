"""
Backtest walk-forward del Survival: 15 temporadas reales (2011-2025).

Para cada temporada:
  - Nuestras estrategias corren deterministas contra el ground truth
    (resultados reales), con información walk-forward (Elo y fuerza de
    mercado solo con semanas ya jugadas; líneas solo de la semana actual).
  - El field se simula (N rivales, sharpness theta) y se mide E[ganancia]
    en unidades de aporte ($300k = 1) y P(cobrar del pozo).

Uso:
  python nfl/SURVIVAL/backtest_survival.py            # tabla completa
  python nfl/SURVIVAL/backtest_survival.py --detalle  # picks por temporada
"""

import argparse
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402
from nfl.SURVIVAL import estrategias as est, simulador as sim  # noqa: E402
from nfl.SURVIVAL.marrano import fuerza_hasta_semana  # noqa: E402

TEMPORADAS = range(2011, 2026)
N_FIELD = [9, 19, 39]        # rivales (pool de 10/20/40 con nosotros)
THETAS = [10, 25, 50]        # sharpness del field (supuesto)
N_SIMS = 400                 # sims de field por (temporada, config)


def preparar_temporada(partidos_todos, temporada):
    """Arma todo lo walk-forward de una temporada."""
    ps = [p for p in partidos_todos if p["season"] == temporada]
    semanas_juegos = {w: js for (_s, w), js in
                      datos.por_semana(ps).items()}
    semanas_ops = {w: est.opciones_semana(js)
                   for w, js in semanas_juegos.items()}

    # Elo hasta ANTES de cada semana (arranca acumulado desde 1999)
    elo = prob.Elo()
    previos = sorted((p for p in partidos_todos
                      if p["season"] < temporada),
                     key=lambda x: (x["season"], x["week"], x["gameday"]))
    for p in previos:
        elo.actualizar(p)
    elo_por_semana, fuerza_por_semana = {}, {}
    import copy
    for w in sorted(semanas_juegos):
        elo_por_semana[w] = copy.deepcopy(elo)
        fuerza = fuerza_hasta_semana(ps, w)
        if fuerza is None or w < 4:
            # semanas tempranas: sin señal de mercado estable — el ranking
            # Elo (walk-forward, arrastra temporadas previas) da los tiers
            equipos = {p[k] for p in ps for k in ("home", "away")}
            fuerza = {eq: elo._get(eq) for eq in equipos}
        fuerza_por_semana[w] = fuerza
        for p in semanas_juegos[w]:
            elo.actualizar(p)
    return semanas_juegos, semanas_ops, elo_por_semana, fuerza_por_semana


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detalle", action="store_true")
    ap.add_argument("--sims", type=int, default=N_SIMS)
    args = ap.parse_args()

    partidos = datos.cargar_partidos()
    rng = np.random.default_rng(7)

    elims = defaultdict(dict)        # estrategia -> temporada -> elim week
    picks_todos = defaultdict(dict)
    field_trays = {}                 # (temporada, theta) -> array de elims

    for temporada in TEMPORADAS:
        sj, so, elo_w, fuerza_w = preparar_temporada(partidos, temporada)
        for nombre in est.ESTRATEGIAS:
            elim, picks = sim.trayectoria_estrategia(
                nombre, so, sj, sj, elo_w, fuerza_w)
            elims[nombre][temporada] = elim
            picks_todos[nombre][temporada] = picks
        for theta in THETAS:
            trays = [sim.trayectoria_field(so, sj, theta, rng)
                     for _ in range(args.sims)]
            field_trays[(temporada, theta)] = np.array(
                [np.inf if e is None else e for e in trays])

    # ---------- semanas sobrevividas ------------------------------------
    print("=" * 74)
    print("SUPERVIVENCIA (semana de eliminación por temporada; 18+ = vivo)")
    print("=" * 74)
    print(f"{'temporada':<10}" + "".join(f"{n:>11}" for n in est.ESTRATEGIAS))
    for t in TEMPORADAS:
        fila = f"{t:<10}"
        for n in est.ESTRATEGIAS:
            e = elims[n][t]
            fila += f"{'VIVO':>11}" if e is None else f"{e:>11}"
        print(fila)
    print(f"{'media':<10}", end="")
    for n in est.ESTRATEGIAS:
        vals = [19 if e is None else e for e in elims[n].values()]
        print(f"{np.mean(vals):>11.1f}", end="")
    print(f"\n{'vivo 18':<10}", end="")
    for n in est.ESTRATEGIAS:
        vivos = sum(1 for e in elims[n].values() if e is None)
        print(f"{vivos:>10}/{len(TEMPORADAS)}", end="")
    print()

    # ---------- E[ganancia] contra el field ------------------------------
    print()
    print("=" * 74)
    print(f"E[GANANCIA] en aportes ($300k=1) y P(cobrar), "
          f"{args.sims} sims de field")
    print("=" * 74)
    for theta in THETAS:
        print(f"\n--- field theta={theta} "
              f"({'casual' if theta == 10 else 'normal' if theta == 25 else 'afilado'}) ---")
        print(f"{'estrategia':<11}"
              + "".join(f"{'N=' + str(nf + 1):>21}" for nf in N_FIELD))
        for nombre in est.ESTRATEGIAS:
            fila = f"{nombre:<11}"
            for nf in N_FIELD:
                gan, cobra = [], []
                for t in TEMPORADAS:
                    e_n = elims[nombre][t]
                    e_n = np.inf if e_n is None else e_n
                    trays = field_trays[(t, theta)]
                    for _ in range(args.sims // 4):
                        muestra = rng.choice(trays, size=nf, replace=True)
                        g = sim.repartir_pozo(e_n, muestra)
                        gan.append(g)
                        cobra.append(g > -1)
                fila += (f"  {np.mean(gan):+7.2f} "
                         f"(P {100 * np.mean(cobra):4.1f}%)")
            print(fila)

    # ---------- detalle de picks ----------------------------------------
    if args.detalle:
        for nombre in ["planeada", "marrano"]:
            print(f"\n===== PICKS {nombre} =====")
            for t in TEMPORADAS:
                linea = " ".join(
                    f"w{w}:{pk}({p:.2f}){'✓' if ok else '✗'}"
                    for w, pk, p, ok in picks_todos[nombre][t] if pk)
                print(f"{t}: {linea}")


if __name__ == "__main__":
    main()
