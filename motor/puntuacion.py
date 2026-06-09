"""
El corazón del enfoque: NO se rellena el formulario con el marcador más
probable, sino con el que MAXIMIZA LOS PUNTOS ESPERADOS según las reglas de
cada polla.

Dada la distribución de marcadores (matriz M del módulo `marcadores`) y una
función de puntuación `regla(prediccion, real) -> puntos`, calculamos para
cada predicción candidata su esperanza de puntos y nos quedamos con la mejor.

Resultado típico y contraintuitivo: cuando la polla premia el marcador exacto,
la mejor predicción suele ser 1-0 o 1-1 aunque "creas" que habrá goleada,
porque esos marcadores concentran más probabilidad que cualquier resultado
abultado.
"""

import numpy as np


# --------------------------------------------------------------------------
# Reglas de puntuación reutilizables (cada polla compone la suya)
# --------------------------------------------------------------------------

def regla_personalizada(pts_exacto=3, pts_diferencia=0, pts_resultado=1):
    """Fábrica de reglas por prioridad: exacto > diferencia de goles > resultado.

    - pts_exacto     : marcador clavado (2-1 y quedó 2-1).
    - pts_diferencia : misma diferencia de goles sin ser exacto (pones 2-0 y
                       quedó 3-1, ambos +2). Pon 0 si tu polla no lo premia.
    - pts_resultado  : acertar solo la "tendencia" 1X2 (gana/empata/pierde).

    Se otorga el tramo más alto que aplique, no se acumulan.
    """
    def regla(prediccion, real):
        ph, pa = prediccion
        rh, ra = real
        if (ph, pa) == (rh, ra):
            return pts_exacto
        if pts_diferencia and (ph - pa) == (rh - ra):
            return pts_diferencia
        if np.sign(ph - pa) == np.sign(rh - ra):
            return pts_resultado
        return 0
    return regla


def regla_solo_resultado(pts=1):
    """Solo importa quién gana o si hay empate; los goles dan igual."""
    def regla(prediccion, real):
        ph, pa = prediccion
        rh, ra = real
        return pts if np.sign(ph - pa) == np.sign(rh - ra) else 0
    return regla


# --------------------------------------------------------------------------
# Esperanza de puntos y optimización
# --------------------------------------------------------------------------

def puntos_esperados(prediccion, M, regla):
    """Esperanza de puntos de una predicción sobre la distribución M."""
    n = M.shape[0]
    total = 0.0
    for i in range(n):
        for j in range(n):
            p = M[i, j]
            if p > 0:
                total += p * regla(prediccion, (i, j))
    return float(total)


def mejor_prediccion(M, regla, max_goles=6):
    """Predicción (i, j) que maximiza los puntos esperados.

    Devuelve dict con la predicción óptima, sus puntos esperados, y el
    ranking completo de candidatos (para ver alternativas cercanas).
    """
    candidatos = [(i, j) for i in range(max_goles + 1)
                  for j in range(max_goles + 1)]
    ranking = sorted(
        ((c, puntos_esperados(c, M, regla)) for c in candidatos),
        key=lambda x: x[1], reverse=True,
    )
    mejor, ev = ranking[0]
    return {
        "prediccion": mejor,
        "puntos_esperados": ev,
        "ranking": ranking,
    }


# --------------------------------------------------------------------------
# Apuestas de bonus (campeón, subcampeón, máximo goleador, ...)
# --------------------------------------------------------------------------

def mejor_apuesta_bonus(probabilidades, puntos):
    """Elige la opción que maximiza puntos esperados en un premio de bonus.

    probabilidades : dict {opcion: probabilidad} (p. ej. de la simulación).
    puntos         : puntos que da la polla por acertar ese premio.

    OJO (teoría de juego): en pollas grandes con premio único conviene a veces
    el pick CONTRARIAN (no el favorito que todos pondrán) para diferenciarte.
    Esta función da el óptimo "en solitario"; la corrección contrarian se hace
    aparte cuando modelemos a los rivales.
    """
    ranking = sorted(
        ((op, p * puntos, p) for op, p in probabilidades.items()),
        key=lambda x: x[1], reverse=True,
    )
    op, ev, p = ranking[0]
    return {"opcion": op, "puntos_esperados": ev, "probabilidad": p,
            "ranking": ranking}
