"""Ingesta nflverse 2021-2025 -> DuckDB. Parquet DIRECTO de nflverse-data
(bypass de nfl_data_py para weekly/def/pbp: sus URLs internas 404ean)."""
from pathlib import Path
import duckdb, pandas as pd
import nfl_data_py as nfl

RAIZ=Path(__file__).resolve().parent.parent
DB=str(RAIZ/'db'/'fantasy.duckdb')
YEARS=list(range(2021,2026))
NV='https://github.com/nflverse/nflverse-data/releases/download'
con=duckdb.connect(DB)

print('== dim_game (schedules + Vegas) ==', flush=True)
sch=nfl.import_schedules(YEARS)
con.execute("CREATE OR REPLACE TABLE dim_game AS SELECT * FROM sch"); print(' ',len(sch))

def carga(tabla, patron, años=YEARS):
    dfs=[]
    for y in años:
        d=pd.read_parquet(f'{NV}/{patron}'.format(y=y))
        dfs.append(d); print(f'  {y}: {len(d)}', flush=True)
    dd=pd.concat(dfs, ignore_index=True)
    con.execute(f"CREATE OR REPLACE TABLE {tabla} AS SELECT * FROM dd")
    print(f' {tabla}: {len(dd)}')
    return dd

print('== fact_player_week (esquema unificado of+def, tag stats_player) ==', flush=True)
carga('fact_player_week','stats_player/stats_player_week_{y}.parquet')
print('== fact_snaps ==', flush=True)
carga('fact_snaps','snap_counts/snap_counts_{y}.parquet')

print('== fact_td_plays (pbp -> distancias de TD) ==', flush=True)
rows=[]
for y in YEARS:
    p=pd.read_parquet(f'{NV}/pbp/play_by_play_{y}.parquet',
        columns=['season','week','game_id','touchdown','play_type','yards_gained',
                 'td_player_id','rusher_player_id','receiver_player_id','passer_player_id'])
    td=p[(p['touchdown']==1)&(p['play_type'].isin(['run','pass']))]
    rows.append(td); print(f'  {y}: {len(td)} TDs', flush=True)
    del p
tds=pd.concat(rows, ignore_index=True)
con.execute("CREATE OR REPLACE TABLE fact_td_plays AS SELECT * FROM tds")
print(' fact_td_plays:',len(tds))

print('== xwalk ids ==', flush=True)
ids=nfl.import_ids()
con.execute("CREATE OR REPLACE TABLE xwalk_ids_nflverse AS SELECT * FROM ids")
print(' ids:',len(ids),'| espn_id presente:', 'espn_id' in ids.columns)
con.close()
print('\nINGESTA COMPLETA')
