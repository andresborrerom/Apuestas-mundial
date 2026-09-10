"""RANKING POR PUNTOS DE TEMPORADA — con roles compartidos (10-sep).

Pedido de Andrés tras el draft: "Cousins va de titular el primer partido...
Jacobs está bajo por su problema legal, pero tengo a Lloyd por eso.
Recalcula el ranking de lo que será puntos totales del season".

EL PUNTO QUE CAMBIA EL MODELO: si un equipo tiene las DOS mitades de un rol
mutuamente excluyente (titular + su suplente directo), cada semana alinea al
que juegue. No captura dos proyecciones recortadas, captura el ROL COMPLETO.
`valor_roster` no lo veía: mete a uno en el slot y el otro queda en banca.

Pares detectados (mismo equipo NFL + misma posición dentro de un roster):
  - QB+QB del mismo equipo NFL: SIEMPRE mutuamente excluyentes.
  - RB+RB: solo si el segundo es claramente suplente (pg < 60% del titular).
    Si es un comité (ambos juegan), NO se fusionan — se pueden alinear los dos.
  - WR+WR: nunca se fusionan (juegan a la vez).
En el draft 2026 solo hay 4 pares en toda la liga y los 2 excluyentes son
nuestros: Jacobs+Lloyd (GB RB) y Mendoza+Cousins (LV QB).

TRES ESCENARIOS (⚠️ el resultado depende de cuál se crea — se reportan los tres):
  crudo        = sin fusionar. Es el suelo: asume que el suplente no aporta nada.
  conservador  = titular + (semanas que se pierde) × pg BLENDED del suplente.
                 Pesimista: el pg del suplente incluye semanas de banca.
  central      = min(suma de los dos, pg del titular × 17). El tope impide
                 que el par valga más que un titular a tiempo completo.

⚠️ SUPUESTOS DECLARADOS
  - "Puntos de temporada" = suma de las proyecciones de los 14 titulares.
    Ignora byes (donde se sube un suplente y se gana un poco) y la varianza
    semanal. Es la misma aproximación que usa todo el tablero.
  - Las proyecciones de ESPN ya descuentan ausencias esperadas (Jacobs
    eg 13.5 de 17 por el tema legal; Cousins pg 4.0 = tarifa de suplente).
  - Andrés reporta a Cousins como titular anunciado de la semana 1. Si de
    verdad juega a tarifa de titular, el rol QB de LV se acerca a su tope
    (pg de Mendoza × 17) y el par sube por encima del escenario central;
    el script imprime esa sensibilidad aparte.

    python optimize/ranking_temporada.py
"""
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

SEMANAS = 17
UMBRAL_COMITE = 0.60      # pg del 2º / pg del 1º por encima de esto = comité
EQ = {1: 'ATL', 2: 'BUF', 3: 'CHI', 4: 'CIN', 5: 'CLE', 6: 'DAL', 7: 'DEN',
      8: 'DET', 9: 'GB', 10: 'TEN', 11: 'IND', 12: 'KC', 13: 'LV', 14: 'LAR',
      15: 'MIA', 16: 'MIN', 17: 'NE', 18: 'NO', 19: 'NYG', 20: 'NYJ',
      21: 'PHI', 22: 'ARI', 23: 'PIT', 24: 'LAC', 25: 'SF', 26: 'SEA',
      27: 'TB', 28: 'WAS', 29: 'CAR', 30: 'JAX', 33: 'BAL', 34: 'HOU'}
# roster 2026: 14 titulares (los dedicados + OP + 1 flex RB/WR)
SLOTS = [('QB', 1), ('RB', 1), ('WR', 2), ('TE', 1), ('DT', 1), ('DE', 1),
         ('LB', 1), ('CB', 1), ('S', 1), ('DST', 1), ('K', 1)]


def cargar():
    todos = json.load(gzip.open(RAIZ / 'data' / 'espn_applied_2025.json.gz', 'rt'))
    nfl = {p['player']['id']: EQ.get(p['player'].get('proTeamId'), '?')
           for p in todos}
    proy = {int(x['espn_id']): x for x in
            csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv'))}
    rosters = defaultdict(list)
    equipos = {}
    for r in csv.DictReader(open(RAIZ / 'data' / 'rosters_2026_postdraft.csv')):
        equipos[r['team_id']] = r['equipo']
        pid = int(r['espn_id'])
        x = proy.get(pid)
        if not x:
            continue                      # p.ej. jugadores en IR sin proyección
        rosters[r['team_id']].append(dict(
            id=pid, nombre=r['jugador'], pos=r['pos'], nfl=nfl.get(pid, '?'),
            proj=float(x['total_v2']), pg=float(x['pg']), eg=float(x['eg'])))
    return rosters, equipos


def alinear(jugadores):
    """Suma de temporada de la mejor alineación de 14 titulares."""
    pp = defaultdict(list)
    for j in jugadores:
        pp[j['pos']].append(j)
    for v in pp.values():
        v.sort(key=lambda j: -j['proj'])
    tot, usados = 0.0, set()
    for p, k in SLOTS:
        for j in pp.get(p, [])[:k]:
            tot += j['proj']
            usados.add(j['id'])

    def libres(poss):
        return sorted((j for p in poss for j in pp.get(p, [])
                       if j['id'] not in usados), key=lambda j: -j['proj'])
    for j in libres(('QB', 'RB', 'WR', 'TE'))[:1]:      # OP (superflex)
        tot += j['proj']
        usados.add(j['id'])
    for j in libres(('RB', 'WR'))[:1]:                  # flex RB/WR
        tot += j['proj']
        usados.add(j['id'])
    return tot


def fusionar(jugadores, modo):
    """Une los pares mutuamente excluyentes en un solo activo."""
    if modo == 'crudo':
        return list(jugadores), []
    grupos = defaultdict(list)
    for j in jugadores:
        grupos[(j['nfl'], j['pos'])].append(j)
    out, fusiones = list(jugadores), []
    for (_, pos), l in grupos.items():
        if len(l) != 2 or pos not in ('QB', 'RB'):
            continue                       # WR/TE del mismo equipo juegan a la vez
        l.sort(key=lambda j: -j['pg'])
        titular, suplente = l
        if pos == 'RB' and suplente['pg'] >= UMBRAL_COMITE * titular['pg']:
            continue                       # comité: los dos son alineables
        if modo == 'conservador':
            nuevo = titular['proj'] + max(0.0, SEMANAS - titular['eg']) * suplente['pg']
        else:                              # central: suma con tope del rol
            nuevo = min(titular['proj'] + suplente['proj'], titular['pg'] * SEMANAS)
        fusiones.append((titular['nombre'], suplente['nombre'],
                         titular['proj'], nuevo, titular['pg'] * SEMANAS))
        titular['proj'] = nuevo
        out = [j for j in out if j['id'] != suplente['id']]
    return out, fusiones


def main():
    rosters, equipos = cargar()
    for modo in ('crudo', 'conservador', 'central'):
        tabla, detalle = [], {}
        for t, jug in rosters.items():
            fus_j, fus = fusionar([dict(j) for j in jug], modo)
            tabla.append((alinear(fus_j), t))
            detalle[t] = fus
        tabla.sort(reverse=True)
        print(f"\n=== {modo.upper()} · puntos de temporada de los 14 titulares ===")
        for i, (v, t) in enumerate(tabla, 1):
            print(f"  {i:>2}. {equipos[t][:28]:28}{v:>8.0f}")
        for a, b, antes, desp, tope in detalle.get('10', []):
            print(f"     fusión {a} + {b}: {antes:.0f} → {desp:.0f} "
                  f"(tope del rol {tope:.0f})")
    print("\n⚠️ Sensibilidad: si Cousins juega a tarifa de TITULAR (no la de "
          "suplente que asume ESPN), el rol QB de LV tiende a su tope y el par "
          "sube por encima del escenario central.")


if __name__ == '__main__':
    main()
