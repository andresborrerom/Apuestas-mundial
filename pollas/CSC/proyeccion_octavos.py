#!/usr/bin/env python3
"""
Proyección competition-aware de OCTAVOS (CSC). Siembra los puntajes REALES del
PDF y simula solo lo que falta (octavos, 8 partidos), para optimizar la
DISPERSIÓN de nuestros 5 cupos según el field contra el que jugamos.

A diferencia de simulacion_polla.simular_utilidad (que arranca todos en 0), aquí:
- Cada cupo (nuestros + 109 rivales) parte de su puntaje ACTUAL (PDF 3-jul).
- Se simulan S torneos de octavos desde las cuotas reales (+ajuste 120').
- Field: mezcla de arquetipos (opt/cal/hum) con sensibilidad de qué tan sharp es.
- Se suma la cosecha de octavos al puntaje actual, se rankea, y se paga el
  top-5 (50/20/15/10/5% del pozo). Métrica = premio esperado y prob. de podio.

Uso: python pollas/CSC/proyeccion_octavos.py
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills

AQUI = os.path.dirname(os.path.abspath(__file__))
PARAMS = RONDAS["octavos"]; G = 7
PRECIO = 100_000


def matrices_octavos(snapshot):
    ev = json.load(open(snapshot, encoding="utf-8"))
    M90, lam = [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]:
            continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("octavos"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
    M120 = [ajuste_120(M, lL, lV, 0.45) for M, (lL, lV) in zip(M90, lam)]
    return [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]


def nuestras_por_estrategia(Ms, estrategia, rng):
    """Devuelve preds (5,M) para los cupos [B4,B1,B2,B3,B5] en ese orden."""
    e_h, e_a, s_h, s_a, gap = sp.fill_evmax_y_segundo(Ms, PARAMS, G)
    rk = ranking_fills(Ms)
    l2h = np.array([r[1][0] for r in rk]); l2a = np.array([r[1][1] for r in rk])
    l3h = np.array([r[2][0] for r in rk]); l3a = np.array([r[2][1] for r in rk])
    anc = (e_h, e_a)

    def perturb(n_swaps, seed):
        r = np.random.default_rng(seed)
        orden = np.argsort(gap); cand = orden[gap[orden] <= 0.30][:40]
        h = e_h.copy(); a = e_a.copy()
        if len(cand):
            sw = r.choice(cand, size=min(n_swaps, len(cand)), replace=False)
            h[sw] = s_h[sw]; a[sw] = s_a[sw]
        return h, a

    if estrategia == "evmax":            # los 5 = EV-máx (máxima correlación)
        picks = [anc, anc, anc, anc, anc]
    elif estrategia == "mixto_def":      # DEFENDER: ancla + 2 suaves + 2 lotería
        picks = [anc, perturb(2, 7), perturb(3, 11), (l2h, l2a), (l3h, l3a)]
    elif estrategia == "mixto_agr":      # AGRESIVO: ancla + 2 medias + 2 lotería fuerte
        picks = [anc, perturb(4, 7), perturb(5, 11), (l2h, l2a), (l3h, l3a)]
    elif estrategia == "todo_loteria":   # 1 ancla + 4 lotería (moonshot puro)
        picks = [anc, (l2h, l2a), (l3h, l3a), (l2h, l2a), (l3h, l3a)]
    else:
        raise ValueError(estrategia)
    ph = np.array([p[0] for p in picks]); pa = np.array([p[1] for p in picks])
    return ph, pa


def proyectar(Ms, rivals_pts, ours_pts_ordenados, field_mix, estrategia,
              S=20000, seed=0):
    """rivals_pts: (Ef,) puntos actuales de rivales. ours_pts_ordenados: [B4,B1,B2,B3,B5]."""
    rng = np.random.default_rng(seed)
    Ef = len(rivals_pts)
    gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
    fh, fa = sp.generar_field_mix(Ms, Ef, field_mix, PARAMS, rng, G)
    oh, oa = nuestras_por_estrategia(Ms, estrategia, rng)
    gain_f = sp._puntos(fh, fa, gh, ga, PARAMS)      # (Ef,S)
    gain_o = sp._puntos(oh, oa, gh, ga, PARAMS)      # (5,S)
    tot_f = rivals_pts[:, None] + gain_f
    tot_o = np.array(ours_pts_ordenados)[:, None] + gain_o
    todo = np.vstack([tot_f, tot_o])                 # (N,S); nuestras = filas Ef..N-1
    todo = todo + rng.random(todo.shape) * 1e-6      # desempate por rifa
    N = todo.shape[0]; pot = N * PRECIO
    premio_val = sp.PREMIOS * pot
    orden = np.argsort(-todo, axis=0)
    top5 = orden[:5, :]
    es_nuestra = top5 >= Ef
    ganancia = (es_nuestra * premio_val[:, None]).sum(axis=0)
    rangos = np.argsort(orden, axis=0)
    mejor_rango = rangos[Ef:, :].min(axis=0)
    return {
        "premio_medio": float(ganancia.mean()),
        "prob_algun_premio": float((ganancia > 0).mean()),
        "slots_top5_medio": float(es_nuestra.sum(axis=0).mean()),
        "prob_1o": float((mejor_rango == 0).mean()),
        "prob_top3": float((mejor_rango <= 2).mean()),
        "gain_ancla_medio": float(gain_o[0].mean()),
        "gain_ancla_sd": float(gain_o[0].std()),
    }


def main():
    Ms = matrices_octavos(os.path.join(AQUI, "oct_odds_snapshot.json"))
    fd = json.load(open("/tmp/claude-0/-home-user-Apuestas-mundial/"
                        "d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/field3.json"))
    rivals_pts = np.array([p for _, p in fd["rivals"]], float)
    o = fd["ours"]
    ours = [o["ANDRES BORRERO 4"], o["ANDRES BORRERO 1"], o["ANDRES BORRERO 2"],
            o["ANDRES BORRERO 3"], o["ANDRES BORRERO 5"]]
    print(f"Partidos octavos: {len(Ms)}  ·  field: {len(rivals_pts)} rivales + 5 nuestros")
    print(f"Nuestros puntos actuales [B4,B1,B2,B3,B5] = {ours}")
    print(f"Cosecha octavos del ancla (EV-máx): media {proyectar(Ms,rivals_pts,ours,{'opt':.15,'cal':.35,'hum':.5},'evmax',S=8000)['gain_ancla_medio']:.0f} "
          f"(sd alta -> octavos reordena fuerte)")

    FIELDS = {
        "casual (opt.05/cal.30/hum.65)": {"opt": .05, "cal": .30, "hum": .65},
        "mixto  (opt.15/cal.35/hum.50)": {"opt": .15, "cal": .35, "hum": .50},
        "sharp  (opt.35/cal.35/hum.30)": {"opt": .35, "cal": .35, "hum": .30},
    }
    ESTRAT = ["evmax", "mixto_def", "mixto_agr", "todo_loteria"]
    for fname, fmix in FIELDS.items():
        print("\n" + "=" * 78)
        print(f"FIELD = {fname}")
        print(f"  {'estrategia':14}{'premio_medio':>13}{'P(premio)':>11}{'E[slots]':>10}{'P(1º)':>8}{'P(top3)':>9}")
        for est in ESTRAT:
            r = proyectar(Ms, rivals_pts, ours, fmix, est, S=20000, seed=1)
            print(f"  {est:14}{r['premio_medio']:>13,.0f}{r['prob_algun_premio']*100:>10.1f}%"
                  f"{r['slots_top5_medio']:>10.2f}{r['prob_1o']*100:>7.1f}%{r['prob_top3']*100:>8.1f}%")


if __name__ == "__main__":
    main()
