"""Hoja de draft imprimible: tiers por posición + tablero global.

Lee data/proyeccion_dist.csv (VBD2 + conos calibrados) y escribe
docs/HOJA_DRAFT.md — el artefacto que se usa EN VIVO el 7-sep.

Los tiers salen de barrancos medidos (caída > max(8 pts, 10%) entre
consecutivos), no de intuición.
"""
import csv
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORDEN_POS = ['QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'K', 'DST']


def tiers(lst):
    out, t, prev = [], 1, None
    for r in lst:
        v = r['vbd']
        if prev is not None and (prev - v) > max(8, 0.10 * max(prev, 1)):
            t += 1
        out.append((t, r))
        prev = v
    return out


def main():
    rows = list(csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv')))
    por = defaultdict(list)
    for r in rows:
        d = dict(nombre=r['nombre'], pos=r['pos'], vbd=float(r['vbd2']),
                 p10=float(r['p10']), p50=float(r['p50']), p90=float(r['p90']),
                 eg=float(r['eg']), edad=r['edad'])
        por[d['pos']].append(d)
    for v in por.values():
        v.sort(key=lambda d: -d['vbd'])
    L = ['# HOJA DE DRAFT — Peace and Love 2026 (pick 5, snake, 18 rondas)',
         '',
         'VBD = puntos por encima del titular más flojo de la liga bajo NUESTRAS',
         'reglas (motor validado 1801/1801). Piso/techo = p10/p90 de conos',
         'calibrados (cobertura real 80.3%). E[j] = juegos esperados (el mercado',
         'proyecta 17 a todos; la historia dice otra cosa).',
         '',
         '## Tablero global — orden de prioridad',
         '',
         '| # | jugador | pos | VBD | piso | techo | E[j] |',
         '|--:|---|---|--:|--:|--:|--:|']
    glob = sorted((d for v in por.values() for d in v), key=lambda d: -d['vbd'])
    for i, d in enumerate(glob[:60], 1):
        L.append(f"| {i} | {d['nombre']} | {d['pos']} | {d['vbd']:.0f} | "
                 f"{d['p10']:.0f} | {d['p90']:.0f} | {d['eg']:.1f} |")
    L += ['', '## Tiers por posición (el barranco es dónde NO puedes esperar)', '']
    for pos in ORDEN_POS:
        lst = por.get(pos, [])[:16]
        if not lst:
            continue
        L.append(f'### {pos}')
        L.append('')
        actual = None
        for t, d in tiers(lst):
            if t != actual:
                L.append(f'**Tier {t}**')
                actual = t
            L.append(f"- {d['nombre']} · vbd {d['vbd']:.0f} · piso {d['p10']:.0f}"
                     f" / techo {d['p90']:.0f}")
        L.append('')
    (RAIZ / 'docs' / 'HOJA_DRAFT.md').write_text('\n'.join(L))
    print(f"docs/HOJA_DRAFT.md — {len(glob)} jugadores, top-60 + tiers de {len(ORDEN_POS)} posiciones")


if __name__ == '__main__':
    main()
