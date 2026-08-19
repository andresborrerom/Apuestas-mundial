"""
Simulador del pool Survival EL FULBITOL sobre una temporada REAL.

Ground truth: los resultados de verdad deciden quién pierde vidas. Lo único
simulado es EL FIELD (los rivales del pool), porque sus picks no se conocen.

Reglas implementadas (del reglamento oficial):
  - 2 vidas; perder, empatar o no meter pick cuesta una vida.
  - Sin repetir equipo (queda bloqueado el resto de la temporada).
  - Semanas 1-18; gana el último vivo (pozo completo); varios vivos al final
    dividen; si todos caen la misma semana, dividen los que cayeron último.

FIELD MODEL (supuesto explícito, como el de LEMAITRE):
  Cada rival escoge cada semana entre sus equipos disponibles con
  probabilidad ∝ exp(theta * p). theta = qué tan afilado es el field:
    theta≈10  field casual (reparte picks),
    theta≈25  field normal (se amontona en los 2-3 favoritos),
    theta≈50  field afilado (casi todos al favorito máximo).
  El resultado depende de este supuesto → se reporta sensibilidad, nunca
  un solo número.
"""

import numpy as np

from nfl.SURVIVAL import estrategias as est


def resultado_pick(equipo, juegos):
    """True=sobrevive, False=pierde vida (pierde o empata). None=no jugó."""
    for j in juegos:
        if j["home"] == equipo:
            return j["result"] > 0
        if j["away"] == equipo:
            return j["result"] < 0
    return None


def trayectoria_field(semanas_ops, semanas_juegos, theta, rng):
    """Simula UN rival del pool. Devuelve semana de eliminación (None=vivo).

    semanas_ops: {week: [(equipo, rival, p)]} — opciones con p de mercado.
    semanas_juegos: {week: [juegos]} — para el ground truth.
    """
    usados, vidas = set(), 2
    for w in sorted(semanas_ops):
        libres = [(eq, p) for eq, _r, p in semanas_ops[w]
                  if eq not in usados]
        if not libres:
            vidas -= 1              # sin equipo disponible = sin pick
        else:
            ps = np.array([p for _eq, p in libres])
            pesos = np.exp(theta * (ps - ps.max()))
            eleccion = rng.choice(len(libres), p=pesos / pesos.sum())
            equipo = libres[eleccion][0]
            usados.add(equipo)
            if not resultado_pick(equipo, semanas_juegos[w]):
                vidas -= 1
        if vidas == 0:
            return w
    return None


def trayectoria_estrategia(nombre, semanas_ops, semanas_juegos,
                           calendario_full, elo_por_semana,
                           fuerza_por_semana):
    """Corre NUESTRA estrategia (determinista). Devuelve (elim_week, picks).

    elo_por_semana[w] es el Elo actualizado hasta ANTES de la semana w
    (walk-forward). calendario_full: {week: [juegos]} de toda la temporada.
    """
    fn = est.ESTRATEGIAS[nombre]
    usados, vidas, picks = set(), 2, []
    elim = None
    for w in sorted(semanas_ops):
        calendario_restante = {u: js for u, js in calendario_full.items()
                               if u >= w}
        pick = fn(semanas_ops[w], usados, semana=w,
                  calendario=calendario_restante,
                  elo=elo_por_semana[w],
                  fuerza=fuerza_por_semana.get(w))
        if pick is None:
            vidas -= 1
            picks.append((w, None, None, False))
        else:
            usados.add(pick)
            ok = resultado_pick(pick, semanas_juegos[w])
            p = next((p for eq, _r, p in semanas_ops[w] if eq == pick), None)
            picks.append((w, pick, p, bool(ok)))
            if not ok:
                vidas -= 1
        if vidas == 0 and elim is None:
            elim = w
            break
    return elim, picks


def repartir_pozo(elim_nuestra, elims_field, aporte=1.0):
    """Nuestra fracción del pozo según las reglas de cierre del reglamento.

    elims_field: array de semanas de eliminación de los rivales (None=vivo,
    representado como np.inf en el llamador; nuestra: np.inf si vivos).
    Devuelve nuestra ganancia neta en unidades de aporte (pozo = n_jug).
    """
    todos = np.append(elims_field, elim_nuestra)
    n = len(todos)
    pozo = n * aporte
    max_e = todos.max()
    if np.isinf(max_e):            # hay vivos a la semana 18: dividen ellos
        ganan = np.isinf(todos)
    else:                          # todos cayeron: dividen los últimos
        ganan = todos == max_e
    nuestra = pozo * ganan[-1] / ganan.sum()
    return nuestra - aporte
