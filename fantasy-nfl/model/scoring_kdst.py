"""Kicker y D/ST desde nflverse, con la semántica exacta de los statIds de ESPN.

Los statIds NO se tomaron de memoria: se derivaron del corpus real de 2025
reconstruyendo dos totales al decimal.

  Aubrey 2025 = 235.2  →  74(11×5) + 76(6×−1) + 77(10×4) + 80(15×3)
                          + 86(47×1) + 88(1×−1) + 198(8×5) + 200(5×−1)
                          + 201(3×6) + 203(1×−0.5) + 108(1×1.5) + 109(1×1)
                          + 212(1×0.2) = 235.2 ✅
  Texans D/ST 2025 = 211.0 → 89(1×20) + 91(3×4) + 92(5×2) + 121(5×1)
                          + 95(19×3) + 96(10×3) + 97(3×2) + 99(47×1)
                          + 103(1×6) + 104(3×6) = 211.0 ✅

De ahí sale la semántica:
  KICKER   74 FG anotado 50+ (TODOS los de 50+, por eso APILA con 198/201)
           76 fallado 50+ · 77 anotado 40-49 · 79 fallado 40-49
           80 anotado 0-39 · 82 fallado 0-39 · 86 PAT anotado · 88 PAT fallado
           198 anotado 50-59 · 200 fallado 50-59 · 201 anotado 60+ · 203 fallado 60+
           ⇒ un FG de 50-59 paga 74+198 = 10 pts; uno de 60+ paga 74+201 = 11.
  D/ST     escalones de PUNTOS PERMITIDOS, uno por partido y excluyentes:
           89 = 0 · 90 = 1-6 · 91 = 7-13 · 92 = 14-17 · 121 = 18-21
           122 = 22-27 · 123 = 28-34 · 124 = 35-45 · 125 = 46+
           (Texans: 1+0+3+5+5+1+2 = 17 partidos ✅)
           95 INT · 96 balón recuperado · 97 patada bloqueada · 98 safety
           99 captura · 103 TD de balón suelto · 104 TD de intercepción
           105 (TD defensivo del JUGADOR) está en 0 para la D/ST: no se paga
           dos veces.

⚠️ LIMITACIONES DECLARADAS (medidas, no supuestas — ver validar_kdst.py):
  - Patadas bloqueadas (97) no existen en fact_player_week: se omiten.
  - El bono de <100 yardas permitidas (128) es rarísimo y se omite.
  - Los TD de retorno de patada/despeje de la D/ST (101/102) se omiten por la
    misma razón: nflverse los asigna al jugador y nuestra liga también.
"""
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------- KICKER
SQL_K = """
select player_id, player_display_name nombre, season, week, team,
       coalesce(fg_made_0_19,0)+coalesce(fg_made_20_29,0)+coalesce(fg_made_30_39,0) m039,
       coalesce(fg_missed_0_19,0)+coalesce(fg_missed_20_29,0)+coalesce(fg_missed_30_39,0) x039,
       coalesce(fg_made_40_49,0) m4049, coalesce(fg_missed_40_49,0) x4049,
       coalesce(fg_made_50_59,0) m5059, coalesce(fg_missed_50_59,0) x5059,
       coalesce(fg_made_60_,0) m60,    coalesce(fg_missed_60_,0) x60,
       coalesce(pat_made,0) pm, coalesce(pat_missed,0) px,
       coalesce(def_tackles_solo,0) solo, coalesce(def_tackle_assists,0) asis,
       coalesce(fg_blocked,0) blk, coalesce(fg_blocked_distance,0) blkd
from fact_player_week
where season_type='REG' and season between ? and ?
  and (coalesce(fg_att,0) > 0 or coalesce(pat_att,0) > 0)
"""


def kicker_semanas(con, y0, y1):
    """{(player_id, season, week): {statId: valor}} para pateadores."""
    out, meta = {}, {}
    for (pid, nom, ss, wk, team, m039, x039, m4049, x4049,
         m5059, x5059, m60, x60, pm, px,
         solo, asis, blk, blkd) in con.execute(SQL_K, [y0, y1]).fetchall():
        # 🔴 ESPN cuenta el FG BLOQUEADO como fallado. nflverse lo lleva en una
        # columna aparte; sin sumarlo quedábamos POR ENCIMA de ESPN. La
        # distancia viene sumada (2 bloqueos -> 92), así que se usa el promedio.
        if blk:
            dist = (blkd / blk) if blkd else 35
            if dist < 40: x039 += blk
            elif dist < 50: x4049 += blk
            elif dist < 60: x5059 += blk
            else: x60 += blk
        d = {}
        if m039: d[80] = m039
        if x039: d[82] = x039
        if m4049: d[77] = m4049
        if x4049: d[79] = x4049
        if m5059: d[198] = m5059
        if x5059: d[200] = x5059
        if m60: d[201] = m60
        if x60: d[203] = x60
        # 74/76 = TODOS los de 50+ (por eso los tramos APILAN)
        if m5059 + m60: d[74] = m5059 + m60
        if x5059 + x60: d[76] = x5059 + x60
        if pm: d[86] = pm
        if px: d[88] = px
        # 🔴 El pateador COBRA TACLEADAS en esta liga. Sin esto el candado daba
        # −9.0 exacto en Patterson (3 solos + 1 asistida = 4.5+4.0+0.5) y un
        # sesgo negativo sistemático en TODOS los pateadores.
        if solo: d[108] = solo
        if asis: d[107] = asis
        if solo + asis: d[109] = solo + asis
        d[210] = 1
        out[(pid, ss, wk)] = d
        meta[(pid, ss, wk)] = (nom, 'K', team)
    return out, meta


# ----------------------------------------------------------------------- D/ST
# Escalón de puntos permitidos: (límite superior inclusive, statId)
ESCALONES_PA = [(0, 89), (6, 90), (13, 91), (17, 92), (21, 121),
                (27, 122), (34, 123), (45, 124), (10 ** 9, 125)]


def escalon_pa(pa):
    for lim, sid in ESCALONES_PA:
        if pa <= lim:
            return sid
    return 125


SQL_DEF_TEAM = """
select team, season, week,
       sum(coalesce(def_sacks,0))            sk,
       sum(coalesce(def_interceptions,0))    it,
       sum(coalesce(fumble_recovery_opp,0))  fr,
       sum(coalesce(def_safeties,0))         sf,
       sum(coalesce(def_tds,0))              td,
       sum(coalesce(special_teams_tds,0))    sttd
from fact_player_week
where season_type='REG' and season between ? and ?
group by 1,2,3
"""

SQL_MARCADOR = """
select season, week, home_team eq, away_score pa from dim_game
where game_type='REG' and season between ? and ?
union all
select season, week, away_team eq, home_score pa from dim_game
where game_type='REG' and season between ? and ?
"""


def dst_semanas(con, y0, y1):
    """{(equipo, season, week): {statId: valor}} para las D/ST.

    Dos correcciones que salieron del candado contra ESPN:
    1. La D/ST cobra TAMBIÉN los TD de retorno de patada y despeje (101/102).
       Nuestra liga se los paga además al jugador (statId 105) — no es doble
       conteo: son dos casillas distintas del roster.
    2. Los PUNTOS PERMITIDOS de ESPN excluyen lo que anotó la defensa/equipos
       especiales del RIVAL: a esa defensa no se le puede culpar de un TD que
       le hicieron a su propia ofensiva. Sin esta corrección, tres de cuatro
       equipos auditados quedaban un escalón por debajo.
    """
    pa = {(ss, wk, eq): p for ss, wk, eq, p
          in con.execute(SQL_MARCADOR, [y0, y1, y0, y1]).fetchall() if p is not None}
    rival = {(ss, wk, eq): op for ss, wk, eq, op
             in con.execute("""
        select season, week, home_team, away_team from dim_game
        where game_type='REG' and season between ? and ?
        union all
        select season, week, away_team, home_team from dim_game
        where game_type='REG' and season between ? and ?
    """, [y0, y1, y0, y1]).fetchall()}
    filas = con.execute(SQL_DEF_TEAM, [y0, y1]).fetchall()
    # TD no ofensivos de cada equipo-semana (para descontárselos al rival)
    no_ofe = {(eq, ss, wk): (td or 0) + (sttd or 0)
              for eq, ss, wk, sk, it, fr, sf, td, sttd in filas}
    out, meta = {}, {}
    for eq, ss, wk, sk, it, fr, sf, td, sttd in filas:
        d = {}
        if sk: d[99] = sk
        if it: d[95] = it
        if fr: d[96] = fr
        if sf: d[98] = sf
        # 101/102/103/104 pagan 6 cada uno para la D/ST: se agrupan en 104
        if (td or 0) + (sttd or 0): d[104] = (td or 0) + (sttd or 0)
        p = pa.get((ss, wk, eq))
        if p is not None:
            op = rival.get((ss, wk, eq))
            ajuste = 7 * no_ofe.get((op, ss, wk), 0) if op else 0
            e = escalon_pa(max(0, p - ajuste))
            d[e] = d.get(e, 0) + 1
        d[210] = 1
        out[(eq, ss, wk)] = d
        meta[(eq, ss, wk)] = (f'{eq} D/ST', 'DST', eq)
    return out, meta
