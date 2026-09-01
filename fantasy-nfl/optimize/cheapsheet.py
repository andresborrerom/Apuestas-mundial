"""FANTASY CHEAP-SHEET (liga 1643420925) — proyección y VBD bajo SUS reglas.

Liga leída de la API (config/espn_settings_cheapsheet_2026.json, 1-sep):
  14 equipos · SNAKE 45s · mi teamId=1 'Remember the Titan'
  titulares: QB, RB×2, WR×2, TE, RB/WR, FLEX(RB/WR/TE), D/ST, K + 4 banca
  half-PPR (rec 0.5) · SIN IDP · SIN superflex

Baselines = titular semanal marginal de ESTA estructura (supuestos declarados):
  QB 14 (un slot, sin OP)
  flex RB/WR 60/40 y FLEX RB/WR/TE 45/40/15 (mismo criterio S2 de vbd.py):
    RB = 28 + 14·(0.60+0.45) ≈ 43   WR = 28 + 14·(0.40+0.40) ≈ 39
    TE = 14 + 14·0.15 ≈ 16          DST = K = 14
p10/p90: forma del cono de distribuciones.py (nuestra liga) escalada por el
ratio de totales — ⚠️ SUPUESTO (la forma por-jugador no depende del scoring).
Recorte por lesión viva: mismos factores S-LESION.
"""
import csv, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model.scoring import cargar_reglas, puntos

RAIZ = Path(__file__).resolve().parent.parent
POS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'DST'}
BASE_CS = {'QB': 14, 'RB': 43, 'WR': 39, 'TE': 16, 'DST': 14, 'K': 14}
REC = {'OUT': 0.55, 'INJURY_RESERVE': 0.30, 'SUSPENSION': 0.65, 'DOUBTFUL': 0.90}


def construir():
    """proj = appliedTotal FRESCO de ESPN bajo las reglas de ESTA liga
    (data/cheapsheet_applied.json, kona de la liga 1643420925 — validado
    contra nuestro motor: mediana Δ1.15 en 235 ofensivos; las diferencias
    grandes son ACTUALIZACIONES de proyección post-28-ago, p.ej. Jacobs
    255→151). Recorte S-LESION solo si ESPN aún NO descontó (fresco ≥ 0.9 ×
    motor con crudos viejos). DST: la liga puntúa CERO a las 32 (verificado
    settings + applied) → proj 0, pick muerto de última ronda."""
    items = cargar_reglas('espn_settings_cheapsheet_2026')
    todos = json.load(open(RAIZ / 'data' / 'espn_applied_2025.json'))
    fresco = json.load(open(RAIZ / 'data' / 'cheapsheet_applied.json'))
    dist = {int(r['espn_id']): r for r in
            csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv'))}
    inj = json.load(open(RAIZ / 'data' / 'injury_vivo.json'))
    out = []
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if not pos:
            continue
        ent = [s for s in (p.get('stats') or [])
               if s.get('seasonId') == 2026 and s.get('statSourceId') == 1
               and s.get('statSplitTypeId') == 0]
        if not ent:
            continue
        mio = puntos(ent[0].get('stats') or {}, p.get('defaultPositionId'), items)
        pts = fresco.get(str(p['id']), mio)   # fresco manda; motor de respaldo
        if pos == 'DST':
            pts = 0.0
        if pts <= 0 and pos != 'DST':
            continue
        st = (inj.get(str(p['id'])) or {}).get('inj')
        f = REC.get(st, 1.0)
        if f < 1.0 and mio > 0 and pts < 0.9 * mio:
            f = 1.0                            # ESPN ya descontó la lesión
        d = dist.get(p['id'])
        esc = (pts / float(d['total_v2'])) if d and float(d['total_v2']) > 0 else 1.0
        out.append({'nombre': p['fullName'], 'pos': pos, 'espn_id': p['id'],
                    'proj': round(pts * f, 1), 'inj': st or '',
                    'p10': round(float(d['p10']) * esc * f, 1) if d else '',
                    'p90': round(float(d['p90']) * esc * f, 1) if d else ''})
    porpos = {}
    for r in out:
        porpos.setdefault(r['pos'], []).append(r)
    for pos, lst in porpos.items():
        lst.sort(key=lambda r: -r['proj'])
        bl = lst[min(BASE_CS[pos], len(lst)) - 1]['proj']
        for i, r in enumerate(lst):
            r['rank_pos'], r['vbd'] = i + 1, round(r['proj'] - bl, 1)
    out.sort(key=lambda r: -r['vbd'])
    with open(RAIZ / 'data' / 'cheapsheet_tablero.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return out


if __name__ == '__main__':
    out = construir()
    print(f'{len(out)} jugadores · data/cheapsheet_tablero.csv')
    print('\nTop-15 por VBD de la Cheap-Sheet (half-PPR, 1QB, 14 eq):')
    for r in out[:15]:
        print(f"  {r['pos']:3} {r['nombre']:24} proy {r['proj']:>5} · vbd {r['vbd']:>5}")
    qb1 = next(r for r in out if r['pos'] == 'QB' and r['rank_pos'] == 1)
    print(f"\ncandado de cordura: QB1 = {qb1['nombre']} vbd {qb1['vbd']} "
          f"(en liga 1QB debe caer muy por debajo del top de RB/WR)")
