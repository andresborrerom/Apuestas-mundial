"""
Conversión de cuotas de casas de apuestas a probabilidades reales.

Las cuotas decimales publicadas NO son probabilidades: sus inversos (1/cuota)
suman más de 1. Ese exceso es el margen de la casa (overround / "vig"), que
hay que repartir para recuperar las probabilidades "limpias".

Métodos implementados:
  - "proporcional": reparte el margen proporcionalmente (a más cuota, más
    descuento). Es el estándar de la industria y el default. También llamado
    método multiplicativo.
  - "aditivo": resta a cada probabilidad bruta la misma cantidad. Tiende a
    favorecer a los favoritos; útil como sensibilidad.
  - "potencia": eleva las probabilidades brutas a un exponente k tal que sumen
    1. Corrige mejor el sesgo favorito-no favorito ("favourite-longshot bias").
  - "shin": modelo de Shin (1992) que asume una proporción de apostadores con
    información privilegiada. Suele ser el más preciso para 1X2.
"""

import numpy as np
from scipy.optimize import brentq


def margen(cuotas):
    """Margen de la casa (overround). 0.06 = 6% de comisión implícita."""
    cuotas = np.asarray(cuotas, dtype=float)
    return float(np.sum(1.0 / cuotas) - 1.0)


def a_probabilidades(cuotas, metodo="proporcional"):
    """Convierte cuotas decimales a probabilidades que suman 1.

    Parámetros
    ----------
    cuotas : lista/array de cuotas decimales (ej. [1.80, 3.60, 4.50]).
    metodo : "proporcional" | "aditivo" | "potencia" | "shin".

    Devuelve un np.array de probabilidades que suma exactamente 1.
    """
    cuotas = np.asarray(cuotas, dtype=float)
    if np.any(cuotas <= 1.0):
        raise ValueError("Las cuotas decimales deben ser > 1.0")

    bruta = 1.0 / cuotas              # probabilidades implícitas sin limpiar
    overround = bruta.sum()

    if metodo == "proporcional":
        p = bruta / overround

    elif metodo == "aditivo":
        n = len(bruta)
        p = bruta - (overround - 1.0) / n
        if np.any(p <= 0):
            # si algún resultado queda en negativo, caemos a proporcional
            p = bruta / overround

    elif metodo == "potencia":
        # buscar k tal que sum(bruta**k) == 1
        f = lambda k: np.sum(bruta ** k) - 1.0
        k = brentq(f, 1e-6, 100.0)
        p = bruta ** k

    elif metodo == "shin":
        p = _shin(bruta)

    else:
        raise ValueError(f"Método desconocido: {metodo}")

    return p / p.sum()  # garantizar suma 1 exacta


def _shin(bruta):
    """Probabilidades por el modelo de Shin. `bruta` = 1/cuotas."""
    B = bruta.sum()

    def prob_dado_z(z):
        return (np.sqrt(z ** 2 + 4 * (1 - z) * bruta ** 2 / B) - z) / (2 * (1 - z))

    # buscar z en [0, 1) tal que las probabilidades sumen 1
    f = lambda z: prob_dado_z(z).sum() - 1.0
    try:
        z = brentq(f, 1e-9, 0.5)
    except ValueError:
        # sin solución estable -> proporcional
        return bruta / B
    return prob_dado_z(z)
