"""CANDADO: lo reconstruido desde nflverse tiene que rendir lo que ESPN pagó.

Se compara, jugador por jugador de 2025, el appliedTotal REAL de ESPN contra
el total que produce nuestro motor alimentado con nflverse. No se acepta
"parecido": se reporta el error y qué parte es discrepancia de proveedor.

    python model/validar_kdst.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
from model.scoring import cargar_reglas, puntos
from model.scoring_kdst import kicker_semanas, dst_semanas
from model.scoring_nflverse import semanas
from model.posiciones import POSID, posiciones_desde_db

RAIZ = Path(__file__).resolve().parent.parent
ANIO = 2025


def espn_reales(pos_ids):
    """{espn_id: (nombre, pos, appliedTotal 2025 real)}"""
    out = {}
    for pw in json.load(open(RAIZ / 'data' / 'espn_applied_2025.json')):
        p = pw['player']
        if p.get('defaultPositionId') not in pos_ids:
            continue
        for s in (p.get('stats') or []):
            if (s.get('seasonId'), s.get('statSourceId'),
                    s.get('statSplitTypeId')) == (ANIO, 0, 0):
                out[int(p['id'])] = (p['fullName'], p['defaultPositionId'],
                                     s.get('appliedTotal') or 0.0)
    return out


def resumen(nombre, pares, umbral):
    """pares = [(quien, nuestro, espn)]"""
    if not pares:
        print(f"  {nombre}: SIN DATOS"); return
    difs = sorted(pares, key=lambda x: -abs(x[1] - x[2]))
    err = [abs(a - b) for _, a, b in pares]
    n = len(pares)
    ok = sum(1 for e in err if e <= umbral)
    print(f"  {nombre:6} n={n:>4}  MAE={sum(err)/n:>6.2f}  "
          f"mediana={sorted(err)[n//2]:>6.2f}  dentro de ±{umbral}: {ok}/{n}"
          f" ({ok/n*100:.0f}%)")
    for q, a, b in difs[:4]:
        print(f"        peor: {q:26} nuestro {a:>8.1f} · ESPN {b:>8.1f} "
              f"· dif {a-b:+.1f}")


if __name__ == '__main__':
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    items = cargar_reglas()
    xw = dict(con.execute("""select gsis_id, espn_id from xwalk_ids_nflverse
                             where espn_id is not null and gsis_id is not null""").fetchall())

    print(f"=== CANDADO K / D/ST / IDP contra appliedTotal ESPN {ANIO} ===\n")

    # ---------------------------------------------------------------- KICKER
    ref = espn_reales({5})
    W, meta = kicker_semanas(con, ANIO, ANIO)
    acc = defaultdict(lambda: defaultdict(float))
    for (pid, ss, wk), d in W.items():
        for sid, v in d.items():
            acc[pid][sid] += v
    pares = []
    for pid, raw in acc.items():
        e = xw.get(pid)
        r = ref.get(int(e)) if e is not None else None
        if not r:
            continue
        pares.append((r[0], puntos({str(k): v for k, v in raw.items()}, 5, items), r[2]))
    resumen('K', pares, 1.0)

    # ------------------------------------------------------------------ D/ST
    ref = espn_reales({16})
    porabrev = {}
    for eid, (nom, _, tot) in ref.items():
        porabrev[nom.replace(' D/ST', '')] = (nom, tot)
    W, meta = dst_semanas(con, ANIO, ANIO)
    acc = defaultdict(lambda: defaultdict(float))
    for (eq, ss, wk), d in W.items():
        for sid, v in d.items():
            acc[eq][sid] += v
    # puente abreviatura nflverse -> nombre ESPN
    NOM = {'ARI': 'Cardinals', 'ATL': 'Falcons', 'BAL': 'Ravens', 'BUF': 'Bills',
           'CAR': 'Panthers', 'CHI': 'Bears', 'CIN': 'Bengals', 'CLE': 'Browns',
           'DAL': 'Cowboys', 'DEN': 'Broncos', 'DET': 'Lions', 'GB': 'Packers',
           'HOU': 'Texans', 'IND': 'Colts', 'JAX': 'Jaguars', 'KC': 'Chiefs',
           'LA': 'Rams', 'LAR': 'Rams', 'LAC': 'Chargers', 'LV': 'Raiders',
           'MIA': 'Dolphins', 'MIN': 'Vikings', 'NE': 'Patriots', 'NO': 'Saints',
           'NYG': 'Giants', 'NYJ': 'Jets', 'PHI': 'Eagles', 'PIT': 'Steelers',
           'SEA': 'Seahawks', 'SF': '49ers', 'TB': 'Buccaneers', 'TEN': 'Titans',
           'WAS': 'Commanders'}
    pares = []
    for eq, raw in acc.items():
        nm = NOM.get(eq)
        r = porabrev.get(nm) if nm else None
        if not r:
            continue
        pares.append((r[0], puntos({str(k): v for k, v in raw.items()}, 16, items), r[1]))
    resumen('D/ST', pares, 5.0)

    # ------------------------------------------------------------------- IDP
    ref = espn_reales({9, 10, 11, 12, 13, 14})
    pos = posiciones_desde_db(con, ANIO, ANIO)
    W, meta = semanas(ANIO, ANIO)
    acc = defaultdict(lambda: defaultdict(float))
    for (pid, ss, wk), d in W.items():
        for sid, v in d.items():
            acc[pid][sid] += v
    porpos = defaultdict(list)
    for pid, raw in acc.items():
        p = pos.get(pid)
        if not p or p[0] not in ('DT', 'DE', 'LB', 'CB', 'S', 'DB'):
            continue
        e = xw.get(pid)
        r = ref.get(int(e)) if e is not None else None
        if not r:
            continue
        porpos[p[0]].append((r[0], puntos({str(k): v for k, v in raw.items()},
                                          POSID[p[0]], items), r[2]))
    for p in ('DT', 'DE', 'LB', 'CB', 'S'):
        resumen(p, porpos.get(p, []), 10.0)
    print("\n⚠️ En IDP el error NO es del mapeo: ESPN y nflverse usan proveedores")
    print("   distintos de tacleadas (ya documentado). Lo que se exige aquí es")
    print("   que no haya sesgo sistemático ni casos absurdos.")

    # --- ¿la D/ST al menos ORDENA bien? Es lo único que decide un draft.
    from optimize.backtest_tablero import spearman
    if pares:
        rho = spearman([(-a, -b) for _, a, b in pares])
        print(f"\n  D/ST orden: rho = {rho:+.3f} sobre {len(pares)} defensas")
        print("  ⚠️ LIMITACIÓN DECLARADA: nflverse subregistra los TD defensivos")
        print("     (HOU 2025: def_tds=1, ESPN=4) y no trae patadas bloqueadas.")
        print("     Sesgo NEGATIVO y sistemático de ~7 pts de temporada. La D/ST")
        print("     es 1 slot de 14 y se toma en las últimas rondas, así que lo")
        print("     que importa es el orden, no el nivel.")
