"""ARCHIVO PROPIO de proyecciones y mercado — con fecha y hash.

Motivo (28-ago-2026): NO existe ningún archivo público, gratuito y auditable
de proyecciones históricas de pretemporada. Todo el análisis de precisión que
circula es auto-reportado por vendedores que no liberan los datos crudos.
Cada temporada que pasa sin archivar es historial que no se recupera.

Guarda, por fecha, un snapshot inmutable de:
  1. ESPN — proyección de stats CRUDAS + puntos bajo NUESTRAS reglas,
     ranking SUPERFLEX/STANDARD/PPR y ADP.                (fuente primaria)
  2. FantasyPros — ECR superflex redraft (vía DynastyProcess).
  3. Fantasy Football Calculator — ADP de mercado 2QB.

Cada archivo va con sha256 en el manifiesto. Dos años de esto nos dan el
track record que nadie publica — y el candado para saber a quién creerle.

    python ingest/archivo.py            # snapshot de hoy
    python ingest/archivo.py --listar   # qué hay archivado
"""
import argparse, csv, hashlib, io, json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import requests
from model.scoring import cargar_reglas, puntos

RAIZ = Path(__file__).resolve().parent.parent
ARCH = RAIZ / 'data' / 'archivo'
POS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 9: 'DT', 10: 'DE', 11: 'LB',
       12: 'CB', 13: 'S', 14: 'DB', 16: 'DST'}
FFC = 'https://fantasyfootballcalculator.com/api/v1/adp/2qb'
ECR = 'https://raw.githubusercontent.com/dynastyprocess/data/master/files/db_fpecr.parquet'


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def espn(dest, temporada):
    """Proyección ESPN + nuestros puntos + rankings + ADP."""
    corpus = RAIZ / 'data' / f'espn_applied_{temporada - 1}.json'
    if not corpus.exists():
        corpus = RAIZ / 'data' / 'espn_applied_2025.json'
    items = cargar_reglas()
    todos = json.load(open(corpus))
    filas = []
    for pw in todos:
        p = pw['player']
        pos = POS.get(p.get('defaultPositionId'))
        if not pos:
            continue
        ent = [s for s in (p.get('stats') or [])
               if (s.get('seasonId'), s.get('statSourceId'), s.get('statSplitTypeId'))
               == (temporada, 1, 0)]
        if not ent:
            continue
        raw = ent[0].get('stats') or {}
        dr = p.get('draftRanksByRankType') or {}
        o = p.get('ownership') or {}
        filas.append({
            'espn_id': p['id'], 'nombre': p['fullName'], 'pos': pos,
            'pro_team': p.get('proTeamId'),
            'proy_espn_pts': round(ent[0].get('appliedTotal') or 0, 2),
            'proy_nuestras_reglas': round(puntos(raw, p.get('defaultPositionId'), items), 2),
            'juegos_proy': raw.get('210'),
            'rank_superflex': dr.get('SUPERFLEX', {}).get('rank'),
            'rank_standard': dr.get('STANDARD', {}).get('rank'),
            'rank_ppr': dr.get('PPR', {}).get('rank'),
            'adp_espn': o.get('averageDraftPosition'),
            'pct_owned': o.get('percentOwned'),
            'crudos': json.dumps({k: v for k, v in raw.items() if v}, separators=(',', ':')),
        })
    f = dest / 'espn_proyeccion.csv'
    with open(f, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    return f, len(filas), f'corpus local {corpus.name} (kona_player_info)'


def fantasypros(dest, temporada):
    """ECR superflex redraft — último snapshot disponible."""
    import duckdb
    tmp = dest / '_ecr.parquet'
    r = requests.get(ECR, timeout=300)
    r.raise_for_status()
    tmp.write_bytes(r.content)
    con = duckdb.connect()
    q = con.execute(f"""
        select player, pos, team, ecr, sd, best, worst, scrape_date
        from read_parquet('{tmp}')
        where fp_page='/nfl/rankings/ppr-superflex-cheatsheets.php'
          and year(cast(scrape_date as date)) = {temporada}
        order by cast(scrape_date as date) desc, ecr
    """).fetchall()
    f = dest / 'fantasypros_superflex_ecr.csv'
    with open(f, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['player', 'pos', 'team', 'ecr', 'sd', 'best', 'worst', 'scrape_date'])
        w.writerows(q)
    tmp.unlink()
    ult = q[0][7] if q else None
    return f, len(q), f'{ECR} (snapshot más reciente {ult})'


def ffc(dest, temporada):
    """ADP de mercado 2QB (proxy declarado de superflex)."""
    r = requests.get(FFC, params={'teams': 12, 'year': temporada, 'position': 'all'},
                     timeout=60)
    r.raise_for_status()
    d = r.json()
    ps = d.get('players', [])
    f = dest / 'ffc_2qb_adp.csv'
    campos = ['adp', 'name', 'position', 'team', 'times_drafted', 'stdev', 'high', 'low', 'bye']
    with open(f, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction='ignore')
        w.writeheader(); w.writerows(ps)
    m = d.get('meta', {})
    return f, len(ps), (f"{FFC}?year={temporada} · {m.get('total_drafts')} drafts"
                        f" · ventana {m.get('start_date')}..{m.get('end_date')}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--temporada', type=int, default=2026)
    ap.add_argument('--listar', action='store_true')
    a = ap.parse_args()
    if a.listar:
        for d in sorted(ARCH.glob('*/manifiesto.json')):
            m = json.load(open(d))
            print(f"\n{d.parent.name}  (temporada {m['temporada']})")
            for f in m['archivos']:
                print(f"   {f['archivo']:34} {f['filas']:>6} filas  sha {f['sha256']}")
        sys.exit(0)
    hoy = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    dest = ARCH / hoy
    dest.mkdir(parents=True, exist_ok=True)
    man = {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'temporada': a.temporada,
           'archivos': []}
    for nombre, fn in (('ESPN', espn), ('FantasyPros', fantasypros), ('FFC', ffc)):
        try:
            f, n, fuente = fn(dest, a.temporada)
            man['archivos'].append({'origen': nombre, 'archivo': f.name, 'filas': n,
                                    'sha256': sha(f), 'fuente': fuente})
            print(f"  ✓ {nombre:12} {n:>5} filas · sha {sha(f)}")
        except Exception as e:
            print(f"  ✗ {nombre:12} FALLÓ: {type(e).__name__}: {e}")
            man['archivos'].append({'origen': nombre, 'error': f'{type(e).__name__}: {e}'})
    json.dump(man, open(dest / 'manifiesto.json', 'w'), ensure_ascii=False, indent=1)
    print(f"\narchivado en data/archivo/{hoy}/")
