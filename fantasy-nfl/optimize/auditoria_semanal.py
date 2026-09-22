"""AUDITORÍA DEL MODELO — calculado vs ejecutado, los 16 participantes.

Pedido de Andrés (14-sep): "Puntos calculados vs ejecutados de todos los
participantes, no solo para mí". El marcador semanal mide ORDEN (¿quién
rankea mejor?); esto mide MAGNITUD (¿por cuánto nos equivocamos, y hacia
dónde?). Son preguntas distintas y ambas hacen falta.

FUENTE DE AUTORIDAD ✅ = la API de ESPN. Los puntos ejecutados NO se
calculan aquí: se leen del servidor que reparte las consecuencias.

QUÉ COMPARA, por equipo y sobre EL MISMO lineup que el manager alineó:
  ejecutado   ✅ puntos reales (appliedTotal, statSourceId=0)
  calc_espn   📊 proyección semanal de ESPN para ese lineup (statSourceId=1)
  calc_propio 📊 el pg de nuestro modelo (proyeccion_dist.csv) para ese lineup

Y una cuarta columna que no es del modelo sino de la DECISIÓN:
  optimo      ✅ el mejor lineup posible con ese roster y los puntos reales.
              `dejado` = optimo - ejecutado = lo que se quedó en la banca.
              Separa "el modelo falló" de "el manager alineó mal".

CANDADOS (truenan y bloquean la conclusión, no solo avisan):
  1. 16 equipos.
  2. La semana debe estar COMPLETA. Con partidos en curso los puntos suben
     mientras se lee y la auditoría sale basura.
  3. RECONSTRUCCIÓN: la suma de los titulares que yo identifico debe dar
     EXACTAMENTE el marcador oficial del equipo. Si no cuadra celda a celda,
     mi lectura del lineup está mal y NO se opina. Cero discrepancias.
  4. COBERTURA: se reporta a cuántos titulares llega nuestro modelo. Un
     sesgo calculado sobre media plantilla no se presenta como el sesgo.

⚠️ SUPUESTO S-CORRECCIONES: ESPN aplica correcciones de estadística los
martes/miércoles (sobre todo tacleadas IDP, que es donde vive medio nuestro
roster). Una auditoría corrida el lunes puede moverse después.
CADUCIDAD: re-correr el jueves y comparar; si `ejecutado` cambió para algún
equipo, la corrida previa queda marcada como provisional.

    python optimize/auditoria_semanal.py [semana]
"""
import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import requests
from ingest.espn_auth import credenciales

SALIDA = RAIZ / 'data' / 'auditoria_semanal.csv'
TOLERANCIA = 0.02          # margen de redondeo al cuadrar contra el oficial

# slots titulares de esta liga (todo lo demás es banca/IR)
SLOTS_BANCA = {20, 21}
# qué slots puede ocupar cada posición, para calcular el lineup óptimo
ELEGIBLE = {
    0: {'QB'}, 2: {'RB'}, 3: {'RB', 'WR'}, 4: {'WR'}, 6: {'TE'},
    7: {'QB', 'RB', 'WR', 'TE'}, 8: {'DT'}, 9: {'DE'}, 10: {'LB'},
    12: {'CB'}, 13: {'S'}, 16: {'DST'}, 17: {'K'},
}
POS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'DST',
       9: 'DT', 10: 'DE', 11: 'LB', 12: 'CB', 13: 'S'}


def nfl_cerrada(semana):
    """¿Terminaron TODOS los partidos de esa semana de NFL?

    No basta con "los 16 equipos tienen puntos": con el Monday Night en curso
    todos ya anotaron algo y los puntos siguen subiendo mientras se lee. La
    autoridad de si la semana cerró es el calendario de la NFL, no el marcador
    de la liga de fantasy.
    """
    d = requests.get(
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        params={'dates': '2026', 'seasontype': '2', 'week': semana, 'limit': '50'},
        timeout=30).json()
    ev = d.get('events', [])
    abiertos = [e['shortName'] for e in ev
                if e['competitions'][0]['status']['type']['name'] != 'STATUS_FINAL']
    return (not abiertos and len(ev) > 0), len(ev), abiertos


def bajar(semana):
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    return requests.get(u, params={'view': ['mRoster', 'mTeam', 'mMatchupScore'],
                                   'scoringPeriodId': semana},
                        cookies={'espn_s2': s2, 'SWID': swid}, timeout=60).json()


def punto(jug, fuente, semana):
    """appliedTotal semanal. fuente 0 = real, 1 = proyección de ESPN."""
    for s in jug.get('stats', []):
        if (s.get('scoringPeriodId') == semana and s.get('statSourceId') == fuente
                and s.get('statSplitTypeId') == 1 and s.get('seasonId') == 2026):
            return s.get('appliedTotal')
    return None


def oficiales(data, semana):
    """{teamId: puntos} según el marcador oficial de ESPN."""
    out = {}
    for m in data.get('schedule', []):
        if m.get('matchupPeriodId') != semana:
            continue
        for lado in ('away', 'home'):
            e = m.get(lado) or {}
            if e.get('teamId') is not None:
                out[e['teamId']] = (e.get('pointsByScoringPeriod') or {}).get(str(semana))
    return out


def mejor_lineup(plantel):
    """Puntos del mejor lineup posible con ese plantel.

    `plantel` = [(id, puntos_reales, posicion), ...] incluyendo la banca.
    Backtracking sobre los slots ordenados de más restrictivo a menos, con
    poda por cota superior. Los slots son 14 y los candidatos por slot pocos,
    así que la búsqueda es exacta, no heurística.
    """
    slots = []
    for sid, cuantos in ((0, 1), (2, 1), (4, 2), (6, 1), (8, 1), (9, 1), (10, 1),
                         (12, 1), (13, 1), (16, 1), (17, 1), (3, 1), (7, 1)):
        slots += [sid] * cuantos
    slots.sort(key=lambda s: len(ELEGIBLE[s]))       # los rígidos primero
    mejor = [0.0]

    def rec(i, usados, acum):
        if i == len(slots):
            mejor[0] = max(mejor[0], acum)
            return
        libres = sorted((p for k, p, _ in plantel if k not in usados), reverse=True)
        if acum + sum(libres[:len(slots) - i]) <= mejor[0]:
            return                                    # cota superior: podar
        cands = sorted((x for x in plantel
                        if x[0] not in usados and x[2] in ELEGIBLE[slots[i]]),
                       key=lambda x: -x[1])
        if not cands:
            rec(i + 1, usados, acum)                  # slot sin jugador elegible
            return
        for k, p, _ in cands[:6]:                     # top-6 por slot basta
            rec(i + 1, usados | {k}, acum + p)

    rec(0, frozenset(), 0.0)
    return mejor[0]


def auditar(semana):
    data = bajar(semana)
    equipos = {t['id']: t.get('name', f"team {t['id']}").strip() for t in data['teams']}
    marcador = oficiales(data, semana)
    modelo = {}
    for r in csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv')):
        if r.get('espn_id'):
            modelo[int(r['espn_id'])] = float(r['pg'])

    candados, filas = [], []
    candados.append(('16 equipos', len(equipos) == 16, str(len(equipos))))
    cerrada, n_ev, abiertos = nfl_cerrada(semana)
    candados.append(('todos los partidos NFL en FINAL', cerrada,
                     f"{n_ev} partidos" + (f" · EN CURSO: {', '.join(abiertos)}"
                                           if abiertos else '')))
    vivos = [e for e, v in marcador.items() if v in (None, 0)]
    candados.append(('ningún equipo en 0', not vivos,
                     f"{len(vivos)} equipo(s) sin puntos"))

    cubiertos = faltantes = 0
    descuadres = []
    for t in data['teams']:
        tid = t['id']
        real = proy_espn = proy_propio = 0.0
        plantel = []
        for e in t['roster']['entries']:
            p = e['playerPoolEntry']['player']
            pts = punto(p, 0, semana) or 0.0
            pos = POS.get(p.get('defaultPositionId'))
            plantel.append((p['id'], pts, pos))
            if e['lineupSlotId'] in SLOTS_BANCA:
                continue
            real += pts
            proy_espn += punto(p, 1, semana) or 0.0
            pg = modelo.get(p['id'])
            if pg is None:
                faltantes += 1
            else:
                cubiertos += 1
                proy_propio += pg
        of = marcador.get(tid)
        if of is not None and abs(real - of) > TOLERANCIA:
            descuadres.append(f"{equipos[tid]}: reconstruido {real:.2f} vs oficial {of:.2f}")
        opt = mejor_lineup(plantel)
        filas.append({'equipo': equipos[tid], 'ejecutado': round(of if of is not None else real, 2),
                      'calc_espn': round(proy_espn, 2), 'calc_propio': round(proy_propio, 2),
                      'optimo': round(opt, 2), 'dejado': round(opt - real, 2)})

    candados.append(('reconstrucción == marcador oficial', not descuadres,
                     '; '.join(descuadres) or 'cuadra celda a celda'))
    cob = cubiertos / (cubiertos + faltantes) if (cubiertos + faltantes) else 0
    candados.append((f'cobertura del modelo propio', cob >= 0.75,
                     f"{cob:.0%} de los titulares ({faltantes} sin pg)"))
    return filas, candados, cob


def resumen(filas, col):
    """(sesgo medio, error absoluto medio) de una columna vs ejecutado."""
    err = [f[col] - f['ejecutado'] for f in filas if f[col]]
    if not err:
        return None, None
    return sum(err) / len(err), sum(abs(e) for e in err) / len(err)


def main():
    semana = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    filas, candados, cob = auditar(semana)
    print(f"=== CANDADOS (semana {semana}) ===")
    for nom, ok, det in candados:
        print(f"  {'✅' if ok else '🚨'} {nom}: {det}")
    duros = [n for n, ok, _ in candados[:-1] if not ok]   # cobertura es el blando
    if duros:
        print(f"\n🚨 CANDADO EN ROJO ({', '.join(duros)}) — no se concluye nada.")
        return 1

    filas.sort(key=lambda f: -f['ejecutado'])
    print(f"\n=== CALCULADO vs EJECUTADO — los {len(filas)} participantes ===")
    print(f"{'#':>3} {'equipo':28}{'ejecut':>8}{'c.ESPN':>8}{'err':>7}"
          f"{'c.propio':>10}{'err':>7}{'óptimo':>8}{'dejado':>8}")
    for i, f in enumerate(filas, 1):
        print(f"{i:>3} {f['equipo'][:27]:28}{f['ejecutado']:>8.1f}{f['calc_espn']:>8.1f}"
              f"{f['calc_espn'] - f['ejecutado']:>+7.1f}{f['calc_propio']:>10.1f}"
              f"{f['calc_propio'] - f['ejecutado']:>+7.1f}{f['optimo']:>8.1f}{f['dejado']:>8.1f}")

    print(f"\n=== ¿HACIA DÓNDE FALLA CADA MODELO? ===")
    for col, et in (('calc_espn', '📊 ESPN semanal'), ('calc_propio', '📊 nuestro pg')):
        sesgo, mae = resumen(filas, col)
        if sesgo is None:
            continue
        signo = 'OPTIMISTA' if sesgo > 0 else 'PESIMISTA'
        print(f"  {et:18} sesgo {sesgo:+6.1f} ({signo})  ·  error abs. medio {mae:5.1f}")
    dej = sorted(filas, key=lambda f: -f['dejado'])
    print(f"\n=== PUNTOS DEJADOS EN LA BANCA (decisión, no modelo) ===")
    for f in dej[:5]:
        print(f"  {f['equipo'][:28]:29}{f['dejado']:>7.1f}  (alineó {f['ejecutado']:.1f} "
              f"de {f['optimo']:.1f} posibles)")

    with open(SALIDA, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['equipo', 'ejecutado', 'calc_espn',
                                           'calc_propio', 'optimo', 'dejado'])
        w.writeheader()
        w.writerows(filas)
    print(f"\n→ {SALIDA.name}")
    if cob < 0.75:
        print("⚠️ Cobertura del modelo propio por debajo del 75%: su sesgo es "
              "indicativo, no concluyente.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
