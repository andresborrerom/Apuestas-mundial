#!/usr/bin/env python3
"""
LEMAITRE — modelo de COMPETENCIA y VALOR ESPERADO DE GANANCIAS.

Convierte E[puntos] en E[dinero]. Premio: 90% de lo recaudado, 60/30/10 (1/2/3).
La polla se GANA superando al campo, no maximizando E[pts]: con varianza alta,
muchos rivales "afilados" se agrupan en clasificación y el ganador se decide por
los aciertos raros de marcador. Esto cuantifica P(1º/2º/3º) y E[ganancia] como
función del nº de inscritos N, y de cuántas planillas compremos.

    python pollas/LEMAITRE/competencia_lemaitre.py --mock /tmp/wc_grupos.json \
        --inscritos 60 --valor 234000 --planillas 1

Supuestos del campo (documentados, ajustables con --p-afilado):
  cada rival tiene una 'habilidad' θ~Beta: θ alto -> elige cerca de lo óptimo;
  θ bajo -> ruido sentimental (nombres grandes, marcadores comunes). Es una
  hipótesis del campo, no un hecho — se reporta sensibilidad.
"""
import argparse, json, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api, cuotas, marcadores, ratings as R
from pollas.CSC.cupos import matriz_de_evento
import pollas.LEMAITRE.modelo_lemaitre as M

PTS, R32, SIG, ETIQUETA = M.PTS, M.R32, M.SIG, M.ETIQUETA
GRUPOS = M.GRUPOS_OFICIALES
MARC_COMUNES = [(1,0),(2,1),(1,1),(2,0),(0,0),(0,1),(1,2),(3,1),(2,2),(0,2)]


def construir(args):
    """Una corrida: realiz (S torneos simulados), ratings calibrados, y nuestros
    picks EV-máx. Devuelve todo lo necesario para puntuar planillas."""
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    part = M.cargar(eventos)
    rat, _ = R.ajustar_ratings([(h, a, lh, la) for h, a, lh, la, _ in part])
    teams = sorted(rat); tid = {t: i for i, t in enumerate(teams)}; NT = len(teams); inv = teams
    atk0 = np.array([rat[t][0] for t in teams]); dfn0 = np.array([rat[t][1] for t in teams])
    S = args.sims; rng = np.random.default_rng(0)
    pos, tercer_slot, gf, gc, avanza, gl = M.sim_grupos(part, tid, NT, S, rng)
    ent_r32 = M.entradas_r32(pos, tercer_slot)
    futures = json.load(open(args.futures)) if os.path.exists(args.futures) else {}
    if futures:
        delta, _, _, _ = M.calibrar(atk0, dfn0, ent_r32, teams, tid, futures, S)
        atk, dfn = atk0 + delta, dfn0 + delta
    else:
        atk, dfn = atk0, dfn0
    occ, score, ganador, perdedor = M.jugar_ko(atk, dfn, ent_r32, rng)
    realiz = dict(pos=pos, ent_r32=ent_r32, score=score, ganador=ganador, perdedor=perdedor,
                  campeon=ganador[104], subcampeon=perdedor[104], tercero=ganador[103],
                  cuarto=perdedor[103], gf=gf, gc=gc, tid=tid, inv=inv, S=S)
    # probabilidades marginales (para generar el campo)
    Pgrupo = {}      # (g,puesto) -> {tid: prob}
    for g in GRUPOS:
        for pu in range(1, 5):
            c = Counter(pos[(g, pu)].tolist()); Pgrupo[(g, pu)] = {k: v / S for k, v in c.items()}
    # nuestros picks EV-máx (mismo criterio que modelo_lemaitre)
    grupo_pick = {}
    for g, ts in GRUPOS.items():
        Pp = {t: [Pgrupo[(g, pu)].get(tid[t], 0) for pu in range(1, 5)] for t in ts}
        libres = set(ts); orden = []
        for pu in range(4):
            b = max(libres, key=lambda t: Pp[t][pu]); orden.append(b); libres.discard(b)
        grupo_pick[g] = [tid[t] for t in orden]
    tercer_pick = {sl: tid[M.top(tercer_slot[sl], inv, S, 1)[0][0]] for sl in M.slot3}
    def occp(code, sl):
        if code.startswith("3:"): return tercer_pick[sl]
        return grupo_pick[code[1]][int(code[0]) - 1]
    r32_occ = {sl: (occp(c1, sl), occp(c2, sl)) for sl, c1, c2 in R32}
    arbolN = M.arbol_consistente(atk, dfn, tid, inv, {sl: (inv[a], inv[b]) for sl, (a, b) in r32_occ.items()})
    arbol = {sl: (tid[A], tid[B], tid[g]) for sl, (A, B, g) in arbolN.items()}
    # marcador EV-máx, orientado a coherencia con el ganador del árbol
    pick_marc = {}
    for sl in PTS:
        A, B, gw = arbol[sl]
        orient = "A" if gw == A else ("B" if gw == B else None)
        pick_marc[sl] = M.evmax_marcador(score[sl][0], score[sl][1], PTS[sl], orient=orient)[0]
    nuestra = dict(grupo=grupo_pick, r32=r32_occ, arbol=arbol, marc=pick_marc,
                   honor={1: arbol[104][2], 2: (arbol[104][0] if arbol[104][2]==arbol[104][1] else arbol[104][1]),
                          3: arbol[103][2], 4: (arbol[103][0] if arbol[103][2]==arbol[103][1] else arbol[103][1])})
    return realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv


def puntuar(entry, realiz):
    """Puntos LEMAITRE (vectorizado sobre S) de una planilla 'entry'."""
    S = realiz["S"]; pos = realiz["pos"]; score = realiz["score"]
    ganador = realiz["ganador"]; ent_r32 = realiz["ent_r32"]
    pts = np.zeros(S)
    # marcadores (exacto)
    for sl in entry["marc"]:
        a, b = entry["marc"][sl]; gA, gB = score[sl]; ex_, re_, pa_ = PTS[sl]
        exact = (gA == a) & (gB == b)
        result = (~exact) & (np.sign(a - b) == np.sign(gA - gB))
        partial = (~exact) & (~result) & ((gA == a) | (gB == b))
        pts += exact * ex_ + result * re_ + partial * pa_
    # clasificacion (aprox lineal por presupuesto, igual que modelo_lemaitre)
    aA = np.zeros(S)
    for sl, c1, c2 in R32:
        Ar, Br = ent_r32[sl]; oa, ob = entry["r32"][sl]
        aA += (Ar == oa) + (Br == ob)
    pts += aA / 32.0 * 640
    aB = np.zeros(S)
    for g in GRUPOS:
        aB += (pos[(g, 1)] == entry["grupo"][g][0]) + (pos[(g, 2)] == entry["grupo"][g][1])
    pts += aB / 24.0 * 280
    woct = np.stack([ganador[s] for s in range(89, 97)])
    cuartos = set(entry["arbol"][s][2] for s in range(89, 97))
    aC = sum((woct == p).any(axis=0) for p in cuartos)
    pts += aC / 8.0 * 240
    wcua = np.stack([ganador[s] for s in range(97, 101)])
    semis = set(entry["arbol"][s][2] for s in range(97, 101))
    aD = sum((wcua == p).any(axis=0) for p in semis)
    pts += aD / 4.0 * 160
    # cuadro de honor (G, exacto) + semis (E)
    rp = {1: realiz["campeon"], 2: realiz["subcampeon"], 3: realiz["tercero"], 4: realiz["cuarto"]}
    setreal = np.stack([rp[1], rp[2], rp[3], rp[4]])
    hp = {1: 80, 2: 60, 3: 40, 4: 30}
    for k in (1, 2, 3, 4):
        ex = rp[k] == entry["honor"][k]
        inh = (setreal == entry["honor"][k]).any(axis=0) & (~ex)
        pts += ex * hp[k] + inh * 25
    fin = np.stack([rp[1], rp[2]]); per = np.stack([rp[3], rp[4]])
    for p in (entry["honor"][1], entry["honor"][2]):
        pts += (fin == p).any(axis=0) * 55
    for p in (entry["honor"][3], entry["honor"][4]):
        pts += (per == p).any(axis=0) * 40
    return pts


def planilla_rival(theta, Pgrupo, nuestra, atk, dfn, tid, inv, rng):
    """Genera una planilla rival con 'habilidad' theta in [0,1].
    theta=1 -> idéntica a la óptima; theta bajo -> ruido sentimental."""
    grupo = {}
    for g in GRUPOS:
        if rng.random() < theta:
            grupo[g] = list(nuestra["grupo"][g])
        else:  # muestrea orden segun prob marginal (mas disperso)
            ts = [tid[t] for t in GRUPOS[g]]
            w = np.array([max(sum(Pgrupo[(g, pu)].get(t, 0) for pu in (1, 2)), 1e-3) for t in ts])
            o1 = rng.choice(ts, p=w / w.sum())
            rest = [t for t in ts if t != o1]
            w2 = np.array([Pgrupo[(g, 2)].get(t, 0) + 1e-3 for t in rest])
            o2 = rng.choice(rest, p=w2 / w2.sum())
            rest2 = [t for t in rest if t != o2]
            grupo[g] = [o1, o2] + list(rng.permutation(rest2))
    # bracket: con prob theta sigue al favorito (árbol óptimo); si no, deja pasar al otro a veces
    r32 = {}
    for sl, c1, c2 in R32:
        a = grupo[c1[1]][int(c1[0]) - 1] if not c1.startswith("3:") else nuestra["r32"][sl][0]
        b = grupo[c2[1]][int(c2[0]) - 1] if not c2.startswith("3:") else nuestra["r32"][sl][1]
        r32[sl] = (a, b)
    win = {}
    for sl, _, _ in R32:
        a, b = r32[sl]; pa = M.p_gana(atk, dfn, a, b)
        fav = a if pa >= 0.5 else b; under = b if pa >= 0.5 else a
        win[sl] = fav if rng.random() < (theta * 0.5 + 0.5) else under
    arbol = {}
    for sl, _, _ in R32:
        arbol[sl] = (r32[sl][0], r32[sl][1], win[sl])
    for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,104]:
        x, y = SIG[sl]; a, b = win[x], win[y]; pa = M.p_gana(atk, dfn, a, b)
        fav = a if pa >= 0.5 else b; under = b if pa >= 0.5 else a
        win[sl] = fav if rng.random() < (theta * 0.5 + 0.5) else under
        arbol[sl] = (a, b, win[sl])
    la = arbol[101][0] if win[101] == arbol[101][1] else arbol[101][1]
    lb = arbol[102][0] if win[102] == arbol[102][1] else arbol[102][1]
    pa = M.p_gana(atk, dfn, la, lb); w3 = la if (pa >= 0.5) == (rng.random() < (theta*0.5+0.5)) else lb
    arbol[103] = (la, lb, w3)
    honor = {1: win[104], 2: (arbol[104][0] if win[104]==arbol[104][1] else arbol[104][1]),
             3: w3, 4: (la if w3 == lb else lb)}
    # marcadores: con prob theta el EV-máx; si no, un marcador comun al azar
    marc = {}
    for sl in PTS:
        if rng.random() < theta:
            marc[sl] = nuestra["marc"][sl]
        else:
            marc[sl] = MARC_COMUNES[rng.integers(len(MARC_COMUNES))]
    return dict(grupo=grupo, r32=r32, arbol=arbol, marc=marc, honor=honor)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--inscritos", type=int, default=0, help="N inscritos (0 = barrido)")
    ap.add_argument("--valor", type=int, default=234000)
    ap.add_argument("--planillas", type=int, default=1, help="cuántas planillas compramos")
    ap.add_argument("--p-afilado", type=float, default=0.25, help="fracción de rivales 'afilados'")
    ap.add_argument("--pool", type=int, default=400, help="tamaño del pool de rivales simulados")
    args = ap.parse_args(argv)

    realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv = construir(args)
    S = realiz["S"]
    nuestros_pts = puntuar(nuestra, realiz)            # (S,)
    print(f"Nuestra planilla: E[pts]={nuestros_pts.mean():.0f}  p10={np.percentile(nuestros_pts,10):.0f} "
          f"p90={np.percentile(nuestros_pts,90):.0f}  (sin extras de jugador)")

    # pool de rivales: habilidad theta mezcla afilados (Beta(6,2)) y casuales (Beta(2,4))
    rng = np.random.default_rng(7)
    K = args.pool
    thetas = np.where(rng.random(K) < args.p_afilado, rng.beta(6, 2, K), rng.beta(2, 4, K))
    pool = np.zeros((K, S))
    for k in range(K):
        e = planilla_rival(float(thetas[k]), Pgrupo, nuestra, atk, dfn, tid, inv, rng)
        pool[k] = puntuar(e, realiz)
    print(f"Pool de {K} rivales: E[pts] medio={pool.mean():.0f}  (afilados~{args.p_afilado:.0%})")

    # si compramos varias planillas, generamos variantes perturbadas y tomamos el MAX por sim
    def nuestras_planillas(nplan):
        outs = [nuestros_pts]
        for j in range(1, nplan):
            e = planilla_rival(0.97, Pgrupo, nuestra, atk, dfn, tid, inv,
                               np.random.default_rng(1000 + j))  # casi óptima, ligeramente distinta
            outs.append(puntuar(e, realiz))
        return np.max(np.stack(outs), axis=0)

    def e_ganancia(N, nplan):
        pozo = 0.90 * N * args.valor
        nuestro = nuestras_planillas(nplan)
        # por sim: CDF empírica del pool -> prob de superar a un rival al azar; los
        # N-nplan rivales se tratan como iid del pool (aprox del campo)
        P1 = P2 = P3 = 0.0
        for s in range(S):
            f = np.mean(pool[:, s] < nuestro[s])
            others = max(N - nplan, 0)
            P1 += f ** others
            P2 += others * (1 - f) * f ** (others - 1) if others >= 1 else 0
            P3 += (others * (others - 1) / 2) * (1 - f) ** 2 * f ** (others - 2) if others >= 2 else 0
        P1 /= S; P2 /= S; P3 /= S
        premio = pozo * (0.60 * P1 + 0.30 * P2 + 0.10 * P3)
        costo = nplan * args.valor
        return P1, P2, P3, premio, premio - costo

    Ns = [args.inscritos] if args.inscritos else [30, 50, 80, 120, 200]
    print(f"\nValor: ${args.valor:,} · planillas compradas: {args.planillas}")
    print(f"{'N':>5} {'P(1º)':>7} {'P(2º)':>7} {'P(3º)':>7} {'E[premio]':>13} {'E[util=premio-costo]':>22}")
    for N in Ns:
        P1, P2, P3, premio, util = e_ganancia(N, args.planillas)
        print(f"{N:>5} {P1*100:6.1f}% {P2*100:6.1f}% {P3*100:6.1f}% ${premio:>12,.0f} ${util:>20,.0f}")

    if not args.inscritos:
        print("\nComparativa nº de planillas (N=80):")
        print(f"{'planillas':>9} {'P(1º)':>7} {'E[premio]':>13} {'E[util]':>15}")
        for nplan in (1, 2, 3, 5):
            P1, P2, P3, premio, util = e_ganancia(80, nplan)
            print(f"{nplan:>9} {P1*100:6.1f}% ${premio:>12,.0f} ${util:>14,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
