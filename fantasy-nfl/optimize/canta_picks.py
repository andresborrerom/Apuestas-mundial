"""CANTA-PICKS — sigue CUALQUIER liga ESPN de la cuenta y canta cada pick
con su lag. Es la prueba de punta a punta del canal en vivo (28-ago) y la
herramienta de respaldo del 7-sep.

    python optimize/canta_picks.py --liga 1234567890
    python optimize/canta_picks.py --buscar   # lista las ligas de la cuenta

Mide lo que nunca hemos podido medir: ¿los picks aparecen en mDraftDetail
MIENTRAS el draft corre, y con cuántos segundos de retraso?
"""
import argparse
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from ingest.espn_auth import credenciales

RAIZ = Path(__file__).resolve().parent.parent


def sesion():
    lid, s2, swid = credenciales()
    return s2, swid


def ligas_de_la_cuenta():
    s2, swid = sesion()
    r = requests.get(f"https://fan.api.espn.com/apis/v2/fans/{swid}",
                     params={'platform': 'web', 'source': 'espncom-fantasy'},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=30)
    r.raise_for_status()
    out = []
    for p in r.json().get('preferences', []):
        meta = (p.get('metaData') or {}).get('entry') or {}
        for g in meta.get('groups') or []:
            if meta.get('abbrev') == 'FFL':
                out.append((g.get('groupId'), g.get('groupName'),
                            meta.get('entryMetadata', {}).get('teamName')))
    return out


def leer(liga, s2, swid):
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{liga}")
    r = requests.get(u, params={'view': ['mDraftDetail', 'mTeam']},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=15)
    r.raise_for_status()
    d = r.json()
    eq = {t['id']: t.get('name', f"team {t['id']}") for t in d.get('teams', [])}
    dd = d.get('draftDetail', {})
    picks = [(p['overallPickNumber'], p['teamId'], p.get('playerId'))
             for p in dd.get('picks', []) if (p.get('playerId') or 0) > 0]
    return sorted(picks), dd.get('drafted'), dd.get('inProgress'), eq


def nombres_jugadores():
    nom = {}
    try:
        for pw in json.load(open(RAIZ / 'data' / 'espn_applied_2025.json')):
            p = pw['player']
            nom[p['id']] = p['fullName']
    except Exception:
        pass
    return nom


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--liga', type=int)
    ap.add_argument('--buscar', action='store_true')
    ap.add_argument('--intervalo', type=float, default=2.0)
    a = ap.parse_args()
    s2, swid = sesion()
    if a.buscar or not a.liga:
        for gid, gnom, tnom in ligas_de_la_cuenta():
            print(f"  liga {gid}  {gnom}  (mi equipo: {tnom})")
        sys.exit(0)
    nom = nombres_jugadores()
    vistos = set()
    lags = []
    print(f"siguiendo liga {a.liga} cada {a.intervalo}s — ctrl+C para parar")
    ultimo_cambio = time.time()
    while True:
        try:
            picks, drafted, en_curso, eq = leer(a.liga, s2, swid)
        except Exception as e:
            print(f"  API: {type(e).__name__}: {e}")
            time.sleep(a.intervalo)
            continue
        nuevos = [p for p in picks if p[0] not in vistos]
        ahora = time.time()
        for gp, tid, pid in nuevos:
            vistos.add(gp)
            lag = ahora - ultimo_cambio
            print(f"  {time.strftime('%H:%M:%S')}  pick {gp:>3}  "
                  f"{nom.get(pid, f'id {pid}'):28} → {eq.get(tid, tid)}"
                  f"   (visto +{lag:.1f}s tras el anterior)")
        if nuevos:
            ultimo_cambio = ahora
        if drafted:
            print(f"\nDRAFT CERRADO · {len(vistos)} picks vistos en vivo ✅")
            break
        time.sleep(a.intervalo)
