"""
Reglas de "La Super Polla de los Pollos 2026" (CSC).

Puntaje por partido = SUMA de:
  1) acertar ganador/empate (tendencia 1X2),
  2) acertar los goles del equipo local (exactos),
  3) acertar los goles del equipo visitante (exactos).

Los goles premian a CADA equipo por separado y entre más goles aciertas, más
puntos. Además los puntos suben por ronda. Detalle en el reglamento (PDF de
esta carpeta), tabla de la diapositiva "LOS PUNTOS AUMENTAN POR RONDA".

CSC NO pide campeón ni goleador: solo marcadores, ronda por ronda.

Ojo eliminatorias: cuenta el resultado tras los 120 min (penales no) y se
puede apostar al empate. Para esas rondas, lo ideal es alimentar el modelo
con cuotas del resultado "tras alargue"/"to advance" si la casa las da; si no,
las cuotas 1X2 de tiempo reglamentario son una buena aproximación.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import analizar_partido
from motor.puntuacion import regla_goles_por_equipo


# Parámetros por ronda: (ganador/empate, goles=0 acertado, base goles!=0).
# El "goles!=0" otorga (# de goles + base).
RONDAS = {
    "primera":       (1, 2, 3),
    "dieciseisavos": (2, 3, 5),
    "octavos":       (3, 4, 7),
    "cuartos":       (4, 6, 10),
    "semis":         (5, 8, 12),
    "tercer_puesto": (6, 10, 14),
    "final":         (8, 12, 16),
}


def regla_de_ronda(ronda):
    """Devuelve la función de puntuación de CSC para la ronda dada."""
    if ronda not in RONDAS:
        raise ValueError(f"Ronda desconocida: {ronda}. Use una de {list(RONDAS)}")
    pts_res, pts_cero, base = RONDAS[ronda]
    return regla_goles_por_equipo(pts_res, pts_cero, base)


def rellenar(ronda, cuotas_1x2, cuotas_ou=None, linea_ou=2.5,
             cuotas_marcador_exacto=None, metodo_margen="proporcional",
             sesgo_goles=0.0):
    """Calcula el relleno óptimo de un partido para CSC en una ronda.

    sesgo_goles: sesgo hacia gol=1 validado en backtest (~0.05 recomendado).

    Devuelve el dict de `analizar_partido` (incluye relleno_optimo,
    puntos_esperados, prob_1x2, ranking, etc.).
    """
    return analizar_partido(
        cuotas_1x2=cuotas_1x2,
        regla=regla_de_ronda(ronda),
        cuotas_ou=cuotas_ou,
        linea_ou=linea_ou,
        cuotas_marcador_exacto=cuotas_marcador_exacto,
        metodo_margen=metodo_margen,
        max_goles_relleno=7,
        sesgo_goles=sesgo_goles,
    )


if __name__ == "__main__":
    # Ejemplo: un favorito claro en fase de grupos.
    # Cambia las cuotas por las reales de tu casa (1X2 = local, empate, visita).
    print("=== Fase de grupos: favorito local ===")
    r = rellenar("primera", cuotas_1x2=[1.50, 4.20, 6.50], cuotas_ou=[2.10, 1.75])
    print("Prob 1X2 :", {k: round(v, 3) for k, v in r["prob_1x2"].items()})
    print("Goles esperados:",
          round(r["modelo"].get("lambda_local", 0), 2), "-",
          round(r["modelo"].get("lambda_visita", 0), 2))
    print("Marcador más probable:", r["marcador_mas_probable"])
    print("RELLENO ÓPTIMO :", r["relleno_optimo"],
          "| pts esperados:", round(r["puntos_esperados"], 3))
    print("Alternativas   :",
          [(m, round(e, 2)) for m, e in r["ranking_relleno"][:6]])

    print("\n=== Misma probabilidad, pero en la FINAL ===")
    r2 = rellenar("final", cuotas_1x2=[1.50, 4.20, 6.50], cuotas_ou=[2.10, 1.75])
    print("RELLENO ÓPTIMO :", r2["relleno_optimo"],
          "| pts esperados:", round(r2["puntos_esperados"], 3))
    print("Alternativas   :",
          [(m, round(e, 2)) for m, e in r2["ranking_relleno"][:6]])
