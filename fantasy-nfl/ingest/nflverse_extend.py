"""Extiende fact_player_week hacia atrás (2010-2020) para el estudio de
ventana histórica del modelo de partidos jugados (pedido de Andrés 19-ago:
"el modelo tiene que ir mucho más allá de 2023").

Pre-2021 la temporada era de 16 juegos: toda comparación usa fracción de
temporada, no juegos absolutos. Aquí solo se ingesta; la normalización
vive en el análisis."""
from pathlib import Path
import duckdb, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
NV = 'https://github.com/nflverse/nflverse-data/releases/download'
con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'))

ya = {r[0] for r in con.execute('select distinct season from fact_player_week').fetchall()}
faltan = [y for y in range(2010, 2026) if y not in ya]
print('temporadas ya en DB:', sorted(ya), '· faltan:', faltan, flush=True)

for y in faltan:
    d = pd.read_parquet(f'{NV}/stats_player/stats_player_week_{y}.parquet')
    cols = [r[0] for r in con.execute(
        "select column_name from information_schema.columns "
        "where table_name='fact_player_week' order by ordinal_position").fetchall()]
    comunes = [c for c in cols if c in d.columns]
    d = d[comunes]
    con.execute(f"INSERT INTO fact_player_week ({', '.join(comunes)}) "
                f"SELECT {', '.join(comunes)} FROM d")
    print(f'  {y}: +{len(d)}', flush=True)

print(con.execute('select min(season), max(season), count(*) from fact_player_week').fetchall())
