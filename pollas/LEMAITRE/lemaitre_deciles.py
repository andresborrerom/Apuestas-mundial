#!/usr/bin/env python3
"""
LEMAITRE — utilidad por DECILES para 1 vs 2 plazas. N=25, entrada $234.000,
premio 90% de la bolsa repartido 60/30/10. La 2ª plaza es un gemelo casi-óptimo
DECORRELADO (sigue los picks ~95% y se separa en marcadores/llaves baratas).
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.LEMAITRE.competencia_lemaitre as C


def util_vec(our, pool, N, K, valor, frac_premio, rng, prem=(0.6, 0.3, 0.1)):
    Kp, S = our.shape; pozo = frac_premio * N * valor; fr = np.array(prem) * pozo
    P = pool.shape[0]; util = np.zeros(S)
    for s in range(S):
        riv = pool[rng.integers(0, P, max(N - K, 0)), s]
        vals = np.concatenate([our[:, s], riv]); mine = np.zeros(len(vals), bool); mine[:K] = True
        order = np.argsort(-vals); vs = vals[order]; ms = mine[order]
        got = 0.0; pos = 0
        while pos < len(vs) and pos < 3:
            j = pos
            while j + 1 < len(vs) and vs[j + 1] == vs[pos]: j += 1
            tie = list(range(pos, j + 1)); cubre = [k for k in tie if k < 3]
            if cubre:
                nm = sum(ms[k] for k in tie)
                if nm: got += fr[cubre].sum() * nm / len(tie)
            pos = j + 1
        util[s] = got - K * valor
    return util


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=6000)
    ap.add_argument("--inscritos", type=int, default=25)
    ap.add_argument("--valor", type=int, default=234000)
    ap.add_argument("--p-afilado", type=float, default=0.20)
    ap.add_argument("--frac-premio", type=float, default=0.90)
    args = ap.parse_args(argv)
    realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv = C.construir(args)
    S = realiz["S"]; N = args.inscritos

    # pool de rivales (mezcla afilados/casuales)
    rng = np.random.default_rng(7); POOL = 500
    thetas = np.where(rng.random(POOL) < args.p_afilado, rng.beta(6, 2, POOL), rng.beta(2, 4, POOL))
    pool = np.stack([C.puntuar(C.planilla_rival(float(t), Pgrupo, nuestra, atk, dfn, tid, inv, rng), realiz)
                     for t in thetas])
    base = C.puntuar(nuestra, realiz)
    # 2ª plaza: gemelo casi-óptimo decorrelado
    seg = C.puntuar(C.planilla_rival(0.95, Pgrupo, nuestra, atk, dfn, tid, inv, np.random.default_rng(11)), realiz)
    print(f"E[pts]: plaza1={base.mean():.0f}  plaza2(decorr)={seg.mean():.0f}  pool rival={pool.mean():.0f}")
    pozo = args.frac_premio * N * args.valor
    print(f"N={N} · bolsa 90% = ${pozo:,.0f} (1º {pozo*.6:,.0f} / 2º {pozo*.3:,.0f} / 3º {pozo*.1:,.0f}) · entrada ${args.valor:,}\n")

    cols = {}
    rngp = np.random.default_rng(3)
    cols[1] = np.sort(util_vec(base[None, :], pool, N, 1, args.valor, args.frac_premio, rngp))
    rngp = np.random.default_rng(3)
    cols[2] = np.sort(util_vec(np.stack([base, seg]), pool, N, 2, args.valor, args.frac_premio, rngp))

    def k(x): return x / 1000.0
    print(f"UTILIDAD POR DECILES (miles de $)   [p_afilado={args.p_afilado}]")
    print(f"{'decil':>10}{'1 plaza':>12}{'2 plazas':>12}{'Δ (2-1)':>12}")
    for d in range(10):
        lo, hi = d * S // 10, (d + 1) * S // 10
        u1 = cols[1][lo:hi].mean(); u2 = cols[2][lo:hi].mean()
        etq = f"D{d+1}" + (" peor" if d == 0 else " mejor" if d == 9 else "")
        print(f"{etq:>10}{k(u1):>12,.0f}{k(u2):>12,.0f}{k(u2-u1):>12,.0f}")
    print("-" * 46)
    print(f"{'MEDIA':>10}{k(cols[1].mean()):>12,.0f}{k(cols[2].mean()):>12,.0f}{k(cols[2].mean()-cols[1].mean()):>12,.0f}")
    print(f"{'P(pierde)':>10}{(cols[1]<0).mean()*100:>11.0f}%{(cols[2]<0).mean()*100:>11.0f}%")
    print(f"{'P(1º)≈':>10}{(cols[1]>pozo*0.5).mean()*100:>11.0f}%{(cols[2]>pozo*0.5).mean()*100:>11.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
