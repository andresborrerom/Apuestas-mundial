"""
Tres proxies de P(gana) por partido NFL, para comparar contra ground truth.

1. MONEYLINE (mercado): cuotas decimales [local, visita] -> de-vig con
   motor/cuotas.py (mismo motor del Mundial; es agnóstico al deporte).
   El mercado de moneyline es a 2 salidas (el empate es push), así que lo
   que devuelve es ~P(gana | no empata). Para Survival (donde el empate
   cuesta vida) se corrige por P(empate) empírica, que es minúscula (~0.4%).

2. SPREAD (mercado, cobertura 1999-hoy): P(local gana) = sigmoide(b * spread).
   La pendiente b se ajusta SOLO con datos de entrenamiento (walk-forward).
   Proxy útil donde no hay moneyline (pre-2010) y chequeo de consistencia.

3. ELO (no-mercado): rating estilo FiveThirtyEight ajustado solo con
   resultados (sin cuotas). Es el proxy independiente: si el mercado no
   está disponible o para proyectar semanas FUTURAS (planeación Survival),
   donde aún no hay líneas publicadas.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor import cuotas  # noqa: E402


# ---------------------------------------------------------------- moneyline

def p_local_moneyline(ml_home, ml_away, metodo="proporcional"):
    """P(local gana | no empate) desde cuotas decimales de moneyline."""
    p = cuotas.a_probabilidades([ml_home, ml_away], metodo=metodo)
    return float(p[0])


# ------------------------------------------------------------------- spread

def ajustar_pendiente_spread(spreads, gano_local):
    """Ajusta b de P(local) = 1/(1+exp(-b*spread)) por máxima verosimilitud.

    Empates excluidos por el llamador. Newton 1-D (la log-verosimilitud es
    cóncava en b).
    """
    s = np.asarray(spreads, dtype=float)
    y = np.asarray(gano_local, dtype=float)
    b = 0.15  # arranque razonable (≈ punto por punto de spread NFL)
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-b * s))
        grad = np.sum((y - p) * s)
        hess = -np.sum(p * (1 - p) * s * s)
        paso = grad / hess
        b -= paso
        if abs(paso) < 1e-10:
            break
    return float(b)


def p_local_spread(spread, b):
    """P(local gana) desde el spread de cierre con pendiente b ya ajustada."""
    return 1.0 / (1.0 + math.exp(-b * spread))


# --------------------------------------------------------------------- Elo

# Constantes estilo FiveThirtyEight (nfelo/538 NFL Elo público):
ELO_INICIAL = 1505.0
ELO_K = 20.0
ELO_VENTAJA_LOCAL = 48.0     # puntos Elo por jugar de local
ELO_REGRESION = 1.0 / 3.0    # regresión a la media entre temporadas
ELO_MEDIA = 1505.0


class Elo:
    """Ratings Elo de los 32 equipos, actualizados partido a partido.

    Uso walk-forward: alimentar los partidos EN ORDEN CRONOLÓGICO con
    `actualizar`; pedir P(gana) con `p_local` ANTES de actualizar ese partido.
    """

    def __init__(self):
        self.r = {}
        self._temporada = None

    def _get(self, equipo):
        return self.r.get(equipo, ELO_INICIAL)

    def _nueva_temporada(self, season):
        if self._temporada is not None and season != self._temporada:
            for eq in self.r:
                self.r[eq] = (self.r[eq] * (1 - ELO_REGRESION)
                              + ELO_MEDIA * ELO_REGRESION)
        self._temporada = season

    def p_local(self, home, away, neutral=False):
        """P(local gana) según los ratings actuales (empate cuenta 1/2)."""
        ventaja = 0.0 if neutral else ELO_VENTAJA_LOCAL
        diff = self._get(home) + ventaja - self._get(away)
        return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

    def actualizar(self, partido):
        """Consume un partido jugado (dict de datos.cargar_partidos)."""
        self._nueva_temporada(partido["season"])
        home, away = partido["home"], partido["away"]
        p_esp = self.p_local(home, away)
        resultado = partido["result"]
        score = 1.0 if resultado > 0 else (0.5 if resultado == 0 else 0.0)
        # multiplicador por margen de victoria (538): amortigua blowouts
        margen = abs(resultado)
        diff_elo = self._get(home) + ELO_VENTAJA_LOCAL - self._get(away)
        if resultado != 0:
            ganador_diff = diff_elo if resultado > 0 else -diff_elo
            mult = (math.log(margen + 1.0)
                    * 2.2 / (ganador_diff * 0.001 + 2.2))
        else:
            mult = 1.0
        delta = ELO_K * mult * (score - p_esp)
        self.r[home] = self._get(home) + delta
        self.r[away] = self._get(away) - delta


# ---------------------------------------------------- corrección por empate

def p_gana_estricta(p_sin_empate, p_empate=0.004):
    """P(gana) estricta para Survival: descuenta la probabilidad de empate.

    El moneyline es a 2 salidas (empate = push): p_sin_empate ≈
    P(gana | no empate). En Survival el empate CUESTA VIDA, así que
    P(sobrevivir el pick) = p_sin_empate * (1 - p_empate).
    p_empate default = frecuencia histórica 2010-2025 (~0.4%).
    """
    return p_sin_empate * (1.0 - p_empate)
