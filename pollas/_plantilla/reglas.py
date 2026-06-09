"""
PLANTILLA de reglas de una polla. Copia este archivo a la carpeta de cada
polla (CSC, COLFONDOS, INGENIERO) y ajústalo a SUS reglas concretas.

Aquí se define todo lo que depende de las reglas de la polla:
  - la función de puntuación de cada partido,
  - los puntos de los premios de bonus (campeón, subcampeón, etc.).
El motor (carpeta `motor/`) es común a todas y no se toca.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import analizar_partido
from motor.puntuacion import regla_personalizada, mejor_apuesta_bonus


# --- 1) Reglas de puntuación de los partidos -----------------------------
# Ejemplo: 5 pts marcador exacto, 3 pts misma diferencia, 2 pts acertar quién
# gana. Cámbialos por los de TU polla.
REGLA_PARTIDO = regla_personalizada(
    pts_exacto=5,
    pts_diferencia=3,
    pts_resultado=2,
)

# --- 2) Puntos de los premios de bonus -----------------------------------
PUNTOS_CAMPEON = 20
PUNTOS_SUBCAMPEON = 10


# --- 3) Ejemplo de uso ----------------------------------------------------
if __name__ == "__main__":
    # Cuotas de ejemplo (sustituye por las de tu casa de apuestas):
    #   1X2 = [local, empate, visita] ; O/U 2.5 = [under, over]
    r = analizar_partido(
        cuotas_1x2=[1.80, 3.60, 4.50],
        cuotas_ou=[2.00, 1.80],
        regla=REGLA_PARTIDO,
    )
    print("Prob 1X2 :", {k: round(v, 3) for k, v in r["prob_1x2"].items()})
    print("Marcador más probable:", r["marcador_mas_probable"])
    print("RELLENO ÓPTIMO :", r["relleno_optimo"],
          "| pts esperados:", round(r["puntos_esperados"], 3))
    print("Alternativas   :",
          [(m, round(e, 3)) for m, e in r["ranking_relleno"][:5]])
