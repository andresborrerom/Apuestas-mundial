import json, sys, re, unicodedata
sys.path.insert(0,'/home/user/Apuestas-mundial')
from pollas.LEMAITRE.puntos_lemaitre import calc_todo, norm
BD=json.load(open('/home/user/Apuestas-mundial/pollas/LEMAITRE/lemaitre_data.json',encoding='utf-8'))
parts=[str(p['num']) for p in BD['participants']]; names={str(p['num']):p['name'] for p in BD['participants']}
pe=BD['predictions_e']; req=BD['real_equipos']; rs=BD['real_scores']
base=calc_todo(BD); tot={n:base[n]['total'] for n in parts}
yo=next(n for n in parts if names[n]=='Pocho')
# equipos VIVOS: los que están en slots de octavos y NO fueron eliminados
oct_teams=set()
for p in range(89,97):
    e=req.get(str(p),{})
    if e.get('e1'): oct_teams.add(norm(e['e1'])); oct_teams.add(norm(e['e2']))
elim=set()
for p in range(89,97):
    r=rs.get(str(p),{})
    if r.get('g1') is not None:
        if r['g1']>r['g2']: elim.add(norm(r['e2']))
        elif r['g2']>r['g1']: elim.add(norm(r['e1']))
# P#92 México-Inglaterra: sabemos Inglaterra avanzó
elim.add(norm('México'))
vivos=oct_teams-elim
print('VIVOS (12):', sorted(vivos))
print('ELIMINADOS en octavos:', sorted(elim),'\n')
# ceiling de MARCADORES restante (igual para todos): 4*40(OCT93-96)+4*50(CUAR)+2*60(SEMI)+70+80
MARC_CEIL=4*40+4*50+2*60+70+80
# para cada participante: campeón/finalistas vivos? y techo de clasif+final VIVO
def alive(t): return t and norm(t) in vivos
print(f"{'Participante':20}{'total':>6}{'Campeón pick':>16}{'vivo?':>7}{'#final4 vivos':>14}")
rows=[]
for n in parts:
    px=pe[n]
    camp=px.get('camp'); sub=px.get('sub'); ter=px.get('3er'); cua=px.get('4to')
    fin4=[camp,sub,ter,cua]; nviv=sum(1 for t in fin4 if alive(t))
    # techo de clasif futura VIVO: cuartos(97-100)+semis(101-102): cuenta cuántos de sus equipos predichos siguen vivos
    clas_ceiling=0
    for slot,mx in [(97,30),(98,30),(99,30),(100,30),(101,25),(102,25)]:
        pr=px.get(str(slot),{})
        if pr and pr.get('e1'):
            if alive(pr['e1']) and alive(pr['e2']): clas_ceiling+=mx      # ambos pueden llegar
            elif alive(pr['e1']) or alive(pr['e2']): clas_ceiling+=mx//2  # solo uno
    fin_ceiling=sum(m for t,m in [(camp,80),(sub,60),(ter,40),(cua,30)] if alive(t))
    rows.append((n,tot[n],camp,alive(camp),nviv,clas_ceiling,fin_ceiling))
for n,t,camp,cv,nviv,cc,fc in sorted(rows,key=lambda x:-x[1])[:10]:
    star=' <<<' if n==yo else ''
    print(f"{names[n][:20]:20}{t:>6}{str(camp)[:15]:>16}{'✅' if cv else '❌':>7}{nviv:>10}/4{star}")
print(f"\n{'Participante':20}{'total':>6}{'+MarcMax':>9}{'+ClasVivo':>10}{'+FinVivo':>9}{'TECHO':>7}{'?vs Dio floor':>14}")
# floor de Dionisio (si no suma NADA más): su total actual
dio=next(n for n in parts if names[n].startswith('Dionisio')); dio_floor=tot[dio]
for n,t,camp,cv,nviv,cc,fc in sorted(rows,key=lambda x:-(x[1]+x[5]+x[6]))[:10]:
    techo=t+MARC_CEIL+cc+fc
    puede = 'VIVO' if techo>dio_floor else 'CAPADO'
    star=' <<<' if n==yo else ''
    print(f"{names[n][:20]:20}{t:>6}{MARC_CEIL:>9}{cc:>10}{fc:>9}{techo:>7}{puede:>14}{star}")
