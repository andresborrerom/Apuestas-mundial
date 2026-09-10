import json, sys
sys.path.insert(0,'/home/user/Apuestas-mundial')
import numpy as np
from pollas.CSC.optim_cuartos import matrices, construir_perfiles
from motor import simulacion_polla as sp
from pollas.CSC.reglas import RONDAS
BD=json.load(open('/home/user/Apuestas-mundial/pollas/LEMAITRE/lemaitre_data.json',encoding='utf-8'))
gr=[(p['e1'],p['e2']) for p in BD['grupos_results'] if p.get('e1') is not None]
grg=[p['e1']+p['e2'] for p in BD['grupos_results'] if p.get('e1') is not None]
ko=[(r['g1'],r['g2']) for k,r in BD['real_scores'].items() if r.get('g1') is not None and 73<=int(k)<=96]
kog=[r['g1']+r['g2'] for k,r in BD['real_scores'].items() if r.get('g1') is not None and 73<=int(k)<=96]
gg=np.mean(grg); kg=np.mean(kog); tag="MENOS" if kg<gg else "MAS"
print('=== EMPIRICO: goles por partido ===')
print('  Grupos (%d):   media %.2f gol/part - empates %.0f%%'%(len(gr),gg,np.mean([a==b for a,b in gr])*100))
print('  Knockout (%d): media %.2f gol/part - empates(90) %.0f%%'%(len(ko),kg,np.mean([a==b for a,b in ko])*100))
print('  -> knockout %s goleador que grupos (%+.2f gol/part)'%(tag, kg-gg))
Ms=matrices('/home/user/Apuestas-mundial/pollas/CSC/cuar_odds_snapshot.json')
PARAMS=RONDAS['cuartos']; G=7
nombres=['Francia-Marruecos','Espana-Belgica','Noruega-Inglaterra','Argentina-Suiza']
def evmax(M):
    EV=sp.ev_grid(M,PARAMS,G); return np.unravel_index(np.argmax(EV),EV.shape)
def modal(M):
    return np.unravel_index(np.argmax(M),M.shape)
def apretar(M,f):
    Mp=M**f; return Mp/Mp.sum()
print('\n=== MODELO cuartos: goles esperados, EV-max, MODAL, y EV-max si apretamos el juego ===')
print('  %-20s %5s %8s %7s %9s %10s'%('Partido','gExp','EV-max','MODAL','P(modal)','EVmax+apret'))
for M,nm in zip(Ms,nombres):
    gexp=float((np.arange(M.shape[0])@M.sum(1))+(np.arange(M.shape[1])@M.sum(0)))
    ev=evmax(M); mo=modal(M); pmo=float(M[mo]); ev_ap=evmax(apretar(M,1.6))
    print('  %-20s %5.2f  %6s  %5s %8.0f%%   %8s'%(nm,gexp,'%d-%d'%ev,'%d-%d'%mo,pmo*100,'%d-%d'%ev_ap))
perf=construir_perfiles(Ms)
rng=np.random.default_rng(3); Sx=40000
gh,ga=sp.muestrear_torneos(Ms,Sx,rng,G)
print('\n=== P(pegar al menos 1 / 2 marcadores EXACTOS en los 4 cuartos) ===')
def phit(ph,pa):
    ex=np.zeros(Sx,dtype=int)
    for m in range(4): ex+=((gh[m]==ph[m])&(ga[m]==pa[m])).astype(int)
    return np.mean(ex>=1)*100, np.mean(ex>=2)*100, ex.mean()
for nm in ['D (EV-máx)','A (rank2 todos)','B (rank3 todos)']:
    ph,pa=perf[nm]; a,b,c=phit(ph,pa)
    print('  %-16s P(>=1)=%.1f%%  P(>=2)=%.1f%%  E[exactos]=%.2f'%(nm.split()[0],a,b,c))
mh=np.array([modal(M)[0] for M in Ms]); ma=np.array([modal(M)[1] for M in Ms])
a,b,c=phit(mh,ma)
print('  %-16s P(>=1)=%.1f%%  P(>=2)=%.1f%%  E[exactos]=%.2f  (marcadores %s)'%('MODAL',a,b,c,['%d-%d'%(mh[i],ma[i]) for i in range(4)]))
