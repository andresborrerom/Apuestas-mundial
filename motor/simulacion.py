"""
Simulación Monte Carlo del torneo para los premios largos: campeón,
subcampeón, semifinalistas, etc.

Un partido suelto no basta para saber quién levanta la copa: hay que jugar el
cuadro entero miles de veces usando las probabilidades partido a partido y
contar cuántas veces gana cada equipo.

El motor es genérico: le pasas
  - los grupos (equipos por grupo),
  - una función prob_partido(a, b) -> (p_gana_a, p_empate, p_gana_b),
  - y la estructura de cruces de la fase final.
Así sirve para cualquier formato (incluido el del Mundial 2026 de 48 equipos).
"""

import numpy as np
from collections import defaultdict


def simular_grupo(equipos, prob_partido, rng):
    """Juega todos contra todos y devuelve los equipos ordenados por posición.

    Puntos: 3 victoria, 1 empate. Desempate aleatorio (aproxima diferencia de
    goles/sorteo sin sesgar). Devuelve lista ordenada de mejor a peor.
    """
    pts = defaultdict(int)
    for i in range(len(equipos)):
        for j in range(i + 1, len(equipos)):
            a, b = equipos[i], equipos[j]
            pa, pe, pb = prob_partido(a, b)
            r = rng.random()
            if r < pa:
                pts[a] += 3
            elif r < pa + pe:
                pts[a] += 1
                pts[b] += 1
            else:
                pts[b] += 3
    # desempate con ruido pequeño
    orden = sorted(equipos, key=lambda e: pts[e] + rng.random() * 0.5,
                   reverse=True)
    return orden


def jugar_eliminatoria(a, b, prob_partido, rng):
    """Devuelve el ganador de un cruce a partido único (sin empates)."""
    pa, pe, pb = prob_partido(a, b)
    # repartir el empate proporcionalmente (penaltis ~ 50/50 ajustado a fuerza)
    if pa + pb == 0:
        return a if rng.random() < 0.5 else b
    pa_final = pa + pe * pa / (pa + pb)
    return a if rng.random() < pa_final else b


def simular_torneo(grupos, prob_partido, cruces_fn, clasifican=2,
                   n=20000, semilla=None):
    """Simula el torneo `n` veces y devuelve frecuencias por fase.

    grupos     : dict {nombre_grupo: [equipos]}.
    prob_partido : función (a, b) -> (p_a, p_empate, p_b).
    cruces_fn  : función (clasificados_por_grupo, prob_partido, rng) que juega
                 la fase final y devuelve dict con claves al menos
                 "campeon" y "subcampeon" (y las que quieras: "semifinalistas",
                 "finalistas", ...). Ver `pollas/_plantilla` para un ejemplo.
    clasifican : cuántos pasan por grupo.

    Devuelve dict {fase: {equipo: probabilidad}}.
    """
    rng = np.random.default_rng(semilla)
    contador = defaultdict(lambda: defaultdict(int))

    for _ in range(n):
        clasificados = {}
        for g, equipos in grupos.items():
            orden = simular_grupo(equipos, prob_partido, rng)
            clasificados[g] = orden[:clasifican]
        resultado = cruces_fn(clasificados, prob_partido, rng)
        for fase, valor in resultado.items():
            equipos_fase = valor if isinstance(valor, (list, tuple, set)) else [valor]
            for e in equipos_fase:
                contador[fase][e] += 1

    return {
        fase: {e: c / n for e, c in sorted(d.items(), key=lambda x: -x[1])}
        for fase, d in contador.items()
    }


def prob_partido_desde_lambdas(lambdas_por_equipo, ataque_base=1.35):
    """Crea una `prob_partido` a partir de una fuerza por equipo.

    Atajo cuando NO tienes cuotas de cada cruce posible (en un torneo hay
    demasiados). Modelas cada equipo con una "fuerza" relativa y de ahí salen
    las probabilidades 1X2 vía Poisson.

    lambdas_por_equipo : dict {equipo: fuerza} donde fuerza ~ goles esperados
                         de ese equipo contra un rival medio.
    """
    from .marcadores import matriz_marcadores, prob_1x2

    def prob_partido(a, b):
        la = lambdas_por_equipo[a]
        lb = lambdas_por_equipo[b]
        # goles esperados ajustados por la fuerza del rival
        lam_a = la * (ataque_base / lb) ** 0.5
        lam_b = lb * (ataque_base / la) ** 0.5
        M = matriz_marcadores(lam_a, lam_b)
        return prob_1x2(M)

    return prob_partido
