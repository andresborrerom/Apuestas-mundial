#!/usr/bin/env python3
"""FINALES CSC — optim de los 2 últimos marcadores (3er puesto + final) para
los 5 cupos, maximizando E[dinero total]. Field real (PDF 15.7). Reglas POR
PARTIDO: tercer_puesto (6,10,14) y final (8,12,16). Pipeline auditado
(ajuste_120 δ=0.45 + sesgo 0.05, menú top-8 por partido por SU regla,
coordinate-descent multi-arranque + candidatos de grilla, validación pareada
en seeds frescas)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120

AQUI = os.path.dirname(os.path.abspath(__file__))
G = 7; PRECIO = 100_000; NMENU = 8
RONDA_M = ["tercer_puesto", "final"]          # orden del snapshot: Fra-Ing, Esp-Arg
PAR_M = [RONDAS[r] for r in RONDA_M]
FD = os.path.join(AQUI, "field_finales.json")

def matrices():
    ev = json.load(open(os.path.join(AQUI, "finales_odds_snapshot.json"), encoding="utf-8"))
    Ms = []
    for e, ronda in zip(ev, RONDA_M):
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda(ronda),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M = ajuste_120(r["matriz"], r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"], 0.45)
        Ms.append(marcadores.aplicar_sesgo_goles(M, 0.05))
    return Ms

def _val(g, cero, base): return np.where(g == 0, cero, g + base)
def score_pick(a, b, gh, ga, par):
    res, cero, base = par
    return (res * (np.sign(a - b) == np.sign(gh - ga))
            + (a == gh) * _val(gh, cero, base) + (b == ga) * _val(ga, cero, base)).astype(np.float64)

def menu_top(Ms):
    out = []
    for M, par in zip(Ms, PAR_M):
        EV = sp.ev_grid(M, par, G).ravel(); o = np.argsort(-EV)[:NMENU]
        out.append([(int(x // (G + 1)), int(x % (G + 1))) for x in o])
    return out

class Env:
    def __init__(self, Ms, menu, rivals, ours_pts, seed, S, mix):
        rng = np.random.default_rng(seed)
        gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
        Ef = len(rivals)
        # field por partido con SU regla (arquetipos independientes por partido)
        f0h, f0a = sp.generar_field_mix([Ms[0]], Ef, mix, PAR_M[0], rng, G)
        f1h, f1a = sp.generar_field_mix([Ms[1]], Ef, mix, PAR_M[1], rng, G)
        gfield = (score_pick(f0h[:, [0]], f0a[:, [0]], gh[0][None, :], ga[0][None, :], PAR_M[0])
                  + score_pick(f1h[:, [0]], f1a[:, [0]], gh[1][None, :], ga[1][None, :], PAR_M[1]))
        field_tot = rivals[:, None] + gfield + rng.random((Ef, S)) * 1e-6  # rifa justa (H1 auditoría)
        self.Ftop = np.sort(np.partition(field_tot, -5, axis=0)[-5:], axis=0)[::-1]
        self.jit = rng.random((5, S)) * 1e-6
        cand = [np.stack([score_pick(a, b, gh[m], ga[m], PAR_M[m]) for (a, b) in menu[m]])
                for m in range(2)]
        self.combo = (cand[0][:, None, :] + cand[1][None, :, :]).reshape(NMENU * NMENU, S)
        self.premio = sp.PREMIOS * (Ef + 5) * PRECIO
        self.ours_pts = ours_pts; self.S = S

    def evaluar(self, assign):
        our = self.ours_pts[:, None] + self.combo[list(assign)] + self.jit
        fab = (self.Ftop[None, :, :] > our[:, None, :]).sum(1)
        oab = (our[:, None, :] > our[None, :, :]).sum(0)
        rank = fab + oab
        pr = np.where(rank < 5, self.premio[np.clip(rank, 0, 4)], 0.0)
        return pr.sum(0).mean(), (rank < 5).mean(1), (rank < 5).sum(0).mean(), (our.max(0) > self.Ftop[0]).mean(), rank

    def ep(self, assign): return self.evaluar(assign)[0]

    def mejor_para_cupo(self, assign, i):
        our = self.ours_pts[:, None] + self.combo[list(assign)] + self.jit
        others = np.delete(our, i, axis=0)
        cand = self.ours_pts[i] + self.combo + self.jit[i]
        fab_c = (self.Ftop[None, :, :] > cand[:, None, :]).sum(1)
        oab_c = (others[None, :, :] > cand[:, None, :]).sum(1)
        tot = np.where(fab_c + oab_c < 5, self.premio[np.clip(fab_c + oab_c, 0, 4)], 0.0)
        fab_o = (self.Ftop[:, None, :] > others[None, :, :]).sum(0)
        for j in range(4):
            oab_j = (np.delete(others, j, axis=0) > others[j][None, :]).sum(0)
            rank_j = fab_o[j][None, :] + oab_j[None, :] + (cand > others[j][None, :])
            tot += np.where(rank_j < 5, self.premio[np.clip(rank_j, 0, 4)], 0.0)
        return tot.mean(1)

def cd(envs, start, sweeps=10):
    a = list(start)
    for _ in range(sweeps):
        moved = False
        for i in range(5):
            vals = np.mean([e.mejor_para_cupo(a, i) for e in envs], axis=0)
            b = int(np.argmax(vals))
            if vals[b] > vals[a[i]] + 50: a[i] = b; moved = True
        if not moved: break
    return tuple(a)

def main():
    Ms = matrices(); menu = menu_top(Ms)
    fd = json.load(open(FD)); rivals = np.array([p for _, p in fd["rivals"]], float)
    o = sorted(fd["ours"].items(), key=lambda kv: -kv[1])
    labels = [k.replace("ANDRES BORRERO ", "B") for k, _ in o]
    ours_pts = np.array([v for _, v in o], float)
    print("cupos:", list(zip(labels, ours_pts.astype(int))))
    print("menú 3er puesto:", menu[0]); print("menú final:", menu[1])
    MIX = {"opt": .15, "cal": .35, "hum": .50}
    def a_of(picks):
        return tuple(menu[0].index(picks[l][0]) * NMENU + menu[1].index(picks[l][1]) for l in labels)
    tr = [Env(Ms, menu, rivals, ours_pts, s, 15000, MIX) for s in (21, 22, 23)]
    rng = np.random.default_rng(5)
    starts = [tuple(rng.integers(0, NMENU * NMENU, 5)) for _ in range(8)]
    starts.append(tuple([0] * 5))
    best = {}
    for st in starts:
        a = cd(tr, st)
        best[a] = np.mean([e.ep(a) for e in tr])
    cands = sorted(best.items(), key=lambda kv: -kv[1])[:3]
    def fmt(a):
        return {labels[i]: f"{menu[0][a[i] // NMENU][0]}-{menu[0][a[i] // NMENU][1]}/"
                           f"{menu[1][a[i] % NMENU][0]}-{menu[1][a[i] % NMENU][1]}" for i in range(5)}
    va = [Env(Ms, menu, rivals, ours_pts, s, 30000, MIX) for s in (501, 502, 503, 504, 505, 506)]
    print("\nVALIDACIÓN (6 seeds frescas, pareada):")
    res = {}
    for a, eptr in cands:
        eps = [e.ep(list(a)) for e in va]
        res[a] = np.mean(eps)
        print(f"  {fmt(a)}")
        print(f"    train {eptr:,.0f}  ->  valid {np.mean(eps):,.0f} ±{np.std(eps):,.0f}")
    win = max(res, key=res.get)
    pr, inm, slots, p1, _ = va[0].evaluar(list(win))
    print(f"\nGANADORA: {fmt(win)}")
    print(f"  E[premio]={res[win]:,.0f} · E[slots]={slots:.2f} · P(#1)={p1 * 100:.0f}%")
    for i, l in enumerate(labels):
        print(f"    {l}({int(ours_pts[i])}): P(en plata)={inm[i] * 100:.0f}%")

if __name__ == "__main__":
    main()
