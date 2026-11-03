"""CANDADO MASIVO (Fase 1.4): TODOS los jugadores con stats reales 2025 del
universo ESPN de la liga -> reconstruir appliedTotal con el motor y exigir
cuadre al decimal. Guarda el corpus crudo en data/espn_applied_2025.json."""
import os, json, sys, time
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")
from model.scoring import cargar_reglas, puntos

CK = {"espn_s2": os.environ["ESPN_S2"], "SWID": os.environ["ESPN_SWID"]}
URL = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
       f"/segments/0/leagues/{os.environ['ESPN_LEAGUE_ID']}")

def bajar_universo():
    todos = []
    offset = 0
    while True:
        filt = {"players": {"limit": 500, "offset": offset,
                            "sortPercOwned": {"sortAsc": False, "sortPriority": 1}}}
        r = requests.get(URL, params={"view": "kona_player_info"}, cookies=CK,
                         timeout=60, headers={"X-Fantasy-Filter": json.dumps(filt)})
        r.raise_for_status()
        lote = r.json().get("players", [])
        if not lote:
            break
        todos += lote
        offset += 500
        if len(lote) < 500 or offset >= 2000:
            break
        time.sleep(0.3)
    return todos

def main():
    corpus_f = RAIZ / "data" / "espn_applied_2025.json"
    if corpus_f.exists():
        todos = json.load(open(corpus_f))
    else:
        todos = bajar_universo()
        json.dump(todos, open(corpus_f, "w"))
    items = cargar_reglas()
    n_ok = n_bad = n_sin = 0
    fallos = []
    for pw in todos:
        p = pw["player"]
        ent = [s for s in (p.get("stats") or [])
               if s.get("seasonId") == 2025 and s.get("statSourceId") == 0
               and s.get("statSplitTypeId") == 0]
        if not ent or ent[0].get("appliedTotal") is None:
            n_sin += 1
            continue
        e = ent[0]
        calc = puntos(e.get("stats") or {}, p.get("defaultPositionId"), items)
        if abs(calc - e["appliedTotal"]) < 0.02:
            n_ok += 1
        else:
            n_bad += 1
            fallos.append((p["fullName"], p.get("defaultPositionId"),
                           e["appliedTotal"], round(calc, 2)))
    print(f"universo bajado: {len(todos)} jugadores · con stats reales 2025: {n_ok+n_bad}")
    print(f"✅ CUADRAN AL DECIMAL: {n_ok}   ❌ discrepancias: {n_bad}   (sin stats: {n_sin})")
    if fallos:
        print("\nDISCREPANCIAS (nombre, posId, ESPN, motor):")
        for f in sorted(fallos, key=lambda x: -abs(x[2]-x[3]))[:25]:
            print("  ", f)
    return 1 if fallos else 0

if __name__ == "__main__":
    raise SystemExit(main())
