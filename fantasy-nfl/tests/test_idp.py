import sys; sys.path.insert(0,'/home/user/Apuestas-mundial/fantasy-nfl')
import duckdb
from optimize.idp_semanal import base, backtest, compara
con=duckdb.connect(); base(con)
n,_=backtest(con)
assert n>30000, f"muestra insuficiente: {n}"
# CANDADO ANTI-FUGA: la 1a semana de 2021 no puede tener prediccion (no hay pasado)
f=con.execute("select count(*) from ev where season=2021 and week=1").fetchone()[0]
assert f==0, f"FUGA: {f} filas de la semana 1 de 2021 tienen historia previa"
# el multiplicador debe centrarse en ~1
m=con.execute("select avg(media_rival/mu_riv_liga) from ev").fetchone()[0]
assert 0.95<m<1.05, f"multiplicador descentrado: {m}"
# reproducibilidad: dos corridas dan lo mismo
a=compara(con,'DL'); b=compara(con,'DL')
assert a==b, "no reproducible"
print(f"  ✅ muestra {n:,} · sin fuga en la primera semana · multiplicador centrado en {m:.3f} · reproducible")
