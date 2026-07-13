#!/usr/bin/env python3
"""
Estudio R32 (16avos) — dispersión de cupos y dinámica de knockout.

Reproducible SIN API key: lee el snapshot de cuotas `r32_odds_snapshot.json`
(tomado el 28/06/2026). Responde dos preguntas que estudiamos para enviar los
5 cupos de R32:

1) ¿Cómo repartir los 5 cupos? Compara estrategias de dispersión por:
   - P(quedar 1º), P(podio), nº de cupos al premio, y E[% del pozo] (premio
     50/20/15/10/5%). Bajo 3 supuestos de "dureza" del campo rival.
   Estrategias: idénticos (evmax) · perturbada (gap_max) · ESCALÓN por ranking
   (k-ésimo fill en todo) · MIXTO (ancla + 2 suaves + 2 "lotería").

2) Dinámica de knockout (120'): las cuotas son de 90' pero CSC puntúa a 120'.
   Un empate a 90' suele resolverse en el alargue. El ajuste mueve masa de los
   empates a marcador decidido (sesgado al favorito) y mide: empates esperados,
   cuántos picks cambian, y cómo se reordenan las estrategias bajo esa realidad
   más creíble.

Uso:
    python pollas/CSC/experimento_r32.py
    python pollas/CSC/experimento_r32.py --delta 0.45   # fracción de empates 90' resueltos en alargue

Hallazgos (28/06, campo del PDF, 30k sims) — ver ESTUDIO_R32.md:
  - Más dispersión sube P(1º) pero baja E[$]; el MIXTO Pareto-domina a la
    perturbada simple. El ESCALÓN maximiza P(1º) pero sacrifica pozo.
  - Bajo realidad 120' (menos empates), las P(1º) caen y el escalón pierde
    ventaja: gran parte de su brillo venía de escenarios de muchos empates.
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from motor import analizar_partido, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC import llenar as L
from motor import odds_api

AQUI = os.path.dirname(os.path.abspath(__file__))
PARAMS = RONDAS["dieciseisavos"]
G = 7

# Estado del torneo al cierre de grupos (PDF 27/06): nuestros 5 cupos y el campo.
NUESTROS = np.array([276, 262, 256, 250, 243])          # B4, B1, B2, B3, B5
RIVALES = np.array([277, 260, 259, 256, 250, 249, 249, 247, 247, 242, 242, 242,
                    241, 240, 239, 239, 238, 236, 236, 235, 234, 234, 233, 233,
                    231, 230, 229, 229, 228, 227, 227, 227, 225, 224, 224])
PREMIO = np.array([0.50, 0.20, 0.15, 0.10, 0.05])       # reparto del pozo (top 5)
CAMPOS = {"blando 15/25/60": [.15, .25, .60],
          "medio  30/30/40": [.30, .30, .40],
          "afilado 50/30/20": [.50, .30, .20]}


def cargar_matrices(path):
    ev = json.load(open(path, encoding="utf-8"))
    M, lab, lam = [], [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]:
            continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("dieciseisavos"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M.append(r["matriz"]); lab.append(f"{L.es(c['home'])} vs {L.es(c['away'])}")
        lam.append((r["modelo"].get("lambda_local"), r["modelo"].get("lambda_visita")))
    return M, lab, lam


def ajuste_120(M, lL, lV, delta):
    """Mueve `delta` de cada empate (k,k) a (k+1,k)/(k,k+1) según fuerza: modela
    que un % de los empates a 90' se deciden con un gol en el alargue."""
    M2 = M.copy(); pL = lL / (lL + lV)
    for k in range(min(M.shape)):
        d = M2[k, k] * delta; M2[k, k] -= d
        if k + 1 < M.shape[0]: M2[k + 1, k] += d * pL
        if k + 1 < M.shape[1]: M2[k, k + 1] += d * (1 - pL)
    return M2 / M2.sum()


def p_empate(M):
    return sum(M[k, k] for k in range(min(M.shape)))


def evmax_fill(M, alpha=0.05):
    EV = sp.ev_grid(marcadores.aplicar_sesgo_goles(M, alpha), PARAMS, G).ravel()
    o = int(np.argmax(EV)); return (o // (G + 1), o % (G + 1))


def ranking_fills(Msesgo, params=None):
    """Top-5 fills por EV de cada partido (para escalón/mixto).

    ⚠️ params default = PARAMS de DIECISEISAVOS (2,3,5) por compatibilidad.
    Para otras rondas PASAR params explícito: el orden de fills puede cambiar
    con la regla (auditoría 13-jul: en semis top-3 coincidía por suerte)."""
    out = []
    for M in Msesgo:
        EV = sp.ev_grid(M, params or PARAMS, G).ravel(); o = np.argsort(-EV)[:5]
        out.append([(int(x // (G + 1)), int(x % (G + 1))) for x in o])
    return out


def estrategias(Msesgo, rng):
    rk = ranking_fills(Msesgo)
    lad = lambda k: (np.array([r[k][0] for r in rk]), np.array([r[k][1] for r in rk]))
    l0, l1, l2, l3, l4 = (lad(k) for k in range(5))
    phI, paI = sp.generar_nuestras(Msesgo, 5, PARAMS, estrategia="evmax", rng=rng, G=G)
    ph3, pa3 = sp.generar_nuestras(Msesgo, 5, PARAMS, estrategia="perturbada",
                                   rng=np.random.default_rng(7), n_swaps=3, pool=40,
                                   gap_max=0.30, G=G)
    esc = (np.array([l0[0], l1[0], l2[0], l3[0], l4[0]]),
           np.array([l0[1], l1[1], l2[1], l3[1], l4[1]]))
    mix = (np.array([ph3[0], ph3[1], ph3[2], l1[0], l2[0]]),
           np.array([pa3[0], pa3[1], pa3[2], l1[1], l2[1]]))
    return {"idénticos": (phI, paI), "perturbada n3": (ph3, pa3),
            "MIXTO": mix, "ESCALÓN": esc}


def score_vec(ph, pa, gh, ga):
    pres, cero, base = PARAMS
    win = (np.sign(ph - pa) == np.sign(gh - ga)) * pres
    loc = np.where(gh == 0, cero, 0) if ph == 0 else np.where(gh == ph, ph + base, 0)
    vis = np.where(ga == 0, cero, 0) if pa == 0 else np.where(ga == pa, pa + base, 0)
    return win + loc + vis


def simular(Mreal, Msesgo, estrats, pesos_campo, S=30000, seed=2026):
    """Muestrea realidad de Mreal, puntúa nuestras estrategias y un campo rival."""
    rng = np.random.default_rng(seed); Mn = len(Mreal)
    GH = np.empty((Mn, S), int); GA = np.empty((Mn, S), int)
    for m, M in enumerate(Mreal):
        f = M.ravel() / M.sum(); idx = rng.choice(f.size, size=S, p=f)
        GH[m] = idx // M.shape[1]; GA[m] = idx % M.shape[1]
    evh, eva = sp.fill_evmax(Msesgo, PARAMS, G)
    R = len(RIVALES); rivF = np.zeros((R, S)); arq = rng.choice(3, size=R, p=pesos_campo)
    for ri in range(R):
        a = arq[ri]
        for m, M in enumerate(Mreal):
            if a == 0:
                ph, pa = evh[m], eva[m]
            else:
                conc = 1.0 if a == 1 else 4.0; fl = (M.ravel() ** conc); fl /= fl.sum()
                k = rng.choice(fl.size, p=fl); ph, pa = k // M.shape[1], k % M.shape[1]
            rivF[ri] += score_vec(ph, pa, GH[m], GA[m])
    rivF += RIVALES[:, None]
    res = {}
    for nombre, (ph, pa) in estrats.items():
        O = np.zeros((5, S))
        for c in range(5):
            for m in range(Mn):
                O[c] += score_vec(ph[c, m], pa[c, m], GH[m], GA[m])
        O += NUESTROS[:, None]
        alls = np.vstack([O, rivF]) + rng.uniform(0, 1e-3, size=(5 + R, S))  # rifa desempate
        pos = np.argsort(np.argsort(-alls, axis=0), axis=0)[:5]
        best = pos.min(axis=0); util = np.zeros(S)
        for c in range(5):
            m5 = pos[c] < 5; util[m5] += PREMIO[pos[c][m5]]
        res[nombre] = dict(p1=float((best == 0).mean()), p3=float((best < 3).mean()),
                           top5=float((pos < 5).sum(0).mean()), util=float(util.mean()))
    return res


def tabla(res, titulo):
    print(f"\n=== {titulo} ===")
    print(f"  {'estrategia':16}{'P(#1)':>7}{'P(top3)':>9}{'#top5':>7}{'E[%pozo]':>10}")
    for n, r in res.items():
        print(f"  {n:16}{r['p1']:7.1%}{r['p3']:9.1%}{r['top5']:7.2f}{r['util']:10.1%}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Estudio R32: dispersión + knockout 120'")
    ap.add_argument("--snapshot", default=os.path.join(AQUI, "r32_odds_snapshot.json"))
    ap.add_argument("--delta", type=float, default=0.45,
                    help="fracción de empates a 90' resueltos en el alargue (120')")
    args = ap.parse_args(argv)

    M90, lab, lam = cargar_matrices(args.snapshot)
    Ms90 = [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M90]
    M120 = [ajuste_120(M, lL, lV, args.delta) for M, (lL, lV) in zip(M90, lam)]
    Ms120 = [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]

    print("############ ESTUDIO 1 — dispersión de los 5 cupos (realidad 90') ############")
    est90 = estrategias(Ms90, np.random.default_rng(7))
    for cn, pe in CAMPOS.items():
        tabla(simular(M90, Ms90, est90, pe), f"campo {cn}")

    print("\n\n############ ESTUDIO 2 — dinámica de knockout 120' ############")
    print(f"delta={args.delta} · empates esperados: 90'={sum(p_empate(M) for M in M90):.2f}/16"
          f"  ->  120'={sum(p_empate(M) for M in M120):.2f}/16")
    flips = sum(evmax_fill(a) != evmax_fill(b) for a, b in zip(M90, M120))
    print(f"picks EV-máx que cambian con el ajuste 120': {flips}/16")
    print("  (los empates 1-1 de partidos cerrados pasan a decididos 2-1/1-2)")
    est120 = estrategias(Ms120, np.random.default_rng(7))
    tabla(simular(M120, Ms120, est120, CAMPOS["blando 15/25/60"]),
          "estrategias bajo REALIDAD 120' (campo blando)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
