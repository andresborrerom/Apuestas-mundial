"""Nota de una línea por jugador para el tablero en vivo.

Dos partes, deliberadamente separadas:
  1) HECHOS NUESTROS (calculados de la data, exactos): cuota del backfield,
     cuota de targets, volumen proyectado, juegos jugados en 2025, E[juegos].
  2) CITA de ESPN (verbatim, recortada) — se cita, NO se parafrasea, para no
     introducir errores de interpretación en algo que se lee a 45 s por pick.

Genera data/notas.json (nombre -> nota).
"""
import json, re
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 9: 'DT', 10: 'DE', 11: 'LB',
       12: 'CB', 13: 'S', 14: 'DB', 16: 'DST'}
CLAVES = ('missed', 'injur', 'torn', 'ACL', 'suspend', 'rookie', 'traded',
          'signed', 'return', 'committee', 'career-high', 'led the league',
          'first season', 'holdout', 'PUP', 'new ', 'second fiddle', 'struggl',
          'breakout', 'top-', 'No. 1', 'starter')


def frase_clave(txt):
    """La oración con más densidad de señal noticiosa."""
    if not txt:
        return ''
    fr = re.split(r'(?<=[.!?])\s+', txt)
    mejor, punt = '', -1
    for f in fr[:6]:
        p = sum(1 for k in CLAVES if k.lower() in f.lower())
        if p > punt and 40 < len(f) < 230:
            mejor, punt = f, p
    return (mejor or fr[0])[:180]


def construir():
    from optimize.sala import abrir_applied
    todos = abrir_applied()
    P26, P25, equipo, pos_de, outlook = {}, {}, {}, {}, {}
    for pw in todos:
        p = pw['player']
        pid = p['id']
        pos_de[pid] = POS.get(p.get('defaultPositionId'))
        equipo[pid] = p.get('proTeamId')
        outlook[pid] = p.get('seasonOutlook') or ''
        for s in (p.get('stats') or []):
            k = (s.get('seasonId'), s.get('statSourceId'), s.get('statSplitTypeId'))
            if k == (2026, 1, 0):
                P26[pid] = s.get('stats') or {}
            elif k == (2025, 0, 0):
                P25[pid] = s.get('stats') or {}
    g = lambda d, k: float((d or {}).get(str(k), 0) or 0)
    # totales por equipo para calcular cuotas
    tot_bf, tot_tg = defaultdict(float), defaultdict(float)
    for pid, r in P26.items():
        t = equipo.get(pid)
        if pos_de.get(pid) == 'RB':
            tot_bf[t] += g(r, 23) + g(r, 53)
        if pos_de.get(pid) in ('WR', 'TE', 'RB'):
            tot_tg[t] += g(r, 58)
    notas = {}
    for pw in todos:
        p = pw['player']; pid = p['id']; pos = pos_de.get(pid)
        r26 = P26.get(pid)
        if not r26 or not pos:
            continue
        gj = g(r26, 210) or 17
        h = []
        if pos == 'RB':
            bf = g(r26, 23) + g(r26, 53)
            c = bf / tot_bf[equipo.get(pid)] * 100 if tot_bf.get(equipo.get(pid)) else 0
            h.append(f"{c:.0f}% del backfield")
            h.append(f"{g(r26,23)/gj:.1f} acarreos + {g(r26,53)/gj:.1f} rec/juego")
        elif pos in ('WR', 'TE'):
            c = g(r26, 58) / tot_tg[equipo.get(pid)] * 100 if tot_tg.get(equipo.get(pid)) else 0
            h.append(f"{c:.0f}% de los targets")
            h.append(f"{g(r26,58)/gj:.1f} targets/juego")
        elif pos == 'QB':
            h.append(f"{g(r26,3)/gj:.0f} yds aéreas + {g(r26,24)/gj:.0f} terrestres/juego")
        elif pos in ('DT', 'DE', 'LB', 'CB', 'S'):
            h.append(f"{(g(r26,108)+g(r26,107))/gj:.1f} tacleadas/juego")
            if g(r26, 99):
                h.append(f"{g(r26,99):.1f} capturas")
        j25 = g(P25.get(pid), 210)
        if j25 and j25 <= 12:
            h.append(f"⚠️ solo {j25:.0f} juegos en 2025")
        notas[p['fullName']] = {
            'hechos': ' · '.join(h),
            'espn': frase_clave(outlook.get(pid, '')),
        }
    json.dump(notas, open(RAIZ / 'data' / 'notas.json', 'w'), ensure_ascii=False)
    return notas


if __name__ == '__main__':
    n = construir()
    print(f"{len(n)} notas -> data/notas.json")
    for k in ('Puka Nacua', 'Bucky Irving', 'Blake Cashman', 'Malik Nabers'):
        if k in n:
            print(f"\n{k}:\n  hechos: {n[k]['hechos']}\n  ESPN: {n[k]['espn'][:130]}")
