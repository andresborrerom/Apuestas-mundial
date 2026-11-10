"""Refresca data/injury_vivo.json desde kona_player_info (estado de lesión
EN VIVO de ESPN, el mismo campo que muestra la app). Pieza del robot de
noticias del 7-sep: correr ANTES de calibrar el pool."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from ingest.espn_auth import credenciales

RAIZ = Path(__file__).resolve().parent.parent


def refrescar():
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}?view=kona_player_info")
    filtro = {"players": {"limit": 3000,
                          "sortPercOwned": {"sortAsc": False, "sortPriority": 1}}}
    r = requests.get(u, headers={'x-fantasy-filter': json.dumps(filtro)},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=60)
    r.raise_for_status()
    out = {}
    for pw in r.json().get('players', []):
        p = pw.get('player') or {}
        st = p.get('injuryStatus')
        if p.get('id'):
            out[str(p['id'])] = {'inj': st, 'activo': p.get('active', True)}
    json.dump(out, open(RAIZ / 'data' / 'injury_vivo.json', 'w'))
    return out


if __name__ == '__main__':
    d = refrescar()
    from collections import Counter
    print(len(d), 'estados ·', dict(Counter(v['inj'] for v in d.values() if v['inj'] and v['inj'] != 'ACTIVE')))
