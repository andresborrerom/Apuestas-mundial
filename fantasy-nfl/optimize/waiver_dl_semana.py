"""Ranking semanal de DE y DT para el waiver, sin acceso a la liga.

Método (validado en idp_semanal.py / idp_modelo.py):
  - tasa propia de las últimas 17 jornadas con TU scoring (sack 3.0 DT / 2.0 DE).
  - rol actual: snaps defensivos de 2026 (juegos jugados, % medio y tendencia).
  - filtros: no estar en bye, haber jugado >=4 de los últimos 6 partidos de su
    equipo, y >=50% de snaps.
  - NO se usa el rival: se midió que no predice (r ~ 0 entre temporadas).

DISPONIBILIDAD (⚠️ SUPUESTO): sin credenciales de ESPN no puedo ver quién está
libre en la liga. Se excluyen los EXCL mejores de cada posición según el ranking
de pretemporada (proyeccion_dist.csv), asumiendo que en 16 equipos están
rostereados. Es una aproximación; el filtro real es la lista de agentes libres.
"""
import csv
import sys
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from optimize.idp_semanal import PESOS

D = RAIZ / 'data' / 'nflverse'
BYE = {'BUF', 'JAX', 'LAC', 'WAS'}
EXCL = 25
NK = ("regexp_replace(regexp_replace(lower({c}),'[.''`\\-]','','g'),"
      "' (jr|sr|ii|iii|iv|v)$','','g')")


def fp(sack):
    return (f"coalesce(def_tackles_solo,0)*{PESOS['solo']}+coalesce(def_tackle_assists,0)*{PESOS['asis']}"
            f"+coalesce(def_sacks,0)*{sack}+coalesce(def_tackles_for_loss,0)*{PESOS['tfl']}"
            f"+coalesce(def_interceptions,0)*{PESOS['int_']}+coalesce(def_pass_defended,0)*{PESOS['pd']}"
            f"+coalesce(def_fumbles_forced,0)*{PESOS['ff']}+coalesce(def_fumbles,0)*{PESOS['fr']}"
            f"+coalesce(def_tds,0)*{PESOS['td']}+coalesce(def_safeties,0)*{PESOS['saf']}")


def main():
    con = duckdb.connect()
    sem = " union all ".join(f"select * from read_parquet('{D}/semanal_{a}.parquet')" for a in (2025, 2026))
    con.execute(f"""create table g as
      select season,week,player_display_name nom,{NK.format(c='player_display_name')} nk,team,
        position pos_nv, ({fp(PESOS['sack_dt'])}) fp_dt, ({fp(PESOS['sack_otro'])}) fp_de
      from ({sem}) where season_type='REG' and position in ('DT','NT','DE','EDGE','DL')""")
    # La posición es la de ESPN (proyeccion_dist.csv), no la de nflverse: ESPN
    # lista como DT a Turner, Z. Allen, Sieler y Heyward, que nflverse llama DE,
    # y el sack vale 3.0 en DT y 2.0 en DE.
    import re
    def nk_py(x):
        x = re.sub(r"[.'`\-]", '', x.lower())
        return re.sub(r' (jr|sr|ii|iii|iv|v)$', '', x)
    espn = {}
    for r in csv.DictReader(open(D.parent / 'proyeccion_dist.csv')):
        if r['pos'] in ('DE', 'DT'):
            espn[nk_py(r['nombre'])] = (r['pos'], int(r['rank_pos']))
    con.execute("create table ep(nk varchar, pos varchar, rk integer)")
    con.executemany("insert into ep values (?,?,?)", [(k, v[0], v[1]) for k, v in espn.items()])
    con.execute("""create table g2 as select g.*,
        coalesce(ep.pos, case when g.pos_nv in ('DT','NT') then 'DT' when g.pos_nv in ('DE','EDGE') then 'DE' end) pos,
        ep.rk,
        case when coalesce(ep.pos, case when g.pos_nv in ('DT','NT') then 'DT' else 'DE' end)='DT' then fp_dt else fp_de end fp
        from g left join ep using(nk)""")
    con.execute("""create table u as select *, row_number() over (partition by nk,pos order by season desc,week desc) rn from g2 where pos is not null""")
    con.execute("""create table tasa as select nk,pos,any_value(nom) nom,any_value(team) team,any_value(rk) rk,
        avg(fp) t17, count(*) n17 from u where rn<=17 group by 1,2""")
    con.execute("""create table t26 as select nk,pos,avg(fp) t26,count(*) j26 from g2 where season=2026 and pos is not null group by 1,2""")
    con.execute(f"""create table sn as select week,team,{NK.format(c='player')} nk,
        coalesce(snaps_def,0) s, coalesce(pct_def,0) p
        from read_parquet('{D}/snaps_2026.parquet')""")
    con.execute("""create table rol as select nk, team,
        count(*) filter (where s>0) jug,
        avg(p) filter (where s>0) pct,
        avg(p) filter (where s>0 and week>=4) pct_rec,
        avg(p) filter (where s>0 and week<4) pct_ini
        from sn group by 1,2""")
    for pos in ('DT', 'DE'):
        rows = con.execute(f"""select t.nom,t.team,t.t17,t.n17,x.t26,x.j26,r.jug,r.pct,r.pct_rec,r.pct_ini,t.rk
          from tasa t left join t26 x using(nk,pos) join rol r on r.nk=t.nk and r.team=t.team
          where t.pos='{pos}' and t.n17>=8 and r.jug>=4 and r.pct>=0.50""").fetchall()
        out = []
        for nom, eq, t17, n17, t26, j26, jug, pct, rec, ini, rk in rows:
            if eq in BYE:
                continue
            if rk is not None and rk <= EXCL:
                continue
            out.append((t17, nom, eq, n17, t26, j26, jug, pct, rec, ini, rk))
        out.sort(reverse=True)
        print(f"\n=== {pos}: candidatos (excluidos los {EXCL} mejores de pretemporada, byes y <50% snaps) ===")
        print(f"{'jugador':22}{'eq':4}{'tasa17':>7}{'n':>4}{'tasa26':>7}{'j26':>4}{'snaps%':>8}{'rec(4-6)':>9}{'ini(1-3)':>9}{'pre':>5}")
        for t17, nom, eq, n17, t26, j26, jug, pct, rec, ini, rk in out[:12]:
            f = lambda x: '   -' if x is None else f"{x:.0%}".rjust(4)
            print(f"{nom[:21]:22}{eq:4}{t17:>7.2f}{n17:>4}{(t26 or 0):>7.2f}{(j26 or 0):>4}{pct:>8.0%}{f(rec):>9}{f(ini):>9}{str(rk or '-'):>5}")


if __name__ == '__main__':
    main()
