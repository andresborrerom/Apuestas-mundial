"""STANDINGS PROYECTADOS — ¿cómo terminamos la temporada regular?

Andrés (22-sep, tras perder la semana 2): "¿cómo nos vemos con el motor que
tienes ahora en standings para el season?"

Simula las 12 jornadas que faltan partido por partido, 20.000 veces, y saca
probabilidad de playoffs (8 de 16), puesto esperado y récord esperado.

FUENTE ✅ = la API de ESPN para récords, puntos ya anotados, calendario
pendiente y rosters actuales. Nada de eso se estima.

LO QUE SÍ HAY QUE ESTIMAR es la fuerza semanal de cada equipo, y ahí hay dos
señales que se contradicen:
  📊 MODELO      suma del pg de los titulares que tiene HOY (proyeccion_dist)
  ✅ OBSERVADO   lo que de verdad anotó en 2 jornadas

Dos jornadas son muy poco: el error estándar de esa media es enorme. Pero el
modelo tampoco es la verdad — la auditoría le mide MAE 24-31. Así que NO se
entrega un número único: se corren TRES escenarios con distinto peso sobre lo
observado y se reporta el rango. Si la conclusión cambia dentro del rango, eso
es lo que hay que decir.

  w=0.00  solo el modelo (ignora lo anotado)
  w=0.50  mitad y mitad        <- el central
  w=1.00  solo lo observado (ignora el modelo)

⚠️ SUPUESTO S-SIGMA: el ruido semanal se mide como la desviación de
(anotado - proyectado) sobre las 32 observaciones equipo-semana que existen.
Con n=32 ese sigma es en sí mismo incierto; se imprime para que se vea.
⚠️ SUPUESTO S-ESTATICO: se asume que el roster de hoy es el de las 12 semanas
que faltan. Ignora lesiones futuras, waivers y cambios de rol. Sesga hacia
arriba a quien hoy tiene a alguien lesionado en la banca, y hacia abajo a
quien vaya a mejorar por waivers.
CADUCIDAD: re-correr cada martes; con 4+ jornadas el peso de lo observado
debería subir y el rango estrecharse solo.

    python optimize/standings_sim.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import numpy as np
import requests

from ingest.espn_auth import credenciales

SIMS = 20000
PLAYOFF = 8
SLOTS_BANCA = {20, 21}


def bajar():
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    return requests.get(u, params={'view': ['mTeam', 'mMatchupScore', 'mRoster']},
                        cookies={'espn_s2': s2, 'SWID': swid}, timeout=60).json()


def estado(d):
    """Récords, puntos anotados por jornada, calendario pendiente y proyección
    del roster ACTUAL de cada equipo."""
    eq = {t['id']: t.get('name', f"t{t['id']}").strip() for t in d['teams']}
    modelo = {int(r['espn_id']): float(r['pg'])
              for r in csv.DictReader(open(RAIZ / 'data' / 'proyeccion_dist.csv'))
              if r.get('espn_id')}
    proy = {}
    for t in d['teams']:
        proy[t['id']] = sum(modelo.get(e['playerPoolEntry']['player']['id'], 0.0)
                            for e in t['roster']['entries']
                            if e['lineupSlotId'] not in SLOTS_BANCA)
    anot, pend, rec = defaultdict(list), [], {}
    for t in d['teams']:
        r = t['record']['overall']
        rec[t['id']] = [r['wins'], r['losses'], r['pointsFor']]
    for m in d['schedule']:
        w = m.get('matchupPeriodId')
        a, h = (m.get('away') or {}), (m.get('home') or {})
        if a.get('teamId') is None or h.get('teamId') is None:
            continue
        pa = (a.get('pointsByScoringPeriod') or {}).get(str(w))
        ph = (h.get('pointsByScoringPeriod') or {}).get(str(w))
        if pa and ph:
            anot[a['teamId']].append(pa)
            anot[h['teamId']].append(ph)
        else:
            pend.append((w, a['teamId'], h['teamId']))
    return eq, rec, anot, pend, proy


def sigma(anot, proy):
    """Ruido semanal medido: desviación de (anotado - proyectado)."""
    res = [p - proy[t] for t, ps in anot.items() for p in ps]
    return float(np.std(res, ddof=1)), len(res)


def simular(rec, pend, mu, sd, rng):
    ids = list(mu)
    w = {i: rec[i][0] for i in ids}
    pf = {i: rec[i][2] for i in ids}
    # una matriz de ruido para todos los partidos pendientes de golpe
    for jor, a, h in pend:
        pa = mu[a] + rng.normal(0, sd)
        ph = mu[h] + rng.normal(0, sd)
        pf[a] += pa
        pf[h] += ph
        if pa > ph:
            w[a] += 1
        elif ph > pa:
            w[h] += 1
        else:                       # empate exacto: lo rompe el que más anotó
            (w.__setitem__(a, w[a] + 1) if pf[a] > pf[h]
             else w.__setitem__(h, w[h] + 1))
    orden = sorted(ids, key=lambda i: (-w[i], -pf[i]))
    return {i: k + 1 for k, i in enumerate(orden)}, w, pf


def correr(eq, rec, anot, pend, proy, peso, sd, sims=SIMS, semilla=0):
    rng = np.random.default_rng(semilla)
    obs = {i: (np.mean(v) if v else proy[i]) for i, v in
           ((i, anot.get(i, [])) for i in eq)}
    mu = {i: (1 - peso) * proy[i] + peso * obs[i] for i in eq}
    puestos = defaultdict(list)
    playoffs = defaultdict(int)
    victorias = defaultdict(float)
    for s in range(sims):
        pos, w, pf = simular(rec, pend, mu, sd, rng)
        for i, p in pos.items():
            puestos[i].append(p)
            victorias[i] += w[i]
            if p <= PLAYOFF:
                playoffs[i] += 1
    return {i: dict(mu=mu[i],
                    playoffs=playoffs[i] / sims,
                    puesto=float(np.mean(puestos[i])),
                    p25=float(np.percentile(puestos[i], 25)),
                    p75=float(np.percentile(puestos[i], 75)),
                    vic=victorias[i] / sims) for i in eq}


def main():
    d = bajar()
    eq, rec, anot, pend, proy = estado(d)
    sd, n = sigma(anot, proy)
    jugadas = max(len(v) for v in anot.values())
    print(f"=== CANDADOS ===")
    print(f"  {'✅' if len(eq)==16 else '🚨'} 16 equipos: {len(eq)}")
    print(f"  {'✅' if len(pend)==96 else '⚠️'} partidos pendientes: {len(pend)}"
          f" (12 jornadas x 8)")
    print(f"  ✅ jornadas ya jugadas: {jugadas}")
    print(f"\n⚠️ ruido semanal medido: sigma = {sd:.1f} pts sobre {n} observaciones "
          f"equipo-semana (n pequeño: el propio sigma es incierto)")

    escen = {}
    for peso, et in ((0.0, 'solo modelo'), (0.5, 'mitad y mitad'), (1.0, 'solo observado')):
        escen[peso] = correr(eq, rec, anot, pend, proy, peso, sd)

    mio = [i for i, n_ in eq.items() if n_ == 'The Replacements']
    mio = mio[0] if mio else 10
    print(f"\n=== ESCENARIO CENTRAL (mitad modelo / mitad observado) ===")
    print(f"{'#':>3} {'equipo':30}{'μ/sem':>8}{'récord esp':>12}{'puesto':>8}"
          f"{'(p25-p75)':>11}{'playoffs':>10}")
    c = escen[0.5]
    for k, i in enumerate(sorted(eq, key=lambda i: -c[i]['playoffs']), 1):
        r = c[i]
        marca = '  <<<' if i == mio else ''
        recd = f"{r['vic']:.1f}-{14 - r['vic']:.1f}"
        iqr = f"{r['p25']:.0f}-{r['p75']:.0f}"
        print(f"{k:>3} {eq[i][:29]:30}{r['mu']:>8.1f}{recd:>12}"
              f"{r['puesto']:>8.1f}{iqr:>11}{r['playoffs']:>9.0%}{marca}")

    print(f"\n=== SENSIBILIDAD — tu equipo en los tres escenarios ===")
    print(f"{'escenario':18}{'μ/sem':>8}{'puesto esp':>12}{'playoffs':>10}")
    for peso, et in ((0.0, 'solo modelo'), (0.5, 'mitad y mitad'), (1.0, 'solo observado')):
        r = escen[peso][mio]
        print(f"{et:18}{r['mu']:>8.1f}{r['puesto']:>12.1f}{r['playoffs']:>9.0%}")
    lo = min(escen[p][mio]['playoffs'] for p in escen)
    hi = max(escen[p][mio]['playoffs'] for p in escen)
    print(f"\n  RANGO de probabilidad de playoffs: {lo:.0%} a {hi:.0%}")
    print(f"  {'✅ la conclusión NO cambia dentro del rango' if (lo>0.5)==(hi>0.5) else '⚠️ la conclusión CAMBIA dentro del rango: no hay veredicto'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
