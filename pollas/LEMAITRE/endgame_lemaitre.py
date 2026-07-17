#!/usr/bin/env python3
"""
ENDGAME LEMAITRE — Monte Carlo del torneo restante para estimar P(ganar) y premio.

LEMAITRE está 100% locked: tenemos las 27 planillas (marcadores + clasificados
futuros). Eso permite simular EXACTO el resto del bracket y rankear.

Modelo (SUPUESTOS declarados):
- Marcadores restantes: goles ~ Poisson(fuerza), fuerza = goles esperados de cada
  equipo sacados de las cuotas de octavos (proxy de ataque). Empate en knockout ->
  penales por Bernoulli proporcional a la fuerza (define avance, no marcador).
- Puntos de marcador por ronda: los VALIDADOS (OCT 40/18/12, CUAR 50/30/14,
  SEMI 60/40/15, TERC 70/48/20, FINAL 80/48/24).
- Clasificación por slot: tramos del app (F32 40/25/20/15, OCT 35/25/18/12) YA en
  el total actual. Para tramos que el app AÚN no codifica se ASUME el patrón
  decreciente: CUAR 30/20/15/10, SEMI 25/18/12/8. Standings final (camp/sub/3er/
  4to) por el Excel: 80/60/40/30 y 25 por acertar en distinto puesto. [SUPUESTO]
- Extras ya concluibles (último lugar=Irak, menos_goles_fav=Panamá) se dejan como
  están (el admin los cargará; no cambian el orden relativo del top).

Premio: pozo = 27 * $234.000 = $6.318.000; se reparte el 90%: 1º 60% / 2º 30% /
3º 10% (empates suman y dividen).

    python pollas/LEMAITRE/endgame_lemaitre.py [N_sims]
"""
import json, os, sys, re, unicodedata
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pollas.LEMAITRE.puntos_lemaitre import calc_todo, calc_marcador, norm

AQUI = os.path.dirname(os.path.abspath(__file__))
PMARC = {"OCT": (40, 18, 12), "CUAR": (50, 30, 14), "SEMI": (60, 40, 15),
         "TERC": (70, 48, 20), "FINAL": (80, 48, 24)}
# clasif 97-102 + finalistas/terceros: YA en calc_todo (regla real validada 17-jul)
PFINAL = {"camp": 80, "sub": 40, "3er": 40, "4to": 30}         # REAL (FINAL_KEYS del app)
CUOTA = 234_000; NPART = 27; PREMIOS = [0.60, 0.30, 0.10]

ALIAS = {'francia':'france','marruecos':'morocco','noruega':'norway','inglaterra':'england',
         'espana':'spain','belgica':'belgium','eeuu':'unitedstates','estadosunidos':'unitedstates',
         'argentina':'argentina','egipto':'egypt','suiza':'switzerland','colombia':'colombia',
         'brasil':'brazil','mexico':'mexico','portugal':'portugal','paraguay':'paraguay',
         'canada':'canada','usa':'unitedstates'}
def cn(s):
    a = re.sub('[^a-z]', '', unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode().lower())
    return ALIAS.get(a, a)


def marc_pts(pred, g1, g2, fase):
    if not pred or pred.get('e1') is None: return 0
    e, g, p = PMARC[fase]; e1, e2 = pred['e1'], pred['e2']
    if e1 == g1 and e2 == g2: return e
    rw = 1 if g1 > g2 else (2 if g1 < g2 else 0); pw = 1 if e1 > e2 else (2 if e1 < e2 else 0)
    pts = (g if rw == pw else 0) + (p if (e1 == g1 or e2 == g2) else 0)
    return pts if rw == pw or (e1 == g1 or e2 == g2) else 0


def clasif_pts(pred, r1, r2, tramo):
    if not pred or not pred.get('e1') or not r1: return 0
    a, b, c, d = tramo
    p1, p2 = norm(pred['e1']), norm(pred['e2']); r1, r2 = norm(r1), norm(r2)
    if p1 == r1 and p2 == r2: return a
    if p1 == r2 and p2 == r1: return b
    if p1 == r1 or p2 == r2: return c
    if p1 == r2 or p2 == r1: return d
    return 0


def main(N=20000):
    BD = json.load(open(os.path.join(AQUI, "lemaitre_data.json"), encoding="utf-8"))
    lam = json.load(open("/tmp/claude-0/-home-user-Apuestas-mundial/"
                         "d76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/lam.json"))
    parts = [str(p['num']) for p in BD['participants']]
    names = {str(p['num']): p['name'] for p in BD['participants']}
    pm = BD['predictions_m']; pe = BD['predictions_e']; ph = BD['partido_phases']
    pt = BD['partido_teams']; req = BD['real_equipos']; rs = BD['real_scores']
    base = calc_todo(BD)                      # total actual validado (hasta P#91 marc, 73-96 clasif)
    base_tot = {n: base[n]['total'] for n in parts}
    yo = next(n for n in parts if names[n] == 'Pocho')

    # Octavos YA jugados: fijos (avance + marcador). Los que están en real_scores
    # ya tienen su marcador en base_tot (no re-sumar); P#92 lo conocemos pero el
    # admin no lo cargó, así que SÍ se le suma el marcador.
    fixed = {}
    for s in range(89, 105):
        r = rs.get(str(s))
        if r and r.get('g1') is not None:
            fixed[s] = (r['e1'], r['e2'], r['g1'], r['g2'])
    PEN_WINNERS = {96: 'Suiza'}   # penales conocidos (Suiza pasó)
    if 92 not in fixed:
        fixed[92] = ('México', 'Inglaterra', 2, 3)   # jugado, admin no lo cargó
    en_base = set(int(k) for k in rs if rs[k].get('g1') is not None)  # marcador ya en base_tot

    def strength(team):
        return max(0.35, lam.get(cn(team), 1.0))

    # ---------------- EXTRAS PENDIENTES (auditoría 15-jul) ----------------
    # Ground truth calculado de los resultados (con P#92): goles totales 293,
    # GF: Argentina 17 / Francia 16 / Inglaterra 14 / España 13; GC: España 1 =
    # Colombia 1 (México 3); último lugar Irak; más GC Túnez=Irak (12); menos GF
    # Panamá; Colombia GF 5 / GC 1. Goleador real (Goal.com 15-jul): Mbappé 8
    # (1 asist) > Messi 8 (0) > Haaland 7 > Kane/Bellingham 6.
    # Solo se suma lo que el admin AÚN no cargó (real_extras[k] is None).
    pxs = BD['predictions_x']; rx = BD.get('real_extras', {})
    def nx(s): return cn(s) if s else ''
    def gpick(n, k): return (pxs.get(n) or {}).get(k)
    det = {n: 0 for n in parts}     # concluibles deterministas
    if rx.get('real_ultimo_lugar') is None:
        for n in parts:
            if nx(gpick(n, 'ultimo_lugar')) == 'irak': det[n] += 30
    if rx.get('real_menos_goles_fav') is None:
        for n in parts:
            if nx(gpick(n, 'menos_goles_fav')) == 'panama': det[n] += 30
    if rx.get('real_mas_goles_contra') is None:      # empate Túnez/Irak: pago generoso a ambos
        for n in parts:
            if nx(gpick(n, 'mas_goles_contra')) in ('tunez', 'irak'): det[n] += 30
    if rx.get('real_col_goles_fav') is None:
        for n in parts:
            try:
                if int(gpick(n, 'col_goles_fav')) == 5: det[n] += 50
            except (TypeError, ValueError): pass
    if rx.get('real_col_goles_contra') is None:
        for n in parts:
            try:
                if int(gpick(n, 'col_goles_contra')) == 1: det[n] += 50
            except (TypeError, ValueError): pass
    for n in parts:
        base_tot[n] += det[n]

    def gol_name(s):
        s = nx(s)
        if 'mbap' in s: return 'mbappe'
        if 'kane' in s or 'kean' in s: return 'kane'
        if 'messi' in s: return 'messi'
        return s
    PICK_GOL = {n: gol_name(gpick(n, 'goleador')) for n in parts}
    def pick_int(n, k):
        try: return int(gpick(n, k))
        except (TypeError, ValueError): return None
    PICK_NGOL = {n: pick_int(n, 'goles_goleador') for n in parts}
    PICK_TOT = {n: pick_int(n, 'total_goles') for n in parts}
    PICK_MGF = {n: nx(gpick(n, 'mas_goles_fav')) for n in parts}
    PICK_mGC = {n: nx(gpick(n, 'menos_goles_contra')) for n in parts}
    PICK_UG = {n: nx(gpick(n, 'ultimo_gol_equipo')) for n in parts}
    PICK_CC = {n: nx(gpick(n, 'continente_camp')) for n in parts}
    PICK_CS = {n: nx(gpick(n, 'continente_subcamp')) for n in parts}
    def es_europa(s): return 'europ' in s
    def es_america(s): return 'amer' in s or 'sudam' in s or s == 'ame'
    GF0 = {'Francia': 16, 'Argentina': 17, 'Inglaterra': 14, 'España': 13}

    def extras_sim(scores, winner, loser, rng):
        """Extras que dependen del 3er puesto (103) y la final (104). SUPUESTOS:
        cuota de goles del goleador en su equipo (Mbappé .45 Fra, Kane .35 Ing,
        Messi .45 Arg); empates de GF/GC pagan a todos los empatados; empate de
        goleador lo gana Mbappé (asistencias) y Messi le gana a Kane."""
        add = {n: 0 for n in parts}
        s3 = scores.get(103); s4 = scores.get(104)
        if not s3 or not s4: return add
        gF, gI = s3[2], s3[3]; gE, gA = s4[2], s4[3]
        # total de goles del torneo (120)
        if rx.get('real_total_goles') is None:
            tot = 293 + gF + gI + gE + gA
            for n in parts:
                if PICK_TOT[n] == tot: add[n] += 120
        # más goles a favor (30)
        if rx.get('real_mas_goles_fav') is None:
            gf = {'francia': GF0['Francia'] + gF, 'inglaterra': GF0['Inglaterra'] + gI,
                  'espana': GF0['España'] + gE, 'argentina': GF0['Argentina'] + gA}
            mx = max(gf.values()); lids = {k for k, v in gf.items() if v == mx}
            for n in parts:
                if PICK_MGF[n] in lids: add[n] += 30
        # menos goles en contra (30): España 1+gA vs Colombia 1 (México 3)
        if rx.get('real_menos_goles_contra') is None:
            lids = {'colombia'} | ({'espana'} if gA == 0 else set())
            for n in parts:
                if PICK_mGC[n] in lids: add[n] += 30
        # último gol del torneo (20): equipo del último gol de la final (o del 3er si final 0-0)
        if rx.get('real_ultimo_gol_equipo') is None:
            if gE + gA > 0:
                ug = 'espana' if rng.random() < gE / (gE + gA) else 'argentina'
            elif gF + gI > 0:
                ug = 'francia' if rng.random() < gF / (gF + gI) else 'inglaterra'
            else: ug = None
            for n in parts:
                if ug and PICK_UG[n] == ug: add[n] += 20
        # continentes (20 c/u)
        camp = winner.get(104); sub = loser.get(104)
        if rx.get('real_continente_camp') is None and camp:
            eur = norm(camp) == norm('España')
            for n in parts:
                if (es_europa(PICK_CC[n]) if eur else es_america(PICK_CC[n])): add[n] += 20
        if rx.get('real_continente_subcamp') is None and sub:
            eur = norm(sub) == norm('España')
            for n in parts:
                if (es_europa(PICK_CS[n]) if eur else es_america(PICK_CS[n])): add[n] += 20
        # goleador (50) + nº goles del goleador (50)
        if rx.get('real_goleador') is None:
            mb = 8 + rng.binomial(gF, 0.45); ms = 8 + rng.binomial(gA, 0.45)
            kn = 6 + rng.binomial(gI, 0.35)
            if mb >= ms and mb >= kn: lider, ngl = 'mbappe', mb
            elif ms >= kn:            lider, ngl = 'messi', ms
            else:                     lider, ngl = 'kane', kn
            for n in parts:
                if PICK_GOL[n] == lider:
                    add[n] += 50
                    if PICK_NGOL[n] == ngl: add[n] += 50
        return add
    # -----------------------------------------------------------------------

    rng = np.random.default_rng(7)
    pot = NPART * CUOTA
    premio_val = [PREMIOS[i] * 0.9 * pot for i in range(3)]
    wins = {n: 0.0 for n in parts}; money = {n: 0.0 for n in parts}
    rank_hist = {n: [] for n in parts}

    for _ in range(N):
        gan = dict(base_tot)                  # copia del total base
        scores = {}                           # slot -> (e1,e2,g1,g2)
        winner = {}; loser = {}

        def equipos_de(slot):
            a, b = pt[str(slot)]
            def resolve(tok):
                if tok.startswith('G#'): return winner.get(int(tok[2:]))
                if tok.startswith('P#'): return loser.get(int(tok[2:]))
                return None
            return resolve(a), resolve(b)

        # slots 89..104: fijos (jugados) o simulados
        for slot in range(89, 105):
            fase = ph[str(slot)]
            if slot in fixed:
                t1, t2, g1, g2 = fixed[slot]
                if slot not in en_base:           # marcador aún no en base (P#92)
                    for n in parts:
                        gan[n] += marc_pts(pm[n].get(str(slot)), g1, g2, fase)
            else:
                if slot <= 96:
                    e = req.get(str(slot), {}); t1, t2 = e.get('e1'), e.get('e2')
                else:
                    t1, t2 = equipos_de(slot)
                if not t1 or not t2:
                    continue
                l1, l2 = strength(t1), strength(t2)
                g1 = min(int(rng.poisson(l1)), 7); g2 = min(int(rng.poisson(l2)), 7)
                for n in parts:
                    gan[n] += marc_pts(pm[n].get(str(slot)), g1, g2, fase)
            scores[slot] = (t1, t2, g1, g2)
            # avance (penales si empate) — no aplica a 3er puesto (103)
            if slot != 103:
                l1, l2 = strength(t1), strength(t2)
                if slot in PEN_WINNERS and g1 == g2:
                    w = PEN_WINNERS[slot]; lo = t2 if w == t1 else t1
                elif g1 > g2: w, lo = t1, t2
                elif g2 > g1: w, lo = t2, t1
                else:
                    w, lo = (t1, t2) if rng.random() < l1 / (l1 + l2) else (t2, t1)
                winner[slot] = w; loser[slot] = lo

        # standings final: campeón=winner[104], sub=loser[104], 3º=winner[103], 4º=loser[103]
        camp = winner.get(104); sub = loser.get(104); ter = winner.get(103); cua = loser.get(103)
        realfin = {'camp': camp, 'sub': sub, '3er': ter, '4to': cua}
        for n in parts:
            for k, pts in PFINAL.items():
                if realfin[k] and pe[n].get(k) and norm(pe[n][k]) == norm(realfin[k]):
                    gan[n] += pts
        # extras pendientes que dependen del 3er puesto y la final
        eadd = extras_sim(scores, winner, loser, rng)
        for n in parts:
            gan[n] += eadd[n]

        # ranking + premios (desempate por rifa)
        arr = sorted(parts, key=lambda n: -(gan[n] + rng.random() * 1e-6))
        for pos in range(3):
            money[arr[pos]] += premio_val[pos]
        wins[arr[0]] += 1
        rank_hist[yo].append(arr.index(yo) + 1)

    print(f"=== ENDGAME LEMAITRE — {N} simulaciones (extras pendientes INCLUIDOS) ===")
    print(f"Pozo ${pot:,.0f} · premios 1º ${premio_val[0]:,.0f} · 2º ${premio_val[1]:,.0f} · 3º ${premio_val[2]:,.0f}")
    print(f"Estado base: Pocho {base_tot[yo]} (a {max(base_tot.values())-base_tot[yo]} del líder)")
    con_det = [(names[n], det[n]) for n in parts if det[n]]
    if con_det:
        print("Extras concluibles sumados (admin aún no carga):",
              " · ".join(f"{nm[:16]} +{d}" for nm, d in sorted(con_det, key=lambda x: -x[1])))
    print()
    rk = np.array(rank_hist[yo])
    print(f"POCHO (nosotros):")
    print(f"  P(quedar 1º / ganar) = {wins[yo]/N*100:.1f}%")
    print(f"  P(top-3 = plata)     = {(rk<=3).mean()*100:.1f}%")
    print(f"  P(2º) = {(rk==2).mean()*100:.1f}%  ·  P(3º) = {(rk==3).mean()*100:.1f}%")
    print(f"  Puesto medio = {rk.mean():.1f}")
    print(f"  💰 Premio esperado = ${money[yo]/N:,.0f}")
    print(f"\nRivales (premio esperado):")
    for n in sorted(parts, key=lambda n: -money[n])[:6]:
        print(f"   {names[n][:20]:20} base {base_tot[n]:>5}  ·  E[premio] ${money[n]/N:,.0f}  ·  P(1º) {wins[n]/N*100:.0f}%")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20000)
