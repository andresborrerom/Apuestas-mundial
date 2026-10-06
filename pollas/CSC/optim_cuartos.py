#!/usr/bin/env python3
"""
CUARTOS CSC — optimización SIN supuestos del mapeo cupo->perfil.

En vez de decidir a mano quién va lotería/defensivo, MIDE:
1) Sweep marginal: para cada cupo (en su posición real) y cada perfil de marcador,
   cuánto cambia el premio esperado (con los demás en EV-máx). Muestra qué prefiere
   cada posición.
2) Óptimo conjunto (greedy) considerando la CORRELACIÓN entre cupos (dos cupos con
   el mismo perfil están correlacionados; la lotería decorrelaciona).

Perfiles = data-driven de las cuotas (ranking de marcadores por partido), sin
inventar valores. Único supuesto necesario: skill del field (no observamos las
planillas rivales) -> se reporta sensibilidad a 3 escenarios.

    python pollas/CSC/optim_cuartos.py
"""
import json, os, sys, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import analizar_partido, odds_api, marcadores, simulacion_polla as sp
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills

AQUI = os.path.dirname(os.path.abspath(__file__))
PARAMS = RONDAS["cuartos"]; G = 7; PRECIO = 100_000; S = 30000


def matrices(snap):
    ev = json.load(open(snap, encoding="utf-8")); M90, lam = [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]: continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("cuartos"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5, sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
    M120 = [ajuste_120(M, lL, lV, 0.45) for M, (lL, lV) in zip(M90, lam)]
    return [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]


def construir_perfiles(Ms):
    """Menú de pick-sets data-driven. Devuelve dict nombre -> (ph, pa) (Mn,)."""
    rk = ranking_fills(Ms)                      # rk[i][k] = k-ésimo marcador del partido i
    Mn = len(Ms)
    def rank_all(k): return (np.array([rk[i][k][0] for i in range(Mn)]),
                             np.array([rk[i][k][1] for i in range(Mn)]))
    perfiles = {"D (EV-máx)": rank_all(0),
                "A (rank2 todos)": rank_all(1),
                "B (rank3 todos)": rank_all(2)}
    # mild: EV-máx pero UN partido movido al 2º (decorrelación barata, por partido)
    d_h, d_a = rank_all(0); r2_h, r2_a = rank_all(1)
    for i in range(Mn):
        h = d_h.copy(); a = d_a.copy(); h[i] = r2_h[i]; a[i] = r2_a[i]
        perfiles[f"s{i+1} (2º en P{i+1})"] = (h, a)
    return perfiles


def main():
    Ms = matrices(os.path.join(AQUI, "cuar_odds_snapshot.json"))
    fd = json.load(open("/tmp/claude-0/-home-user-Apuestas-mundial/"
                        "d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/field7.json"))
    rivals = np.array([p for _, p in fd["rivals"]], float)
    o = sorted(fd["ours"].items(), key=lambda kv: -kv[1])
    labels = [k.replace("ANDRES BORRERO ", "B") for k, _ in o]
    ours_pts = np.array([v for _, v in o], float)
    Ef = len(rivals)
    perfiles = construir_perfiles(Ms)
    pn = list(perfiles)
    print(f"Cupos (por posición): {list(zip(labels, ours_pts.astype(int)))}")
    print(f"Perfiles: {pn}\n")

    def run_field(fmix, seed=1):
        rng = np.random.default_rng(seed)
        gh, ga = sp.muestrear_torneos(Ms, S, rng, G)
        fh, fa = sp.generar_field_mix(Ms, Ef, fmix, PARAMS, rng, G)
        field_tot = rivals[:, None] + sp._puntos(fh, fa, gh, ga, PARAMS)   # (Ef,S)
        field_sorted = np.sort(field_tot, axis=0)                          # asc
        # ganancia por perfil (misma para cualquier cupo)
        pg = {name: sp._puntos(np.array([ph]), np.array([pa]), gh, ga, PARAMS)[0]
              for name, (ph, pa) in perfiles.items()}                      # name -> (S,)
        premio = sp.PREMIOS * (Ef + 5) * PRECIO
        jitter = rng.random((5, S)) * 1e-6
        def evaluar(assign):
            our = ours_pts[:, None] + np.array([pg[a] for a in assign]) + jitter   # (5,S)
            # rank de cada cupo = #field por encima + #nuestros-otros por encima
            # cuántos field superan a cada cupo:
            fabove = Ef - np.array([np.searchsorted(field_sorted[:, s], our[:, s], side='left')
                                    for s in range(S)]).T    # (5,S) lento; vectorizamos abajo
            return our, fabove
        # vectorizar el conteo field-above con searchsorted por columna es caro;
        # usamos comparación directa (5,S) vs (Ef,S) por broadcasting en bloques.
        def prize(assign):
            our = ours_pts[:, None] + np.array([pg[a] for a in assign]) + jitter   # (5,S)
            # field above (Ef,S) count per cupo: sum over field of field>our
            fabove = (field_tot[None, :, :] > our[:, None, :]).sum(axis=1)         # (5,S)
            # nuestros-otros above:
            oabove = (our[:, None, :] > our[None, :, :]).sum(axis=0)   # #cupos nuestros ARRIBA
            rank = fabove + oabove                                                 # 0-indexed
            inmoney = rank < 5
            # premio: cada cupo en puesto r (si <5) cobra premio[r]... pero premios son por PUESTO global
            pr = np.where(rank < 5, premio[np.clip(rank, 0, 4)], 0.0)
            return pr.sum(axis=0).mean(), inmoney.mean(axis=1)                      # premio_esp, P(cada cupo en money)
        return prize

    for fname, fmix in [("mixto", {"opt": .15, "cal": .35, "hum": .50}),
                        ("sharp", {"opt": .35, "cal": .35, "hum": .30}),
                        ("casual", {"opt": .05, "cal": .30, "hum": .65})]:
        prize = run_field(fmix)
        base = ["D (EV-máx)"] * 5
        base_pr, _ = prize(base)
        print("=" * 78)
        print(f"FIELD = {fname}   ·  baseline (5×EV-máx) premio = {base_pr:,.0f}")
        # 1) SWEEP MARGINAL: cambiar SOLO un cupo de perfil (resto EV-máx)
        print("\n  SWEEP MARGINAL — Δpremio si el cupo i toma el perfil (resto EV-máx):")
        header = "  %-14s" % "cupo\\perfil" + "".join("%12s" % p.split()[0] for p in pn)
        print(header)
        for i, lab in enumerate(labels):
            deltas = []
            for p in pn:
                a = list(base); a[i] = p
                pr, _ = prize(a)
                deltas.append(pr - base_pr)
            best = pn[int(np.argmax(deltas))].split()[0]
            print("  %-14s" % f"{lab}({int(ours_pts[i])})" + "".join("%+12.0f" % d for d in deltas) + f"   mejor:{best}")
        # 2) ÓPTIMO GREEDY (captura correlación)
        assign = list(base); cur, _ = prize(assign)
        improved = True
        while improved:
            improved = False
            for i in range(5):
                for p in pn:
                    a = list(assign); a[i] = p
                    pr, _ = prize(a)
                    if pr > cur + 1:
                        assign = a; cur = pr; improved = True
        _, inm = prize(assign)
        print(f"\n  ÓPTIMO (greedy) = premio {cur:,.0f}  (+{cur-base_pr:,.0f} vs baseline)")
        for i, lab in enumerate(labels):
            print(f"     {lab}({int(ours_pts[i])}): {assign[i]:16}  P(en premio)={inm[i]*100:.0f}%")


if __name__ == "__main__":
    main()
