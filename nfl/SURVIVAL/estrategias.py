"""
Estrategias de pick para el Survival (2 vidas, sin repetir equipo).

Todas reciben el mismo contexto walk-forward: en la semana w solo se conoce
- las líneas (moneyline) de la semana w,
- los resultados de las semanas < w (vía Elo actualizado),
- el calendario completo (rival y sede de cada semana futura, sin líneas).

Estrategias:
  greedy      — el favorito más grande disponible esta semana. Baseline.
  marrano     — heurística del usuario: pegarle al marrano (bottom-K de
                fuerza) con equipos NO-élite si p >= umbral; los élite solo
                se usan si no hay pick anti-marrano decente. Ejecutable a
                mano sin computador.
  planeada    — asignación óptima semanas-restantes × equipos (Hungarian)
                maximizando sum(log p̂): p̂ de la semana actual sale del
                moneyline; p̂ de semanas futuras se proyecta con Elo.
                Resuelta de nuevo cada semana con la información nueva.
  anticrowd   — planeada + decorrelación: si el pick coincide con el
                favorito máximo de la semana (donde se amontona el field)
                y hay alternativa a menos de `delta` de p, toma la
                alternativa. (La idea de perturbación mínima de CSC.)
"""

import math

import numpy as np
from scipy.optimize import linear_sum_assignment

P_EMPATE = 0.004        # frecuencia histórica; empate cuesta vida
UMBRAL_MARRANO = 0.70   # p mínima para pegarle al marrano con un no-élite
N_MARRANOS = 5
N_ELITE = 5
DELTA_ANTICROWD = 0.03


def _estricta(p):
    return p * (1.0 - P_EMPATE)


def opciones_semana(juegos_ml):
    """[(equipo, rival, p_gana_estricta)] de una semana con moneylines."""
    ops = []
    for j in juegos_ml:
        if j["ml_home"] is None:
            continue
        # import local para evitar ciclo en el paquete
        from nfl import probabilidades as prob
        ph = prob.p_local_moneyline(j["ml_home"], j["ml_away"])
        ops.append((j["home"], j["away"], _estricta(ph)))
        ops.append((j["away"], j["home"], _estricta(1 - ph)))
    return ops


def greedy(ops, usados, **_):
    """Máxima p disponible esta semana."""
    libres = [(eq, riv, p) for eq, riv, p in ops if eq not in usados]
    return max(libres, key=lambda x: x[2])[0] if libres else None


def marrano(ops, usados, fuerza=None, **_):
    """Heurística: no-élite vs marrano si p>=umbral; si no, greedy."""
    libres = [(eq, riv, p) for eq, riv, p in ops if eq not in usados]
    if not libres:
        return None
    if fuerza:
        orden = sorted(fuerza, key=fuerza.get)
        marranos = set(orden[:N_MARRANOS])
        elite = set(orden[-N_ELITE:])
        anti = [(eq, riv, p) for eq, riv, p in libres
                if riv in marranos and eq not in elite and p >= UMBRAL_MARRANO]
        if anti:
            return max(anti, key=lambda x: x[2])[0]
        # sin pick anti-marrano decente: greedy PERO evitando quemar élite
        # si hay opción no-élite a menos de 5 puntos de p
        mejor = max(libres, key=lambda x: x[2])
        if mejor[0] in elite:
            no_elite = [o for o in libres if o[0] not in elite]
            if no_elite:
                alt = max(no_elite, key=lambda x: x[2])
                if mejor[2] - alt[2] <= 0.05:
                    return alt[0]
        return mejor[0]
    return max(libres, key=lambda x: x[2])[0]


def _matriz_futura(semana, ops, usados, calendario, elo, semanas_restantes):
    """Filas=semanas restantes, columnas=equipos; valor=log p̂ (o -inf)."""
    equipos = sorted({eq for sems in calendario.values()
                      for j in sems for eq in (j["home"], j["away"])}
                     - set(usados))
    idx = {eq: i for i, eq in enumerate(equipos)}
    W = len(semanas_restantes)
    M = np.full((W, len(equipos)), -1e9)
    for fila, w in enumerate(semanas_restantes):
        if w == semana:
            for eq, _riv, p in ops:
                if eq in idx:
                    M[fila, idx[eq]] = math.log(max(p, 1e-9))
        else:
            for j in calendario.get(w, []):
                p_home = elo.p_local(j["home"], j["away"])
                ph = _estricta(p_home)
                pa = _estricta(1 - p_home)
                if j["home"] in idx:
                    M[fila, idx[j["home"]]] = math.log(max(ph, 1e-9))
                if j["away"] in idx:
                    M[fila, idx[j["away"]]] = math.log(max(pa, 1e-9))
    return M, equipos


def planeada(ops, usados, semana=None, calendario=None, elo=None, **_):
    """Asignación óptima de equipos a semanas restantes (max sum log p̂)."""
    semanas_restantes = [w for w in sorted(calendario) if w >= semana]
    M, equipos = _matriz_futura(semana, ops, usados, calendario, elo,
                                semanas_restantes)
    if not equipos:
        return None
    filas, cols = linear_sum_assignment(-M)
    for f, c in zip(filas, cols):
        if semanas_restantes[f] == semana and M[f, c] > -1e8:
            return equipos[c]
    # sin asignación válida esta semana (no debería pasar): greedy
    return greedy(ops, usados)


def anticrowd(ops, usados, semana=None, calendario=None, elo=None,
              delta=DELTA_ANTICROWD, **_):
    """Planeada, pero se baja del pick masivo si la alternativa es barata."""
    pick = planeada(ops, usados, semana=semana, calendario=calendario,
                    elo=elo)
    if pick is None:
        return None
    libres = [(eq, riv, p) for eq, riv, p in ops if eq not in usados]
    if not libres:
        return pick
    top_semana = max(ops, key=lambda x: x[2])[0]  # donde se amontona el field
    if pick != top_semana:
        return pick
    p_pick = next(p for eq, _r, p in libres if eq == pick)
    alternativas = [(eq, p) for eq, _r, p in libres
                    if eq != pick and p_pick - p <= delta]
    if alternativas:
        return max(alternativas, key=lambda x: x[1])[0]
    return pick


ESTRATEGIAS = {
    "greedy": greedy,
    "marrano": marrano,
    "planeada": planeada,
    "anticrowd": anticrowd,
}
