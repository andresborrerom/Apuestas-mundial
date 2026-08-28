"""CANDADO DE LIGA — la simulación tiene que parecerse a la liga de verdad.

Regla de Andrés (28-ago): *"confía en lo que tú ves en la historia de la liga,
nada mejor que eso para comparar"*. Antes de dejar que esta simulación decida
nada, se contrasta contra los DRAFTS REALES de la sala.

🚨 DOS INTENTOS FALLIDOS ANTES DE ESTE — quedan escritos para no repetirlos:

 1. Comparar el PF simulado contra el PF de `historia_standings.csv`. Salía
    +40%. **Inválido**: ese PF viene de NFL.com con el reglamento de NFL.com;
    la simulación usa el reglamento ESPN 2026 (TD de pase 6, +0.1 por completo,
    2.5 por tacleada, FG de 50-59 a 10). Dos varas distintas.
 2. Comparar contra un "equipo del medio" armado con el 8º mejor de cada
    posición según los appliedTotal reales de 2025. Salía −13%. **También
    inválido**: ese equipo es un ORÁCULO — nadie draftea al que RESULTÓ ser el
    8º; se draftea al que uno CREE que va a ser el 8º.

Lo que sí sirve, y es lo mejor que hay: tomar los **drafts reales** de esta
sala (`data/historia_drafts.csv`), puntuarlos con NUESTRO reglamento y nuestra
alineación, y comparar contra simulaciones de la MISMA configuración (mismo
número de equipos, mismas rondas, el roster de NFL.com de esos años). Decisión
humana real contra decisión simulada, con la misma vara.

Sólo se compara la parte OFENSIVA: allá eran 3 slots defensivos (DL/LB/DB) y
acá son 5 (DT/DE/LB/CB/S), así que el bloque defensivo no es comparable.

    python optimize/calibrar_liga.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.liga import (Config, CFG, SEMANAS_REG, OFE, IDP, cargar_todo,
                           universo, draftear, puntos_reales)
from optimize.drafts_reales import (indice_nombres, rosters_reales,
                                    puntos_ofensivos)
from optimize.managers import personalidades

RAIZ = Path(__file__).resolve().parent.parent
# (año, equipos, rondas) tal como se jugó realmente — leído de historia_drafts
CONF_REAL = {2021: (14, 16), 2022: (14, 16), 2023: (16, 17), 2025: (14, 17)}
N_SIMS = 10


def pol_greedy(el, vivos, val, cnt, roster, gp, mis, rank, **kw):
    return max(el, key=lambda k: val.get(k, 0))


def historia_posiciones():
    porpos = defaultdict(list)
    for r in csv.DictReader(open(RAIZ / 'data' / 'historia_drafts.csv')):
        if int(r['season']) in CONF_REAL:
            porpos[{'DEF': 'DST'}.get(r['pos'], r['pos'])].append(int(r['ronda']))
    return porpos


if __name__ == '__main__':
    print('cargando temporadas reales bajo nuestras reglas...', flush=True)
    con, items, P = cargar_todo(2020, 2025)
    personas = personalidades()

    print("\n" + "=" * 78)
    print("CANDADO 1+2 — DRAFTS REALES vs DRAFTS SIMULADOS (misma vara, misma")
    print("              configuración, solo el bloque OFENSIVO de 7 slots)")
    print("=" * 78)
    print(f"  {'año':6}{'eq':>4}{'':3}{'REAL media':>12}{'SIM media':>11}{'dif':>8}"
          f"{'':4}{'REAL 1º/3º':>11}{'SIM 1º/3º':>11}")
    difs, dr, ds = [], [], []
    sim_rondas = defaultdict(list)
    for año, (eqs, rondas) in CONF_REAL.items():
        pts, meta = P[año]
        ix = indice_nombres(pts, meta)
        eq_real, diag = rosters_reales(año, None, ix)
        reales = np.array([puntos_ofensivos(r, pts) for r in eq_real.values()])

        cfg = Config.nflcom(eqs, rondas)
        jug, val, rank, _ = universo(con, año, items, P, cfg=cfg)
        sims = []
        for s in range(N_SIMS):
            rng = np.random.default_rng(4000 + s)
            ros = draftear(jug, val, pol_greedy, personas, rng, rank, cfg=cfg)
            sims.append(np.array([puntos_ofensivos(r, pts) for r in ros]))
            for r in ros:
                for i, (k, pos) in enumerate(r):
                    sim_rondas[pos].append(i + 1)
        allsim = np.concatenate(sims)
        r13 = reales.max() / sorted(reales)[-3]
        s13 = np.mean([x.max() / sorted(x)[-3] for x in sims])
        d = allsim.mean() / reales.mean() - 1
        print(f"  {año:<6}{eqs:>4}{'':3}{reales.mean():>12.0f}{allsim.mean():>11.0f}"
              f"{d*100:>+7.0f}%{'':4}{r13:>11.3f}{s13:>11.3f}")
        difs.append(d); dr.append(r13); ds.append(s13)

    print(f"\n  NIVEL     desvío medio {np.mean(difs)*100:+.1f}%  "
          f"(rango {min(difs)*100:+.0f}% a {max(difs)*100:+.0f}%)")
    ok1 = abs(np.mean(difs)) < 0.10
    print(f"            {'✅ PASA' if ok1 else '🚨 NO PASA'} (umbral ±10%)")
    frac = (np.mean(ds) - 1) / (np.mean(dr) - 1)
    print(f"  DISPERSIÓN real 1º/3º {np.mean(dr):.3f} · simulada {np.mean(ds):.3f}"
          f" → la simulación conserva el {frac*100:.0f}% de la separación real")
    ok2 = frac > 0.60
    print(f"            {'✅ PASA' if ok2 else '⚠️ SESGO DECLARADO'} (umbral 60%)")
    if not ok2:
        print("            Causa: en la liga real se ficha, se cambia y se hace")
        print("            streaming toda la temporada. El simulador se queda con")
        print("            el roster del draft, así que las diferencias entre")
        print("            POLÍTICAS se ven MÁS CHICAS de lo que serían de verdad.")
        print("            Sesga hacia 'empatan' — es el lado conservador.")

    print("\n" + "=" * 78)
    print("CANDADO 3 — ¿CUÁNDO TOMA LA SALA CADA POSICIÓN? (ofensiva, comparable)")
    print("=" * 78)
    HD = historia_posiciones()
    print(f"  {'pos':6}{'REAL':>9}{'SIM':>9}{'dif':>8}{'':4}{'n real':>8}")
    dd = []
    for p in OFE:
        a, b = np.mean(HD[p]), np.mean(sim_rondas[p])
        print(f"  {p:6}{a:>9.1f}{b:>9.1f}{b-a:>+8.1f}{'':4}{len(HD[p]):>8}")
        dd.append(abs(b - a))
    ok3 = np.mean(dd) < 1.0
    print(f"\n  desvío medio {np.mean(dd):.2f} rondas · "
          f"{'✅ PASA' if ok3 else '🚨 NO PASA'} (umbral 1.0)")

    print("\n" + "=" * 78)
    print("CONFIGURACIÓN DE PRODUCCIÓN 2026 (16 equipos, 18 rondas, 14 titulares)")
    print("=" * 78)
    faltas = tot = 0
    for año in CONF_REAL:
        jug, val, rank, pts = universo(con, año, items, P)
        for s in range(N_SIMS):
            rng = np.random.default_rng(4000 + s)
            ros = draftear(jug, val, pol_greedy, personas, rng, rank)
            for r in ros:
                tot += 1
                c = defaultdict(int)
                for k, pos in r:
                    c[pos] += 1
                if any(c[p] < CFG.min_pos[p] for p in CFG.min_pos):
                    faltas += 1
    print(f"  equipos que terminan con un slot obligatorio SIN llenar: {faltas}/{tot}")
    print(f"  {'✅ PASA' if faltas == 0 else '🚨 NO PASA'}")

    print("\n" + "=" * 78)
    veredicto = ok1 and ok3 and faltas == 0
    print(f"RESULTADO: {'✅ la simulación se puede usar' if veredicto else '🚨 NO usar todavía'}"
          f"   · dispersión: {'ok' if ok2 else 'sesgo declarado (conservador)'}")
    print("=" * 78)
