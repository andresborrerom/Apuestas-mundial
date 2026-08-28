"""VBD v1 — proyecciones 2026 (stats crudas ESPN × motor validado 1403/1403)
con baselines de LA estructura real: 16 equipos, slots QB/RB/RBWR×2/WR/TE/OP/
DT/DE/LB/CB/S/DST/K.

SUPUESTOS DECLARADOS (sensibilidad en el reporte):
- S1 OP: se llena con QB en ~85-95% de equipos (superflex racional) -> baseline
  QB en rango 28-31; usamos 30 y reportamos 28/32.
- S2 flex RBWR (2 por equipo): split RB/WR 60/40 histórico -> RB 35, WR 29;
  sensibilidad 50/50 -> RB 32, WR 32.
- S3 proyección = consenso ESPN de stats crudas (mercado) re-puntuado con
  NUESTRAS reglas. El edge aritmético de la tesis; SIN alpha propio todavía.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model.scoring import cargar_reglas, puntos

RAIZ = Path(__file__).resolve().parent.parent
POS = {1:'QB',2:'RB',3:'WR',4:'TE',5:'K',9:'DT',10:'DE',11:'LB',12:'CB',13:'S',14:'DB',16:'DST'}
# Baselines = TITULARES SEMANALES en la liga (16 equipos), roster v3 (19-ago):
#   QB/RB/WR/TE/DT/DE/LB/CB/S/DST/K ×1 + WR ×1 extra (2 en total) + 1 flex
#   RB/WR + 1 OP (superflex).
#   QB = 16 + OP×~0.9 = 30 (✅ confirmado por Andrés: "la liga alinea ~30")
#   RB = 16 + flex×0.6 = 26   |   WR = 32 + flex×0.4 = 38
# ⚠️ CAMBIO v2→v3: el flex RB/WR bajó de 2 a 1 y WR subió de 1 a 2 → la WR se
# volvió MÁS profunda (baseline peor ⇒ más valor) y la RB más superficial.
BASE = {'QB':30,'RB':26,'WR':38,'TE':17,'K':17,'DST':17,'DT':17,'DE':17,'LB':17,'CB':17,'S':17}

def proyecciones():
    todos = json.load(open(RAIZ/'data'/'espn_applied_2025.json'))
    items = cargar_reglas()
    out = []
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if not pos: continue
        ent = [s for s in (p.get('stats') or [])
               if s.get('seasonId')==2026 and s.get('statSourceId')==1 and s.get('statSplitTypeId')==0]
        if not ent: continue
        raw = ent[0].get('stats') or {}
        pts = puntos(raw, p.get('defaultPositionId'), items)
        if pts <= 0: continue
        out.append({'nombre':p['fullName'],'pos':pos,'espn_id':p.get('id'),
                    'equipo':p.get('proTeamId'),'proj':round(pts,1)})
    return out

def vbd(proys, base=None):
    base = base or BASE
    porpos = {}
    for r in proys: porpos.setdefault(r['pos'],[]).append(r)
    for pos, lst in porpos.items():
        lst.sort(key=lambda r:-r['proj'])
        n = base.get(pos)
        if not n or len(lst) < 2: continue
        bl = lst[min(n,len(lst))-1]['proj']
        for i,r in enumerate(lst):
            r['rank_pos'] = i+1
            r['baseline'] = bl
            r['vbd'] = round(r['proj'] - bl,1)
    todos = [r for lst in porpos.values() for r in lst if 'vbd' in r]
    todos.sort(key=lambda r:-r['vbd'])
    return todos

if __name__ == '__main__':
    proys = proyecciones()
    print(f'jugadores proyectados: {len(proys)}')
    ranking = vbd(proys)
    import csv
    with open(RAIZ/'data'/'vbd_v1.csv','w',newline='') as f:
        w = csv.DictWriter(f, fieldnames=['nombre','pos','rank_pos','proj','baseline','vbd','espn_id','equipo'])
        w.writeheader()
        for r in ranking: w.writerow({k:r.get(k) for k in w.fieldnames})
    print(f"{'#':>3} {'jugador':24}{'pos':>4}{'pr#':>4}{'proj':>7}{'base':>7}{'VBD':>7}")
    for i,r in enumerate(ranking[:40]):
        print(f"{i+1:>3} {r['nombre'][:24]:24}{r['pos']:>4}{r['rank_pos']:>4}{r['proj']:>7}{r['baseline']:>7}{r['vbd']:>7}")
    print('\n-- top-3 por posición --')
    vistos={}
    for r in ranking:
        vistos.setdefault(r['pos'],[]).append(r)
    for pos in ['QB','RB','WR','TE','DT','DE','LB','CB','S','DST','K']:
        top=vistos.get(pos,[])[:3]
        print(f"  {pos:>3}: " + ' · '.join(f"{t['nombre']} ({t['proj']}, vbd {t['vbd']})" for t in top))
    # sensibilidad S1/S2
    print('\n-- sensibilidad de baselines (top-10 bajo variantes) --')
    for nombre,b in [('QB28/RB32/WR32',dict(BASE,QB=28,RB=32,WR=32)),
                     ('QB32/RB37/WR27',dict(BASE,QB=32,RB=37,WR=27))]:
        alt=vbd([dict(r) for r in proys], b)
        print(f"  {nombre}: " + ', '.join(f"{r['nombre'].split()[-1]}({r['pos']})" for r in alt[:10]))
