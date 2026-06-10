#!/usr/bin/env python3
"""
LEMAITRE — ¿cuánto vale la ALEATORIEDAD y DÓNDE meterla? (decorrelación de planillas)

Misma idea que en CSC: comprar K planillas y diferenciarlas en las decisiones
BARATAS y de ALTA VARIANZA decorrelaciona la cola superior y multiplica P(1º),
casi sin costar E[puntos]. Aquí medimos, por separado, el valor de meter
aleatoriedad en:
  - MARCADORES (1430 pts, 37%): lotería de marcador exacto -> el lugar más barato.
  - GRUPOS cerrados (1º/2º casi 50-50): swap con crédito 'invertido' que amortigua.
  - BRACKET disputado (cruces de contendientes parejos): caro pero alto impacto.

Para cada estrategia, K y N reporta E[util], P(1º), P(top3) y el COSTO en
E[puntos] de la planilla (para ver el trade-off).

    python pollas/LEMAITRE/aleatoriedad_lemaitre.py --mock /tmp/wc_grupos.json
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.LEMAITRE.modelo_lemaitre as M
import pollas.LEMAITRE.competencia_lemaitre as C

PTS, R32, SIG = M.PTS, M.R32, M.SIG
KO_SLOTS = [89,90,91,92,93,94,95,96,97,98,99,100,101,102,104]


def top_marcadores(gA, gB, pe, orient, n=6):
    """Lista [(marc,(a,b)), ev] ordenada desc, respetando orientación del ganador."""
    exact, res, parc = pe; cand = []
    for a in range(7):
        for b in range(7):
            if orient == "A" and a < b: continue
            if orient == "B" and a > b: continue
            ex = (gA == a) & (gB == b)
            rm = (np.sign(a - b) == np.sign(gA - gB)) & ~ex
            pm = ((gA == a) | (gB == b)) & ~ex & (np.sign(a - b) != np.sign(gA - gB))
            cand.append(((a, b), ex.mean()*exact + rm.mean()*res + pm.mean()*parc))
    cand.sort(key=lambda x: -x[1])
    return cand[:n]


def construir_planilla(grupo_ord, thirds, flips, marc_ovr, atk, dfn, tid, inv, score):
    """Arma una planilla (dict para puntuar) dada: orden de grupos (tids 1..4 por
    grupo), terceros por slot, set de slots con ganador volteado (underdog), y
    overrides de marcador {slot:(a,b)}."""
    def occp(code, sl):
        if code.startswith("3:"): return thirds[sl]
        return grupo_ord[code[1]][int(code[0]) - 1]
    r32 = {sl: (occp(c1, sl), occp(c2, sl)) for sl, c1, c2 in R32}
    win = {}; arbol = {}
    for sl, _, _ in R32:
        A, B = r32[sl]; fav = A if M.p_gana(atk, dfn, A, B) >= 0.5 else B
        und = B if fav == A else A
        win[sl] = und if sl in flips else fav; arbol[sl] = (A, B, win[sl])
    for sl in KO_SLOTS:
        x, y = SIG[sl]; A, B = win[x], win[y]
        fav = A if M.p_gana(atk, dfn, A, B) >= 0.5 else B; und = B if fav == A else A
        win[sl] = und if sl in flips else fav; arbol[sl] = (A, B, win[sl])
    la = arbol[101][0] if win[101] == arbol[101][1] else arbol[101][1]
    lb = arbol[102][0] if win[102] == arbol[102][1] else arbol[102][1]
    fav = la if M.p_gana(atk, dfn, la, lb) >= 0.5 else lb
    win[103] = fav; arbol[103] = (la, lb, fav)
    honor = {1: win[104], 2: (arbol[104][0] if win[104]==arbol[104][1] else arbol[104][1]),
             3: win[103], 4: (la if win[103]==lb else lb)}
    marc = {}
    for sl in PTS:
        if sl in marc_ovr:
            marc[sl] = marc_ovr[sl]; continue
        A, B, gw = arbol[sl]
        orient = "A" if gw == A else ("B" if gw == B else None)
        marc[sl] = M.evmax_marcador(score[sl][0], score[sl][1], PTS[sl], orient)[0]
    return dict(grupo={g: grupo_ord[g] for g in grupo_ord}, r32=r32, arbol=arbol,
                marc=marc, honor=honor)


def reparto(our, pool, N, K, valor, rng, prem=(0.6, 0.3, 0.1)):
    """E[util], P(1º), P(top3) repartiendo premios (con desempates por split)."""
    Kp, S = our.shape; pozo = 0.9 * N * valor
    fr = np.array(prem) * pozo
    util = np.zeros(S); p1 = np.zeros(S); ptop = np.zeros(S)
    P = pool.shape[0]
    for s in range(S):
        riv = pool[rng.integers(0, P, max(N - K, 0)), s]
        vals = np.concatenate([our[:, s], riv])
        mine = np.zeros(len(vals), bool); mine[:K] = True
        order = np.argsort(-vals); vs = vals[order]; ms = mine[order]
        # asignar fracciones a las 3 primeras posiciones, split por empate
        got = 0.0; pos = 0; got1 = False; got3 = False
        while pos < len(vs) and pos < 3:
            j = pos
            while j + 1 < len(vs) and vs[j + 1] == vs[pos]: j += 1   # grupo empatado
            tie = list(range(pos, j + 1))
            cubre = [k for k in tie if k < 3]
            premio_grupo = fr[cubre].sum() if cubre else 0.0
            nmios = sum(ms[k] for k in tie)
            if nmios:
                got += premio_grupo * nmios / len(tie)
                if pos == 0: got1 = True
                got3 = True
            pos = j + 1
        util[s] = got; p1[s] = got1; ptop[s] = got3
    return util.mean() - K * valor, p1.mean(), ptop.mean()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=5000)
    ap.add_argument("--valor", type=int, default=234000)
    ap.add_argument("--p-afilado", type=float, default=0.12)
    ap.add_argument("--pool", type=int, default=400)
    args = ap.parse_args(argv)

    realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv = C.construir(args)
    S = realiz["S"]; score = realiz["score"]
    G = M.GRUPOS_OFICIALES
    base_grupo = {g: list(nuestra["grupo"][g]) for g in G}
    thirds = {sl: nuestra["r32"][sl][0] if False else None for sl in M.slot3}
    for sl in M.slot3:  # tercero modal usado en la base
        # recuperar del r32_occ base: el lado 3: es el que coincide con tercer slot
        for s2, c1, c2 in R32:
            if s2 == sl:
                thirds[sl] = nuestra["r32"][sl][0] if c1.startswith("3:") else nuestra["r32"][sl][1]

    # ---- diagnóstico: dónde es BARATO meter aleatoriedad ----
    flex = []   # (slot, margen best-2nd, alternativas)
    for sl in PTS:
        A, B, gw = nuestra["arbol"][sl]
        orient = "A" if gw == A else ("B" if gw == B else None)
        tm = top_marcadores(score[sl][0], score[sl][1], PTS[sl], orient, 4)
        margen = tm[0][1] - tm[1][1]
        flex.append((sl, margen, [m for m, _ in tm]))
    flex.sort(key=lambda x: x[1])
    flex_slots = [f for f in flex if f[1] < 1.5]    # baratos: 2ª opción casi igual
    cerrados = sorted(G, key=lambda g: abs(
        max(Pgrupo[(g,1)].values()) - sorted(Pgrupo[(g,1)].values())[-2]))[:4]
    print(f"Decisiones BARATAS para aleatorizar:")
    print(f"  · {len(flex_slots)} marcadores con 2ª opción casi igual (margen<1.5 pts)")
    print(f"  · grupos más cerrados (1º/2º): {', '.join(cerrados)}")

    # ---- generador de K planillas por estrategia ----
    def variantes(K, tipos):
        outs = [construir_planilla(base_grupo, thirds, set(), {}, atk, dfn, tid, inv, score)]
        for j in range(1, K):
            grupo = {g: list(base_grupo[g]) for g in G}
            flips = set(); ovr = {}
            if "marc" in tipos:
                for i, (sl, mg, alts) in enumerate(flex_slots):
                    ovr[sl] = alts[(j + i) % len(alts)]      # 2ª/3ª opción rotando
            if "grupos" in tipos:
                g = cerrados[(j - 1) % len(cerrados)]
                grupo[g][0], grupo[g][1] = grupo[g][1], grupo[g][0]   # swap 1º/2º
            if "bracket" in tipos:
                # voltear un cruce disputado de cuartos/semis rotando
                flips.add([97, 98, 99, 100, 101, 102][(j - 1) % 6])
            outs.append(construir_planilla(grupo, thirds, flips, ovr, atk, dfn, tid, inv, score))
        return np.stack([C.puntuar(e, realiz) for e in outs])   # (K,S)

    # ---- pool de rivales ----
    rng = np.random.default_rng(7); K0 = args.pool
    thetas = np.where(rng.random(K0) < args.p_afilado, rng.beta(6, 2, K0), rng.beta(2, 4, K0))
    pool = np.stack([C.puntuar(C.planilla_rival(float(t), Pgrupo, nuestra, atk, dfn, tid, inv, rng), realiz)
                     for t in thetas])
    base_pts = C.puntuar(nuestra, realiz)
    print(f"\nNuestra base E[pts]={base_pts.mean():.0f} · pool rival medio={pool.mean():.0f} "
          f"(p_afilado={args.p_afilado:.0%})\n")

    estr = {"identicas": (), "+marcadores": ("marc",),
            "+marc+grupos": ("marc", "grupos"), "+marc+grupos+bracket": ("marc", "grupos", "bracket")}
    rngp = np.random.default_rng(99)
    for N in (50, 100):
        print(f"================  N = {N} inscritos  ================")
        print(f"{'estrategia':24} {'K':>2} {'E[pts]plla':>10} {'P(1º)':>7} {'P(top3)':>8} {'E[utilidad]':>14}")
        for nombre, tipos in estr.items():
            for K in (1, 2, 3, 5):
                if K == 1 and nombre != "identicas":
                    continue
                pts = variantes(K, tipos)
                util, p1, ptop = reparto(pts, pool, N, K, args.valor, rngp)
                etiqueta = "1 planilla" if K == 1 else nombre
                print(f"{etiqueta:24} {K:>2} {pts.mean():>10.0f} {p1*100:>6.1f}% {ptop*100:>7.1f}% ${util:>13,.0f}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
