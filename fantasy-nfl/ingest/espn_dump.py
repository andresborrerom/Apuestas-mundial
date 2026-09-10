"""TAREA 0: volcado COMPLETO de settings+scoring, crudo desde la API (la fuente),
para 2025 Y 2026 (pendiente P8: ¿cambió el scoring entre años?).

- Baja el JSON crudo (view=mSettings) → config/espn_settings_{year}.json  [VERSIONADO]
- Cruza scoringItems con el mapa comunitario de statIds y responde P1-P9.
- El mapa comunitario es una LENTE, no la fuente: la validación final es el
  candado de Fase 1.4 (recalcular 2025 al decimal contra box scores).

Uso:  python ingest/espn_dump.py [2025] [2026]
"""
import json, sys
from pathlib import Path
import requests
from espn_auth import credenciales
from espn_api.football.constant import SETTINGS_SCORING_FORMAT_MAP as SMAP, POSITION_MAP

RAIZ = Path(__file__).resolve().parent.parent
SLOTS = {0:"QB",1:"TQB",2:"RB",3:"RB/WR",4:"WR",5:"WR/TE",6:"TE",7:"OP",8:"DT",9:"DE",
         10:"LB",11:"DL",12:"CB",13:"S",14:"DB",15:"DP",16:"D/ST",17:"K",18:"P",
         19:"HC",20:"BE",21:"IR",22:"?",23:"FLEX",24:"EDR",25:"Rookie"}

def dump(year: int):
    lid, s2, swid = credenciales()
    url = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}"
           f"/segments/0/leagues/{lid}")
    r = requests.get(url, params={"view": ["mSettings", "mTeam"]},
                     cookies={"espn_s2": s2, "SWID": swid}, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = RAIZ / "config" / f"espn_settings_{year}.json"
    out.write_text(json.dumps(data, indent=2))
    print(f"\n===== {year}: crudo guardado en {out.relative_to(RAIZ)} =====")
    st = data["settings"]
    print(f"Liga: {st['name']}")
    # --- scoring items ---
    items = st["scoringSettings"]["scoringItems"]
    print(f"scoringItems: {len(items)}")
    rows = []
    for it in items:
        sid = it["statId"]; pts = it.get("points", 0)
        po = it.get("pointsOverrides") or {}
        eff = po.get("16", pts)   # override por posición si existe
        label = SMAP.get(sid, {}).get("label", f"?? statId {sid} SIN MAPEO")
        rows.append((sid, label, pts, po))
    for sid, label, pts, po in sorted(rows):
        extra = f"  overrides={po}" if po else ""
        print(f"  [{sid:>3}] {label:<38} {pts:+g}{extra}")
    # --- respuestas P1-P9 ---
    ids = {r[0]: r[2] for r in rows}
    print("\n--- PENDIENTES DE FUENTE ---")
    print(f"P1 sack IDP (statId 99 'Each Sack'): {ids.get(99, 'AUSENTE')}  · 1/2 sack (100): {ids.get(100,'AUSENTE')}")
    print(f"P2 INT IDP (95 'Each Interception'): {ids.get(95, 'AUSENTE')}")
    print(f"P3 passing: yds(3)={ids.get(3,'AUSENTE')} TD(4)={ids.get(4,'AUSENTE')} "
          f"INT(20)={ids.get(20,'AUSENTE')} 300-399(101/…)={ids.get(101,'—')} 400+(102/…)={ids.get(102,'—')}")
    print(f"P5 D/ST yds permitidas (129-136): {[ids[i] for i in range(129,137) if i in ids] or 'AUSENTES'}")
    print(f"   D/ST pts permitidos (89-92 etc): {[i for i in range(89,93) if i in ids] or 'AUSENTES'}")
    print(f"P6 FG 50+ (74)={ids.get(74,'—')} · 50-59(198)={ids.get(198,'—')} · 60+(201)={ids.get(201,'—')}")
    # --- roster ---
    rs = st["rosterSettings"]["lineupSlotCounts"]
    print("\nP7/P9 slots:")
    for slot_id, n in sorted(rs.items(), key=lambda kv: int(kv[0])):
        if n: print(f"  {SLOTS.get(int(slot_id), slot_id):<6} × {n}")
    print(f"\nAcumulación de bonos (P4): NO responde el dump — se resuelve empíricamente")
    print(f"contra un box score real con juego de 200+ yardas (candado Fase 1.4).")
    return data

if __name__ == "__main__":
    years = [int(a) for a in sys.argv[1:]] or [2025, 2026]
    for y in years:
        dump(y)
