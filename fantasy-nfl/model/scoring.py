"""Motor de scoring parametrizado (fórmula VALIDADA 4/4 al decimal, 10-ago):
    appliedTotal = Σ_items  raw[statId] × puntos_efectivos(item, posId)
donde puntos_efectivos usa pointsOverrides[posId] si existe, si no points.
Las reglas se cargan SIEMPRE del dump crudo versionado (la fuente)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

def cargar_reglas(ruleset="espn_settings_2026"):
    cfg = json.load(open(RAIZ / "config" / f"{ruleset}.json"))
    return cfg["settings"]["scoringSettings"]["scoringItems"]

def puntos(raw: dict, pos_id: int, items) -> float:
    """raw: {statId(str|int): valor}. pos_id: defaultPositionId del jugador."""
    pid = str(pos_id)
    total = 0.0
    for it in items:
        sid = it["statId"]
        v = raw.get(sid, raw.get(str(sid)))
        if not v:
            continue
        pts = (it.get("pointsOverrides") or {}).get(pid, it.get("points", 0))
        total += v * pts
    return total

def desglose(raw: dict, pos_id: int, items):
    pid = str(pos_id)
    out = []
    for it in items:
        sid = it["statId"]
        v = raw.get(sid, raw.get(str(sid)))
        if not v:
            continue
        pts = (it.get("pointsOverrides") or {}).get(pid, it.get("points", 0))
        if pts:
            out.append((sid, v, pts, v * pts))
    return sorted(out, key=lambda x: -abs(x[3]))
