"""Qué ofensiva concede más puntos de fantasy a los DE y a los DT (tu scoring).

Pedido de Andrés (20-oct). Se suman los puntos de TODOS los DE (y por separado
de los DT) de la defensa rival en cada partido y se promedia por partido de la
ofensiva que los enfrenta.

PESOS: los de idp_semanal.PESOS. solo=1.0 y asistida=0.5 están VALIDADOS contra
los scoringItems de ESPN; el sack es 3.0 para DT y 2.0 para DE (override por
slot, validado); el resto sale de un ajuste con R²=0.978 contra el appliedTotal.
POSICIÓN: la etiqueta de nflverse. DL genérico (16 filas) queda fuera y NT va
con DT. Un jugador que ESPN lista como DE y nflverse como DT cae del otro lado.
"""
import sys
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from optimize.idp_semanal import PESOS

D = RAIZ / 'data' / 'nflverse'
FP = lambda sack: (f"coalesce(def_tackles_solo,0)*{PESOS['solo']}+coalesce(def_tackle_assists,0)*{PESOS['asis']}"
    f"+coalesce(def_sacks,0)*{sack}+coalesce(def_tackles_for_loss,0)*{PESOS['tfl']}"
    f"+coalesce(def_interceptions,0)*{PESOS['int_']}+coalesce(def_pass_defended,0)*{PESOS['pd']}"
    f"+coalesce(def_fumbles_forced,0)*{PESOS['ff']}+coalesce(def_fumbles,0)*{PESOS['fr']}"
    f"+coalesce(def_tds,0)*{PESOS['td']}+coalesce(def_safeties,0)*{PESOS['saf']}"
    f"+(coalesce(def_fg_blocks,0)+coalesce(def_punt_blocks,0)+coalesce(def_pat_blocks,0))*{PESOS['blk']}")


def tabla(con, anios):
    union = " union all ".join(f"select * from read_parquet('{D}/semanal_{a}.parquet')" for a in anios)
    con.execute(f"""create or replace table p as
      select season, week, opponent_team conc, position,
             case when position in ('DT','NT') then ({FP(PESOS['sack_dt'])})
                  when position in ('DE','EDGE') then ({FP(PESOS['sack_otro'])}) end fp,
             coalesce(def_sacks,0) sk
      from ({union}) where season_type='REG' and position in ('DT','NT','DE','EDGE')""")
    con.execute("""create or replace table t as
      select conc, season, week,
             sum(case when position in ('DE','EDGE') then fp else 0 end) de,
             sum(case when position in ('DT','NT') then fp else 0 end) dt,
             sum(sk) sk
      from p group by 1,2,3""")
    return con.execute("""select conc, count(*) j, avg(de) de, avg(dt) dt, avg(de+dt) tot, avg(sk) sk
        from t group by 1""").fetchall()


def main():
    con = duckdb.connect()
    anio = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    filas = tabla(con, [anio])
    liga = {k: sum(f[i] for f in filas) / len(filas) for k, i in (('de', 2), ('dt', 3), ('tot', 4), ('sk', 5))}
    print(f"=== PUNTOS CONCEDIDOS A LOS DE Y DT · {anio} · promedio por partido ===")
    print(f"media de la liga: DE {liga['de']:.1f} · DT {liga['dt']:.1f} · total {liga['tot']:.1f}\n")
    print(f"{'#':>3} {'ofensiva':9}{'j':>3}{'DE':>8}{'DT':>8}{'DE+DT':>9}{'x liga':>8}{'sacks/j':>9}")
    for i, (eq, j, de, dt, tot, sk) in enumerate(sorted(filas, key=lambda x: -x[4]), 1):
        print(f"{i:>3} {eq:9}{j:>3}{de:>8.1f}{dt:>8.1f}{tot:>9.1f}{tot/liga['tot']:>8.2f}{sk:>9.2f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
