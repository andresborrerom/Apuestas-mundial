#!/usr/bin/env python3
"""
COLFONDOS — UTILIDAD POR DECILES para K=1,2,3,4 plazas (una sola matriz).
"El costo de la pereza": cuánto E[util] y upside dejas si te quedas en 2 plazas.
Premio 60/30/10 de la bolsa; rivales fijos (otros), N=otros+K (la bolsa crece).
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.COLFONDOS.competencia_colfondos as CC
import pollas.COLFONDOS.caminos_colfondos as CA


def util_vec(our, pool, N, K, valor, frac_premio, rng, prem=(0.6, 0.3, 0.1)):
    """Vector de utilidad por sim (premio cobrado - costo)."""
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
    ap.add_argument("--otros", type=int, default=17)
    ap.add_argument("--valor", type=int, default=65000)
    ap.add_argument("--p-afilado", type=float, default=0.12)
    ap.add_argument("--frac-premio", type=float, default=1.0)
    args = ap.parse_args(argv)
    realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv = CC.construir(args)
    S = realiz["S"]
    pool = CA.build_pool(realiz, arbol, Padv, tid, inv, args.p_afilado)

    def nuestras(K):
        return np.stack([CC.puntuar(CC.entrada_nuestra(realiz, grupo_pick, r32_occ, arbol, Padv,
                         tid, inv, j, decorrel=(j > 0), rng=np.random.default_rng(100 + j)), realiz)
                         for j in range(K)])
    Ks = [1, 2, 3, 4]
    cols = {}
    for K in Ks:
        rng = np.random.default_rng(3)
        u = util_vec(nuestras(K), pool, args.otros + K, K, args.valor, args.frac_premio, rng)
        cols[K] = np.sort(u)
    def m(pesos):  # en miles
        return pesos / 1000.0

    print(f"UTILIDAD POR DECILES (miles de $) · otros={args.otros}, plaza ${args.valor:,}, premio 60/30/10")
    print(f"(cada plaza suma a la bolsa; campo casual p_afilado={args.p_afilado})\n")
    print(f"{'decil':>8}" + "".join(f"{'K='+str(K):>10}" for K in Ks))
    for d in range(10):
        lo, hi = d * S // 10, (d + 1) * S // 10
        row = "".join(f"{m(cols[K][lo:hi].mean()):>10,.0f}" for K in Ks)
        etq = f"D{d+1}" + (" (peor)" if d == 0 else " (mejor)" if d == 9 else "")
        print(f"{etq:>8}{row}")
    print("-" * (8 + 10 * len(Ks)))
    print(f"{'MEDIA':>8}" + "".join(f"{m(cols[K].mean()):>10,.0f}" for K in Ks))
    print(f"{'P(pierde)':>8}" + "".join(f"{(cols[K]<0).mean()*100:>9.0f}%" for K in Ks))
    print(f"{'P(util=0)':>8}" + "".join(f"{(cols[K]==(-K*args.valor)).mean()*100:>9.0f}%" for K in Ks))
    print(f"\nCosto de la pereza (quedarte en 2 vs ir a 4):")
    print(f"  E[util]: K2={m(cols[2].mean()):,.0f}k  K4={m(cols[4].mean()):,.0f}k  -> dejas {m(cols[4].mean()-cols[2].mean()):,.0f}k en la mesa")
    print(f"  Mejor decil (D10): K2={m(cols[2][9*S//10:].mean()):,.0f}k  K4={m(cols[4][9*S//10:].mean()):,.0f}k")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
