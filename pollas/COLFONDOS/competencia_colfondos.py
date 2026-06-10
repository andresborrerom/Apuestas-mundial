#!/usr/bin/env python3
"""
COLFONDOS — ¿cuántas entradas (decorreladas) y cuánto suben las chances? (N=50)

COLFONDOS está DOMINADO por marcadores (~104 partidos × hasta 9 pts) + outrights
(campeón/sub/3º/clasificados/malla). Es muy de varianza, así que decorrelar
muchas entradas (sobre todo en marcadores) multiplica P(1º). Esto simula el
torneo, puntúa N=50 rivales casuales + K entradas nuestras decorreladas, y da
P(1º)/P(top3) vs K.

(No incluye premios de jugador ~55 pts: correlacionados y chicos frente a ~300+
de marcadores; se omiten en la competencia. Pollaya: entradas ilimitadas.)

    python pollas/COLFONDOS/competencia_colfondos.py --mock /tmp/wc_grupos.json
"""
import argparse, json, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api, cuotas, marcadores, ratings as R
from pollas.CSC.cupos import matriz_de_evento
import pollas.LEMAITRE.modelo_lemaitre as M
import pollas.LEMAITRE.competencia_lemaitre as C
import pollas.COLFONDOS.marcadores_colfondos as CM

KO = [s for s, _, _ in M.R32] + [89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104]


def cf_pts(pred, gx, gy):
    """puntos COLFONDOS (vectorizado sobre S) de un pick (a,b) vs marcador real."""
    a, b = pred
    s = 3 * (np.sign(a - b) == np.sign(gx - gy))
    s = s + 1 * ((a - b) == (gx - gy))
    s = s + 1 * (a == gx) + 1 * (b == gy)   # goles de CADA equipo (per-team)
    s = s + 4 * ((a == gx) & (gy == b))
    return s


def construir(args):
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    part = M.cargar(eventos)
    rat, _ = R.ajustar_ratings([(h, a, lh, la) for h, a, lh, la, _ in part])
    teams = sorted(rat); tid = {t: i for i, t in enumerate(teams)}; NT = len(teams); inv = teams
    atk0 = np.array([rat[t][0] for t in teams]); dfn0 = np.array([rat[t][1] for t in teams])
    S = args.sims; rng = np.random.default_rng(0)
    # --- simular grupos GUARDANDO marcador de cada partido ---
    pts = np.zeros((NT, S)); gd = np.zeros((NT, S)); gf = np.zeros((NT, S)); gc = np.zeros((NT, S))
    gmatch = {}                       # (h,a) -> (gh(S,), ga(S,))
    Mmat = {}
    for h, a, _, _, Mx in part:
        fl = Mx.ravel() / Mx.sum(); k = rng.choice(fl.size, size=S, p=fl)
        gh, ga = k // Mx.shape[1], k % Mx.shape[1]; ih, ia = tid[h], tid[a]
        gmatch[(h, a)] = (gh, ga); Mmat[(h, a)] = Mx
        pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[ih] += gh - ga; gd[ia] += ga - gh; gf[ih] += gh; gf[ia] += ga
        gc[ih] += ga; gc[ia] += gh
    clave = pts * 1e6 + gd * 1e3 + gf + rng.random((NT, S)) * 1e-3
    pos = {}; tercer_key = {}
    for g, ts in M.GRUPOS_OFICIALES.items():
        ids = np.array([tid[t] for t in ts]); orden = np.argsort(-clave[ids], axis=0)
        for pu in range(4): pos[(g, pu + 1)] = ids[orden[pu]]
        tercer_key[g] = clave[ids][orden[2], np.arange(S)]
    gl = list(M.GRUPOS_OFICIALES); keys = np.array([tercer_key[g] for g in gl])
    avanza = np.argsort(-keys, axis=0)[:8]
    tercer_slot = {s: np.full(S, -1) for s in M.slot3}
    for s in range(S):
        disp = [gl[avanza[i, s]] for i in range(8)]
        for sl in sorted(M.slot3, key=lambda sl: len(M.slot3[sl] & set(disp))):
            for g in disp:
                if g in M.slot3[sl] and (tercer_slot[sl][s] == -1) and \
                   g not in [gl[avanza[i, s]] for i in range(8) if tercer_slot.get(sl, [-1])[s] != -1]:
                    pass
        # asignación simple (igual que modelo): más restringidos primero
        usados = set()
        for sl in sorted(M.slot3, key=lambda sl: len(M.slot3[sl] & set(disp))):
            for g in disp:
                if g not in usados and g in M.slot3[sl]:
                    tercer_slot[sl][s] = pos[(g, 3)][s]; usados.add(g); break
    ent_r32 = M.entradas_r32(pos, tercer_slot)
    # calibrar ratings a futures
    futures = json.load(open(args.futures)) if os.path.exists(args.futures) else {}
    if futures:
        delta, _, _, _ = M.calibrar(atk0, dfn0, ent_r32, teams, tid, futures, S)
        atk, dfn = atk0 + delta, dfn0 + delta
    else:
        atk, dfn = atk0, dfn0
    occ, score, ganador, perdedor = M.jugar_ko(atk, dfn, ent_r32, rng)
    # P(avanzar) por equipo
    adv = np.zeros((NT, S))
    for sl in M.R32:
        a, b = ent_r32[sl[0]]
        for arr in (a, b):
            m = arr >= 0; adv[arr[m], np.arange(S)[m]] = 1
    realiz = dict(gmatch=gmatch, Mmat=Mmat, score=score, ganador=ganador, perdedor=perdedor,
                  ent_r32=ent_r32, occ=occ, campeon=ganador[104], subcampeon=perdedor[104],
                  tercero=ganador[103], cuarto=perdedor[103], adv=adv, gc=gc, tid=tid,
                  inv=inv, S=S, pos=pos)
    # árbol coherente nuestro (para outrights + marcadores KO orientados)
    grupo_pick = {}
    for g, ts in M.GRUPOS_OFICIALES.items():
        Pp = {t: [Counter(pos[(g, pu)].tolist()).get(tid[t], 0) / S for pu in range(1, 5)] for t in ts}
        libres = set(ts); ordr = []
        for pu in range(4):
            bt = max(libres, key=lambda t: Pp[t][pu]); ordr.append(bt); libres.discard(bt)
        grupo_pick[g] = [tid[t] for t in ordr]
    tercer_pick = {sl: Counter(tercer_slot[sl][tercer_slot[sl] >= 0].tolist()).most_common(1)[0][0]
                   for sl in M.slot3}
    def occp(code, sl):
        return tercer_pick[sl] if code.startswith("3:") else grupo_pick[code[1]][int(code[0]) - 1]
    r32_occ = {sl: (occp(c1, sl), occp(c2, sl)) for sl, c1, c2 in M.R32}
    arbolN = M.arbol_consistente(atk, dfn, tid, inv, {s: (inv[a], inv[b]) for s, (a, b) in r32_occ.items()})
    arbol = {s: (tid[A], tid[B], tid[g]) for s, (A, B, g) in arbolN.items()}
    Padv = adv.mean(axis=1)
    return realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv


def entrada_nuestra(realiz, grupo_pick, r32_occ, arbol, Padv, tid, inv, j=0, decorrel=False, rng=None):
    """Construye una entrada (picks) COLFONDOS. j>0 + decorrel: variar marcadores,
    burbuja de clasificados y tesis de campeón para decorrelacionar."""
    score = realiz["score"]; gmatch = realiz["Mmat"]
    riesgo = 0.0 if j == 0 else 0.0
    # marcadores de grupo (EV-máx; si decorrel, 2ª opción en algunos)
    mg = {}
    for i, (key, Mx) in enumerate(gmatch.items()):
        (a, b), _ = CM.evmax(Mx)
        if decorrel and j > 0 and (i + j) % 3 == 0:
            # 2ª mejor: pequeña perturbación hacia marcador vecino
            alts = [(a, b + 1), (a + 1, b), (a, max(b - 1, 0))]
            a, b = alts[(i + j) % len(alts)]
        mg[key] = (a, b)
    # marcadores KO (EV-máx orientado al ganador del árbol)
    mk = {}
    for sl in KO:
        A, B, gw = arbol[sl]; orient = "A" if gw == A else ("B" if gw == B else None)
        (a, b), _ = M.evmax_marcador(score[sl][0], score[sl][1], M.PTS.get(sl, (4, 3, 1)), orient)
        if decorrel and j > 0 and (sl + j) % 4 == 0:
            a, b = (b, a) if a != b else (a, b + 1)
        mk[sl] = (a, b)
    # outrights coherentes (tesis): j=0 España; variar campeón para otras entradas
    h = {1: arbol[104][2], 2: (arbol[104][0] if arbol[104][2] == arbol[104][1] else arbol[104][1]),
         3: arbol[103][2]}
    if decorrel and j > 0:
        contend = [i for i, _ in Counter(realiz["campeon"].tolist()).most_common(5)]
        h = dict(h); h[1] = contend[j % len(contend)]
    # clasificados: top 32 por Padv; en burbuja (puestos 26-32) variar
    orden = list(np.argsort(-Padv))
    picks32 = orden[:32]
    if decorrel and j > 0:
        picks32 = orden[:25] + [orden[25 + (k + j) % 11] for k in range(7)]
    return dict(mg=mg, mk=mk, honor=h, clasif=set(int(x) for x in picks32))


def puntuar(e, realiz):
    S = realiz["S"]; p = np.zeros(S)
    for key, pred in e["mg"].items():
        gx, gy = realiz["gmatch"][key]; p = p + cf_pts(pred, gx, gy)
    for sl, pred in e["mk"].items():
        gx, gy = realiz["score"][sl]; p = p + cf_pts(pred, gx, gy)
    p = p + 20 * (realiz["campeon"] == e["honor"][1])
    p = p + 15 * (realiz["subcampeon"] == e["honor"][2])
    p = p + 10 * (realiz["tercero"] == e["honor"][3])
    cl = np.zeros(S)
    for t in e["clasif"]:
        cl = cl + realiz["adv"][t]
    p = p + 4 * cl
    return p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--inscritos", type=int, default=50)
    ap.add_argument("--p-afilado", type=float, default=0.12)
    args = ap.parse_args(argv)
    realiz, atk, dfn, grupo_pick, tercer_pick, r32_occ, arbol, Padv, teams, tid, inv = construir(args)
    S = realiz["S"]; N = args.inscritos
    base = entrada_nuestra(realiz, grupo_pick, r32_occ, arbol, Padv, tid, inv, 0)
    bp = puntuar(base, realiz)
    print(f"Entrada base COLFONDOS: E[pts]={bp.mean():.0f}  p10={np.percentile(bp,10):.0f} "
          f"p90={np.percentile(bp,90):.0f}")

    # field de N-? rivales casuales (nombres obvios): theta bajo en marcadores y outrights
    rng = np.random.default_rng(7); POOL = 500
    thetas = np.where(rng.random(POOL) < args.p_afilado, rng.beta(6, 2, POOL), rng.beta(2, 4, POOL))
    # rival = base con ruido segun theta (marcadores comunes; campeón nombre obvio)
    obvios = [i for i, _ in Counter(realiz["campeon"].tolist()).most_common(8)]
    nombres_grandes = [tid.get(t) for t in ("Brazil", "Argentina", "Spain", "France", "England") if t in tid]
    pool = np.zeros((POOL, S))
    for kk in range(POOL):
        th = float(thetas[kk]); e = dict(mg={}, mk={}, honor={}, clasif=set())
        for i, (key, Mx) in enumerate(realiz["Mmat"].items()):
            if rng.random() < th:
                (a, b), _ = CM.evmax(Mx)
            else:
                a, b = [(1, 0), (2, 1), (1, 1), (2, 0), (0, 0)][rng.integers(5)]
            e["mg"][key] = (a, b)
        for sl in KO:
            if rng.random() < th:
                A, B, gw = arbol[sl]; orient = "A" if gw == A else ("B" if gw == B else None)
                (a, b), _ = M.evmax_marcador(realiz["score"][sl][0], realiz["score"][sl][1], M.PTS.get(sl,(4,3,1)), orient)
            else:
                a, b = [(1,0),(2,1),(1,1)][rng.integers(3)]
            e["mk"][sl] = (a, b)
        camp = (arbol[104][2] if rng.random() < th else nombres_grandes[rng.integers(len(nombres_grandes))])
        e["honor"] = {1: camp, 2: arbol[104][1] if rng.random()<th else nombres_grandes[rng.integers(len(nombres_grandes))],
                      3: arbol[103][2]}
        orden = list(np.argsort(-Padv))
        e["clasif"] = set(int(x) for x in (orden[:32] if rng.random() < th else orden[:28] + list(rng.choice(orden[28:40], 4, replace=False))))
        pool[kk] = puntuar(e, realiz)
    print(f"Pool rival medio={pool.mean():.0f}\n")

    def nuestras(K, decorrel):
        outs = []
        for j in range(K):
            e = entrada_nuestra(realiz, grupo_pick, r32_occ, arbol, Padv, tid, inv, j, decorrel,
                                np.random.default_rng(100 + j))
            outs.append(puntuar(e, realiz))
        return np.stack(outs)

    rngp = np.random.default_rng(3)
    def chances(K, decorrel):
        our = nuestras(K, decorrel); P = pool.shape[0]
        p1 = ptop = 0.0
        for s in range(S):
            riv = pool[rngp.integers(0, P, max(N - K, 0)), s]
            best = our[:, s].max()
            below = np.sum(riv < best)
            p1 += (below == len(riv)); ptop += (below >= len(riv) - 2)
        return our.mean(), p1 / S, ptop / S

    print(f"{'K entradas':>10} {'decorrel':>9} {'E[pts]':>7} {'P(1º)':>7} {'P(top3)':>8}")
    for K in (1, 2, 3, 5, 8, 12):
        for dec in ([False, True] if K > 1 else [False]):
            m, p1, pt = chances(K, dec)
            print(f"{K:>10} {str(dec):>9} {m:>7.0f} {p1*100:>6.1f}% {pt*100:>7.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
