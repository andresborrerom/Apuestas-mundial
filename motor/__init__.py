"""
Motor de probabilidades para pollas del Mundial.

Flujo general:
  1. cuotas      -> probabilidades limpias (sin margen de la casa)
  2. marcadores  -> distribución completa de marcadores (Poisson/Dixon-Coles)
  3. puntuacion  -> relleno que MAXIMIZA puntos esperados según cada polla
  4. simulacion  -> Monte Carlo del torneo para campeón/subcampeón/etc.

Atajo de alto nivel: `analizar_partido`.
"""

from . import cuotas, marcadores, puntuacion, simulacion


def analizar_partido(cuotas_1x2, regla,
                     cuotas_ou=None, linea_ou=2.5,
                     cuotas_marcador_exacto=None,
                     metodo_margen="proporcional",
                     usar_dixon_coles=True,
                     max_goles_relleno=6,
                     sesgo_goles=0.0):
    """Analiza un partido de punta a punta y devuelve el relleno óptimo.

    Parámetros
    ----------
    cuotas_1x2 : [cuota_local, cuota_empate, cuota_visita].
    regla      : función de puntuación de la polla (ver motor.puntuacion).
    cuotas_ou  : [cuota_under, cuota_over] para `linea_ou` (opcional pero
                 recomendado para clavar mejor los goles).
    cuotas_marcador_exacto : dict {(i,j): cuota}. Si lo pasas, se usa
                 directamente en vez de ajustar el modelo Poisson.
    sesgo_goles : sesgo hacia gol=1 al ELEGIR el relleno (no toca las
                 probabilidades reportadas). ~0.05 da +~0.03 pts/partido
                 validado fuera de muestra. 0 = sin sesgo.

    Devuelve un dict con probabilidades 1X2, lambdas, marcador más probable
    y, sobre todo, la predicción que maximiza los puntos esperados.
    """
    if cuotas_marcador_exacto is not None:
        M = marcadores.matriz_desde_cuotas_exactas(
            cuotas_marcador_exacto, metodo_margen=metodo_margen)
        info_modelo = {"fuente": "cuotas_marcador_exacto"}
    else:
        p_local, p_empate, p_visita = cuotas.a_probabilidades(
            cuotas_1x2, metodo=metodo_margen)
        p_over = None
        if cuotas_ou is not None:
            _, p_over = cuotas.a_probabilidades(cuotas_ou, metodo=metodo_margen)
        ajuste = marcadores.ajustar_lambdas(
            p_local, p_empate, p_visita,
            p_over=p_over, linea=linea_ou,
            usar_dixon_coles=usar_dixon_coles)
        M = ajuste["matriz"]
        info_modelo = {
            "fuente": "modelo_poisson",
            "lambda_local": ajuste["lambda_local"],
            "lambda_visita": ajuste["lambda_visita"],
            "rho": ajuste["rho"],
            "error_ajuste": ajuste["error"],
        }

    local, empate, visita = marcadores.prob_1x2(M)
    marc, p_marc = marcadores.marcador_mas_probable(M)
    # El sesgo hacia gol=1 se aplica SOLO para elegir el relleno; los puntos
    # esperados que reportamos son bajo la distribución REAL (sin sesgo).
    M_relleno = marcadores.aplicar_sesgo_goles(M, sesgo_goles)
    optimo = puntuacion.mejor_prediccion(M_relleno, regla, max_goles=max_goles_relleno)
    pred = optimo["prediccion"]
    ev_real = puntuacion.puntos_esperados(pred, M, regla)

    return {
        "prob_1x2": {"local": local, "empate": empate, "visita": visita},
        "marcador_mas_probable": {"marcador": marc, "prob": p_marc},
        "relleno_optimo": pred,
        "puntos_esperados": ev_real,
        "ranking_relleno": optimo["ranking"][:8],
        "modelo": info_modelo,
        "matriz": M,
    }


__all__ = ["cuotas", "marcadores", "puntuacion", "simulacion",
           "analizar_partido"]
