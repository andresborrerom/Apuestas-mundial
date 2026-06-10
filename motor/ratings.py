"""
Modelo de FUERZAS por equipo (ataque/defensa), para simular partidos entre
equipos ARBITRARIOS (eliminatorias) — no solo los cruces de grupo conocidos.

Se ajusta a los goles esperados (λ) de los partidos de grupos (de las cuotas):
    log λ_local  = ataque[local]  − defensa[visita] + ventaja_local
    log λ_visita = ataque[visita] − defensa[local]
Mínimos cuadrados sobre log λ. En sedes neutrales (Mundial) la ventaja_local ~0.

Con los ratings, cualquier cruce A vs B → (λ_A, λ_B) → matriz de marcadores.
Es la base para simular el bracket completo de LEMAITRE (campeón, llaves,
marcadores por slot).
"""

import numpy as np


def ajustar_ratings(partidos):
    """partidos: lista de (local, visita, lambda_local, lambda_visita).
    Devuelve dict {equipo: (ataque, defensa)} y ventaja_local."""
    teams = sorted({t for p in partidos for t in (p[0], p[1])})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    A, y = [], []
    for h, a, lh, la in partidos:
        r1 = np.zeros(2 * n + 1)
        r1[idx[h]] = 1; r1[n + idx[a]] = -1; r1[2 * n] = 1       # log λ_local
        A.append(r1); y.append(np.log(max(lh, 1e-3)))
        r2 = np.zeros(2 * n + 1)
        r2[idx[a]] = 1; r2[n + idx[h]] = -1                       # log λ_visita
        A.append(r2); y.append(np.log(max(la, 1e-3)))
    x, *_ = np.linalg.lstsq(np.array(A), np.array(y), rcond=None)
    atk, dfn, home = x[:n], x[n:2 * n], x[2 * n]
    ratings = {t: (float(atk[idx[t]]), float(dfn[idx[t]])) for t in teams}
    return ratings, float(home)


def lambdas_cruce(ratings, A, B, neutral=True, home=0.0):
    """λ esperados de un cruce A vs B (neutral por defecto = eliminatoria)."""
    aA, dA = ratings[A]; aB, dB = ratings[B]
    h = 0.0 if neutral else home
    return float(np.exp(aA - dB + h)), float(np.exp(aB - dA))


def fuerza(ratings, t):
    """Fuerza global de un equipo (ataque + defensa), para rankear.
    `defensa` alta = concede pocos goles (buena), así que SUMA."""
    a, d = ratings[t]
    return a + d
