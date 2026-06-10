#!/usr/bin/env python3
"""
LEMAITRE — simulador del TORNEO COMPLETO (Monte Carlo).

Grupos (modelos de partido) -> clasificados -> bracket (ratings para cruces
arbitrarios) -> campeón / 4 primeros, y la distribución de marcadores de CADA
LLAVE (los marcadores se puntúan por slot, no por equipo).

Salidas: P(campeón), 4 primeros más probables, y el marcador EV-máximo de cada
llave bajo el puntaje de LEMAITRE.

    python pollas/LEMAITRE/torneo_completo.py --mock /tmp/wc_grupos.json
"""
import argparse, json, os, sys
import numpy as np
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api, cuotas, marcadores, ratings as R
from pollas.CSC.cupos import matriz_de_evento

# Grupos oficiales (nombres de la API)
GRUPOS_OFICIALES = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia & Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["USA", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}
# Ronda de 32: (slot, lado1, lado2). 1A=1º grupo A; 2A=2º; 3:ABCDF=mejor 3º de esos grupos
R32 = [
    (73, "2A", "2B"), (74, "1E", "3:ABCDF"), (75, "1F", "2C"), (76, "1C", "2F"),
    (77, "1I", "3:CDFGH"), (78, "2E", "2I"), (79, "1A", "3:CEFHI"), (80, "1L", "3:EHIJK"),
    (81, "1D", "3:BEFIJ"), (82, "1G", "3:AEHIJ"), (83, "2K", "2L"), (84, "1H", "2J"),
    (85, "1B", "3:EFGIJ"), (86, "1J", "2H"), (87, "1K", "3:DEIJL"), (88, "2D", "2G"),
]
# Cruces siguientes: slot -> (ganador_de, ganador_de)
SIG = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
       97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96),
       101: (97, 98), 102: (99, 100), 104: (101, 102)}  # 104 = final
# Puntaje de marcador por ronda: (exacto, resultado, parcial)
PTS = {**{s: (40, 18, 12) for s, _, _ in R32},
       **{s: (40, 18, 12) for s in range(89, 97)},   # octavos
       **{s: (50, 30, 14) for s in range(97, 101)},  # cuartos
       **{s: (60, 40, 15) for s in (101, 102)},      # semis
       103: (70, 48, 20), 104: (80, 48, 24)}


def cargar(eventos):
    part = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        p = cuotas.a_probabilidades(c["cuotas_1x2"], "proporcional")
        po = cuotas.a_probabilidades(c["cuotas_ou"], "proporcional")[1] if c["cuotas_ou"] else None
        aj = marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=po)
        part.append((c["home"], c["away"], aj["lambda_local"], aj["lambda_visita"],
                     matriz_de_evento(c, "proporcional", 2.5)))
    return part


def jugar(atk, dfn, A, B, rng):
    """Vectorizado: arrays de team-ids A,B (S,) -> goles y ganador (penales si empate)."""
    lA = np.exp(atk[A] - dfn[B]); lB = np.exp(atk[B] - dfn[A])
    gA = rng.poisson(lA); gB = rng.poisson(lB)
    pA = lA / (lA + lB)
    gana = np.where(gA > gB, A, np.where(gB > gA, B, np.where(rng.random(len(A)) < pA, A, B)))
    pierde = np.where(gana == A, B, A)
    return gA, gB, gana, pierde


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=8000)
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    part = cargar(eventos)
    rat, _ = R.ajustar_ratings([(h, a, lh, la) for h, a, lh, la, _ in part])
    teams = sorted(rat); tid = {t: i for i, t in enumerate(teams)}; NT = len(teams)
    atk = np.array([rat[t][0] for t in teams]); dfn = np.array([rat[t][1] for t in teams])
    S = args.sims; rng = np.random.default_rng(0)

    # matrices por matchup de grupo
    Mmap = {(h, a): M for h, a, _, _, M in part}
    grupo_de = {t: g for g, ts in GRUPOS_OFICIALES.items() for t in ts}

    # simular grupos -> posiciones (team-id por grupo y puesto, por sim)
    pts = np.zeros((NT, S)); gd = np.zeros((NT, S)); gf = np.zeros((NT, S))
    for h, a, _, _, M in part:
        fl = M.ravel() / M.sum(); k = rng.choice(fl.size, size=S, p=fl)
        gh, ga = k // M.shape[1], k % M.shape[1]; ih, ia = tid[h], tid[a]
        pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[ih] += gh - ga; gd[ia] += ga - gh; gf[ih] += gh; gf[ia] += ga
    clave = pts * 1e6 + gd * 1e3 + gf + rng.random((NT, S)) * 1e-3

    pos = {}  # (grupo,puesto) -> team-id array (S,)
    tercer_key = {}
    for g, ts in GRUPOS_OFICIALES.items():
        ids = np.array([tid[t] for t in ts])
        orden = np.argsort(-clave[ids], axis=0)   # (4,S) locales
        for puesto in range(4):
            pos[(g, puesto + 1)] = ids[orden[puesto]]
        tercer_key[g] = clave[ids][orden[2], np.arange(S)]

    # mejores 8 terceros + asignación a slots (greedy con restricción de grupo)
    gl = list(GRUPOS_OFICIALES)
    keys = np.array([tercer_key[g] for g in gl])         # (12,S)
    avanza = np.argsort(-keys, axis=0)[:8]               # (8,S) índices de grupo (en gl)
    slot3 = {74: set("ABCDF"), 77: set("CDFGH"), 79: set("CEFHI"), 80: set("EHIJK"),
             81: set("BEFIJ"), 82: set("AEHIJ"), 85: set("EFGIJ"), 87: set("DEIJL")}
    tercer_slot = {s: np.full(S, -1) for s in slot3}     # team-id del 3º en cada slot
    for s in range(S):
        disp = [gl[avanza[i, s]] for i in range(8)]      # grupos cuyos 3º clasifican
        slots = sorted(slot3, key=lambda sl: len(slot3[sl] & set(disp)))  # más restringidos 1º
        usados = set()
        for sl in slots:
            for g in disp:
                if g not in usados and g in slot3[sl]:
                    tercer_slot[sl][s] = pos[(g, 3)][s]; usados.add(g); break

    def lado(code, s_all=True):
        if code.startswith("3:"):
            return None  # se resuelve por slot
        puesto = int(code[0]); g = code[1]
        return pos[(g, puesto)]

    # ronda de 32
    occ = {}  # slot -> (teamA array, teamB array)
    score = {}  # slot -> (gA, gB)
    ganador = {}; perdedor = {}
    for sl, c1, c2 in R32:
        A = tercer_slot[sl] if c1.startswith("3:") else lado(c1)
        B = tercer_slot[sl] if c2.startswith("3:") else lado(c2)
        occ[sl] = (A, B)
        gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
        score[sl] = (gA, gB); ganador[sl] = gana; perdedor[sl] = pierde
    # rondas siguientes
    for sl in [89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104]:
        a, b = SIG[sl]; A, B = ganador[a], ganador[b]
        occ[sl] = (A, B); gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
        score[sl] = (gA, gB); ganador[sl] = gana; perdedor[sl] = pierde
    # 3er puesto: perdedores de semis
    A, B = perdedor[101], perdedor[102]
    occ[103] = (A, B); gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
    score[103] = (gA, gB); ganador[103] = gana; perdedor[103] = pierde

    inv = teams
    campeon = ganador[104]; subcampeon = perdedor[104]
    tercero = ganador[103]; cuarto = perdedor[103]

    def top(arr, n=6):
        c = Counter(arr.tolist())
        return [(inv[i], v / S) for i, v in c.most_common(n)]

    print(f"=== CAMPEÓN (P) ===")
    for t, p in top(campeon, 8): print(f"   {t:16} {p*100:4.1f}%")
    print("=== SUBCAMPEÓN ===")
    for t, p in top(subcampeon, 5): print(f"   {t:16} {p*100:4.1f}%")
    print("=== 3er PUESTO ===")
    for t, p in top(tercero, 5): print(f"   {t:16} {p*100:4.1f}%")

    print("\n=== Marcador EV-máximo por LLAVE (slot) ===")
    def evmax_marcador(gA, gB, pe):
        exact, res, parc = pe
        best, bev = None, -1
        for a in range(6):
            for b in range(6):
                e = (np.mean((gA == a) & (gB == b)) * exact
                     + np.mean((np.sign(a-b) == np.sign(gA-gB)) & ~((gA == a) & (gB == b))) * res
                     + np.mean(((gA == a) | (gB == b)) & ~((gA == a) & (gB == b)) & (np.sign(a-b) != np.sign(gA-gB))) * parc)
                if e > bev: bev, best = e, (a, b)
        return best, bev
    for sl, c1, c2 in R32:
        gA, gB = score[sl]; (a, b), ev = evmax_marcador(gA, gB, PTS[sl])
        oc = "/".join(top(occ[sl][0], 1)[0][0][:3] for _ in [0]) if False else ""
        favA = top(occ[sl][0], 1)[0]; favB = top(occ[sl][1], 1)[0]
        print(f"  P#{sl} {c1:8}vs {c2:9}: {a}-{b}  (prob {favA[0][:12]} vs {favB[0][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
