import json, csv, sys, re, unicodedata
sys.path.insert(0,'/home/user/Apuestas-mundial')
from motor import backtest as bt
from pollas.CSC.reglas import RONDAS
CSCP = RONDAS['dieciseisavos']
def nrm(s): return re.sub('[^a-z]','',unicodedata.normalize('NFD',str(s)).encode('ascii','ignore').decode().lower())
AL={'usa':'unitedstates','estadosunidos':'unitedstates','eeuu':'unitedstates','rdcongo':'drcongo','congo':'drcongo',
 'costamarfil':'ivorycoast','costademarfil':'ivorycoast','bosniaherzegovina':'bosnia','paisesbajos':'netherlands','holanda':'netherlands','norway':'norway','noruega':'norway','sweden':'sweden','suecia':'sweden','austria':'austria','croacia':'croatia','algeria':'algeria','argelia':'algeria','egipto':'egypt','capeverde':'capeverde','caboverde':'capeverde','ghana':'ghana'}
def canon(x):
    a=nrm(x); return AL.get(a,a)
# resultados reales R32 (de la data LEMAITRE, partidos 73-82)
BD=json.load(open('/home/user/Apuestas-mundial/pollas/LEMAITRE/lemaitre_data.json',encoding='utf-8'))
res={}
for k,r in BD['real_scores'].items():
    if r.get('g1') is not None and 73<=int(k)<=88:
        res[(canon(r['e1']),canon(r['e2']))]=(r['g1'],r['g2'])
# cupos CSC
rows=list(csv.DictReader(open('/home/user/Apuestas-mundial/pollas/CSC/r32_CSC.csv',encoding='utf-8')))
tot=[0]*5; jug=0
print("%-24s %-8s %s" % ("Partido","real","cupos B1..B5 -> pts"))
for r in rows:
    cl,cv=r['local'],r['visita']; key=None
    for (a,b),sc in res.items():
        if canon(cl)==a and canon(cv)==b: key=(a,b,sc,False); break
        if canon(cl)==b and canon(cv)==a: key=(a,b,(sc[1],sc[0]),True); break
    if not key: continue
    real=key[2]; jug+=1
    cupos=[tuple(map(int,r[f'cupo_{i}'].split('-'))) for i in range(1,6)]
    pts=[bt.puntos(c, real, CSCP) for c in cupos]
    for i in range(5): tot[i]+=pts[i]
    print("%-24s %-8s %s" % (f"{cl[:11]}-{cv[:11]}", f"{real[0]}-{real[1]}", " ".join(f"B{i+1}:{p}" for i,p in enumerate(pts))))
print(f"\nPartidos R32 jugados y puntuados: {jug}/16")
print("COSECHA R32 por cupo:")
for i in range(5):
    tag=" <- ANCLA (EV-max)" if i==3 else ""
    print(f"   ANDRES BORRERO {i+1}: {tot[i]} pts{tag}")
