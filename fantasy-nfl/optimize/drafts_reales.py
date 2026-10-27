"""Puntúa los DRAFTS REALES de la liga con NUESTRO reglamento.

Es el mejor patrón de comparación que existe para el simulador: decisiones
humanas de verdad, de esta sala, contra las mismas reglas y la misma lógica de
alineación que usa la simulación.

Lo que sí y lo que no:
  ✅ La parte OFENSIVA es comparable: la app vieja también tenía QB/RB/RB/WR/
     WR/TE/OP, prácticamente los mismos 7 slots que el roster v3.
  ❌ La parte defensiva NO: allá eran DL/LB/DB (3 slots) y acá DT/DE/LB/CB/S
     (5). Se excluye de la comparación.
  ⚠️ 2021, 2022 y 2025 se jugaron con 14 equipos; 2023 con 16. La comparación
     se hace contra una simulación del MISMO tamaño.

Unión de nombres: el histórico de NFL.com no trae identificadores, así que se
une por (nombre normalizado, posición). Se reporta la tasa de emparejamiento y
los que quedan fuera — nunca se calla un faltante.
"""
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
SLOTS_OFE = [('QB',), ('RB',), ('WR',), ('WR',), ('TE',), ('RB', 'WR'),
             ('QB', 'RB', 'WR', 'TE')]
SUFIJOS = re.compile(r'\b(jr|sr|ii|iii|iv|v)\b')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
    s = re.sub(r"[.'`-]", '', s.lower())
    s = SUFIJOS.sub('', s)
    return re.sub(r'\s+', ' ', s).strip()


def rosters_reales(año, pos_map, nombres):
    """[(team_id, manager, [(clave,pos)...])] con los picks OFENSIVOS reales.

    nombres: {(nombre_normalizado, pos): [gsis_id...]} construido de la propia
    temporada, así que un homónimo que no jugó ese año no estorba.
    """
    filas = [r for r in csv.DictReader(open(RAIZ / 'data' / 'historia_drafts.csv'))
             if int(r['season']) == año and r['pos'] in ('QB', 'RB', 'WR', 'TE')]
    eq = defaultdict(list)
    sin, amb, tot = [], 0, 0
    for r in filas:
        tot += 1
        c = nombres.get((norm(r['jugador']), r['pos']))
        if not c:
            sin.append(f"{r['jugador']} ({r['pos']})")
            continue
        if len(c) > 1:
            amb += 1
        eq[(r['team_id'], r['equipo'], r['manager'])].append((c[0], r['pos']))
    return eq, dict(total=tot, sin=sin, ambiguos=amb)


def indice_nombres(pts, meta):
    ix = defaultdict(list)
    for k, (nom, pos) in meta.items():
        if pos in ('QB', 'RB', 'WR', 'TE') and k in pts:
            ix[(norm(nom), pos)].append(k)
    # el que más jugó primero: si hay homónimo, gana el titular
    for key in ix:
        ix[key].sort(key=lambda k: -sum(pts[k].values()))
    return ix


def alinear_ofe(jugadores, val):
    disp = sorted(jugadores, key=lambda j: -val.get(j[0], 0))
    usados, tot = set(), 0.0
    for slot in SLOTS_OFE:
        for k, pos in disp:
            if k not in usados and pos in slot:
                usados.add(k); tot += val.get(k, 0); break
    return tot


def puntos_ofensivos(ros, pts, semanas_reg=14):
    tot = 0.0
    for wk in range(1, semanas_reg + 1):
        v = {k: pts.get(k, {}).get(wk, 0.0) for k, pos in ros}
        tot += alinear_ofe(ros, v)
    return tot


if __name__ == '__main__':
    from optimize.liga import cargar_todo
    print('cargando temporadas bajo nuestras reglas...', flush=True)
    con, items, P = cargar_todo(2021, 2025)
    for año in (2021, 2022, 2023, 2025):
        pts, meta = P[año]
        ix = indice_nombres(pts, meta)
        eq, diag = rosters_reales(año, None, ix)
        vals = {}
        for (tid, nom, mgr), ros in eq.items():
            vals[(tid, nom, mgr)] = puntos_ofensivos(ros, pts)
        v = sorted(vals.items(), key=lambda kv: -kv[1])
        print(f"\n=== {año} · {len(eq)} equipos · picks ofensivos emparejados "
              f"{diag['total']-len(diag['sin'])}/{diag['total']} "
              f"({(1-len(diag['sin'])/diag['total'])*100:.0f}%) ===")
        if diag['sin']:
            print(f"    sin emparejar ({len(diag['sin'])}): "
                  f"{', '.join(diag['sin'][:8])}{'...' if len(diag['sin'])>8 else ''}")
        for (tid, nom, mgr), x in v:
            print(f"    {x:>8.0f}  {mgr or '—':16} {nom[:30]}")
        import statistics as st
        xs = [x for x in vals.values()]
        print(f"    media {st.mean(xs):.0f} · máx {max(xs):.0f} · mín {min(xs):.0f}"
              f" · 1º/3º {max(xs)/sorted(xs)[-3]:.3f}")
