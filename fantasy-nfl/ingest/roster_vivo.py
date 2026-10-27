"""Roster ACTUAL de un equipo, leído de la API de ESPN (fuente de autoridad).

Existe porque el 27-oct se reportó el estado de lesiones de 'tu roster' leyendo
data/rosters_2026_postdraft.csv, que es el roster del 7-sep: se listaron
jugadores que Andrés no tenía hacía semanas. Todo lo que hable del roster HOY
debe pasar por aquí.

    python ingest/roster_vivo.py [team_id]      (default 10 = The Replacements)
"""
import sys
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ingest.espn_auth import credenciales

SLOT = {0: 'QB', 2: 'RB', 3: 'RB/WR', 4: 'WR', 6: 'TE', 7: 'OP', 8: 'DT', 9: 'DE',
        10: 'LB', 12: 'CB', 13: 'S', 16: 'DST', 17: 'K', 20: 'BANCA', 21: 'IR'}
POS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 9: 'DT', 10: 'DE', 11: 'LB',
       12: 'CB', 13: 'S', 16: 'DST'}


def roster(team_id=10, año=2026):
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{año}"
         f"/segments/0/leagues/{lid}")
    d = requests.get(u, params={'view': ['mRoster', 'mTeam', 'mSettings']},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=60).json()
    t = next(x for x in d['teams'] if x['id'] == team_id)
    filas = []
    for e in t['roster']['entries']:
        p = e['playerPoolEntry']['player']
        filas.append(dict(id=p['id'], nombre=p['fullName'],
                          pos=POS.get(p['defaultPositionId'], '?'),
                          slot=SLOT.get(e['lineupSlotId'], str(e['lineupSlotId'])),
                          lesion=p.get('injuryStatus')))
    cupos = {SLOT.get(int(k), k): v for k, v in
             d['settings']['rosterSettings']['lineupSlotCounts'].items() if v}
    return t.get('name', '').strip(), filas, cupos


def main():
    tid = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    nombre, filas, cupos = roster(tid)
    print(f"{nombre} (team_id {tid}) — {len(filas)} jugadores")
    for f in sorted(filas, key=lambda f: list(SLOT.values()).index(f['slot']) if f['slot'] in SLOT.values() else 99):
        print(f"  {f['slot']:6}{f['nombre']:26}{f['pos']:4}{f['lesion'] or '-'}")
    vacios = [s for s, n in cupos.items() if s not in ('BANCA', 'IR')
              and sum(1 for f in filas if f['slot'] == s) < n]
    if vacios:
        print(f"🚨 slots titulares VACÍOS: {', '.join(vacios)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
