#!/usr/bin/env python3
"""CANDADO planilla≡simulación para las FINALES CSC (3er puesto + final).

Lee finales_CSC.csv y snippet_finales.js TAL COMO ESTÁN ESCRITOS, verifica que
coincidan entre sí y evalúa ESOS picks exactos en el simulador (field 15.7,
corte 515, matrices 120', reglas POR PARTIDO, rifa de empates JUSTA — jitter a
ambos lados, hallazgo H1 de la auditoría 17-jul). Falla si la planilla escrita
no rinde como la config auditada (A_hedge).

    python pollas/CSC/verificar_finales.py
"""
import csv, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120

AQUI = os.path.dirname(os.path.abspath(__file__))
RONDA_M = ["tercer_puesto", "final"]; PAR_M = [RONDAS[r] for r in RONDA_M]
G = 7; PRECIO = 100_000
FD = os.path.join(AQUI, "field_finales.json")
E_MIN = 5_100_000   # A_hedge con rifa justa ≈ 5.2-5.5M según Carvajal; configs malas <5.0M

def leer_csv():
    filas = list(csv.DictReader(open(os.path.join(AQUI, "finales_CSC.csv"), encoding="utf-8")))
    return {n: [tuple(int(x) for x in f[f"cupo_{n}"].split("-")) for f in filas] for n in range(1, 6)}

def leer_snippet():
    js = open(os.path.join(AQUI, "snippet_finales.js"), encoding="utf-8").read()
    PART = json.loads(re.search(r"var PART = (\[.*?\]);", js).group(1))
    return {n: [tuple(p["s"][n - 1]) for p in PART] for n in range(1, 6)}

def pts(pick, gh, ga, par):
    res, cero, b = par; a, v = pick
    return (res * (np.sign(a - v) == np.sign(gh - ga))
            + (a == gh) * np.where(gh == 0, cero, gh + b)
            + (v == ga) * np.where(ga == 0, cero, ga + b)).astype(float)

def main():
    picks = leer_csv(); snip = leer_snippet()
    assert picks == snip, f"❌ CSV ≠ snippet: {picks} vs {snip}"
    print("✅ CSV ≡ snippet:", {n: [f"{a}-{b}" for a, b in picks[n]] for n in sorted(picks)})

    ev = json.load(open(os.path.join(AQUI, "finales_odds_snapshot.json")))
    Ms = []
    for e, ronda in zip(ev, RONDA_M):
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda(ronda),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        Ms.append(marcadores.aplicar_sesgo_goles(
            ajuste_120(r["matriz"], r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"], 0.45), 0.05))

    fd = json.load(open(FD)); rivals = np.array([p for _, p in fd["rivals"]], float); Ef = len(rivals)
    base = {k.replace("ANDRES BORRERO ", ""): v for k, v in fd["ours"].items()}
    ordk = sorted(base, key=lambda k: -base[k]); ours = np.array([base[k] for k in ordk], float)
    premio = sp.PREMIOS * (Ef + 5) * PRECIO

    eps, p1s = [], []
    for seed in (601, 602, 603, 604):
        rng = np.random.default_rng(seed); S = 30000
        gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
        f0h, f0a = sp.generar_field_mix([Ms[0]], Ef, {"opt": .15, "cal": .35, "hum": .50}, PAR_M[0], rng, G)
        f1h, f1a = sp.generar_field_mix([Ms[1]], Ef, {"opt": .15, "cal": .35, "hum": .50}, PAR_M[1], rng, G)
        g0 = np.array([pts((int(f0h[j, 0]), int(f0a[j, 0])), gh[0], ga[0], PAR_M[0]) for j in range(Ef)])
        g1 = np.array([pts((int(f1h[j, 0]), int(f1a[j, 0])), gh[1], ga[1], PAR_M[1]) for j in range(Ef)])
        field_tot = rivals[:, None] + g0 + g1 + rng.random((Ef, S)) * 1e-6   # rifa justa
        jit = rng.random((5, S)) * 1e-6
        our = np.array([ours[i] + pts(picks[int(k)][0], gh[0], ga[0], PAR_M[0])
                        + pts(picks[int(k)][1], gh[1], ga[1], PAR_M[1])
                        for i, k in enumerate(ordk)]) + jit
        fab = (field_tot[None, :, :] > our[:, None, :]).sum(1)
        oab = (our[:, None, :] > our[None, :, :]).sum(0)
        rank = fab + oab
        pr = np.where(rank < 5, premio[np.clip(rank, 0, 4)], 0.0)
        eps.append(pr.sum(0).mean()); p1s.append((our.max(0) > field_tot.max(0)).mean())
    m = np.mean(eps)
    print(f"E[premio] planilla ESCRITA = ${m:,.0f} (±{np.std(eps):,.0f}, 4 seeds, rifa justa)  ·  P(#1)={np.mean(p1s)*100:.0f}%")
    assert m > E_MIN, f"❌ ${m:,.0f} < ${E_MIN:,} — NO es la config auditada. NO ENVIAR."
    print(f"✅ CANDADO OK: la planilla escrita rinde como A_hedge (>{E_MIN/1e6:.1f}M). Segura para enviar.")

if __name__ == "__main__":
    main()
