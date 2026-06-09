"""
Modelo de marcadores: de las probabilidades de mercado a la distribución
completa de resultados (cuántos goles mete cada equipo).

Idea central
------------
Los goles de cada equipo se modelan como Poisson. Con un parámetro de goles
esperados por equipo (lambda_local, lambda_visita) queda definida la
probabilidad de CADA marcador posible (0-0, 1-0, 2-1, ...).

¿De dónde salen esas lambdas? Las despejamos para que el modelo reproduzca
las probabilidades que ya sacamos de las cuotas:
  - el 1X2 (gana local / empate / gana visita), y
  - opcionalmente el Over/Under (probabilidad de más de X goles totales).

Corrección de Dixon-Coles
-------------------------
El Poisson independiente subestima los empates y los marcadores bajos (0-0,
1-1). Dixon-Coles añade un parámetro `rho` que ajusta esas cuatro celdas. Lo
dejamos activado por defecto.

Si tu casa publica cuotas de MARCADOR EXACTO, puedes saltarte el modelo y
construir la matriz directamente con `matriz_desde_cuotas_exactas` (más
directo, sin supuestos).
"""

import numpy as np
from scipy.stats import poisson
from scipy.optimize import minimize


# --------------------------------------------------------------------------
# Matriz de marcadores
# --------------------------------------------------------------------------

def _tau(M, lh, la, rho):
    """Aplica la corrección de Dixon-Coles a las 4 celdas de marcador bajo."""
    M = M.copy()
    M[0, 0] *= 1.0 - lh * la * rho
    M[0, 1] *= 1.0 + lh * rho
    M[1, 0] *= 1.0 + la * rho
    M[1, 1] *= 1.0 - rho
    return M


def matriz_marcadores(lambda_local, lambda_visita, rho=0.0, max_goles=10):
    """Matriz M donde M[i, j] = P(local marca i, visita marca j)."""
    i = np.arange(max_goles + 1)
    ph = poisson.pmf(i, lambda_local)
    pa = poisson.pmf(i, lambda_visita)
    M = np.outer(ph, pa)
    if rho != 0.0:
        M = _tau(M, lambda_local, lambda_visita, rho)
        M = np.clip(M, 0.0, None)  # evitar celdas negativas por rho extremo
    return M / M.sum()


# --------------------------------------------------------------------------
# Lecturas de la matriz
# --------------------------------------------------------------------------

def prob_1x2(M):
    """(P_gana_local, P_empate, P_gana_visita) a partir de la matriz."""
    local = float(np.tril(M, -1).sum())   # i > j
    empate = float(np.trace(M))           # i == j
    visita = float(np.triu(M, 1).sum())   # i < j
    return local, empate, visita


def prob_totales(M, linea=2.5):
    """(P_under, P_over) para una línea de goles totales."""
    n = M.shape[0]
    total_goles = np.add.outer(np.arange(n), np.arange(n))
    over = float(M[total_goles > linea].sum())
    return 1.0 - over, over


def marcador_mas_probable(M):
    """((i, j), probabilidad) del marcador más probable."""
    idx = np.unravel_index(np.argmax(M), M.shape)
    return (int(idx[0]), int(idx[1])), float(M[idx])


# --------------------------------------------------------------------------
# Ajuste de lambdas a las probabilidades de mercado
# --------------------------------------------------------------------------

def ajustar_lambdas(p_local, p_empate, p_visita,
                    p_over=None, linea=2.5,
                    usar_dixon_coles=True, max_goles=10):
    """Despeja (lambda_local, lambda_visita, rho) que reproducen el mercado.

    Devuelve dict con lambdas, rho, la matriz resultante y el error de ajuste.
    """
    objetivo_over = p_over

    def perdida(params):
        lh, la = params[0], params[1]
        rho = params[2] if usar_dixon_coles else 0.0
        M = matriz_marcadores(lh, la, rho, max_goles=max_goles)
        h, d, a = prob_1x2(M)
        err = (h - p_local) ** 2 + (d - p_empate) ** 2 + (a - p_visita) ** 2
        if objetivo_over is not None:
            _, over = prob_totales(M, linea)
            err += (over - objetivo_over) ** 2
        return err

    if usar_dixon_coles:
        x0 = [1.3, 1.1, -0.05]
        bounds = [(0.05, 6.0), (0.05, 6.0), (-0.15, 0.15)]
    else:
        x0 = [1.3, 1.1]
        bounds = [(0.05, 6.0), (0.05, 6.0)]

    res = minimize(perdida, x0, bounds=bounds, method="L-BFGS-B")
    lh, la = res.x[0], res.x[1]
    rho = res.x[2] if usar_dixon_coles else 0.0
    M = matriz_marcadores(lh, la, rho, max_goles=max_goles)
    return {
        "lambda_local": float(lh),
        "lambda_visita": float(la),
        "rho": float(rho),
        "matriz": M,
        "error": float(res.fun),
    }


# --------------------------------------------------------------------------
# Construcción directa desde cuotas de marcador exacto
# --------------------------------------------------------------------------

def matriz_desde_cuotas_exactas(cuotas_por_marcador, max_goles=10,
                                metodo_margen="proporcional"):
    """Construye la matriz a partir de cuotas de marcador exacto.

    cuotas_por_marcador : dict {(i, j): cuota_decimal}, p. ej.
        {(1, 0): 7.0, (2, 1): 8.5, (0, 0): 9.0, ...}

    Quita el margen sobre el conjunto de marcadores ofrecidos y normaliza.
    Los marcadores no listados quedan con probabilidad 0.
    """
    M = np.zeros((max_goles + 1, max_goles + 1))
    bruto = {ij: 1.0 / c for ij, c in cuotas_por_marcador.items()}
    s = sum(bruto.values())  # incluye el margen
    for (i, j), b in bruto.items():
        if i <= max_goles and j <= max_goles:
            M[i, j] = b / s
    if M.sum() == 0:
        raise ValueError("Ningún marcador válido dentro de max_goles")
    return M / M.sum()
