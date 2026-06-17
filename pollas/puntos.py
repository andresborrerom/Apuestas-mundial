#!/usr/bin/env python3
"""
TABLERO — baja resultados reales y dice cuántos puntos vamos en cada polla, más
los marcadores que tenemos para los partidos de HOY.

    ODDS_API_KEY=... python pollas/puntos.py            # totales + hoy
    ODDS_API_KEY=... python pollas/puntos.py --hoy 2026-06-13
    ODDS_API_KEY=... python pollas/puntos.py --detalle  # partido por partido
"""
import argparse, csv, json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pollas.LEMAITRE.llenar_excel as LX
from pollas.CSC.reglas import regla_de_ronda

ESP2EN = {sp: en for en, (sp, code) in LX.ESP.items()}
TEAMS_EN = set(LX.ESP)
AQUI = os.path.dirname(os.path.abspath(__file__))


def norm(n):
    n = (n or "").strip()
    if n in TEAMS_EN: return n
    if n in ESP2EN: return ESP2EN[n]
    for sp, en in ESP2EN.items():
        if n.lower() == sp.lower(): return en
    return n


def sgn(d): return (d > 0) - (d < 0)


def cf_pts(pred, real):  # COLFONDOS per-team acumulativo (exacto=10)
    a, b = pred; x, y = real; s = 0
    if sgn(a - b) == sgn(x - y): s += 3
    if (a - b) == (x - y): s += 1
    if a == x: s += 1
    if b == y: s += 1
    if a == x and b == y: s += 4
    return s


def parse_marc(m):
    a, b = m.replace(" ", "").split("-"); return (int(a), int(b))


def bajar_scores(api_key, days=3):
    url = (f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/scores/"
           f"?apiKey={api_key}&daysFrom={days}")
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def fecha_local(iso, tz=-5):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (dt + timedelta(hours=tz)).strftime("%Y-%m-%d")
    except Exception:
        return str(iso)[:10]


def cargar_csc():
    pred = {}
    with open(os.path.join(AQUI, "CSC", "grupos_CSC.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            k = (norm(row["local"]), norm(row["visita"]))
            pred[k] = [parse_marc(row[f"cupo_{i}"]) for i in range(1, 6)]
    return pred


def cargar_colfondos():
    pred = {}
    with open(os.path.join(AQUI, "COLFONDOS", "predicciones.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            k = (norm(row["local"]), norm(row["visita"]))
            pred[k] = (parse_marc(row["plaza1"]), parse_marc(row["plaza2"]))
    return pred


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--mock", default="/tmp/wc_scores.json")
    ap.add_argument("--hoy", default="")
    ap.add_argument("--detalle", action="store_true")
    args = ap.parse_args(argv)
    ev = None
    if args.api_key:
        try:
            ev = bajar_scores(args.api_key)
        except Exception as ex:
            print(f"(aviso: no hay datos en vivo: {ex})")
    if ev is None:
        try:
            with open(args.mock, encoding="utf-8") as f:
                ev = json.load(f)
            print(f"(usando datos en caché: {args.mock})")
        except Exception:
            ev = []
    csc = cargar_csc(); col = cargar_colfondos()
    regla = regla_de_ronda("primera")

    csc_tot = [0, 0, 0, 0, 0]; col_tot = [0, 0]; jugados = 0
    detalle = []
    fechas = set()
    for e in ev:
        h, a = norm(e["home_team"]), norm(e["away_team"])
        fechas.add(fecha_local(e.get("commence_time", "")))
        if not e.get("completed") or not e.get("scores"):
            continue
        sc = {x["name"]: int(x["score"]) for x in e["scores"]}
        real = (sc.get(e["home_team"]), sc.get(e["away_team"]))
        if None in real: continue
        jugados += 1; k = (h, a)
        d = {"match": f"{h} {real[0]}-{real[1]} {a}"}
        if k in csc:
            ps = [regla(p, real) for p in csc[k]]
            for i in range(5): csc_tot[i] += ps[i]
            d["csc"] = ps
        if k in col:
            p1 = cf_pts(col[k][0], real); p2 = cf_pts(col[k][1], real)
            col_tot[0] += p1; col_tot[1] += p2
            d["col"] = (col[k][0], p1, col[k][1], p2)
        detalle.append(d)

    print(f"=== PUNTOS ACUMULADOS ({jugados} partidos jugados) ===")
    print(f"CSC (5 cupos): " + " · ".join(f"c{i+1}={csc_tot[i]}" for i in range(5)) +
          f"   (mejor {max(csc_tot)})")
    print(f"COLFONDOS:     plaza1={col_tot[0]}   plaza2={col_tot[1]}")
    print(f"LEMAITRE:      0   (no puntúa marcadores de grupo; arranca en clasificados/eliminatorias)")

    if args.detalle:
        print("\n--- detalle por partido ---")
        for d in detalle:
            cs = f"CSC {d['csc']}" if "csc" in d else ""
            co = (f"COL P1 {d['col'][0][0]}-{d['col'][0][1]}={d['col'][1]} "
                  f"P2 {d['col'][2][0]}-{d['col'][2][1]}={d['col'][3]}") if "col" in d else ""
            print(f"  {d['match']:34} {cs:22} {co}")

    hoy = args.hoy or (datetime.now(timezone.utc) + timedelta(hours=-5)).strftime("%Y-%m-%d")
    print(f"\n=== MARCADORES QUE TENEMOS PARA HOY ({hoy}) ===")
    hay = False
    for e in ev:
        if fecha_local(e.get("commence_time", "")) != hoy:
            continue
        hay = True
        h, a = norm(e["home_team"]), norm(e["away_team"]); k = (h, a)
        res = ""
        if e.get("completed") and e.get("scores"):
            sc = {x["name"]: x["score"] for x in e["scores"]}
            res = f"  [REAL {sc.get(e['home_team'])}-{sc.get(e['away_team'])}]"
        c = csc.get(k); cf = col.get(k)
        cscs = f"CSC {c[0][0]}-{c[0][1]}" + ("*" if c and len(set(c)) > 1 else "") if c else "CSC -"
        cols = f"COL P1 {cf[0][0]}-{cf[0][1]} / P2 {cf[1][0]}-{cf[1][1]}" if cf else "COL -"
        print(f"  {h[:16]:16} vs {a[:16]:16}  {cscs:10}  {cols}{res}")
    if not hay:
        print(f"  (no hay partidos para {hoy}; fechas con partidos: {', '.join(sorted(fechas)[:6])}...)")
    print("\n* = los 5 cupos de CSC no coinciden en ese partido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
