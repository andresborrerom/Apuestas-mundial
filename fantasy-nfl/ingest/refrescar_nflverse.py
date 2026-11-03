"""Refresca los parquet de nflverse de la temporada en curso.

Tres veces en dos semanas di analisis con datos congelados en una jornada
vieja mientras los de ESPN estaban al dia: los snaps de IDP se quedaron en la
semana 1 diez dias, y los ofensivos en la 2. El dato viejo no se ve roto -- se
ve normal -- y por eso hay que refrescarlo por rutina, no por acordarse.

    python ingest/refrescar_nflverse.py [año]
"""
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
D = RAIZ / 'data' / 'nflverse'
BASE = "https://github.com/nflverse/nflverse-data/releases/download"

FUENTES = {
    'semanal_{a}.parquet': (f"{BASE}/stats_player/stats_player_week_{{a}}.parquet", """
        select season,week,season_type,player_id,player_display_name,position,team,opponent_team,
          def_tackles_solo,def_tackle_assists,def_sacks,def_tackles_for_loss,def_qb_hits,
          def_interceptions,def_pass_defended,def_fumbles_forced,def_fumbles,def_tds,
          def_safeties,def_fg_blocks,def_punt_blocks,def_pat_blocks
        from read_parquet('{u}') where season_type='REG'"""),
    'of_{a}.parquet': (f"{BASE}/stats_player/stats_player_week_{{a}}.parquet", """
        select season,week,player_display_name nombre,position pos,team,
          coalesce(carries,0) car, coalesce(rushing_yards,0) yc, coalesce(rushing_tds,0) tdc,
          coalesce(targets,0) tgt, coalesce(receptions,0) rec, coalesce(receiving_yards,0) yr,
          coalesce(receiving_tds,0) tdr, coalesce(passing_yards,0) yp, coalesce(passing_tds,0) tdp,
          coalesce(fantasy_points_ppr,0) ppr
        from read_parquet('{u}') where season_type='REG'"""),
    'snaps_{a}.parquet': (f"{BASE}/snap_counts/snap_counts_{{a}}.parquet", """
        select season,week,player,pfr_player_id,position,team,opponent,
          coalesce(defense_snaps,0) snaps_def, coalesce(defense_pct,0) pct_def
        from read_parquet('{u}') where game_type='REG'"""),
    'snaps_of_{a}.parquet': (f"{BASE}/snap_counts/snap_counts_{{a}}.parquet", """
        select season,week,player,position,team,
          coalesce(offense_snaps,0) snaps_of, coalesce(offense_pct,0) pct_of
        from read_parquet('{u}') where game_type='REG'"""),
    'equipo_{a}.parquet': (f"{BASE}/stats_team/stats_team_week_{{a}}.parquet", """
        select season,week,team,opponent_team,
          coalesce(attempts,0) pases, coalesce(carries,0) carreras,
          coalesce(sacks_suffered,0) sacks_perm, coalesce(sack_yards_lost,0) yds_sack,
          coalesce(passing_epa,0) epa_pase, coalesce(rushing_epa,0) epa_carrera,
          coalesce(passing_yards,0)+coalesce(rushing_yards,0) yardas
        from read_parquet('{u}') where season_type='REG'"""),
}


def main():
    anio = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    print(f"refrescando nflverse {anio} →")
    for plantilla, (url_t, sql) in FUENTES.items():
        dst = D / plantilla.format(a=anio)
        antes = None
        if dst.exists():
            antes = con.execute("select max(week) from read_parquet(?)", [str(dst)]).fetchone()[0]
            dst.unlink()
        url = url_t.format(a=anio)
        try:
            con.execute(f"COPY ({sql.format(u=url)}) TO '{dst}' (FORMAT PARQUET)")
            ahora = con.execute("select max(week) from read_parquet(?)", [str(dst)]).fetchone()[0]
            flecha = '→' if antes != ahora else '='
            print(f"  {dst.name:26} semana {antes} {flecha} {ahora}")
        except Exception as e:
            print(f"  🚨 {dst.name}: {str(e)[:90]}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
