"""CANDADO del recibo del draft (10-sep).

Historia: el filtro de picks reales usaba `playerId > 0` para descartar el
placeholder de la grilla pre-publicada. Pero las D/ST de ESPN tienen ID
NEGATIVO (-16034 Texans, -16007 Broncos...) mientras que los K son
positivos → el recibo del draft del 7-sep perdió las 16 defensas y el
ranking de equipos salió con TODOS los rosters incompletos.

El placeholder es exactamente -1. Este test fija esa distinción.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def filtrar(picks):
    """La misma expresión que usa live_draft.api_picks()."""
    return [(p['overallPickNumber'], p['teamId'], p['playerId'])
            for p in picks if p.get('playerId') not in (None, 0, -1)]


def test_placeholder_fuera_dst_dentro():
    picks = [
        {'overallPickNumber': 1, 'teamId': 10, 'playerId': 3139477},   # QB
        {'overallPickNumber': 2, 'teamId': 3, 'playerId': -16034},     # Texans D/ST
        {'overallPickNumber': 3, 'teamId': 7, 'playerId': 3953687},    # K
        {'overallPickNumber': 4, 'teamId': 1, 'playerId': -1},         # placeholder
        {'overallPickNumber': 5, 'teamId': 2, 'playerId': None},       # sin pick
    ]
    out = filtrar(picks)
    assert [p[0] for p in out] == [1, 2, 3], 'la D/ST debe entrar, el -1 no'
    assert -16034 in [p[2] for p in out], 'D/ST con ID negativo perdida'


def test_corpus_real_dst_negativas_k_positivas():
    """Contra el corpus archivado: la premisa del filtro debe seguir viva."""
    import gzip
    f = RAIZ / 'data' / 'espn_applied_2025.json.gz'
    if not f.exists():
        return
    todos = json.load(gzip.open(f, 'rt'))
    dst = [p['player']['id'] for p in todos
           if p['player'].get('defaultPositionId') == 16]
    ks = [p['player']['id'] for p in todos
          if p['player'].get('defaultPositionId') == 5]
    assert dst and all(i < 0 for i in dst), 'las D/ST dejaron de ser negativas'
    assert ks and all(i > 0 for i in ks), 'los K dejaron de ser positivos'
    assert -1 not in dst, 'ninguna D/ST puede colisionar con el placeholder'
