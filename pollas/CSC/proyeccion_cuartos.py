#!/usr/bin/env python3
"""
CUARTOS CSC — comparación rigurosa de estrategias de dispersión para maximizar
el PREMIO esperado (ocupar puestos de plata: top-5 = 50/20/15/10/5%).

Siembra el field REAL (PDF 7-jul), simula los 4 cuartos desde las cuotas reales
(+ajuste 120'), y evalúa varias asignaciones de rol a nuestros 5 cupos. Los roles
se asignan por la POSICIÓN actual del cupo (el mejor cupo defiende con EV-máx;
los que están lejos del premio arriesgan con lotería). Sensibilidad al skill del field.

    python pollas/CSC/proyeccion_cuartos.py
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills

AQUI = os.path.dirname(os.path.abspath(__file__))
PARAMS = RONDAS["cuartos"]; G = 7; PRECIO = 100_000


def matrices(snapshot):
    ev = json.load(open(snapshot, encoding="utf-8"))
    M90, lam = [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]:
            continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("cuartos"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
    M120 = [ajuste_120(M, lL, lV, 0.45) for M, (lL, lV) in zip(M90, lam)]
    return [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]


def picks_por_rol(Ms, roles, rng):
    """roles: lista de 5 en {'A' ancla EV-máx, 'S' suave perturb, 'M' media perturb,
    'L2' lotería 2º fill, 'L3' lotería 3º fill}. Devuelve preds (5,Mn)."""
    e_h, e_a, s_h, s_a, gap = sp.fill_evmax_y_segundo(Ms, PARAMS, G)
    rk = ranking_fills(Ms)
    l2 = (np.array([r[1][0] for r in rk]), np.array([r[1][1] for r in rk]))
    l3 = (np.array([r[2][0] for r in rk]), np.array([r[2][1] for r in rk]))

    def perturb(n_swaps, seed):
        r = np.random.default_rng(seed)
        orden = np.argsort(gap); cand = orden[gap[orden] <= 0.40]
        h = e_h.copy(); a = e_a.copy()
        if len(cand):
            sw = r.choice(cand, size=min(n_swaps, len(cand)), replace=False)
            h[sw] = s_h[sw]; a[sw] = s_a[sw]
        return h, a

    out_h, out_a = [], []
    for i, ro in enumerate(roles):
        if ro == 'A':   h, a = e_h, e_a
        elif ro == 'S': h, a = perturb(1, 10 + i)
        elif ro == 'M': h, a = perturb(2, 20 + i)
        elif ro == 'L2': h, a = l2
        elif ro == 'L3': h, a = l3
        out_h.append(h); out_a.append(a)
    return np.array(out_h), np.array(out_a)


def evaluar(Ms, rivals_pts, ours_pts, roles, field_mix, S=25000, seed=1):
    rng = np.random.default_rng(seed)
    Ef = len(rivals_pts)
    gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
    fh, fa = sp.generar_field_mix(Ms, Ef, field_mix, PARAMS, rng, G)
    oh, oa = picks_por_rol(Ms, roles, rng)
    gf = sp._puntos(fh, fa, gh, ga, PARAMS)
    go = sp._puntos(oh, oa, gh, ga, PARAMS)
    tot = np.vstack([rivals_pts[:, None] + gf, ours_pts[:, None] + go])
    tot = tot + rng.random(tot.shape) * 1e-6
    N = tot.shape[0]; premio = sp.PREMIOS * N * PRECIO
    orden = np.argsort(-tot, axis=0); top5 = orden[:5]; mine = top5 >= Ef
    gan = (mine * premio[:, None]).sum(0)
    rangos = np.argsort(orden, axis=0); best = rangos[Ef:].min(0)
    return dict(premio=gan.mean(), pprem=(gan > 0).mean(),
                slots=mine.sum(0).mean(), p1=(best == 0).mean(), ptop3=(best <= 2).mean())


def main():
    Ms = matrices(os.path.join(AQUI, "cuar_odds_snapshot.json"))
    fd = json.load(open("/tmp/claude-0/-home-user-Apuestas-mundial/"
                        "d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/field7.json"))
    rivals = np.array([p for _, p in fd["rivals"]], float)
    o = fd["ours"]
    # cupos ordenados por su puntaje ACTUAL (para asignar roles por posición)
    ord_cupos = sorted(o.items(), key=lambda kv: -kv[1])
    ours_pts = np.array([v for _, v in ord_cupos], float)
    etiquetas = [k.replace("ANDRES BORRERO ", "B") for k, _ in ord_cupos]
    print(f"Cuartos: {len(Ms)} partidos · field {len(rivals)} rivales + 5 nuestros")
    print(f"Nuestros cupos (por posición): {list(zip(etiquetas, ours_pts.astype(int)))}")
    print(f"Corte top-5 actual: {sorted(list(rivals)+list(ours_pts), reverse=True)[4]:.0f}\n")

    # ESTRATEGIAS = asignación de roles a los 5 cupos (ordenados por posición):
    # [mejor cupo ... peor cupo]
    ESTRAT = {
        "evmax (todos EV-máx)":        ['A', 'A', 'A', 'A', 'A'],
        "def_puro (ancla+4 suaves)":   ['A', 'S', 'S', 'S', 'M'],
        "posic (3 def + 2 lotería)":   ['A', 'S', 'M', 'L2', 'L3'],
        "posic_medio (2def+1med+2lot)":['A', 'S', 'L2', 'M', 'L3'],
        "agresivo (ancla+4 lotería)":  ['A', 'L2', 'L3', 'L2', 'L3'],
    }
    FIELDS = {"casual": {"opt": .05, "cal": .30, "hum": .65},
              "mixto":  {"opt": .15, "cal": .35, "hum": .50},
              "sharp":  {"opt": .35, "cal": .35, "hum": .30}}
    for fn, fx in FIELDS.items():
        print("=" * 82)
        print(f"FIELD = {fn}")
        print(f"  {'estrategia':32}{'premio_esp':>12}{'P(prem)':>9}{'E[slots]':>9}{'P(1º)':>7}{'P(top3)':>8}")
        res = {}
        for name, roles in ESTRAT.items():
            r = evaluar(Ms, rivals, ours_pts, roles, fx)
            res[name] = r
            print(f"  {name:32}{r['premio']:>12,.0f}{r['pprem']*100:>8.1f}%{r['slots']:>9.2f}{r['p1']*100:>6.1f}%{r['ptop3']*100:>7.1f}%")
        best = max(res, key=lambda k: res[k]['premio'])
        print(f"  → MEJOR por premio esperado: {best}")


if __name__ == "__main__":
    main()
