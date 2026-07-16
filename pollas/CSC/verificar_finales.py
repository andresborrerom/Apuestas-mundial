#!/usr/bin/env python3
"""CANDADO planilla≡simulación (post-mortem 13-jul: se envió una config
distinta a la simulada por un error de etiqueta "EV-máx"=1-1 vs 2-1 real).

Lee finales_CSC.csv Y snippet_finales.js TAL COMO ESTÁN ESCRITOS, verifica que
coincidan entre sí, y evalúa ESOS picks exactos en el simulador (field 11.7,
matrices 120'). Falla ruidosamente si la planilla escrita no rinde ≈ G3.

    python pollas/CSC/verificar_semis.py
"""
import csv, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120

AQUI = os.path.dirname(os.path.abspath(__file__))
PAR_M = [RONDAS["tercer_puesto"], RONDAS["final"]]
PARAMS = PAR_M[0]; G = 7; PRECIO = 100_000
FD = os.path.join(AQUI, "field_finales.json")   # field 11.7 CORREGIDO (v2 del PDF)
E_MIN = 5_300_000     # G3 con field 11.7v2 ~5.4-5.6M (rivales corregidos al alza,
                      # corte 482); configs malas rinden <5.0M. Antes 6.2M con field v1.

def leer_csv():
    filas = list(csv.DictReader(open(os.path.join(AQUI, "finales_CSC.csv"), encoding="utf-8")))
    picks = {n: [tuple(int(x) for x in f[f"cupo_{n}"].split("-")) for f in filas] for n in range(1, 6)}
    return filas, picks

def leer_snippet():
    js = open(os.path.join(AQUI, "snippet_finales.js"), encoding="utf-8").read()
    PART = json.loads(re.search(r"var PART = (\[.*?\]);", js).group(1))
    return {n: [tuple(p["s"][n-1]) for p in PART] for n in range(1, 6)}

def main():
    filas, picks = leer_csv()
    snip = leer_snippet()
    assert picks == snip, f"❌ CSV ≠ snippet: {picks} vs {snip}"
    print("✅ CSV ≡ snippet:", {n: [f"{a}-{b}" for a, b in picks[n]] for n in sorted(picks)})

    ev = json.load(open(os.path.join(AQUI, "finales_odds_snapshot.json")))
    M90, lam = [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("tercer_puesto" if len(M90)==0 else "final"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
    Ms = [marcadores.aplicar_sesgo_goles(ajuste_120(M, lL, lV, 0.45), 0.05)
          for M, (lL, lV) in zip(M90, lam)]

    fd = json.load(open(FD)); rivals = np.array([p for _, p in fd["rivals"]], float)
    base = {k.replace("ANDRES BORRERO ", ""): v for k, v in fd["ours"].items()}
    Ef = len(rivals); premio = sp.PREMIOS * (Ef + 5) * PRECIO
    ordk = sorted(base, key=lambda k: -base[k])          # por puntos, como el optim
    ours_pts = np.array([base[k] for k in ordk], float)

    def pts(pick, gh, ga, par):
        res, cero, b = par
        a, v = pick
        return (res * (np.sign(a - v) == np.sign(gh - ga))
                + (a == gh) * np.where(gh == 0, cero, gh + b)
                + (v == ga) * np.where(ga == 0, cero, ga + b)).astype(float)

    eps, p1s = [], []
    for seed in (201, 202, 203, 204):
        rng = np.random.default_rng(seed); S = 40000
        gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
        fh, fa = sp.generar_field_mix(Ms, Ef, {"opt": .15, "cal": .35, "hum": .50}, PAR_M[0], rng, G)
        field_tot = rivals[:, None] + (pts((0,0),0,0,PAR_M[0])*0 + np.array([pts((int(fh[j][0]),int(fa[j][0])), gh[0], ga[0], PAR_M[0]) + pts((int(fh[j][1]),int(fa[j][1])), gh[1], ga[1], PAR_M[1]) for j in range(Ef)]))
        jit = rng.random((5, S)) * 1e-6
        our = np.array([ours_pts[i] + pts(picks[int(k)][0], gh[0], ga[0], PAR_M[0])
                        + pts(picks[int(k)][1], gh[1], ga[1], PAR_M[1])
                        for i, k in enumerate(ordk)]) + jit
        fab = (field_tot[None, :, :] > our[:, None, :]).sum(1)
        oab = (our[:, None, :] > our[None, :, :]).sum(0)
        rank = fab + oab
        pr = np.where(rank < 5, premio[np.clip(rank, 0, 4)], 0.0)
        eps.append(pr.sum(0).mean()); p1s.append((our.max(0) > field_tot.max(0)).mean())
    m = np.mean(eps)
    print(f"E[premio] planilla ESCRITA = ${m:,.0f} (±{np.std(eps):,.0f}, 4 seeds)  ·  P(#1)={np.mean(p1s)*100:.0f}%")
    assert m > E_MIN, f"❌ La planilla escrita rinde ${m:,.0f} < ${E_MIN:,} — NO es la config auditada. NO ENVIAR."
    print(f"✅ CANDADO OK: la planilla escrita rinde como G3 (>{E_MIN/1e6:.1f}M). Segura para enviar.")

if __name__ == "__main__":
    main()
