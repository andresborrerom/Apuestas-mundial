"""TRIPWIRE de settings de la liga (lección LEMAITRE §III.9, instalado ANTES
del golpe esta vez). El scoring de Peace and Love es una conversión automática
NFL→ESPN sin garantía oficial: el commissioner puede ajustarlo entre hoy y el
draft, y además DEBE cambiar el tamaño 14→16 (D1).

Baja settings frescos, hashea scoring+roster+size y compara contra el snapshot
validado. Si cambió: EXIT 1 → re-dump, re-validar motor, re-calcular baselines.

    python ingest/check_settings.py            # verifica
    python ingest/check_settings.py --accept   # acepta el estado actual
"""
import hashlib, json, sys
from pathlib import Path
import requests
from espn_auth import credenciales

RAIZ = Path(__file__).resolve().parent.parent
SNAP = RAIZ / "config" / "settings_hash.json"

def estado():
    lid, s2, swid = credenciales()
    url = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
           f"/segments/0/leagues/{lid}")
    r = requests.get(url, params={"view": "mSettings"},
                     cookies={"espn_s2": s2, "SWID": swid}, timeout=30)
    r.raise_for_status()
    st = r.json()["settings"]
    scoring = sorted((it["statId"], it.get("points"), tuple(sorted((it.get("pointsOverrides") or {}).items())))
                     for it in st["scoringSettings"]["scoringItems"])
    roster = sorted(st["rosterSettings"]["lineupSlotCounts"].items())
    return {
        "size": st.get("size"),
        "scoring_hash": hashlib.sha256(json.dumps(scoring).encode()).hexdigest()[:16],
        "roster_hash": hashlib.sha256(json.dumps(roster).encode()).hexdigest()[:16],
        "draft_date": (st.get("draftSettings") or {}).get("date"),
    }

def main():
    ahora = estado()
    if "--accept" in sys.argv or not SNAP.exists():
        SNAP.write_text(json.dumps(ahora, indent=2))
        print("✅ snapshot de settings aceptado:", json.dumps(ahora))
        return 0
    antes = json.loads(SNAP.read_text())
    diff = [k for k in ahora if antes.get(k) != ahora.get(k)]
    if diff:
        print(f"🚨 CAMBIARON SETTINGS DE LA LIGA en: {', '.join(diff)}")
        for k in diff:
            print(f"   {k}: {antes.get(k)} -> {ahora.get(k)}")
        print("   NO proyectes: re-dump (espn_dump.py 2026), re-validar motor")
        print("   (candado kona) y re-calcular baselines. Luego --accept.")
        if antes.get("size") != ahora.get("size"):
            print(f"   ⚠️ D1: tamaño {antes.get('size')}→{ahora.get('size')} — si es 16, era lo ESPERADO: baselines nuevos.")
        return 1
    print(f"✅ settings sin cambios (size={ahora['size']}, scoring y roster intactos)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
