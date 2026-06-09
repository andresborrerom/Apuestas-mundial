"""
Simulador del TORNEO COMPLETO para estudiar la dispersión por ronda.

La polla paga por el puntaje TOTAL acumulado (grupos + todas las eliminatorias),
con puntos que CRECEN por ronda. Pocos partidos en rondas avanzadas pero valen
mucho más. Pregunta: ¿conviene SUBIR la dispersión (perturbación entre cupos) a
medida que avanzan las rondas?

Estructura Mundial 2026 (rondas CSC) y sus puntos:
  primera 72 · dieciseisavos 16 · octavos 8 · cuartos 4 · semis 2 ·
  tercer_puesto 1 · final 1.

Nota honesta: solo tenemos modelos reales de los partidos de GRUPOS. Para las
eliminatorias usamos como PROXY los partidos de grupos más PAREJOS (las
eliminatorias enfrentan equipos más igualados). La conclusión es sobre la
ESTRUCTURA (muchos vs pocos partidos × multiplicadores), robusta al proxy.
"""

import numpy as np

from .marcadores import aplicar_sesgo_goles, prob_1x2
from .simulacion_polla import (PREMIOS, fill_evmax, generar_nuestras,
                               generar_field_mix, muestrear_torneos, _puntos)
from pollas.CSC.reglas import RONDAS

# (nombre, n_partidos)
ESTRUCTURA = [("primera", 72), ("dieciseisavos", 16), ("octavos", 8),
              ("cuartos", 4), ("semis", 2), ("tercer_puesto", 1), ("final", 1)]


def construir_rondas(grupo_matrices, rng):
    """Asigna matrices a cada ronda. Grupos = reales; eliminatorias = proxy
    (los partidos de grupos más parejos, muestreados)."""
    balance = sorted(grupo_matrices,
                     key=lambda M: abs(prob_1x2(M)[0] - prob_1x2(M)[2]))
    pool_ko = balance[:max(8, len(balance) // 3)]  # los más parejos
    rondas = []
    for nombre, n in ESTRUCTURA:
        if nombre == "primera":
            mats = list(grupo_matrices)
        else:
            idx = rng.choice(len(pool_ko), size=n, replace=True)
            mats = [pool_ko[i] for i in idx]
        rondas.append((nombre, mats, RONDAS[nombre]))
    return rondas


def simular_torneo(rondas, N, k, schedule, field_pesos, precio=100_000,
                   S=4000, sesgo=0.05, semilla=0, detalle=False):
    """Simula el torneo completo y devuelve métricas de cola.

    schedule: dict {ronda: n_swaps} = cuántos partidos perturbar por ronda.
    detalle=True añade los arrays por simulación (util, ganancia, mejor_rango,
    rangos_nuestros) para inspeccionar la distribución.
    """
    rng = np.random.default_rng(semilla)
    Ef = N - k
    pts_field = np.zeros((Ef, S))
    pts_ours = np.zeros((k, S))

    for nombre, mats, params in rondas:
        Mses = [aplicar_sesgo_goles(M, sesgo) for M in mats]
        ns = min(schedule.get(nombre, 0), len(mats))
        pool = min(len(mats), max(ns * 2 + 1, 1))  # perturbar entre los casi-empates
        oh, oa = generar_nuestras(Mses, k, params, estrategia="perturbada",
                                  rng=rng, n_swaps=ns, pool=pool)
        fh, fa = generar_field_mix(mats, Ef, field_pesos, params, rng)
        gh, ga = muestrear_torneos(mats, S, rng)
        pts_ours += _puntos(oh, oa, gh, ga, params)
        pts_field += _puntos(fh, fa, gh, ga, params)

    todo = np.vstack([pts_field, pts_ours]) + rng.random((N, S)) * 1e-6
    pot = N * precio
    premio = PREMIOS * pot
    orden = np.argsort(-todo, axis=0)
    es_nuestra = orden[:5, :] >= Ef
    ganancia = (es_nuestra * premio[:, None]).sum(axis=0)
    util = ganancia - k * precio
    rangos = np.argsort(orden, axis=0)
    rangos_nuestros = rangos[Ef:, :] + 1          # puesto 1..N de cada cupo
    mejor_rango = rangos_nuestros.min(axis=0)
    res = {
        "utilidad_media": float(util.mean()),
        "prob_primera": float((mejor_rango == 1).mean()),
        "prob_top3": float((mejor_rango <= 3).mean()),
        "prob_premio": float((ganancia > 0).mean()),
    }
    if detalle:
        res.update(util=util, ganancia=ganancia, mejor_rango=mejor_rango,
                   rangos_nuestros=rangos_nuestros, pot=N * precio)
    return res
