#!/usr/bin/env python3
"""
COLFONDOS — E[utilidad] por nº de plazas. Premio 60/30/10 de la bolsa de
inscripciones; costo $65.000/plaza. Maneja que nuestras plazas tomen varios
puestos del podio (con desempates por split).

    python pollas/COLFONDOS/colfondos_utilidad.py --inscritos 18
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.COLFONDOS.competencia_colfondos as CC
import pollas.COLFONDOS.caminos_colfondos as CA


def reparto(our, pool, N, K, valor, frac_premio, rng, prem=(0.6, 0.3, 0.1)):
    Kp, S = our.shape
    pozo = frac_premio * N * valor
    fr = np.array(prem) * pozo
    P = pool.shape[0]
    util = np.zeros(S); p1 = np.zeros(S); ptop = np.zeros(S)
    for s in range(S):
        riv = pool[rng.integers(0, P, max(N - K, 0)), s]
        vals = np.concatenate([our[:, s], riv]); mine = np.zeros(len(vals), bool); mine[:K] = True
        order = np.argsort(-vals); vs = vals[order]; ms = mine[order]
        got = 0.0; pos = 0; g1 = False; g3 = False
        while pos < len(vs) and pos < 3:
            j = pos
            while j + 1 < len(vs) and vs[j + 1] == vs[pos]: j += 1
            tie = list(range(pos, j + 1)); cubre = [k for k in tie if k < 3]
            premio_g = fr[cubre].sum() if cubre else 0.0
            nm = sum(ms[k] for k in tie)
            if nm:
                got += premio_g * nm / len(tie)
                if pos == 0: g1 = True
                g3 = True
            pos = j + 1
        util[s] = got; p1[s] = g1; ptop[s] = g3
    return util.mean() - K * valor, util.mean(), p1.mean(), ptop.mean()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--inscritos", type=int, default=18)
    ap.add_argument("--otros", type=int, default=None, help="rivales fijos; N=otros+K (la bolsa crece con tus plazas)")
    ap.add_argument("--valor", type=int, default=65000)
    ap.add_argument("--p-afilado", type=float, default=0.12)
    ap.add_argument("--frac-premio", type=float, default=1.0, help="fracción de la bolsa que se paga")
    args = ap.parse_args(argv)
    realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv = CC.construir(args)
    S = realiz["S"]; N = args.inscritos
    pool = CA.build_pool(realiz, arbol, Padv, tid, inv, args.p_afilado)

    def nuestras(K):
        return np.stack([CC.puntuar(CC.entrada_nuestra(realiz, grupo_pick, r32_occ, arbol, Padv,
                         tid, inv, j, decorrel=(j > 0), rng=np.random.default_rng(100 + j)), realiz)
                         for j in range(K)])
    rng = np.random.default_rng(3)
    modo = f"otros={args.otros} fijos, N=otros+K" if args.otros is not None else f"N={N} fijo"
    print(f"{modo} · plaza ${args.valor:,} · premio 60/30/10")
    print(f"{'K':>2} {'N':>3} {'bolsa':>11} {'P(1º)':>7} {'P(top3)':>8} {'E[premio]':>12} {'E[util]':>12} {'Δutil':>10}")
    prev = None
    for K in (1, 2, 3, 4, 5, 6):
        Nk = (args.otros + K) if args.otros is not None else N
        our = nuestras(K)
        util, premio, p1, ptop = reparto(our, pool, Nk, K, args.valor, args.frac_premio, rng)
        d = "" if prev is None else f"{util - prev:+,.0f}"
        print(f"{K:>2} {Nk:>3} ${args.frac_premio*Nk*args.valor:>10,.0f} {p1*100:>6.1f}% {ptop*100:>7.1f}% ${premio:>11,.0f} ${util:>11,.0f} {d:>10}")
        prev = util
    print("\nΔutil/plaza > 0 => esa plaza extra es +EV. (Bolsa crece si entran más; re-correr con N real.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
