#!/usr/bin/env python3
"""
Walk-forward del modelo de CLASIFICACIÓN de grupos, sobre 4 Mundiales reales
(paquete oddor: grupos 2010-2022 con 1X2 + resultados). Simula cada grupo desde
las cuotas y compara contra quién clasificó/ganó de verdad.

Hallazgo: P(clasificar) bien calibrada, pero acertar el top-2 EXACTO es ~38%
(los grupos son genuinamente impredecibles). Ganador del grupo ~69%.

    python pollas/LEMAITRE/backtest_clasificacion.py
"""
import os, sys, urllib.request, numpy as np
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import cuotas, marcadores

RDA = "/tmp/wc_oddor.rda"
URL = "https://github.com/ikashnitsky/oddor/raw/main/data/soccer_world_cup.rda"
KO = ['play', 'final', '16', 'quarter', 'semi', 'third', 'octav', 'cuart']


def matriz(oh, od, oa):
    p = cuotas.a_probabilidades([oh, od, oa], "proporcional")
    return marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=None)["matriz"]


def main():
    import pyreadr
    if not os.path.exists(RDA):
        urllib.request.urlretrieve(URL, RDA)
    df = list(pyreadr.read_r(RDA).values())[0]
    df = df.assign(gr=df['stage'].astype(str).str.lower())
    grp = df[~df['gr'].apply(lambda s: any(k in s for k in KO))].dropna(
        subset=['goals_home', 'goals_away', 'odds_home', 'odds_draw', 'odds_away'])
    cal, acc_top2, acc_win, ng = [], 0, 0, 0
    rng = np.random.default_rng(0)
    for (yr,), g in grp.groupby(['year']):
        opp = defaultdict(set); rows = list(g.itertuples())
        for r in rows: opp[r.home].add(r.away); opp[r.away].add(r.home)
        vistos = set()
        for t in list(opp):
            if t in vistos: continue
            grupo = frozenset({t} | opp[t])
            if len(grupo) != 4 or (grupo & vistos): continue
            vistos |= grupo
            eq = sorted(grupo); idx = {e: i for i, e in enumerate(eq)}
            mm = [r for r in rows if r.home in grupo and r.away in grupo]
            if len(mm) < 6: continue
            ng += 1; S = 10000
            pts = np.zeros((4, S)); gd = np.zeros((4, S)); gf = np.zeros((4, S))
            ap = np.zeros(4); agd = np.zeros(4); agf = np.zeros(4)
            for r in mm:
                M = matriz(r.odds_home, r.odds_draw, r.odds_away); fl = M.ravel()/M.sum()
                k = rng.choice(fl.size, size=S, p=fl); gh, ga = k//M.shape[1], k % M.shape[1]
                ih, ia = idx[r.home], idx[r.away]
                pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
                pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
                gd[ih] += gh-ga; gd[ia] += ga-gh; gf[ih] += gh; gf[ia] += ga
                rh, ra = int(r.goals_home), int(r.goals_away)
                ap[ih] += 3 if rh > ra else (1 if rh == ra else 0)
                ap[ia] += 3 if ra > rh else (1 if rh == ra else 0)
                agd[ih] += rh-ra; agd[ia] += ra-rh; agf[ih] += rh; agf[ia] += ra
            orden = np.argsort(-(pts*1e6+gd*1e3+gf+rng.random((4, S))*1e-3), axis=0)
            Ppasa = np.array([np.mean((orden[:2] == e).any(0)) for e in range(4)])
            Pwin = np.array([np.mean(orden[0] == e) for e in range(4)])
            ar = np.argsort(-(ap*1e6+agd*1e3+agf+np.arange(4)*1e-6))
            real_top2, real_win = set(ar[:2].tolist()), ar[0]
            for e in range(4): cal.append((Ppasa[e], 1.0 if e in real_top2 else 0.0))
            acc_top2 += set(np.argsort(-Ppasa)[:2].tolist()) == real_top2
            acc_win += int(np.argmax(Pwin)) == real_win
    print(f"{ng} grupos de Mundial validados ({grp['year'].nunique()} Mundiales)")
    print(f"  Acierto top-2 EXACTO: {acc_top2}/{ng} = {acc_top2/ng*100:.0f}%")
    print(f"  Acierto del GANADOR : {acc_win}/{ng} = {acc_win/ng*100:.0f}%")
    cal.sort()
    print("  Calibracion P(clasificar): predicho -> observado")
    for b in range(5):
        ch = cal[b*len(cal)//5:(b+1)*len(cal)//5]
        print(f"    {np.mean([c[0] for c in ch]):.2f} -> {np.mean([c[1] for c in ch]):.2f}")


if __name__ == "__main__":
    main()
