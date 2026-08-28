"""Puntúa datos de nflverse con NUESTRO reglamento — la pieza que faltaba
para poder hacer backtest con resultados REALES de temporadas pasadas.

Mapeo statId↔nflverse determinado EMPÍRICAMENTE (no de memoria), cotejando
los crudos de ESPN contra nflverse jugador por jugador. Hallazgo clave:

    ESPN trunca las yardas POR PARTIDO, no por temporada:
      statId  8 = Σ_juegos floor(yardas_pase / 25)
      statId 28 = Σ_juegos floor(yardas_tierra / 10)
      statId 48 = Σ_juegos floor(yardas_aire / 10)
    (verificado exacto en 9/9 casos: Stafford 180, Gibbs 114, Nacua 165...)
    Un partido de 24 yardas paga CERO. No es equivalente a dividir el total.

Alcance: ofensiva (QB/RB/WR/TE) e IDP. K y D/ST quedan fuera del backtest
(su valuación no cambia ninguna decisión de draft y su mapeo es más frágil).

⚠️ DISCREPANCIA DE FUENTE DECLARADA: ESPN y nflverse usan proveedores
distintos de TACLEADAS. Ej. Schwesinger 2025: ESPN 67 solos / nflverse 58
(9 de diferencia = 22.5 pts con nuestras reglas). No es un bug del mapeo:
son dos mediciones del mismo hecho. Para el backtest se usa nflverse de
forma CONSISTENTE (todas las políticas se miden con la misma vara), pero
los totales IDP no son comparables uno a uno contra ESPN.
"""
import math
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent

SQL_SEMANAL = """
select player_id, player_display_name nombre, position pos, season, week,
       coalesce(completions,0) comp, coalesce(attempts,0) att,
       coalesce(passing_yards,0) py, coalesce(passing_tds,0) ptd,
       coalesce(passing_interceptions,0) pint, coalesce(sacks_suffered,0) sk,
       coalesce(passing_first_downs,0) p1d, coalesce(passing_2pt_conversions,0) p2,
       coalesce(carries,0) car, coalesce(rushing_yards,0) ry,
       coalesce(rushing_tds,0) rtd, coalesce(rushing_first_downs,0) r1d,
       coalesce(rushing_2pt_conversions,0) r2,
       coalesce(receptions,0) rec, coalesce(receiving_yards,0) recy,
       coalesce(receiving_tds,0) rectd, coalesce(receiving_first_downs,0) rec1d,
       coalesce(receiving_2pt_conversions,0) rec2,
       coalesce(sack_fumbles_lost,0)+coalesce(rushing_fumbles_lost,0)
         +coalesce(receiving_fumbles_lost,0) fl,
       coalesce(def_tackles_solo,0) solo, coalesce(def_tackle_assists,0) asis,
       coalesce(def_sacks,0) dsk, coalesce(def_interceptions,0) dint,
       coalesce(def_pass_defended,0) pd, coalesce(def_fumbles_forced,0) ff,
       coalesce(def_tds,0) dtd, coalesce(fumble_recovery_opp,0) fr,
       coalesce(special_teams_tds,0) sttd
from fact_player_week
where season_type='REG' and season between ? and ?
"""


def crudos_temporada(con, y0, y1):
    """{(player_id, season): dict statId->valor} con la semántica de ESPN."""
    filas = con.execute(SQL_SEMANAL, [y0, y1]).fetchall()
    cols = [d[0] for d in con.description]
    ix = {c: i for i, c in enumerate(cols)}
    acc = {}
    meta = {}
    for f in filas:
        k = (f[ix['player_id']], f[ix['season']])
        d = acc.setdefault(k, {})
        meta[k] = (f[ix['nombre']], f[ix['pos']])
        g = lambda c: f[ix[c]] or 0
        add = lambda sid, v: d.__setitem__(sid, d.get(sid, 0) + v)
        # --- pase
        add(1, g('comp')); add(2, g('att') - g('comp')); add(4, g('ptd'))
        add(8, math.floor(g('py') / 25)); add(20, g('pint')); add(64, g('sk'))
        add(211, g('p1d')); add(19, g('p2'))
        if 300 <= g('py') < 400: add(17, 1)
        elif g('py') >= 400: add(18, 1)
        # --- tierra
        add(25, g('rtd')); add(28, math.floor(g('ry') / 10)); add(212, g('r1d'))
        add(26, g('r2'))
        if 100 <= g('ry') < 200: add(37, 1)
        elif g('ry') >= 200: add(38, 1)
        # --- aire
        add(43, g('rectd')); add(48, math.floor(g('recy') / 10))
        add(53, g('rec')); add(213, g('rec1d')); add(44, g('rec2'))
        if 100 <= g('recy') < 200: add(56, 1)
        elif g('recy') >= 200: add(57, 1)
        # --- pérdidas
        add(72, g('fl'))
        # --- IDP
        add(108, g('solo')); add(107, g('asis')); add(109, g('solo') + g('asis'))
        add(99, g('dsk')); add(95, g('dint')); add(113, g('pd')); add(106, g('ff'))
        add(96, g('fr'))
        # statId 105 = TD defensivo O DE RETORNO (6 pts salvo D/ST). Sin los
        # de retorno faltaban 12-18 pts en returners (Shaheed, Dike, Washington).
        add(105, g('dtd') + g('sttd'))
        add(210, 1)                       # juegos
    return acc, meta


def bonos_td_distancia(con, y0, y1):
    """statIds 15/16 (pase), 35/36 (tierra), 45/46 (aire) desde play-by-play.
    Los bonos APILAN: un TD de 50+ dispara también el de 40+."""
    filas = con.execute("""
        select td_player_id, season, play_type, yards_gained, passer_player_id
        from fact_td_plays where season between ? and ?
    """, [y0, y1]).fetchall()
    out = {}
    for pid, season, tipo, yds, passer in filas:
        if yds is None:
            continue
        # receptor/corredor
        if pid:
            d = out.setdefault((pid, season), {})
            a, b = (45, 46) if tipo == 'pass' else (35, 36)
            if yds >= 40: d[a] = d.get(a, 0) + 1
            if yds >= 50: d[b] = d.get(b, 0) + 1
        if tipo == 'pass' and passer:
            d = out.setdefault((passer, season), {})
            if yds >= 40: d[15] = d.get(15, 0) + 1
            if yds >= 50: d[16] = d.get(16, 0) + 1
    return out


POSID = {'QB': 1, 'RB': 2, 'WR': 3, 'TE': 4, 'DT': 9, 'DE': 10, 'LB': 11,
         'CB': 12, 'S': 13, 'FS': 13, 'SS': 13, 'DB': 14, 'K': 5}


def temporadas(y0=2011, y1=2025, db=None):
    """Devuelve {(player_id, season): (nombre, pos, dict_statIds)}."""
    con = duckdb.connect(str(db or RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    acc, meta = crudos_temporada(con, y0, y1)
    tdb = bonos_td_distancia(con, y0, y1)
    for k, extra in tdb.items():
        if k in acc:
            for sid, v in extra.items():
                acc[k][sid] = acc[k].get(sid, 0) + v
    return {k: (meta[k][0], meta[k][1], v) for k, v in acc.items()}
