"""
Batería 2 (QBs) y 3 (matchups de estilo con EPA) contra la línea de cierre.

Ideas del usuario: def vs ofensiva, equipo terrestre vs aéreo, top QB vs
top DL. Datos: nflverse stats_team_week (EPA por pase/carrera de cada
equipo-semana, sacks) 2003-2025 + games.csv (QBs titulares por partido).

PERFILES WALK-FORWARD: el perfil de un equipo antes de la semana w usa SOLO
sus semanas < w de esa temporada, mezclado con la temporada anterior
(shrinkage: la temporada previa pesa como 6 juegos, decayendo al avanzar).
Nada del futuro contamina el pasado.

HIPÓTESIS (batch 2-3, declaradas antes de mirar; K=7):
  Q1 equipo con QB nuevo (titular != el del juego anterior) — resid propio
  Q2 rival del QB nuevo — resid del rival
  G1 "aire vs muro": ofensiva aérea (tercil sup. pass_rate) contra defensa
     aérea élite (tercil inf. EPA/pase permitido) — resid propio
  G2 "tierra vs colador": ofensiva terrestre élite vs defensa terrestre
     mala — resid propio
  G3 "cazadores vs QB comilón": defensa tercil sup. en sack-rate contra
     ofensiva tercil sup. en sacks sufridos — resid del atacado
  G4 velocidad espejo: dos ofensivas aéreas élite — resid del favorito
  G5 (la prueba REINA) ¿el EPA agrega info MÁS ALLÁ del mercado?
     logística walk-forward: logit(p) ~ logit(p_mkt) + matchups EPA,
     entrenada en temporadas < Y, testeada en Y (2011-2025). Si el
     Δlog-loss no mejora, el mercado ya digirió el EPA.

Uso:  python nfl/EDGE/matchups.py
"""

import csv
import glob
import math
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl.EDGE.buscar_edge import cargar, resid  # noqa: E402

RUTA_STATS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "datos", "stats_team")
PESO_PREVIA = 6.0     # la temporada anterior pesa como 6 juegos


def cargar_stats():
    """{(season, week, team): dict con ataque propio y permitido}."""
    crudo = {}
    for ruta in glob.glob(os.path.join(RUTA_STATS, "*.csv")):
        for r in csv.DictReader(open(ruta)):
            if r["season_type"] != "REG":
                continue
            k = (int(r["season"]), int(r["week"]), r["team"])
            crudo[k] = {
                "opp": r["opponent_team"],
                "att": float(r["attempts"] or 0),
                "car": float(r["carries"] or 0),
                "p_epa": float(r["passing_epa"] or 0),
                "r_epa": float(r["rushing_epa"] or 0),
                "sacked": float(r["sacks_suffered"] or 0),
                "def_sacks": float(r["def_sacks"] or 0),
            }
    # lo permitido = lo que hizo el rival esa semana
    for (s, w, eq), d in crudo.items():
        rival = crudo.get((s, w, d["opp"]))
        d["p_epa_perm"] = rival["p_epa"] if rival else 0.0
        d["db_perm"] = (rival["att"] + rival["sacked"]) if rival else 0.0
        d["r_epa_perm"] = rival["r_epa"] if rival else 0.0
        d["car_perm"] = rival["car"] if rival else 0.0
    return crudo


def perfiles_walk_forward(crudo):
    """{(season, week, team): perfil ANTES de esa semana}."""
    campos = ["att", "car", "p_epa", "r_epa", "sacked", "def_sacks",
              "p_epa_perm", "db_perm", "r_epa_perm", "car_perm"]
    totales_temp = defaultdict(lambda: defaultdict(float))
    for (s, w, eq), d in crudo.items():
        for c in campos:
            totales_temp[(s, eq)][c] += d[c]
        totales_temp[(s, eq)]["juegos"] += 1

    perfiles = {}
    equipos_sem = defaultdict(list)
    for (s, w, eq) in crudo:
        equipos_sem[(s, eq)].append(w)
    for (s, eq), sems in equipos_sem.items():
        acum = defaultdict(float)
        previa = totales_temp.get((s - 1, eq))
        for w in sorted(sems):
            j = acum["juegos"]
            mix = dict(acum)
            if previa and previa["juegos"] > 0:
                f = PESO_PREVIA * max(0.0, 1 - j / 10.0) / previa["juegos"]
                for c in campos:
                    mix[c] = mix.get(c, 0.0) + previa[c] * f
                mix["juegos"] = j + PESO_PREVIA * max(0.0, 1 - j / 10.0)
            if mix.get("juegos", 0) >= 3:      # mínimo de señal
                db = mix["att"] + mix["sacked"]
                perfiles[(s, w, eq)] = {
                    "pass_rate": mix["att"] / max(mix["att"] + mix["car"], 1),
                    "of_pase": mix["p_epa"] / max(db, 1),
                    "of_carr": mix["r_epa"] / max(mix["car"], 1),
                    "def_pase": mix["p_epa_perm"] / max(mix["db_perm"], 1),
                    "def_carr": mix["r_epa_perm"] / max(mix["car_perm"], 1),
                    "sack_def": mix["def_sacks"] / max(mix["db_perm"], 1),
                    "sack_of": mix["sacked"] / max(db, 1),
                }
            d = crudo[(s, w, eq)]
            for c in campos:
                acum[c] += d[c]
            acum["juegos"] += 1
    return perfiles


def terciles(vals):
    a = np.percentile(vals, 33.3), np.percentile(vals, 66.7)
    return a


def main():
    filas = cargar()
    crudo = cargar_stats()
    perf = perfiles_walk_forward(crudo)

    # QB titular del juego anterior de cada equipo (games.csv)
    qb_prev, qb_nuevo = {}, {}
    for r in csv.DictReader(open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "datos",
            "games.csv"))):
        if not r["result"] or r["game_type"] != "REG":
            continue
        s, w = int(r["season"]), int(r["week"])
        for eq, qb in [(r["home_team"], r["home_qb_name"]),
                       (r["away_team"], r["away_qb_name"])]:
            clave = (s, w, eq)
            ant = qb_prev.get(eq)
            qb_nuevo[clave] = (ant is not None and qb != ant)
            qb_prev[eq] = qb

    # anexar features por lado a cada partido
    con_perf = []
    for f in filas:
        s, w = f["season"], f["week"]
        ph, pa = perf.get((s, w, f["home"])), perf.get((s, w, f["away"]))
        if not ph or not pa:
            continue
        f = dict(f)
        f["ph"], f["pa"] = ph, pa
        f["qb_h"] = qb_nuevo.get((s, w, f["home"]), False)
        f["qb_a"] = qb_nuevo.get((s, w, f["away"]), False)
        con_perf.append(f)
    print(f"partidos con perfil walk-forward y línea: {len(con_perf)}")

    # terciles de la liga por temporada-semana (sobre perfiles vigentes)
    def es_tercil(f, lado, campo, sup=True):
        s, w = f["season"], f["week"]
        vals = [p[campo] for (ss, ww, _e), p in perf.items()
                if ss == s and ww == w]
        if len(vals) < 20:
            return False
        lo, hi = terciles(vals)
        v = f[lado][campo]
        return v >= hi if sup else v <= lo

    def lado_home(f, cond_home):
        return cond_home(f)

    print("\nK=7 hipótesis (batch 2-3):")
    print(f"{'hipótesis':<40} {'n':>5} {'E[p]':>6} {'real':>6} "
          f"{'resid':>7} {'z':>6}  mitades")
    HIP = [
        ("Q1 QB nuevo (equipo, local)", lambda f: f["qb_h"], "home"),
        ("Q2 QB nuevo (rival: visita lo tiene)", lambda f: f["qb_a"], "home"),
        ("G1 aire local vs muro aereo visita",
         lambda f: es_tercil(f, "ph", "pass_rate") and
         es_tercil(f, "pa", "def_pase", sup=False), "home"),
        ("G2 tierra elite local vs colador visita",
         lambda f: es_tercil(f, "ph", "of_carr") and
         es_tercil(f, "pa", "def_carr"), "home"),
        ("G3 cazadores visita vs QB comilon local",
         lambda f: es_tercil(f, "pa", "sack_def") and
         es_tercil(f, "ph", "sack_of"), "home"),
        ("G4 dos ofensivas aereas elite",
         lambda f: es_tercil(f, "ph", "of_pase") and
         es_tercil(f, "pa", "of_pase"), "fav"),
    ]
    for nombre, cond, lado in HIP:
        sub = [f for f in con_perf if cond(f)]
        n, ep, real, r, z = resid(sub, lado)
        m1 = [f for f in sub if f["season"] <= 2013]
        m2 = [f for f in sub if f["season"] > 2013]
        _, _, _, r1, _ = resid(m1, lado)
        _, _, _, r2, _ = resid(m2, lado)
        consist = "==" if r1 * r2 > 0 else "!="
        print(f"{nombre:<40} {n:>5} {ep:>6.3f} {real:>6.3f} "
              f"{r:>+7.3f} {z:>+6.2f}  {r1:+.3f}/{r2:+.3f} {consist}")

    # ---- G5: ¿EPA agrega info más allá del mercado? (walk-forward) ----
    print("\nG5 — logística walk-forward: mercado solo vs mercado+EPA")

    def features(f):
        ph, pa = f["ph"], f["pa"]
        return [
            (ph["of_pase"] - pa["def_pase"]) - (pa["of_pase"] - ph["def_pase"]),
            (ph["of_carr"] - pa["def_carr"]) - (pa["of_carr"] - ph["def_carr"]),
            (ph["sack_def"] - pa["sack_of"]) - (pa["sack_def"] - ph["sack_of"]),
            1.0 * f["qb_h"] - 1.0 * f["qb_a"],
        ]

    def logit(p):
        return math.log(p / (1 - p))

    def entrenar(X, y, l2=1.0):
        w = np.zeros(X.shape[1])
        for _ in range(200):
            p = 1 / (1 + np.exp(-X @ w))
            g = X.T @ (y - p) - l2 * w
            H = -(X * (p * (1 - p))[:, None]).T @ X - l2 * np.eye(len(w))
            paso = np.linalg.solve(H, g)
            w -= paso
            if np.abs(paso).max() < 1e-9:
                break
        return w

    mejoras = []
    for anio in range(2011, 2026):
        tr = [f for f in con_perf if 2006 <= f["season"] < anio]
        te = [f for f in con_perf if f["season"] == anio]
        if len(te) < 100:
            continue
        Xtr = np.array([[1, logit(f["p"])] + features(f) for f in tr])
        Xte = np.array([[1, logit(f["p"])] + features(f) for f in te])
        ytr = np.array([f["y"] for f in tr])
        yte = np.array([f["y"] for f in te])
        w_full = entrenar(Xtr, ytr)
        w_mkt = entrenar(Xtr[:, :2], ytr)
        eps = 1e-12
        p1 = 1 / (1 + np.exp(-Xte[:, :2] @ w_mkt))
        p2 = 1 / (1 + np.exp(-Xte @ w_full))
        ll1 = -np.mean(yte * np.log(p1 + eps) + (1 - yte) * np.log(1 - p1 + eps))
        ll2 = -np.mean(yte * np.log(p2 + eps) + (1 - yte) * np.log(1 - p2 + eps))
        mejoras.append(ll1 - ll2)
        print(f"  {anio}: logloss mercado {ll1:.4f} -> +EPA {ll2:.4f} "
              f"(mejora {ll1 - ll2:+.4f})")
    m = np.mean(mejoras)
    print(f"\n  MEDIA de mejora out-of-sample: {m:+.5f} "
          f"({'EPA AGREGA señal' if m > 0.001 else 'el mercado ya digirió el EPA'})")


if __name__ == "__main__":
    main()
