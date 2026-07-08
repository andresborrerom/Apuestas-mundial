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
PCLAS = {"CUAR": (30, 20, 15, 10), "SEMI": (25, 18, 12, 8)}   # SUPUESTO (app aún no codifica)
PFINAL = {"camp": 80, "sub": 60, "3er": 40, "4to": 30}         # SUPUESTO (Excel)
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
    for s in range(89, 97):
        r = rs.get(str(s))
        if r and r.get('g1') is not None:
            fixed[s] = (r['e1'], r['e2'], r['g1'], r['g2'])
    PEN_WINNERS = {96: 'Suiza'}   # penales conocidos (Suiza pasó)
    if 92 not in fixed:
        fixed[92] = ('México', 'Inglaterra', 2, 3)   # jugado, admin no lo cargó
    en_base = set(int(k) for k in rs if rs[k].get('g1') is not None)  # marcador ya en base_tot

    def strength(team):
        return max(0.35, lam.get(cn(team), 1.0))

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

        # clasificación de tramos futuros (cuartos 97-100, semis 101-102)
        for slot, tramo in [(97, 'CUAR'), (98, 'CUAR'), (99, 'CUAR'), (100, 'CUAR'),
                            (101, 'SEMI'), (102, 'SEMI')]:
            if slot in scores:
                t1, t2, _, _ = scores[slot]
                for n in parts:
                    gan[n] += clasif_pts(pe[n].get(str(slot)), t1, t2, PCLAS[tramo])
        # standings final: campeón=winner[104], sub=loser[104], 3º=winner[103], 4º=loser[103]
        camp = winner.get(104); sub = loser.get(104); ter = winner.get(103); cua = loser.get(103)
        realfin = {'camp': camp, 'sub': sub, '3er': ter, '4to': cua}
        for n in parts:
            for k, pts in PFINAL.items():
                if realfin[k] and pe[n].get(k) and norm(pe[n][k]) == norm(realfin[k]):
                    gan[n] += pts

        # ranking + premios (desempate por rifa)
        arr = sorted(parts, key=lambda n: -(gan[n] + rng.random() * 1e-6))
        for pos in range(3):
            money[arr[pos]] += premio_val[pos]
        wins[arr[0]] += 1
        rank_hist[yo].append(arr.index(yo) + 1)

    print(f"=== ENDGAME LEMAITRE — {N} simulaciones ===")
    print(f"Pozo ${pot:,.0f} · premios 1º ${premio_val[0]:,.0f} · 2º ${premio_val[1]:,.0f} · 3º ${premio_val[2]:,.0f}")
    print(f"Estado base: Pocho {base_tot[yo]} (2º, a {max(base_tot.values())-base_tot[yo]} del líder)\n")
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
