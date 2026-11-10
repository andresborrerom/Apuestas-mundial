import json, csv, sys, re, unicodedata
sys.path.insert(0,'/home/user/Apuestas-mundial')
import numpy as np
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills
from motor import backtest as bt
CSCP=RONDAS['dieciseisavos']; G=7
def nrm(s): return re.sub('[^a-z]','',unicodedata.normalize('NFD',str(s)).encode('ascii','ignore').decode().lower())
AL={'usa':'unitedstates','eeuu':'unitedstates','estadosunidos':'unitedstates','rdcongo':'drcongo','congo':'drcongo',
'costamarfil':'ivorycoast','costademarfil':'ivorycoast','bosniaherzegovina':'bosnia','holanda':'netherlands','paisesbajos':'netherlands',
'norway':'norway','noruega':'norway','sweden':'sweden','suecia':'sweden','croacia':'croatia','argelia':'algeria','egipto':'egypt','caboverde':'capeverde'}
def canon(x):
    a=nrm(x); return AL.get(a,a)
# resultados R32 a 120' (CSC): los aet usan el final
RES={('southafrica','canada'):(0,1),('germany','paraguay'):(1,1),('netherlands','morocco'):(1,1),
('brazil','japan'):(2,1),('france','sweden'):(3,0),('ivorycoast','norway'):(1,2),('mexico','ecuador'):(2,0),
('england','drcongo'):(2,1),('unitedstates','bosnia'):(2,0),('belgium','senegal'):(3,2),('portugal','croatia'):(2,1),
('spain','austria'):(3,0),('switzerland','algeria'):(2,0),('argentina','capeverde'):(3,2),('colombia','ghana'):(1,0),
('australia','egypt'):(1,1)}
# matrices R32 desde odds (pre-ronda) para regenerar esquemas
ev=json.load(open('/home/user/Apuestas-mundial/pollas/CSC/r32_odds_snapshot.json',encoding='utf-8'))
Ms=[]; keys=[]
for e in ev:
    c=odds_api.consenso_evento(e,linea_pref=2.5)
    if not c['cuotas_1x2']: continue
    r=analizar_partido(cuotas_1x2=c['cuotas_1x2'],regla=regla_de_ronda('dieciseisavos'),cuotas_ou=c['cuotas_ou'],linea_ou=c['linea'] or 2.5,sesgo_goles=0.0,max_goles_relleno=7)
    M90=r['matriz']; M120=ajuste_120(M90,r['modelo']['lambda_local'],r['modelo']['lambda_visita'],0.45)
    Ms.append(marcadores.aplicar_sesgo_goles(M120,0.05)); keys.append((canon(e['home_team']),canon(e['away_team'])))
# resultado real alineado a cada matriz
real=[]
for k in keys:
    r=RES.get(k) or RES.get((k[1],k[0]))
    if RES.get(k): real.append(RES[k])
    elif RES.get((k[1],k[0])): rr=RES[(k[1],k[0])]; real.append((rr[1],rr[0]))
    else: real.append(None)
def haul(ph,pa):
    return sum(bt.puntos((int(ph[i]),int(pa[i])), real[i], CSCP) for i in range(len(real)) if real[i])
# esquemas
e_h,e_a,s_h,s_a,gap=sp.fill_evmax_y_segundo(Ms,CSCP,G)
rk=ranking_fills(Ms); l2h=np.array([r[1][0] for r in rk]); l2a=np.array([r[1][1] for r in rk])
l3h=np.array([r[2][0] for r in rk]); l3a=np.array([r[2][1] for r in rk])
# modal (humano): argmax de M (marcador más probable)
mh=np.array([np.unravel_index(np.argmax(M),M.shape)[0] for M in Ms]); ma=np.array([np.unravel_index(np.argmax(M),M.shape)[1] for M in Ms])
print("WALK-FORWARD R32 (16 partidos, ground truth 120') — cosecha real:")
print(f"   EV-máx (ancla)      : {haul(e_h,e_a)}")
print(f"   2º fill (lotería)   : {haul(l2h,l2a)}")
print(f"   3º fill (lotería)   : {haul(l3h,l3a)}")
print(f"   MODAL (más probable): {haul(mh,ma)}   <- lo que juega un 'humano'")
# field: distribución de cosecha de un casual/humano (Monte Carlo sobre picks del arquetipo hum)
rng=np.random.default_rng(3)
ghS=np.array([[real[i][0]] for i in range(len(real)) if real[i]]); # not used
# simular hauls de arquetipos vs el resultado REAL fijo
def sim_field_haul(arq_conc, n=4000):
    hauls=[]
    for M,rl in zip(Ms,real):
        if rl is None: continue
        flat=(M.ravel()**arq_conc); flat/=flat.sum()
        idx=rng.choice(flat.size,size=n,p=flat)
        hh=idx//M.shape[1]; aa=idx%M.shape[1]
        pts=np.array([bt.puntos((int(hh[j]),int(aa[j])),rl,CSCP) for j in range(n)])
        hauls.append(pts)
    return np.sum(hauls,axis=0)
casual=sim_field_haul(1.0); humano=sim_field_haul(4.0)
print(f"\n   Field CASUAL (crudo)  : media {casual.mean():.0f}  (p90 {np.percentile(casual,90):.0f})")
print(f"   Field HUMANO (modal)  : media {humano.mean():.0f}  (p90 {np.percentile(humano,90):.0f})")
print(f"\n   EDGE del EV-máx vs humano medio: +{haul(e_h,e_a)-humano.mean():.0f} pts en R32 (ground truth)")
