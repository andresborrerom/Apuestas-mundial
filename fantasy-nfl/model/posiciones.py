"""La posición que MANDA es la de ESPN, no la de nflverse.

Motivo medido (28-ago-2026), sobre los 1.485 jugadores con tacleadas en 2025:

    nflverse 'LB'  -> ESPN DE   en  85 casos
    nflverse 'DE'  -> ESPN DT   en  42 casos
    nflverse 'SAF' -> ESPN S    (nflverse NO usa 'S'; el mapeo viejo buscaba
                                 'S'/'FS'/'SS' y por eso la posición S salía
                                 con n=6 en vez de ~130)

La liga reparte un slot por CADA una de DT/DE/LB/CB/S, así que clasificar mal
a un edge rusher como LB en vez de DE cambia la línea base de dos posiciones
a la vez. La fuente de autoridad es el `defaultPositionId` de ESPN, que es el
que decide en qué slot se puede alinear al jugador.

Cadena: gsis_id (nflverse) --xwalk--> espn_id --corpus ESPN--> posición.
Respaldo cuando no hay puente: traducción conservadora de la etiqueta de
nflverse, marcada como ⚠️ para poder medir cuánta cobertura viene de ahí.
"""
import json
from functools import lru_cache
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent

POS_ESPN = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 9: 'DT', 10: 'DE',
            11: 'LB', 12: 'CB', 13: 'S', 14: 'DB', 16: 'DST'}
POSID = {v: k for k, v in POS_ESPN.items()}

# Respaldo SOLO para quien no tiene puente a ESPN. Etiquetas reales vistas en
# nflverse 2010-2025.
RESPALDO = {
    'QB': 'QB', 'RB': 'RB', 'FB': 'RB', 'WR': 'WR', 'TE': 'TE', 'K': 'K',
    'DT': 'DT', 'NT': 'DT', 'DL': 'DT',
    'DE': 'DE',
    'LB': 'LB', 'OLB': 'LB', 'MLB': 'LB', 'ILB': 'LB',
    'CB': 'CB', 'DB': 'CB',
    'SAF': 'S', 'S': 'S', 'FS': 'S', 'SS': 'S',
}


@lru_cache(maxsize=1)
def _tablas(corpus='espn_applied_2025.json'):
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    xw = dict(con.execute("""select gsis_id, espn_id from xwalk_ids_nflverse
                             where espn_id is not null and gsis_id is not null""").fetchall())
    con.close()
    esp = {}
    for pw in json.load(open(RAIZ / 'data' / corpus)):
        p = pw['player']
        pos = POS_ESPN.get(p.get('defaultPositionId'))
        if pos:
            esp[int(p['id'])] = pos
    return xw, esp


def mapa_posiciones(gsis_ids=None, nflverse_pos=None):
    """{gsis_id: (pos, fuente)} donde fuente ∈ {'espn', 'respaldo'}."""
    xw, esp = _tablas()
    nflverse_pos = nflverse_pos or {}
    out = {}
    for g in (gsis_ids if gsis_ids is not None else nflverse_pos):
        e = xw.get(g)
        p = esp.get(int(e)) if e is not None else None
        if p:
            out[g] = (p, 'espn')
        else:
            r = RESPALDO.get(nflverse_pos.get(g))
            if r:
                out[g] = (r, 'respaldo')
    return out


def posiciones_desde_db(con, y0, y1):
    """Atajo: lee las posiciones nflverse de la ventana y devuelve el mapa."""
    filas = con.execute("""
        select player_id, any_value(position)
        from fact_player_week where season between ? and ? and season_type='REG'
        group by 1""", [y0, y1]).fetchall()
    return mapa_posiciones(nflverse_pos=dict(filas))
