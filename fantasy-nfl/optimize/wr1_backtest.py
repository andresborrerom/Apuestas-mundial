"""¿Puede un WR de bajo uso temprano terminar como WR1 de su equipo?

Pregunta de Andrés (17-oct): Jalen Royals (KC, 4a ronda 2025) como posible WR1
de Mahomes, dado que Rice se lesiona, Worthy nunca dio el paso y Kelce ya no es
el objetivo principal.

MÉTODO: backtest sobre 2019-2025, un corte por temporada en la semana 4.
  Features (solo con semanas 1-4): target share, air-yards share, snap% medio,
  juegos jugados, años de experiencia, ronda de draft.
  Objetivo: ¿lidera a los WR de su equipo en targets en las semanas 5-17?

CANDADO ANTI-FUGA: nada de lo que pasa después de la semana 4 entra a las
features. El objetivo se mide con semanas 5-17 solamente.

SUPUESTO: el WR1 por TARGETS es la definición. No es por puntos ni por yardas.
"""
import sys
import duckdb

B = "https://github.com/nflverse/nflverse-data/releases/download"
NK = ("regexp_replace(regexp_replace(lower({c}),'[.''`\\-]','','g'),"
      "' (jr|sr|ii|iii|iv|v)$','','g')")


def preparar(con):
    st = " union all ".join(
        f"select season,week,team,player_id,player_display_name nom,position,"
        f"coalesce(targets,0) tgt,coalesce(receiving_air_yards,0) ay,"
        f"target_share ts,air_yards_share ays "
        f"from read_parquet('{B}/stats_player/stats_player_week_{y}.parquet') "
        f"where season_type='REG'" for y in range(2019, 2026))
    sn = " union all ".join(
        f"select season,week,team,{NK.format(c='player')} nk,"
        f"coalesce(offense_pct,0) pct from "
        f"read_parquet('{B}/snap_counts/snap_counts_{y}.parquet') where game_type='REG'"
        for y in range(2019, 2026))
    con.execute(f"create table st as select *, {NK.format(c='nom')} nk from ({st})")
    con.execute(f"create table sn as select * from ({sn})")
    con.execute(f"""create table pl as select gsis_id, draft_year, draft_round, rookie_season
                    from read_parquet('{B}/players/players.parquet')""")
    # corte semana 4: features
    con.execute("""create table f as
      select s.season,s.team,s.player_id,any_value(s.nom) nom,
             count(*) filter (where s.tgt>0 or n.pct>0) jug,
             sum(s.tgt) tgt4, avg(s.ts) ts4, avg(s.ays) ays4, avg(n.pct) snap4
      from st s left join sn n on n.season=s.season and n.week=s.week and n.team=s.team and n.nk=s.nk
      where s.position='WR' and s.week between 1 and 4
      group by 1,2,3 having count(*) filter (where s.tgt>0 or n.pct>0)>=2""")
    # objetivo: targets semanas 5-17 y si lidera a los WR del equipo
    con.execute("""create table o as
      select season,team,player_id,sum(tgt) tgt_ros from st
      where position='WR' and week between 5 and 17 group by 1,2,3""")
    con.execute("""create table d as
      select f.*, coalesce(o.tgt_ros,0) tgt_ros,
             p.draft_round, (f.season - p.rookie_season) exp
      from f left join o using(season,team,player_id)
      left join pl p on p.gsis_id=f.player_id""")
    con.execute("""create table d2 as
      select *, tgt_ros = max(tgt_ros) over (partition by season,team) and tgt_ros>0 as wr1,
             rank() over (partition by season,team order by tgt4 desc) rk4
      from d""")


def tabla(con, titulo, cond):
    r = con.execute(f"select count(*), sum(case when wr1 then 1 else 0 end) from d2 where {cond}").fetchone()
    p = r[1] / r[0] if r[0] else float('nan')
    print(f"  {titulo:62}{r[0]:>5}{r[1]:>5}{p:>8.1%}")
    return r


def main():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    preparar(con)
    n = con.execute("select count(*), sum(case when wr1 then 1 else 0 end) from d2").fetchone()
    print(f"WR con ≥2 juegos en las semanas 1-4, 2019-2025: n={n[0]} · fueron WR1 ROS: {n[1]}")
    print(f"\n  {'grupo (semanas 1-4)':62}{'n':>5}{'WR1':>5}{'%':>8}")
    print("  --- por target share en las semanas 1-4 ---")
    for a, b in ((0, .06), (.06, .10), (.10, .15), (.15, .20), (.20, .25), (.25, 1)):
        tabla(con, f"target share {a:.0%}-{b:.0%}", f"ts4>={a} and ts4<{b}")
    print("  --- por posición en la jerarquía de targets del equipo (WR) ---")
    for k in (1, 2, 3, 4, 5, 6):
        tabla(con, f"{k}º WR de su equipo en targets", f"rk4={k}")
    print("  --- el perfil de Royals: poca producción, snaps variables ---")
    tabla(con, "ts4<8% (cualquier snap)", "ts4<0.08")
    tabla(con, "ts4<8% y snap medio ≥40%", "ts4<0.08 and snap4>=0.40")
    tabla(con, "ts4<8% y snap medio <40%", "ts4<0.08 and snap4<0.40")
    tabla(con, "ts4<8%, ronda ≥3 de draft, exp 0-2", "ts4<0.08 and draft_round>=3 and exp<=2")
    tabla(con, "ts4<8%, ronda ≥3, exp 1 (2º año)", "ts4<0.08 and draft_round>=3 and exp=1")
    print("\n  los que SÍ lo lograron con ts4<8%:")
    for r in con.execute("""select season,team,nom,round(ts4,3),round(snap4,2),draft_round,exp,tgt_ros
          from d2 where ts4<0.08 and wr1 order by season""").fetchall():
        print(f"     {r[0]} {r[1]:3} {r[2]:22} ts4 {r[3]:.1%} snap {r[4]:.0%} ronda {r[5]} exp {r[6]} → {r[7]:.0f} tgt ROS")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
