import sys; sys.path.insert(0,'/home/user/Apuestas-mundial')
import numpy as np
from pollas.CSC.optim_cuartos import matrices
from motor import simulacion_polla as sp
from pollas.CSC.reglas import RONDAS
Ms=matrices('/home/user/Apuestas-mundial/pollas/CSC/cuar_odds_snapshot.json')
PARAMS=RONDAS['cuartos']; G=7
nombres=['Francia-Marruecos','Espana-Belgica','Noruega-Inglaterra','Argentina-Suiza']
def gmean(M): return float((np.arange(M.shape[0])@M.sum(1))+(np.arange(M.shape[1])@M.sum(0)))
def evmax(M):
    EV=sp.ev_grid(M,PARAMS,G); return np.unravel_index(np.argmax(EV),EV.shape)
def tighten_to(M, target):
    # penaliza cada gol: M[i,j]*=exp(-a*(i+j)); busca 'a' para que la media = target
    lo,hi=0.0,3.0
    for _ in range(40):
        a=(lo+hi)/2
        W=M*np.exp(-a*(np.add.outer(np.arange(M.shape[0]),np.arange(M.shape[1])))); W/=W.sum()
        if gmean(W)>target: lo=a
        else: hi=a
    W=M*np.exp(-a*(np.add.outer(np.arange(M.shape[0]),np.arange(M.shape[1])))); return W/W.sum()
print('Condicionando el modelo a la tasa REAL de knockout (2.43 gol/part):')
print('  %-20s %6s %8s %6s %8s'%('Partido','gExp0','EVmax0','gExpKO','EVmaxKO'))
for M,nm in zip(Ms,nombres):
    ev0=evmax(M); MK=tighten_to(M,2.43); evk=evmax(MK)
    print('  %-20s %6.2f  %6s %6.2f  %6s'%(nm,gmean(M),'%d-%d'%ev0,gmean(MK),'%d-%d'%evk))
print('\n(EVmax0 = con el modelo del mercado; EVmaxKO = tras apretar a la media real de knockout)')
