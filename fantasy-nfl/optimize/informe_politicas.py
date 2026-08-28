"""INFORME COMPLETO de políticas: tabla, comparación pareada contra el MOTOR
(que es la que uso hoy) y la DISTRIBUCIÓN entera de cada una.

Andrés pidió explícitamente "revisamos las funciones de distribución de
probabilidad de cada una". El promedio esconde al caso que mata: dos políticas
pueden dar el mismo dinero esperado y una llevarte al último puesto el triple
de veces.

Guarda el resultado crudo en data/politicas_resultado.npz para no tener que
volver a correr 20 minutos cada vez que se quiera mirar otra cosa.

    python optimize/informe_politicas.py --sims 300
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.liga import CFG, cargar_todo, universo, draftear, temporada
from optimize.politicas import POLITICAS
from optimize.managers import personalidades

RAIZ = Path(__file__).resolve().parent.parent
DEST = RAIZ / 'data' / 'politicas_resultado.npz'
ORDEN_POS = ['QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'DST', 'K']


def correr(con, items, P, años, pols, sims, cfg=CFG):
    personas = personalidades()
    D = {}
    for año in años:
        jug, val, rank, pts = universo(con, año, items, P, cfg=cfg)
        for nom in pols:
            fn = POLITICAS[nom]
            fila = []
            for s in range(sims):
                ros = draftear(jug, val, fn, personas,
                               np.random.default_rng(1000 + s), rank, cfg=cfg)
                din, pue, pf, vic, camp = temporada(
                    ros, pts, np.random.default_rng(5000 + s), cfg=cfg)
                t = cfg.mi_asiento
                c = defaultdict(int)
                for k, p in ros[t]:
                    c[p] += 1
                fila.append([din[t], pue[t], pf[t], vic[t],
                             1.0 if camp == t else 0.0]
                            + [c[p] for p in ORDEN_POS])
            D[f'{año}|{nom}'] = np.array(fila)
            print(f"  {año} {nom:9} E[$]={np.mean([f[0] for f in fila]):>7.0f}",
                  flush=True)
    return D


def tabla(D, años, pols):
    print("\n" + "=" * 86)
    print("DINERO POR TEMPORADA — la distribución entera, no solo el promedio")
    print("=" * 86)
    print(f"  {'política':10}{'E[$]':>8}{'sd':>7}{'p10':>7}{'p25':>7}{'p50':>7}"
          f"{'p75':>7}{'p90':>7}{'':3}{'DFL':>6}{'sin $':>7}{'top8':>7}{'campeón':>8}")
    agg = {}
    for nom in pols:
        m = np.concatenate([D[f'{a}|{nom}'] for a in años])
        agg[nom] = m
        din, pue, camp = m[:, 0], m[:, 1], m[:, 4]
        print(f"  {nom:10}{din.mean():>8.0f}{din.std():>7.0f}"
              + ''.join(f"{np.percentile(din, q):>7.0f}" for q in (10, 25, 50, 75, 90))
              + f"{'':3}{np.mean(pue == 16)*100:>5.1f}%{np.mean(pue > 8)*100:>6.0f}%"
              f"{np.mean(pue <= 8)*100:>6.0f}%{camp.mean()*100:>7.1f}%")
    return agg


def pareado(agg, pols, base='motor'):
    print("\n" + "=" * 86)
    print(f"COMPARACIÓN PAREADA CONTRA '{base}' — misma sala, mismo calendario,")
    print("la única diferencia es mi decisión. Δ$ por temporada.")
    print("=" * 86)
    print(f"  {'':22}{'Δ$ medio':>10}{'error':>8}{'t':>7}{'':3}"
          f"{'gana':>7}{'empata':>8}{'pierde':>8}")
    a = agg[base][:, 0]
    for nom in pols:
        if nom == base:
            continue
        b = agg[nom][:, 0]
        d = b - a
        se = d.std(ddof=1) / np.sqrt(len(d))
        print(f"  {nom + ' vs ' + base:22}{d.mean():>+10.0f}{se:>8.0f}"
              f"{(d.mean()/se if se else 0):>7.1f}{'':3}"
              f"{np.mean(d > 1)*100:>6.0f}%{np.mean(np.abs(d) <= 1)*100:>7.0f}%"
              f"{np.mean(d < -1)*100:>7.0f}%")


def por_anio(D, años, pols):
    print("\n" + "=" * 86)
    print("POR TEMPORADA — ¿es estable o depende del año? (dinero esperado)")
    print("=" * 86)
    print(f"  {'política':10}" + ''.join(f"{a:>10}" for a in años)
          + f"{'peor año':>12}")
    for nom in pols:
        v = [D[f'{a}|{nom}'][:, 0].mean() for a in años]
        print(f"  {nom:10}" + ''.join(f"{x:>10.0f}" for x in v)
              + f"{min(v):>12.0f}")


def composicion(D, años, pols):
    print("\n" + "=" * 86)
    print("QUÉ ROSTER CONSTRUYE CADA UNA (jugadores por posición, media)")
    print("=" * 86)
    print(f"  {'política':10}" + ''.join(f"{p:>6}" for p in ORDEN_POS))
    for nom in pols:
        m = np.concatenate([D[f'{a}|{nom}'] for a in años])[:, 5:]
        print(f"  {nom:10}" + ''.join(f"{x:>6.1f}" for x in m.mean(axis=0)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=300)
    ap.add_argument('--anios', default='2021,2022,2023,2025')
    ap.add_argument('--politicas', default='greedy,motor,motor2,regla,no-miope')
    ap.add_argument('--usar-guardado', action='store_true')
    a = ap.parse_args()
    años = [int(x) for x in a.anios.split(',')]
    pols = a.politicas.split(',')
    if a.usar_guardado and DEST.exists():
        D = dict(np.load(DEST))
        print(f"leído de {DEST.name}")
    else:
        print('cargando temporadas reales bajo nuestras reglas...', flush=True)
        con, items, P = cargar_todo(2020, 2025)
        D = correr(con, items, P, años, pols, a.sims)
        np.savez_compressed(DEST, **D)
        print(f"\nguardado en data/{DEST.name}")
    agg = tabla(D, años, pols)
    pareado(agg, pols, base='motor')
    por_anio(D, años, pols)
    composicion(D, años, pols)
