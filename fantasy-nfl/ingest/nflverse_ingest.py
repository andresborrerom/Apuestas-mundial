"""Ingesta nflverse 2021-2025 -> DuckDB. Capa 1: hechos crudos."""
import sys
from pathlib import Path
import duckdb
import pandas as pd
import nfl_data_py as nfl

RAIZ=Path(__file__).resolve().parent.parent
DB=str(RAIZ/'db'/'fantasy.duckdb')
YEARS=list(range(2021,2026))
con=duckdb.connect(DB)

print('== schedules (dim_game con Vegas) ==')
sch=nfl.import_schedules(YEARS)
con.execute("CREATE OR REPLACE TABLE dim_game AS SELECT * FROM sch")
print(' dim_game:',len(sch))

print('== weekly ofensivo ==')
wk=nfl.import_weekly_data(YEARS)
con.execute("CREATE OR REPLACE TABLE fact_player_week_off AS SELECT * FROM wk")
print(' fact_player_week_off:',len(wk),'cols:',len(wk.columns))

print('== snap counts ==')
try:
    sn=nfl.import_snap_counts(YEARS)
    con.execute("CREATE OR REPLACE TABLE fact_snaps AS SELECT * FROM sn")
    print(' fact_snaps:',len(sn))
except Exception as e:
    print(' snaps FALLO:',type(e).__name__,e)

print('== defensivo semanal (parquet nflverse directo) ==')
defs=[]
for y in YEARS:
    try:
        d=pd.read_parquet(f'https://github.com/nflverse/nflverse-data/releases/download/player_stats/player_stats_def_{y}.parquet')
        defs.append(d); print(f' def {y}: {len(d)}')
    except Exception as e:
        print(f' def {y} FALLO: {type(e).__name__}')
if defs:
    dd=pd.concat(defs)
    con.execute("CREATE OR REPLACE TABLE fact_player_week_def AS SELECT * FROM dd")
    print(' fact_player_week_def:',len(dd))

print('== pbp -> TDs por distancia (bonos 40+/50+) ==')
rows=[]
for y in YEARS:
    p=nfl.import_pbp_data([y],downcast=True,cache=False)
    td=p[(p['touchdown']==1)&(p['play_type'].isin(['run','pass']))][
        ['season','week','td_player_id','yards_gained','play_type','rusher_player_id','receiver_player_id']]
    rows.append(td); print(f' pbp {y}: {len(td)} TDs')
    del p
tds=pd.concat(rows)
con.execute("CREATE OR REPLACE TABLE fact_td_plays AS SELECT * FROM tds")
print(' fact_td_plays:',len(tds))

print('== ids (crosswalk base) ==')
ids=nfl.import_ids()
con.execute("CREATE OR REPLACE TABLE xwalk_ids_nflverse AS SELECT * FROM ids")
print(' xwalk_ids_nflverse:',len(ids),'| tiene espn_id:',('espn_id' in ids.columns))
con.close()
print('\nINGESTA COMPLETA -> db/fantasy.duckdb')
