"""CONTEXTO RICO por jugador — pedido de Andrés (31-ago):

  QB → sus receptores principales (con targets proyectados)
  WR → quién es su QB (y cuánto proyecta), su lugar en el orden de targets
       del equipo y quién lo acompaña
  RB → con quiénes comparte el backfield, % de acarreos (¿bellcow o comité?)
       y calidad de la línea ofensiva
  TE → su lugar en el orden de recepción del equipo; TDs de recepción
       proyectados como PROXY de zona roja (⚠️ no tenemos targets RZ — declarado)
  novatos → ronda y pick overall del draft NFL 2026

TODO sale de fuentes verificadas, cero memoria:
  - jerarquías de equipo: la MISMA proyección 2026 de ESPN (crudos archivados
    con hash el 28-ago): targets statId 58, acarreos 23, intentos de pase 0.
  - novatos: crosswalk nflverse (draft_year/round/ovr).
  - línea ofensiva: ranking 2026 traído por agente web (data/oline_2026.json),
    con fuente y fecha adentro.

Produce data/contexto_2026.json: {espn_id: texto}.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb

RAIZ = Path(__file__).resolve().parent.parent
# proTeamId de ESPN -> sigla (verificado: 8=DET Gibbs, 14=LAR Stafford)
EQ = {1: 'ATL', 2: 'BUF', 3: 'CHI', 4: 'CIN', 5: 'CLE', 6: 'DAL', 7: 'DEN',
      8: 'DET', 9: 'GB', 10: 'TEN', 11: 'IND', 12: 'KC', 13: 'LV', 14: 'LAR',
      15: 'MIA', 16: 'MIN', 17: 'NE', 18: 'NO', 19: 'NYG', 20: 'NYJ',
      21: 'PHI', 22: 'ARI', 23: 'PIT', 24: 'LAC', 25: 'SF', 26: 'SEA',
      27: 'TB', 28: 'WAS', 29: 'CAR', 30: 'JAX', 33: 'BAL', 34: 'HOU'}


def apellido(nombre):
    t = [x for x in nombre.split(' ')
         if x not in ('Jr.', 'Sr.', 'II', 'III', 'IV', 'V', 'Jr', 'Sr')]
    return t[-1] if t else nombre


def construir():
    rows = list(csv.DictReader(open(RAIZ / 'data' / 'archivo' / '2026-08-28' /
                                    'espn_proyeccion.csv')))
    for r in rows:
        r['c'] = json.loads(r['crudos'])
        r['tid'] = int(r['pro_team']) if r['pro_team'] else 0
    # novatos 2026
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    novato = {}
    for nm, esp, rd, ovr in con.execute("""
            select name, espn_id, draft_round, draft_ovr from xwalk_ids_nflverse
            where draft_year = 2026 and espn_id is not null
              and draft_ovr is not null""").fetchall():
        novato[int(esp)] = (int(rd) if rd else 0, int(ovr))
    # línea ofensiva (del agente web; puede no existir aún)
    try:
        ol = json.load(open(RAIZ / 'data' / 'oline_2026.json'))
        ol_rank = {k: v['rank'] for k, v in ol['equipos'].items()}
        ol_nota = {k: v['nota'] for k, v in ol['equipos'].items()}
    except Exception:
        ol_rank, ol_nota = {}, {}

    equipo = defaultdict(list)
    for r in rows:
        if r['tid']:
            equipo[r['tid']].append(r)

    def qb1(tid):
        l = [x for x in equipo[tid] if x['pos'] == 'QB']
        return max(l, key=lambda x: x['c'].get('0', 0), default=None)

    def receptores(tid):
        l = [x for x in equipo[tid] if x['pos'] in ('WR', 'TE', 'RB')
             and x['c'].get('58', 0) > 15]
        return sorted(l, key=lambda x: -x['c'].get('58', 0))

    def backfield(tid):
        l = [x for x in equipo[tid] if x['pos'] == 'RB'
             and x['c'].get('23', 0) > 15]
        return sorted(l, key=lambda x: -x['c'].get('23', 0))

    def ol_txt(tid):
        ab = EQ.get(tid, '?')
        if ab in ol_rank:
            return f"OL #{ol_rank[ab]} ({ol_nota.get(ab, '')})"
        return ''

    out = {}
    for r in rows:
        tid, pos, c = r['tid'], r['pos'], r['c']
        if not tid or pos not in ('QB', 'RB', 'WR', 'TE'):
            continue
        ab = EQ.get(tid, '?')
        partes = []
        nv = novato.get(int(r['espn_id']))
        if nv:
            partes.append(f"NOVATO 2026: ronda {nv[0]}, pick {nv[1]} overall")
        if pos == 'QB':
            rec = receptores(tid)[:4]
            armas = ' · '.join(f"{apellido(x['nombre'])} "
                               f"({x['c'].get('58', 0):.0f} tg)" for x in rec)
            partes.append(f"{ab}. Sus armas por targets proyectados: {armas}")
        elif pos in ('WR', 'TE'):
            q = qb1(tid)
            rec = receptores(tid)
            idx = next((i for i, x in enumerate(rec)
                        if x['espn_id'] == r['espn_id']), None)
            if q:
                partes.append(f"Su QB: {q['nombre']} "
                              f"({float(q['proy_nuestras_reglas']):.0f} pts "
                              f"proyectados con nuestras reglas)")
            if idx is not None:
                delante = ', '.join(apellido(x['nombre'])
                                    for x in rec[:idx][:2])
                detras = ', '.join(apellido(x['nombre'])
                                   for x in rec[idx + 1:idx + 3])
                partes.append(
                    f"Opción #{idx + 1} de {ab} por targets "
                    f"({c.get('58', 0):.0f} proy)"
                    + (f", detrás de {delante}" if delante else "")
                    + (f"; le siguen {detras}" if detras else ""))
            if pos == 'TE':
                partes.append(f"TDs de recepción proy: {c.get('43', 0):.1f} "
                              f"(proxy de zona roja — targets RZ no disponibles)")
        elif pos == 'RB':
            bf = backfield(tid)
            tot = sum(x['c'].get('23', 0) for x in bf) or 1
            idx = next((i for i, x in enumerate(bf)
                        if x['espn_id'] == r['espn_id']), None)
            mi = c.get('23', 0)
            share = mi / tot * 100
            otros = ' · '.join(f"{apellido(x['nombre'])} "
                               f"({x['c'].get('23', 0) / tot * 100:.0f}%)"
                               for x in bf if x['espn_id'] != r['espn_id'])[:80]
            perfil = ('BELLCOW' if share >= 62 else
                      'comité en punta' if share >= 45 else 'comité')
            partes.append(f"{ab}: {perfil} — {share:.0f}% de los acarreos "
                          f"proyectados ({mi:.0f}); comparte con {otros or 'nadie relevante'}")
            partes.append(f"{c.get('58', 0):.0f} targets proy (valor PPR)")
        o = ol_txt(tid)
        if o:
            partes.append(o)
        out[int(r['espn_id'])] = '. '.join(partes)
    json.dump(out, open(RAIZ / 'data' / 'contexto_2026.json', 'w'),
              ensure_ascii=False)
    return out


if __name__ == '__main__':
    out = construir()
    print(f'{len(out)} contextos generados')
    import csv as _csv
    dist = list(_csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv')))
    for n in ('Matthew Stafford', 'Puka Nacua', 'Jahmyr Gibbs', 'Brock Bowers',
              "Jeremiyah Love"):
        r = next((x for x in dist if x['nombre'] == n), None)
        if r:
            print(f"\n{n}:\n  {out.get(int(r['espn_id']), '—')}")
