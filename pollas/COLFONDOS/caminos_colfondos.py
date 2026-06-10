#!/usr/bin/env python3
"""
COLFONDOS — CAMINOS ADAPTATIVOS con 2+ plazas (política de riesgo según el field).

La polla se gana superando al líder del field. Si vas ATRÁS necesitas VARIANZA
(arriesgar marcadores hacia upside); si vas ADELANTE, la proteges. Con 2 plazas,
una es ANCLA (EV-máx, segura) y la otra se DISPERSA según el déficit.

Este motor recomienda, para cada déficit D (puntos que te saca el líder) y cada
fracción de torneo que falta, el RIESGO óptimo de la 2ª plaza, y cuánto sube
P(1º). Re-córrelo después de cada jornada con tu D real.

    python pollas/COLFONDOS/caminos_colfondos.py --mock /tmp/wc_grupos.json
"""
import argparse, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.LEMAITRE.modelo_lemaitre as M
import pollas.COLFONDOS.competencia_colfondos as CC
import pollas.COLFONDOS.marcadores_colfondos as CM


def build_entry(realiz, arbol, Padv, tid, inv, nivel=0, frac=1.0, seed=0, champ_alt=None):
    """Entrada COLFONDOS con NIVEL de dispersión (0=ancla EV-máx .. 4=contrario
    fuerte). La dispersión combina: decorrelar marcadores (busca-varianza en los
    flex), burbuja de clasificados y, lo más potente, una TESIS de campeón
    distinta (champ_alt). frac = fracción de torneo por jugar (a eso se aplica)."""
    rng = np.random.default_rng(seed)
    score = realiz["score"]
    risk = {0: 0.0, 1: 0.8, 2: 1.5, 3: 2.0, 4: 3.0}.get(nivel, 0.0)
    pflex = {0: 0.0, 1: 0.25, 2: 0.4, 3: 0.6, 4: 0.8}.get(nivel, 0.0)
    mg = {}
    for key, Mx in realiz["Mmat"].items():
        if nivel > 0 and rng.random() < pflex * frac:
            (a, b), _, _ = CM.evmax_riesgo(Mx, risk)
        else:
            (a, b), _ = CM.evmax(Mx)
        mg[key] = (a, b)
    mk = {}
    for sl in CC.KO:
        A, B, gw = arbol[sl]; orient = "A" if gw == A else ("B" if gw == B else None)
        (a, b), _ = M.evmax_marcador(score[sl][0], score[sl][1], M.PTS.get(sl, (4, 3, 1)), orient)
        mk[sl] = (a, b)
    # tesis de campeón: nivel bajo = la del árbol; nivel alto = champ_alt (contraria)
    if champ_alt is not None and nivel >= 3:
        h = {1: champ_alt[0], 2: champ_alt[1], 3: champ_alt[2]}
    else:
        h = {1: arbol[104][2], 2: (arbol[104][0] if arbol[104][2] == arbol[104][1] else arbol[104][1]),
             3: arbol[103][2]}
    orden = list(np.argsort(-Padv))
    if nivel >= 2:  # burbuja: variar puestos 26-32
        cl = orden[:25] + [orden[25 + (k + seed) % 11] for k in range(7)]
    else:
        cl = orden[:32]
    return dict(mg=mg, mk=mk, honor=h, clasif=set(int(x) for x in cl))


def build_pool(realiz, arbol, Padv, tid, inv, p_afilado, POOL=500, seed=7):
    rng = np.random.default_rng(seed)
    thetas = np.where(rng.random(POOL) < p_afilado, rng.beta(6, 2, POOL), rng.beta(2, 4, POOL))
    grandes = [tid[t] for t in ("Brazil", "Argentina", "Spain", "France", "England") if t in tid]
    orden = list(np.argsort(-Padv)); pool = np.zeros((POOL, realiz["S"]))
    for kk in range(POOL):
        th = float(thetas[kk]); e = dict(mg={}, mk={}, honor={}, clasif=set())
        for key, Mx in realiz["Mmat"].items():
            e["mg"][key] = CM.evmax(Mx)[0] if rng.random() < th else [(1,0),(2,1),(1,1),(2,0),(0,0)][rng.integers(5)]
        for sl in CC.KO:
            if rng.random() < th:
                A, B, gw = arbol[sl]; o = "A" if gw == A else ("B" if gw == B else None)
                e["mk"][sl] = M.evmax_marcador(realiz["score"][sl][0], realiz["score"][sl][1], M.PTS.get(sl,(4,3,1)), o)[0]
            else:
                e["mk"][sl] = [(1,0),(2,1),(1,1)][rng.integers(3)]
        e["honor"] = {1: arbol[104][2] if rng.random()<th else grandes[rng.integers(len(grandes))],
                      2: arbol[104][1] if rng.random()<th else grandes[rng.integers(len(grandes))],
                      3: arbol[103][2]}
        e["clasif"] = set(int(x) for x in (orden[:32] if rng.random()<th else orden[:28]+list(rng.choice(orden[28:40],4,replace=False))))
        pool[kk] = CC.puntuar(e, realiz)
    return pool


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=3000)
    ap.add_argument("--inscritos", type=int, default=50)
    ap.add_argument("--p-afilado", type=float, default=0.12)
    ap.add_argument("--frac", type=float, default=1.0, help="fracción de torneo por jugar")
    args = ap.parse_args(argv)
    realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv = CC.construir(args)
    S = realiz["S"]; N = args.inscritos
    pool = build_pool(realiz, arbol, Padv, tid, inv, args.p_afilado)

    # tesis de campeón contrarias (coherentes con las mitades del cuadro)
    # mitad 1 (semi 101): España, Francia · mitad 2 (semi 102): Inglaterra, Portugal
    def t(name): return tid[name]
    TESIS = {
        "Francia":   (t("France"), t("England"), t("Spain")),
        "Inglaterra":(t("England"), t("Spain"), t("Portugal")),
        "Portugal":  (t("Portugal"), t("Spain"), t("France")),
    }
    # ancla A (nivel 0) y candidatas de 2ª plaza (nivel + tesis)
    A = build_entry(realiz, arbol, Padv, tid, inv, 0, args.frac, seed=1)
    pA = CC.puntuar(A, realiz)
    cands = {"n1 (decorr marc)": build_entry(realiz, arbol, Padv, tid, inv, 1, args.frac, seed=2),
             "n2 (+burbuja)":    build_entry(realiz, arbol, Padv, tid, inv, 2, args.frac, seed=3),
             "n3 campeón=Francia": build_entry(realiz, arbol, Padv, tid, inv, 3, args.frac, seed=4, champ_alt=TESIS["Francia"]),
             "n4 campeón=Inglaterra": build_entry(realiz, arbol, Padv, tid, inv, 4, args.frac, seed=5, champ_alt=TESIS["Inglaterra"]),
             "n4 campeón=Portugal": build_entry(realiz, arbol, Padv, tid, inv, 4, args.frac, seed=6, champ_alt=TESIS["Portugal"])}
    pB = {k: CC.puntuar(v, realiz) for k, v in cands.items()}
    print(f"Ancla A (España, EV-máx): E[pts]={pA.mean():.0f} std={pA.std():.0f}")
    for k in pB: print(f"  2ª {k:24} E[pts]={pB[k].mean():.0f} std={pB[k].std():.0f}")

    rng = np.random.default_rng(3); P = pool.shape[0]
    def pgana(best, deficit):
        w = 0.0
        for s in range(S):
            riv = pool[rng.integers(0, P, max(N - 2, 0)), s].max() + deficit
            w += best[s] > riv
        return w / S

    print(f"\n=== POLÍTICA: qué camino dar a la 2ª plaza según DÉFICIT (N={N}, frac={args.frac}) ===")
    print(f"{'déficit':>8} {'P(1º) sólo A':>12}  mejor 2ª plaza               {'P(1º) A+B':>10}")
    for D in (-30, -15, 0, 15, 30, 50, 80):
        solo = pgana(pA, D)
        best_k, best_p = None, -1
        for k in pB:
            p = pgana(np.maximum(pA, pB[k]), D)
            if p > best_p: best_p, best_k = p, k
        print(f"{D:>+8} {solo*100:>11.1f}%  {best_k:28} {best_p*100:>9.1f}%")
    print("\nLeer: D>0 = vas ATRÁS del líder. Cerca/adelante -> 2ª plaza decorrela suave")
    print("(misma tesis España). Atrás -> 2ª plaza cambia la TESIS de campeón (camino")
    print("contrario) para cubrir el escenario donde España NO gana. Re-correr cada")
    print("jornada con tu D real y --frac. Comprar una 3ª plaza = cubrir una tesis más.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
