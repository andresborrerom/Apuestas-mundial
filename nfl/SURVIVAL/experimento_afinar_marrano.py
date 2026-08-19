"""
Afinar la heurística marrano SIN hacer trampa: dos refinamientos posibles.

1. NESTED WALK-FORWARD de parámetros: en el backtest principal, (umbral=0.70,
   bottom-5) se fijaron a priori. La malla de robustez mostró que todas las
   celdas son positivas, pero elegir "la mejor celda" mirando 2011-2025
   sería tunear en test. Acá lo honesto: para cada temporada Y, elegir los
   parámetros que MEJOR sobrevivieron en 2011..Y-1 y jugarlos en Y.
   Si el nested le gana al fijo, hay señal de que adaptar parámetros paga;
   si no, el default a priori era suficiente (y nos quedamos con él).

2. CONSCIENTE DE VIDAS: la heurística ignora cuántas vidas quedan. Variante:
   con las 2 vidas intactas se juega marrano normal (ruta barata); con 1
   vida se cambia a máxima p disponible (proteger la última vida).
   La intuición: la primera vida es un amortiguador que te deja tomar el
   descuento estructural; la última no.

Uso:  python nfl/SURVIVAL/experimento_afinar_marrano.py
"""

import os
import sys
from itertools import product

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from nfl.SURVIVAL import estrategias as est, simulador as sim  # noqa: E402
from nfl.SURVIVAL.backtest_survival import (  # noqa: E402
    TEMPORADAS, preparar_temporada)

MALLA = list(product((0.65, 0.70, 0.75), (3, 5, 7)))
DEFAULT = (0.70, 5)
THETA, SIMS = 25, 400


def trayectoria(semanas_ops, semanas_juegos, fuerza_w,
                umbral, k, proteger_ultima_vida=False):
    """Marrano con params dados; opcional: 1 vida -> máxima p (greedy)."""
    est.UMBRAL_MARRANO, est.N_MARRANOS = umbral, k
    usados, vidas = set(), 2
    for w in sorted(semanas_ops):
        ops = semanas_ops[w]
        if proteger_ultima_vida and vidas == 1:
            pick = est.greedy(ops, usados)
        else:
            pick = est.marrano(ops, usados, fuerza=fuerza_w.get(w))
        if pick is None:
            vidas -= 1
        else:
            usados.add(pick)
            if not sim.resultado_pick(pick, semanas_juegos[w]):
                vidas -= 1
        if vidas == 0:
            return w
    return None


def main():
    partidos = datos.cargar_partidos()
    rng = np.random.default_rng(7)

    prep = {t: preparar_temporada(partidos, t) for t in TEMPORADAS}

    # precomputar semanas sobrevividas por (param, temporada) — determinista
    sobrev = {}
    for (u, k), t in product(MALLA, TEMPORADAS):
        sj, so, _elo, fz = prep[t]
        sobrev[(u, k, t)] = trayectoria(so, sj, fz, u, k)

    variantes = {}
    # 1) fijo (el del backtest principal)
    variantes["fijo (0.70/5)"] = {
        t: sobrev[(0.70, 5, t)] for t in TEMPORADAS}
    # 2) nested: params elegidos solo con el pasado
    nested, eleccion = {}, {}
    for t in TEMPORADAS:
        pasado = [y for y in TEMPORADAS if y < t]
        if not pasado:
            u, k = DEFAULT
        else:
            u, k = max(MALLA, key=lambda p: np.mean(
                [19 if sobrev[(p[0], p[1], y)] is None
                 else sobrev[(p[0], p[1], y)] for y in pasado]))
        eleccion[t] = (u, k)
        nested[t] = sobrev[(u, k, t)]
    variantes["nested (párams del pasado)"] = nested
    # 3) consciente de vidas (params default)
    variantes["vidas (1 vida -> máx p)"] = {
        t: trayectoria(prep[t][1], prep[t][0], prep[t][3],
                       *DEFAULT, proteger_ultima_vida=True)
        for t in TEMPORADAS}
    est.UMBRAL_MARRANO, est.N_MARRANOS = DEFAULT  # restaurar

    print("params elegidos por nested:",
          {t: eleccion[t] for t in list(TEMPORADAS)[1::3]})
    print()
    print(f"{'variante':<28} {'sem. medias':>11} {'vivo 18':>8} "
          f"{'E[neto] N=14':>13}")
    for nombre, elims in variantes.items():
        sems = [19 if e is None else e for e in elims.values()]
        netos = []
        for t in TEMPORADAS:
            sj, so = prep[t][0], prep[t][1]
            trays = [sim.trayectoria_field(so, sj, THETA, rng)
                     for _ in range(SIMS)]
            field = np.array([np.inf if e is None else e for e in trays])
            e_n = np.inf if elims[t] is None else elims[t]
            for _ in range(SIMS // 4):
                muestra = rng.choice(field, size=13, replace=True)
                netos.append(sim.repartir_pozo(e_n, muestra))
        vivos = sum(1 for e in elims.values() if e is None)
        print(f"{nombre:<28} {np.mean(sems):>11.1f} "
              f"{vivos:>5}/15 {np.mean(netos):>+9.2f} ap. "
              f"(${np.mean(netos) * 0.3:+.2f}M)")


if __name__ == "__main__":
    main()
