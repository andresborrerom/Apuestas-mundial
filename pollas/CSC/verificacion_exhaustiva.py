import json, sys, itertools
sys.path.insert(0,'/home/user/Apuestas-mundial')
import numpy as np
from motor import simulacion_polla as sp
from pollas.CSC.reglas import RONDAS
from pollas.CSC.optim_cuartos import matrices, construir_perfiles
PARAMS=RONDAS['cuartos']; G=7; PRECIO=100000; S=30000
Ms=matrices('/home/user/Apuestas-mundial/pollas/CSC/cuar_odds_snapshot.json')
fd=json.load(open('/tmp/claude-0/-home-user-Apuestas-mundial/d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/field7.json'))
rivals=np.array([p for _,p in fd['rivals']],float)
o=sorted(fd['ours'].items(),key=lambda kv:-kv[1]); labels=[k.replace('ANDRES BORRERO ','B') for k,_ in o]
ours_pts=np.array([v for _,v in o],float); Ef=len(rivals)
perf=construir_perfiles(Ms)
# menú COMPLETO (7 perfiles) para exhaustivo
menu=['D (EV-máx)','A (rank2 todos)','B (rank3 todos)']
rng=np.random.default_rng(1)
gh,ga=sp.muestrear_torneos(Ms,S,rng,G)
fh,fa=sp.generar_field_mix(Ms,Ef,{'opt':.15,'cal':.35,'hum':.50},PARAMS,rng,G)
field_tot=rivals[:,None]+sp._puntos(fh,fa,gh,ga,PARAMS)
pg={n:sp._puntos(np.array([ph]),np.array([pa]),gh,ga,PARAMS)[0] for n,(ph,pa) in perf.items()}
premio=sp.PREMIOS*(Ef+5)*PRECIO; jit=rng.random((5,S))*1e-6
def prize(assign):
    our=ours_pts[:,None]+np.array([pg[a] for a in assign])+jit
    fabove=(field_tot[None,:,:]>our[:,None,:]).sum(axis=1)
    oabove=(our[:,None,:]>our[None,:,:]).sum(axis=0)
    rank=fabove+oabove
    return np.where(rank<5,premio[np.clip(rank,0,4)],0.0).sum(0).mean()
# EXHAUSTIVO sobre 7^5 = 16807 asignaciones
best=None; res=[]
for combo in itertools.product(menu,repeat=5):
    p=prize(combo); res.append((p,combo))
res.sort(key=lambda x:-x[0])
print(f"EXHAUSTIVO: {len(res)} asignaciones evaluadas (premio TOTAL conjunto)")
print(f"baseline 5xD = {prize(['D (EV-máx)']*5):,.0f}\n")
print("TOP-6 asignaciones (por premio total):")
for p,c in res[:6]:
    tag=' '.join(f'{labels[i]}={c[i].split()[0]}' for i in range(5))
    print(f'   {p:>12,.0f}   {tag}')
print("\nPEOR-3:")
for p,c in res[-3:]:
    tag=' '.join(f'{labels[i]}={c[i].split()[0]}' for i in range(5))
    print(f'   {p:>12,.0f}   {tag}')
# nuestra asignación elegida
mine=['D (EV-máx)','A (rank2 todos)','B (rank3 todos)','D (EV-máx)','A (rank2 todos)']  # B1,B2,B3,B4,B5 -> orden labels [B4,B1,B5,B2,B3]
# reordenar a labels [B4,B1,B5,B2,B3]:
elegida={'B4':'D (EV-máx)','B1':'D (EV-máx)','B5':'A (rank2 todos)','B2':'A (rank2 todos)','B3':'B (rank3 todos)'}
asg=[elegida[l] for l in labels]
print(f"\nNuestra asignación elegida: {' '.join(f'{labels[i]}={asg[i].split()[0]}' for i in range(5))}")
print(f"   premio = {prize(asg):,.0f}   ·   ranking exhaustivo: #{[c for _,c in res].index(tuple(asg))+1} de {len(res)}")
