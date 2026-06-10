#!/usr/bin/env python3
"""
LEMAITRE — modelo FINAL calibrado y optimizado para el puntaje de la polla.

Dos fuentes de verdad, combinadas de forma honesta:
  1) Cuotas de cada PARTIDO de grupos (mercado directo) -> sim de grupos ->
     quién clasifica, posiciones, mejores terceros, marcadores de Fase 32.
     (validado en backtest_clasificacion: P(clasificar) calibrada.)
  2) Cuotas de CAMPEÓN (futures, 5 casas) -> CALIBRA la fuerza de eliminatorias.
     Los ratings sacados solo de partidos de grupo sobre-valoran a equipos de
     grupos débiles (Bélgica, Alemania) e infra-valoran escuadras élite en
     grupos medios (Francia, Inglaterra). El futures corrige justo eso.

Salida: el FORMULARIO completo de LEMAITRE optimizado para EV (no el más
probable cuando difieren), con su valor esperado en puntos por sección.

    ODDS_API_KEY=... python pollas/LEMAITRE/modelo_lemaitre.py            # live
    python pollas/LEMAITRE/modelo_lemaitre.py --mock /tmp/wc_grupos.json  # cache
"""
import argparse, json, os, sys
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api, cuotas, marcadores, ratings as R
from pollas.CSC.cupos import matriz_de_evento

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
# Continente de cada equipo (para extras Continente Campeón/Sub)
CONT = {
    "UEFA": ["Spain","France","England","Portugal","Germany","Netherlands","Belgium",
             "Croatia","Switzerland","Norway","Austria","Czech Republic","Scotland",
             "Sweden","Turkey","Ukraine","Italy","Denmark","Poland"],
    "CONMEBOL": ["Brazil","Argentina","Uruguay","Colombia","Ecuador","Paraguay","Bolivia"],
    "CONCACAF": ["Mexico","USA","Canada","Panama","Haiti","Jamaica","Costa Rica"],
    "CAF": ["Morocco","Senegal","Ivory Coast","Egypt","Algeria","Tunisia","Ghana",
            "South Africa","Cape Verde","DR Congo"],
    "AFC": ["Japan","South Korea","Iran","Saudi Arabia","Australia","Qatar","Iraq",
            "Uzbekistan","Jordan","New Zealand"],  # OFC NZ agrupado en zona AFC/play
}
cont_de = {t: c for c, ts in CONT.items() for t in ts}

R32 = [
    (73, "2A", "2B"), (74, "1E", "3:ABCDF"), (75, "1F", "2C"), (76, "1C", "2F"),
    (77, "1I", "3:CDFGH"), (78, "2E", "2I"), (79, "1A", "3:CEFHI"), (80, "1L", "3:EHIJK"),
    (81, "1D", "3:BEFIJ"), (82, "1G", "3:AEHIJ"), (83, "2K", "2L"), (84, "1H", "2J"),
    (85, "1B", "3:EFGIJ"), (86, "1J", "2H"), (87, "1K", "3:DEIJL"), (88, "2D", "2G"),
]
SIG = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
       93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87),
       97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96),
       101: (97, 98), 102: (99, 100), 104: (101, 102)}
slot3 = {74: set("ABCDF"), 77: set("CDFGH"), 79: set("CEFHI"), 80: set("EHIJK"),
         81: set("BEFIJ"), 82: set("AEHIJ"), 85: set("EFGIJ"), 87: set("DEIJL")}
# Marcador por ronda: (exacto, resultado, parcial)
PTS = {**{s: (40, 18, 12) for s, _, _ in R32},
       **{s: (40, 18, 12) for s in range(89, 97)},
       **{s: (50, 30, 14) for s in range(97, 101)},
       **{s: (60, 40, 15) for s in (101, 102)},
       103: (70, 48, 20), 104: (80, 48, 24)}
ETIQUETA = {**{s: "Fase32" for s, _, _ in R32}, **{s: "Octavos" for s in range(89, 97)},
            **{s: "Cuartos" for s in range(97, 101)}, 101: "Semi", 102: "Semi",
            103: "3er/4to", 104: "Final"}


def cargar(eventos):
    part = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        p = cuotas.a_probabilidades(c["cuotas_1x2"], "proporcional")
        po = (cuotas.a_probabilidades(c["cuotas_ou"], "proporcional")[1]
              if c.get("cuotas_ou") else None)
        aj = marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=po)
        part.append((c["home"], c["away"], aj["lambda_local"], aj["lambda_visita"],
                     matriz_de_evento(c, "proporcional", 2.5)))
    return part


def jugar(atk, dfn, A, B, rng):
    """A,B arrays de team-id -> goles 90' y ganador (penales si empate)."""
    lA = np.exp(np.clip(atk[A] - dfn[B], -3, 2.5)); lB = np.exp(np.clip(atk[B] - dfn[A], -3, 2.5))
    gA = rng.poisson(lA); gB = rng.poisson(lB)
    pA = lA / (lA + lB)
    gana = np.where(gA > gB, A, np.where(gB > gA, B, np.where(rng.random(len(A)) < pA, A, B)))
    pierde = np.where(gana == A, B, A)
    return gA, gB, gana, pierde


def sim_grupos(part, tid, NT, S, rng):
    """Devuelve pos[(g,puesto)], tercer_slot[slot], y goles de grupo gf/gc por team."""
    pts = np.zeros((NT, S)); gd = np.zeros((NT, S)); gf = np.zeros((NT, S)); gc = np.zeros((NT, S))
    for h, a, _, _, M in part:
        fl = M.ravel() / M.sum(); k = rng.choice(fl.size, size=S, p=fl)
        gh, ga = k // M.shape[1], k % M.shape[1]; ih, ia = tid[h], tid[a]
        pts[ih] += np.where(gh > ga, 3, np.where(gh == ga, 1, 0))
        pts[ia] += np.where(ga > gh, 3, np.where(gh == ga, 1, 0))
        gd[ih] += gh - ga; gd[ia] += ga - gh
        gf[ih] += gh; gf[ia] += ga; gc[ih] += ga; gc[ia] += gh
    clave = pts * 1e6 + gd * 1e3 + gf + rng.random((NT, S)) * 1e-3
    pos, tercer_key = {}, {}
    for g, ts in GRUPOS_OFICIALES.items():
        ids = np.array([tid[t] for t in ts])
        orden = np.argsort(-clave[ids], axis=0)
        for puesto in range(4):
            pos[(g, puesto + 1)] = ids[orden[puesto]]
        tercer_key[g] = clave[ids][orden[2], np.arange(S)]
    gl = list(GRUPOS_OFICIALES)
    keys = np.array([tercer_key[g] for g in gl])
    avanza = np.argsort(-keys, axis=0)[:8]
    tercer_slot = {s: np.full(S, -1) for s in slot3}
    for s in range(S):
        disp = [gl[avanza[i, s]] for i in range(8)]
        slots = sorted(slot3, key=lambda sl: len(slot3[sl] & set(disp)))
        usados = set()
        for sl in slots:
            for g in disp:
                if g not in usados and g in slot3[sl]:
                    tercer_slot[sl][s] = pos[(g, 3)][s]; usados.add(g); break
    return pos, tercer_slot, gf, gc, avanza, gl


def entradas_r32(pos, tercer_slot):
    """team-id arrays de cada lado de cada llave de R32 (fijos ante calibración)."""
    ent = {}
    for sl, c1, c2 in R32:
        A = tercer_slot[sl] if c1.startswith("3:") else pos[(int(c1[0]), c1[1])] if False else None
        # lado por código
        def lado(code):
            if code.startswith("3:"):
                return tercer_slot[sl]
            return pos[(code[1], int(code[0]))]
        ent[sl] = (lado(c1), lado(c2))
    return ent


def jugar_ko(atk, dfn, ent_r32, rng):
    """Juega R32->final dadas las entradas fijas. Devuelve occ, score, ganador, perdedor."""
    occ, score, ganador, perdedor = {}, {}, {}, {}
    for sl, _, _ in R32:
        A, B = ent_r32[sl]; occ[sl] = (A, B)
        gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
        score[sl] = (gA, gB); ganador[sl] = gana; perdedor[sl] = pierde
    for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,104]:
        a, b = SIG[sl]; A, B = ganador[a], ganador[b]; occ[sl] = (A, B)
        gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
        score[sl] = (gA, gB); ganador[sl] = gana; perdedor[sl] = pierde
    A, B = perdedor[101], perdedor[102]; occ[103] = (A, B)
    gA, gB, gana, pierde = jugar(atk, dfn, A, B, rng)
    score[103] = (gA, gB); ganador[103] = gana; perdedor[103] = pierde
    return occ, score, ganador, perdedor


def _sim_champ(atk, dfn, ent_r32, NT, S, seed=777):
    rng = np.random.default_rng(seed)
    _, _, ganador, _ = jugar_ko(atk, dfn, ent_r32, rng)
    c = Counter(ganador[104].tolist())
    return np.array([c.get(i, 0) / S for i in range(NT)])


def calibrar(atk0, dfn0, ent_r32, teams, tid, futures, S):
    """Recalibra la FUERZA de eliminatorias a las cuotas de CAMPEÓN (mercado).

    El futures es la mejor estimación de fuerza de eliminatoria (corrige el sesgo
    de derivar ratings solo de partidos de grupo: equipos de grupos débiles se
    sobre-estiman). Importamos su RANKING: δ_t ∝ (log p_t − media), que aplica
    una fuerza extra monótona en la prob de campeón del mercado. Una sola
    temperatura τ controla cuánto; se busca τ en 1-D para que la distribución de
    campeón simulada cuadre con la del mercado (mínima divergencia KL). Estable
    por construcción (1 parámetro, monótono)."""
    NT = len(teams)
    p_mkt = np.array([futures.get(t, 1e-6) for t in teams]); p_mkt = p_mkt / p_mkt.sum()
    f_sim = atk0 + dfn0
    cov = p_mkt > 0.003                           # contendientes con cuota informativa
    forma = np.log(p_mkt[cov]) - np.log(p_mkt[cov]).mean()   # ranking del mercado, centrado
    mu = f_sim[cov].mean()                         # nivel global (preserva goles)
    pm = p_mkt[cov] / p_mkt[cov].sum()             # objetivo renormalizado a contendientes
    best = (1e9, 0.6, None)
    for tau in np.arange(0.1, 1.21, 0.1):
        d = np.zeros(NT)
        d[cov] = ((mu + tau * forma) - f_sim[cov]) / 2.0   # REEMPLAZA fuerza sim por la del mercado
        q = _sim_champ(atk0 + d, dfn0 + d, ent_r32, NT, S)
        qc = np.clip(q[cov], 1e-4, 1); qc = qc / qc.sum()
        kl = float(np.sum(pm * np.log(pm / qc)))
        if kl < best[0]:
            best = (kl, tau, d)
    _, tau, delta = best
    q = _sim_champ(atk0 + delta, dfn0 + delta, ent_r32, NT, S)
    return delta, q, p_mkt, tau


def evmax_marcador(gA, gB, pe):
    exact, res, parc = pe
    best, bev = (1, 0), -1.0
    for a in range(7):
        for b in range(7):
            ex = (gA == a) & (gB == b)
            rmatch = (np.sign(a - b) == np.sign(gA - gB)) & ~ex
            pmatch = ((gA == a) | (gB == b)) & ~ex & (np.sign(a - b) != np.sign(gA - gB))
            e = ex.mean() * exact + rmatch.mean() * res + pmatch.mean() * parc
            if e > bev:
                bev, best = e, (a, b)
    return best, bev


def top(arr, inv, S, n=6):
    return [(inv[i], v / S) for i, v in Counter(arr.tolist()).most_common(n)]


def p_gana(atk, dfn, ia, ib, kmax=10):
    """P(ia vence a ib) en eliminatoria (90' + penales si empata), analítica."""
    lA = float(np.exp(np.clip(atk[ia] - dfn[ib], -3, 2.5)))
    lB = float(np.exp(np.clip(atk[ib] - dfn[ia], -3, 2.5)))
    from math import exp, factorial
    pa = lambda k, l: exp(-l) * l ** k / factorial(k)
    PA = np.array([pa(k, lA) for k in range(kmax)]); PB = np.array([pa(k, lB) for k in range(kmax)])
    win = sum(PA[i] * PB[j] for i in range(kmax) for j in range(kmax) if i > j)
    emp = sum(PA[i] * PB[i] for i in range(kmax))
    return win + emp * lA / (lA + lB)


def arbol_consistente(atk, dfn, tid, inv, r32_occ):
    """Forward pass: árbol coherente. En cada llave avanza el equipo con mayor
    P(ganar) head-to-head entre los DOS ocupantes elegidos. Devuelve dict
    slot -> (equipoA, equipoB, ganador)."""
    win = {}; res = {}
    for sl, _, _ in R32:
        A, B = r32_occ[sl]
        g = A if p_gana(atk, dfn, tid[A], tid[B]) >= 0.5 else B
        win[sl] = g; res[sl] = (A, B, g)
    for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,104]:
        a, b = SIG[sl]; A, B = win[a], win[b]
        g = A if p_gana(atk, dfn, tid[A], tid[B]) >= 0.5 else B
        win[sl] = g; res[sl] = (A, B, g)
    # 3er puesto: perdedores de semis
    lA = res[101][0] if win[101] == res[101][1] else res[101][1]
    lB = res[102][0] if win[102] == res[102][1] else res[102][1]
    g = lA if p_gana(atk, dfn, tid[lA], tid[lB]) >= 0.5 else lB
    win[103] = g; res[103] = (lA, lB, g)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=20000)
    ap.add_argument("--no-calibrar", action="store_true")
    args = ap.parse_args(argv)

    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    part = cargar(eventos)
    rat, _ = R.ajustar_ratings([(h, a, lh, la) for h, a, lh, la, _ in part])
    teams = sorted(rat); tid = {t: i for i, t in enumerate(teams)}; NT = len(teams)
    inv = teams
    atk0 = np.array([rat[t][0] for t in teams]); dfn0 = np.array([rat[t][1] for t in teams])
    S = args.sims; rng = np.random.default_rng(0)

    pos, tercer_slot, gf, gc, avanza, gl = sim_grupos(part, tid, NT, S, rng)
    ent_r32 = entradas_r32(pos, tercer_slot)

    futures = (json.load(open(args.futures)) if os.path.exists(args.futures) else {})
    if futures and not args.no_calibrar:
        q_uncal = _sim_champ(atk0, dfn0, ent_r32, NT, S)
        delta, q_cal, p_mkt, tau = calibrar(atk0, dfn0, ent_r32, teams, tid, futures, S)
        atk, dfn = atk0 + delta, dfn0 + delta
        print(f"=== CALIBRACIÓN a champion futures (5 casas) · τ={tau:.1f} ===")
        print(f"{'equipo':16} {'sim_crudo':>9} {'calibrado':>9} {'mercado':>8} {'Δfuerza':>8}")
        for t in sorted(teams, key=lambda t: -futures.get(t, 0))[:14]:
            i = tid[t]
            print(f"{t:16} {q_uncal[i]*100:8.1f}% {q_cal[i]*100:8.1f}% {p_mkt[i]*100:7.1f}% {2*delta[i]:+8.2f}")
        print()
    else:
        atk, dfn = atk0, dfn0

    occ, score, ganador, perdedor = jugar_ko(atk, dfn, ent_r32, rng)
    campeon, subcampeon = ganador[104], perdedor[104]
    tercero, cuarto = ganador[103], perdedor[103]

    print("=== CAMPEÓN (calibrado) ===")
    for t, p in top(campeon, inv, S, 8): print(f"   {t:16} {p*100:5.1f}%")
    print("=== SUBCAMPEÓN ===")
    for t, p in top(subcampeon, inv, S, 5): print(f"   {t:16} {p*100:5.1f}%")
    print("=== 3º / 4º (finalistas perdedores de semi) ===")
    for t, p in top(tercero, inv, S, 5): print(f"   {t:16} {p*100:5.1f}%")

    # ---------- FORMULARIO ----------
    print("\n=== GRUPOS — orden 1/2/3/4 (EV-máx por posición) ===")
    grupo_pick = {}
    for g, ts in GRUPOS_OFICIALES.items():
        ids = [tid[t] for t in ts]
        # P(equipo termina en puesto p)
        Pp = {t: [0]*4 for t in ts}
        for puesto in range(1, 5):
            c = Counter(pos[(g, puesto)].tolist())
            for t in ts: Pp[t][puesto-1] = c.get(tid[t], 0)/S
        # asignación EV-máx: greedy por puesto 1..4 maximizando prob marginal sin repetir
        libres = set(ts); orden_pick = []
        for puesto in range(4):
            best = max(libres, key=lambda t: Pp[t][puesto])
            orden_pick.append(best); libres.discard(best)
        grupo_pick[g] = orden_pick
        det = "  ".join(f"{t[:11]}({Pp[t][i]*100:.0f}%)" for i, t in enumerate(orden_pick))
        print(f"  {g}: {det}")

    print("\n=== 8 MEJORES TERCEROS (asignados a su llave) ===")
    c3 = Counter()
    for s in range(S):
        for i in range(8):
            c3[gl[avanza[i, s]]] += 1
    tercer_pick = {}                     # slot -> equipo 3º (modal)
    for sl in sorted(slot3):
        t3 = top(tercer_slot[sl], inv, S, 1)[0]
        tercer_pick[sl] = t3[0]
    for g, v in c3.most_common(8):
        t3 = top(pos[(g, 3)], inv, S, 1)[0][0]
        print(f"  3º {g}: {t3:18} (grupo avanza {v/S*100:3.0f}%)")

    # ----- ocupantes R32 (coherentes con picks de grupo + terceros) -----
    def occ_pick(code, sl):
        if code.startswith("3:"):
            return tercer_pick[sl]
        return grupo_pick[code[1]][int(code[0]) - 1]
    r32_occ = {sl: (occ_pick(c1, sl), occ_pick(c2, sl)) for sl, c1, c2 in R32}
    arbol = arbol_consistente(atk, dfn, tid, inv, r32_occ)   # árbol coherente

    print("\n=== BRACKET (árbol coherente) — equipos + marcador EV-máx ===")
    ev_total_marc = 0.0
    pick_marc = {}
    for sl, c1, c2 in R32:
        A, B, g = arbol[sl]
        (a, b), ev = evmax_marcador(score[sl][0], score[sl][1], PTS[sl]); ev_total_marc += ev
        pick_marc[sl] = (a, b)
        print(f"  P#{sl} [{c1:8}vs {c2:9}] {A[:13]:13} {a}-{b} {B[:13]:13} | gana {g[:12]} (EV marc {ev:.1f})")
    for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104]:
        A, B, g = arbol[sl]
        (a, b), ev = evmax_marcador(score[sl][0], score[sl][1], PTS[sl]); ev_total_marc += ev
        pick_marc[sl] = (a, b)
        print(f"  P#{sl} [{ETIQUETA[sl]:8}] {A[:13]:13} {a}-{b} {B[:13]:13} | gana {g[:12]}")
    camp = arbol[104][2]; sub = arbol[104][0] if arbol[104][2] == arbol[104][1] else arbol[104][1]
    ter = arbol[103][2]; cua = arbol[103][0] if arbol[103][2] == arbol[103][1] else arbol[103][1]
    print(f"\n  CUADRO DE HONOR (coherente):  1º {camp}   2º {sub}   3º {ter}   4º {cua}")
    print(f"  EV total de MARCADORES (suma de slots) ≈ {ev_total_marc:.0f} / 1430")

    # ---------- EXTRAS modelables ----------
    print("\n=== EXTRAS (modelables desde la simulación) ===")
    # total goles del torneo = goles de grupos + goles de eliminatorias
    tot_grupo = gf.sum(axis=0)                       # (S,) suma de GF de todos = todos los goles de grupo
    tot_ko = np.zeros(S)
    for sl in list(score):
        tot_ko += score[sl][0] + score[sl][1]
    tot = tot_grupo + tot_ko
    print(f"  Número total de goles: media {tot.mean():.0f}  (p10 {np.percentile(tot,10):.0f} - p90 {np.percentile(tot,90):.0f})  -> pick {round(tot.mean())}")
    # continente campeón / sub
    cc = Counter(cont_de.get(inv[i], "?") for i in campeon.tolist())
    cs = Counter(cont_de.get(inv[i], "?") for i in subcampeon.tolist())
    print(f"  Continente campeón:   {cc.most_common(1)[0][0]} ({cc.most_common(1)[0][1]/S*100:.0f}%)")
    print(f"  Continente subcampeón:{cs.most_common(1)[0][0]} ({cs.most_common(1)[0][1]/S*100:.0f}%)")
    # equipo + / - goles a favor / en contra (en grupos, proxy de todo el torneo)
    gf_mean = gf.mean(axis=1); gc_mean = gc.mean(axis=1)
    print(f"  Equipo + goles a favor (grupos):  {inv[int(np.argmax(gf_mean))]} ({gf_mean.max():.1f})")
    print(f"  Equipo - goles a favor (grupos):  {inv[int(np.argmin(gf_mean))]} ({gf_mean.min():.1f})")
    print(f"  Equipo + goles en contra (grupos):{inv[int(np.argmax(gc_mean))]} ({gc_mean.max():.1f})")
    print(f"  Equipo - goles en contra (grupos):{inv[int(np.argmin(gc_mean))]} ({gc_mean.min():.1f})")
    # último lugar: equipo con peor clave promedio (menos puntos) -> usar gf-gc proxy
    # Colombia (grupo K)
    ic = tid["Colombia"]
    print(f"  Colombia — GF grupos: {gf[ic].mean():.1f}  GC grupos: {gc[ic].mean():.1f}")
    # posición final Colombia: P de cada ronda alcanzada
    avK = (Counter([g for s in range(S) for g in [gl[avanza[i,s]] for i in range(8)]]))
    # P Colombia 1/2/3/4 en grupo K
    PcolK = []
    for puesto in range(1,5):
        PcolK.append(Counter(pos[("K",puesto)].tolist()).get(ic,0)/S)
    print(f"  Colombia en grupo K — 1º:{PcolK[0]*100:.0f}% 2º:{PcolK[1]*100:.0f}% 3º:{PcolK[2]*100:.0f}% 4º:{PcolK[3]*100:.0f}%")

    # ============== VALOR ESPERADO EN PUNTOS (Monte Carlo, vs el torneo simulado)
    # Reglas EXACTAS donde el reglamento es inequívoco (marcadores, cuadro de honor,
    # semis); CLASIFICACIÓN se reporta como nº esperado de aciertos exactos × (presupuesto
    # de la sección / nº de casillas) — aproximación lineal, claramente etiquetada.
    print("\n=== VALOR ESPERADO EN PUNTOS (sobre el torneo simulado) ===")
    cid = {t: tid[t] for t in teams}
    # --- MARCADORES (exacto) ---
    ev_marc = np.zeros(S)
    for sl in pick_marc:
        a, b = pick_marc[sl]; gA, gB = score[sl]; ex_, re_, pa_ = PTS[sl]
        exact = (gA == a) & (gB == b)
        result = (~exact) & (np.sign(a - b) == np.sign(gA - gB))
        partial = (~exact) & (~result) & ((gA == a) | (gB == b))
        ev_marc += exact * ex_ + result * re_ + partial * pa_
    # --- CUADRO DE HONOR (G, 210): 80/60/40/30 exacto; 25 si está pero en otro puesto ---
    real_pos = {1: campeon, 2: subcampeon, 3: tercero, 4: cuarto}
    honor_pick = {1: cid[camp], 2: cid[sub], 3: cid[ter], 4: cid[cua]}
    honor_pts = {1: 80, 2: 60, 3: 40, 4: 30}
    setreal = np.stack([campeon, subcampeon, tercero, cuarto])  # (4,S)
    ev_honor = np.zeros(S)
    for k in (1, 2, 3, 4):
        exacto = real_pos[k] == honor_pick[k]
        enhonor = (setreal == honor_pick[k]).any(axis=0) & (~exacto)
        ev_honor += exacto * honor_pts[k] + enhonor * 25
    # --- SEMIS ganadores/perdedores (E, 190): 55 por finalista, 40 por perdedor de semi ---
    finalistas_real = np.stack([campeon, subcampeon])     # (2,S)
    perdsemi_real = np.stack([tercero, cuarto])           # (2,S)
    ev_semE = np.zeros(S)
    for p in (cid[camp], cid[sub]):
        ev_semE += (finalistas_real == p).any(axis=0) * 55
    for p in (cid[ter], cid[cua]):
        ev_semE += (perdsemi_real == p).any(axis=0) * 40
    # --- EXTRAS modelables (continente, total goles, Colombia) ---
    cont_camp = np.array([cont_de.get(inv[i], "?") for i in campeon.tolist()])
    cont_sub = np.array([cont_de.get(inv[i], "?") for i in subcampeon.tolist()])
    pick_cont_c = cc.most_common(1)[0][0]; pick_cont_s = cs.most_common(1)[0][0]
    pick_tot = round(tot.mean())
    ev_extra = ((cont_camp == pick_cont_c) * 20 + (cont_sub == pick_cont_s) * 20
                + (np.abs(tot - pick_tot) <= 3) * 100)   # total goles: ±3 (regla exacta incierta)
    # --- CLASIFICACIÓN (aprox lineal por presupuesto) ---
    # A Fase32 (640): aciertos de ocupante exacto en 32 casillas
    aciertos_A = np.zeros(S)
    for sl, c1, c2 in R32:
        A_real, B_real = ent_r32[sl]
        aciertos_A += (A_real == cid[r32_occ[sl][0]]) + (B_real == cid[r32_occ[sl][1]])
    evA = aciertos_A / 32.0 * 640
    # B Octavos / orden de grupo (280): aciertos de 1º y 2º exactos en 12 grupos (24 casillas)
    aciertos_B = np.zeros(S)
    for g in GRUPOS_OFICIALES:
        aciertos_B += (pos[(g, 1)] == cid[grupo_pick[g][0]]) + (pos[(g, 2)] == cid[grupo_pick[g][1]])
    evB = aciertos_B / 24.0 * 280
    # C Cuartos (240): aciertos de equipos en cuartos (8 plazas = ganadores de octavos)
    win_oct_real = np.stack([ganador[s] for s in range(89, 97)])  # (8,S)
    mis_cuartos = set(cid[arbol[s][2]] for s in range(89, 97))
    aciertos_C = np.zeros(S)
    for p in mis_cuartos:
        aciertos_C += (win_oct_real == p).any(axis=0)
    evC = aciertos_C / 8.0 * 240
    # D Semis (160): aciertos de equipos en semis (4 plazas)
    win_cua_real = np.stack([ganador[s] for s in range(97, 101)])  # (4,S)
    mis_semis = set(cid[arbol[s][2]] for s in range(97, 101))
    aciertos_D = np.zeros(S)
    for p in mis_semis:
        aciertos_D += (win_cua_real == p).any(axis=0)
    evD = aciertos_D / 4.0 * 160

    ev_clasif = evA + evB + evC + evD
    ev_total = ev_marc + ev_honor + ev_semE + ev_extra + ev_clasif
    def linea(nombre, arr, mx):
        print(f"  {nombre:28} {arr.mean():7.0f}  (p10 {np.percentile(arr,10):4.0f} - p90 {np.percentile(arr,90):4.0f})  / {mx}")
    linea("Marcadores (exacto)", ev_marc, 1430)
    linea("Clasificación (aprox lineal)", ev_clasif, 1320)
    linea("  · A Fase 32", evA, 640); linea("  · B grupos/octavos", evB, 280)
    linea("  · C cuartos", evC, 240); linea("  · D semis", evD, 160)
    linea("Cuadro de honor (G, exacto)", ev_honor, 210)
    linea("Semis gan/perd (E, exacto)", ev_semE, 190)
    linea("Extras modelables", ev_extra, 140)
    print(f"  {'-'*60}")
    linea("TOTAL estimado", ev_total, 3900)
    print(f"  (no incluye extras de jugadores ~360 pts: goleador, 1er/últ gol, gol 50/100)")

    # ============== GUARDAR FORMULARIO ==============
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FORMULARIO_lemaitre.csv")
    with open(out, "w", encoding="utf-8") as f:
        f.write("seccion,casilla,pick,marcador,detalle\n")
        for g in GRUPOS_OFICIALES:
            for i, t in enumerate(grupo_pick[g]):
                f.write(f"GRUPO_{g},pos{i+1},{t},,\n")
        for sl, c1, c2 in R32:
            A, B, gw = arbol[sl]; a, b = pick_marc[sl]
            f.write(f"FASE32,P#{sl}_{c1},{A},,\n")
            f.write(f"FASE32,P#{sl}_{c2},{B},,\n")
            f.write(f"FASE32,P#{sl}_marcador,{gw},{a}-{b},gana {gw}\n")
        for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104]:
            A, B, gw = arbol[sl]; a, b = pick_marc[sl]
            f.write(f"{ETIQUETA[sl]},P#{sl},{gw},{a}-{b},{A} vs {B}\n")
        f.write(f"HONOR,campeon,{camp},,\n")
        f.write(f"HONOR,subcampeon,{sub},,\n")
        f.write(f"HONOR,tercero,{ter},,\n")
        f.write(f"HONOR,cuarto,{cua},,\n")
        f.write(f"EXTRA,continente_campeon,{pick_cont_c},,\n")
        f.write(f"EXTRA,continente_subcampeon,{pick_cont_s},,\n")
        f.write(f"EXTRA,total_goles,{pick_tot},,\n")
        f.write(f"EXTRA,equipo_mas_gf,{inv[int(np.argmax(gf_mean))]},,\n")
        f.write(f"EXTRA,equipo_menos_gf,{inv[int(np.argmin(gf_mean))]},,\n")
        f.write(f"EXTRA,equipo_mas_gc,{inv[int(np.argmax(gc_mean))]},,\n")
        f.write(f"EXTRA,equipo_menos_gc,{inv[int(np.argmin(gc_mean))]},,\n")
        col_pos = int(np.argmax(PcolK)) + 1
        f.write(f"EXTRA_COL,posicion_grupo_colombia,{col_pos},,GF~{gf[ic].mean():.0f} GC~{gc[ic].mean():.0f}\n")
        f.write(f"EXTRA_COL,colombia_gf,{round(gf[ic].mean())},,\n")
        f.write(f"EXTRA_COL,colombia_gc,{round(gc[ic].mean())},,\n")
    print(f"\nFormulario guardado en {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
