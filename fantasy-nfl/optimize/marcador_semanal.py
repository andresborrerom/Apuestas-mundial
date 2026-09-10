"""MARCADOR SEMANAL — ¿quién predice mejor ESTA liga: nosotros o FantasyPros?

Nace de un desacuerdo real (10-sep): nuestro modelo pone a Andrés entre #1 y
#5; FantasyPros le da 37% de playoffs (#10 de 16). No se resuelve discutiendo
modelos: se resuelve midiendo contra los puntos que de verdad se anotan.

FUENTE DE AUTORIDAD ✅ = la API de ESPN (view mMatchupScore), que es la que
reparte las consecuencias. Los puntos NO se estiman: se leen del servidor.

QUÉ COMPARA (cada predictor ordena a los 16 equipos; se mide qué tan bien ese
orden anticipa los puntos REALES acumulados, con correlación de rangos):
  📊 vbd            — VBD del titular (la métrica de decisión del draft)
  📊 temporada      — puntos de temporada del titular, escenario central
                      (fusiona roles compartidos; ver ranking_temporada.py)
  🔍 fp_ros         — ranking ROS de FantasyPros (snapshot 10-sep)
  🔍 fp_odds        — sus playoff odds (snapshot 10-sep)

CANDADOS (truenan y bloquean la conclusión, no solo avisan):
  1. 16 equipos y 14 jornadas de 8 partidos en el calendario.
  2. Una semana entra al análisis SOLO si los 16 equipos ya jugaron. Una
     semana a medias (jueves jugado, domingo no) produce correlaciones
     basura: se marca PARCIAL y se excluye.
  3. Los snapshots de FantasyPros no cubren los 16 equipos (varios ilegibles
     en las fotos). La correlación se calcula sobre la intersección y se
     reporta cuántos equipos entraron — nunca se rellenan huecos.

⚠️ SUPUESTO S-MARCADOR: comparar ORDEN de equipos supone que ambos modelos
intentan predecir lo mismo (fuerza para anotar puntos). Los playoff odds de
FantasyPros además incluyen calendario y azar, así que ordenar por ellos
mezcla dos cosas; por eso se reportan fp_ros y fp_odds por separado.
CADUCIDAD: con 4+ semanas completas la señal empieza a ser interpretable;
antes de eso el ruido semanal domina y NO se debe concluir nada.

    python optimize/marcador_semanal.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import requests
from ingest.espn_auth import credenciales

HISTORIAL = RAIZ / 'data' / 'marcador_semanal.csv'
MIN_SEMANAS = 4          # antes de esto no se concluye (ver caducidad)


def puntos_reales():
    """{semana: {equipo: puntos}} desde la API + nombres + candados."""
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    d = requests.get(u, params={'view': ['mMatchupScore', 'mTeam']},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=30).json()
    equipos = {t['id']: t.get('name', f'team {t["id"]}').strip() for t in d['teams']}
    semanas = defaultdict(dict)
    jornadas = defaultdict(int)
    for m in d['schedule']:
        sem = m.get('matchupPeriodId')
        jornadas[sem] += 1
        for lado in ('away', 'home'):
            e = m.get(lado) or {}
            tid = e.get('teamId')
            if tid is None:
                continue
            pts = (e.get('pointsByScoringPeriod') or {}).get(str(sem))
            semanas[sem][equipos[tid]] = pts
    candados = []
    candados.append(('16 equipos en la liga', len(equipos) == 16, f'{len(equipos)}'))
    ok_cal = all(v == 8 for v in jornadas.values()) and len(jornadas) == 14
    candados.append(('14 jornadas × 8 partidos', ok_cal,
                     f'{len(jornadas)} jornadas'))
    return semanas, equipos, candados, d.get('status', {})


def completa(marcador):
    """Una semana cuenta solo si los 16 equipos ya anotaron algo."""
    vals = [v for v in marcador.values() if v is not None]
    return len(vals) == 16 and all(v > 0 for v in vals)


def rangos(d):
    """Convierte {clave: valor} en rangos (1 = el mayor)."""
    orden = sorted(d, key=lambda k: -d[k])
    return {k: i + 1 for i, k in enumerate(orden)}


def spearman(a, b):
    """Correlación de rangos sobre las claves comunes. Devuelve (rho, n)."""
    comunes = sorted(set(a) & set(b))
    if len(comunes) < 3:
        return None, len(comunes)
    ra, rb = rangos({k: a[k] for k in comunes}), rangos({k: b[k] for k in comunes})
    xs = [ra[k] for k in comunes]
    ys = [rb[k] for k in comunes]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** .5
    return (num / den if den else None), len(comunes)


def predictores():
    """Los cuatro órdenes a evaluar. Mayor = mejor equipo, en los cuatro."""
    from optimize.ranking_temporada import cargar, alinear, fusionar
    from optimize.sala import valor_roster
    rosters, equipos = cargar()
    proy = {x['nombre']: x for x in
            csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv'))}
    temporada, vbd = {}, {}
    for t, jug in rosters.items():
        fus, _ = fusionar([dict(j) for j in jug], 'central')
        temporada[equipos[t]] = alinear(fus)
        ros = {j['nombre']: dict(nombre=j['nombre'], pos=j['pos'],
                                 vbd=float(proy[j['nombre']]['vbd2']))
               for j in jug if j['nombre'] in proy}
        vbd[equipos[t]] = valor_roster(ros, 'vbd')
    fp = json.load(open(RAIZ / 'data' / 'fantasypros_snapshot.json'))
    ros_fp = {k: v['score'] for k, v in
              fp['pantalla_rankings_ros']['equipos'].items() if v.get('score')}
    odds = {k: v['playoff_odds'] for k, v in
            fp['pantalla_league_analyzer']['equipos'].items()
            if v.get('playoff_odds')}
    return {'📊 vbd': vbd, '📊 temporada': temporada,
            '🔍 fp_ros': ros_fp, '🔍 fp_odds': odds}, fp['fecha']


def main():
    semanas, equipos, candados, status = puntos_reales()
    print('=== CANDADOS ===')
    for nom, ok, det in candados:
        print(f"  {'✅' if ok else '🚨'} {nom}: {det}")
    if not all(ok for _, ok, _ in candados):
        print('\n🚨 CANDADO EN ROJO — no se concluye nada.')
        return 1

    hechas = sorted(s for s in semanas if completa(semanas[s]))
    parciales = sorted(s for s in semanas if s not in hechas
                       and any(v for v in semanas[s].values() if v))
    print(f"\nsemanas COMPLETAS: {hechas or 'ninguna'}"
          f" · en curso/parciales (excluidas): {parciales or 'ninguna'}")

    acum = defaultdict(float)
    for s in hechas:
        for e, v in semanas[s].items():
            acum[e] += v or 0.0
    if hechas:
        with open(HISTORIAL, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['semana', 'equipo', 'puntos'])
            for s in hechas:
                for e, v in sorted(semanas[s].items()):
                    w.writerow([s, e, round(v or 0, 2)])
        print(f"histórico → {HISTORIAL.name} ({len(hechas)} semanas)")

    preds, fecha_fp = predictores()
    print(f"\n=== PREDICTORES (FantasyPros: snapshot {fecha_fp}) ===")
    for nom, d in preds.items():
        top = sorted(d, key=lambda k: -d[k])[:3]
        print(f"  {nom:14} {len(d):>2} equipos · top-3: {', '.join(t[:18] for t in top)}")

    if not hechas:
        print(f"\n⏳ Aún no hay ninguna semana COMPLETA (la 1 está en curso).")
        print("   El marcador queda armado: se re-corre cada martes y empieza a")
        print(f"   ser interpretable con {MIN_SEMANAS}+ semanas. Hoy no concluye nada,")
        print("   que es exactamente lo correcto.")
        return 0

    print(f"\n=== ¿QUIÉN ORDENA MEJOR? (rho de rangos vs puntos acumulados, "
          f"{len(hechas)} semana(s)) ===")
    for nom, d in preds.items():
        rho, n = spearman(acum, d)
        txt = f"{rho:+.2f}" if rho is not None else "sin datos"
        print(f"  {nom:14} rho {txt} (sobre {n} equipos)")
    if len(hechas) < MIN_SEMANAS:
        print(f"\n⚠️ Con {len(hechas)} semana(s) el ruido domina: NO se concluye "
              f"nada todavía (mínimo {MIN_SEMANAS}).")
    print("\n=== puntos acumulados ===")
    for i, (e, v) in enumerate(sorted(acum.items(), key=lambda kv: -kv[1]), 1):
        print(f"  {i:>2}. {e[:28]:28}{v:>8.1f}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
