"""Autenticación ESPN aislada (prompt §5). Credenciales SOLO en .env.

.env esperado (en fantasy-nfl/.env, jamás en git):
    ESPN_LEAGUE_ID=...
    ESPN_S2=...          # token largo, sin llaves
    ESPN_SWID={...}      # CON llaves

Diagnóstico:  python ingest/espn_auth.py
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def credenciales():
    lid = os.getenv("ESPN_LEAGUE_ID"); s2 = os.getenv("ESPN_S2"); swid = os.getenv("ESPN_SWID")
    faltan = [k for k, v in [("ESPN_LEAGUE_ID", lid), ("ESPN_S2", s2), ("ESPN_SWID", swid)] if not v]
    if faltan:
        raise SystemExit(f"❌ Faltan en .env: {', '.join(faltan)}. Ver instrucciones en docs/CREDENCIALES.md")
    if not swid.startswith("{"):
        swid = "{" + swid.strip("{}") + "}"   # el swid VA con llaves
    return int(lid), s2, swid

def league(year: int):
    from espn_api.football import League
    lid, s2, swid = credenciales()
    return League(league_id=lid, year=year, espn_s2=s2, swid=swid)

def diagnostico():
    lid, s2, swid = credenciales()
    print(f"league_id={lid} · espn_s2={'*'*8}{s2[-6:]} · swid={swid[:6]}...")
    try:
        lg = league(2026)
        print(f"✅ Conexión 2026 OK: '{lg.settings.name}', {len(lg.teams)} equipos")
    except Exception as e:
        print(f"❌ Falla 2026: {type(e).__name__}: {e}")
        print("   Causas típicas: cookies caducas (re-extraer), league_id equivocado,")
        print("   o la temporada 2026 aún no inicializada en ESPN.")
        raise SystemExit(1)

if __name__ == "__main__":
    diagnostico()
