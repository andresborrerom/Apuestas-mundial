"""Plan de draft desde el pick 5 — Monte Carlo de la sala + comparación
PAREADA de estrategias (mismas semillas para todas).

Estrategias comparadas:
  greedy   : mejor VBD2 disponible que quepa en el roster
  lookahead: maximiza VBD2(ahora) − E[VBD2 en mi próximo turno] por posición
             (usa supervivencia estimada por Monte Carlo)
  qbqb     : fuerza QB en las 2 primeras (tesis superflex)
  rbrb     : fuerza RB en las 2 primeras (anti-tesis)
  qbrb/rbqb: mixtas

Salida: E[valor del titular] por estrategia + qué toma cada una por ronda.
"""
import argparse, csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.sala import (EQUIPOS, RONDAS, MI_PICK, ORDEN, MAX_UTIL, MAX_UTIL_MIO, OBLIG, OBLIG_MIO,
                           OFE, OFE_MIN, cargar, score_sala, orden_snake,
                           valor_roster)

RAIZ = Path(__file__).resolve().parent.parent
POOL = 420                      # jugadores que realmente entran en juego
UMBRAL_BYE = 5.0                # pts de VBD que vale sacrificar por no apilar byes


def preparar(alpha=0.55):
    jug = cargar()
    for j in jug:
        j['s'] = score_sala(j, alpha)
    jug.sort(key=lambda j: j['s'])
    # garantiza cupo suficiente de cada posición obligatoria en el pool
    pool = jug[:POOL]
    en = {j['nombre'] for j in pool}
    for pos, k in (('K', 20), ('DST', 20), ('DT', 40), ('DE', 40), ('LB', 40),
                   ('CB', 40), ('S', 40), ('TE', 30), ('QB', 45)):
        extra = [j for j in jug if j['pos'] == pos and j['nombre'] not in en][:k]
        pool += extra
        en |= {j['nombre'] for j in extra}
    pool.sort(key=lambda j: j['s'])
    return pool


IDP = ('DT', 'DE', 'LB', 'CB', 'S')
# Pesos por asiento medidos en las temporadas con slot OP (managers.py).
# Se aplican POR DEFECTO en todo el simulador: cada rival juega como él.
from optimize.managers import pesos as _pesos
W_QB, W_IDP = _pesos()


class Draft:
    """`qb_bonus` (negativo = la sala adelanta QBs) e `idp_pen` (positivo =
    la sala los ignora) son los DOS supuestos vivos del modelo de sala.
    Se calibran contra el comportamiento medido en la historia 2023-2025."""

    def __init__(self, pool, rng, sigma=12.0, qb_bonus=0.0, idp_pen=0.0,
                 w_qb=None, w_idp=None):
        self.p = pool
        self.n = len(pool)
        base = np.array([j['s'] for j in pool])
        es_qb = np.array([j['pos'] == 'QB' for j in pool])
        es_idp = np.array([j['pos'] in IDP for j in pool])
        # Score POR ASIENTO: cada rival tiene su avidez medida (managers.py).
        # Sin pesos -> todos iguales (comportamiento anterior).
        wq = w_qb if w_qb is not None else W_QB
        wi = w_idp if w_idp is not None else W_IDP
        self.s_eq = [base - qb_bonus * wq[t] * es_qb + idp_pen * wi[t] * es_idp
                     for t in range(EQUIPOS)]
        self.s = self.s_eq[0]
        self.pos = [j['pos'] for j in pool]
        self.vbd = np.array([j['vbd'] for j in pool])
        self.alive = np.ones(self.n, bool)
        self.rng = rng
        self.sigma = sigma
        self.cnt = [defaultdict(int) for _ in range(EQUIPOS)]
        self.roster = [[] for _ in range(EQUIPOS)]

    def faltantes(self, t):
        """(gaps por posición, ofensivos extra que aún exige el roster)."""
        cnt = self.cnt[t]
        # 🔒 guardarraíl QB>=2: mis obligatorios incluyen el segundo QB
        oblig = OBLIG_MIO if t == MI_PICK - 1 else OBLIG
        gaps = {p: max(0, k - cnt[p]) for p, k in oblig.items()}
        ofe = sum(cnt[p] for p in OFE) + sum(gaps[p] for p in OFE)
        return gaps, max(0, OFE_MIN - ofe)

    def candidatos(self, t, ronda, forzado, limite=110):
        cnt = self.cnt[t]
        gaps, extra_ofe = self.faltantes(t)
        # 🔒 mis topes son más estrictos que los de la sala: un IDP por posición
        tope = MAX_UTIL_MIO if t == MI_PICK - 1 else MAX_UTIL
        out = []
        for i in range(self.n):
            if not self.alive[i]:
                continue
            p = self.pos[i]
            if cnt[p] >= tope.get(p, 3):
                continue
            if forzado and not (gaps.get(p, 0) > 0 or (extra_ofe > 0 and p in OFE)):
                continue
            if p in ('K', 'DST') and ronda < 11 and not forzado:
                continue
            out.append(i)
            if len(out) >= limite:
                break
        return out

    def forzado(self, t):
        gaps, extra_ofe = self.faltantes(t)
        return sum(gaps.values()) + extra_ofe >= RONDAS - len(self.roster[t])

    def pick_rival(self, t, ronda):
        cand = self.candidatos(t, ronda, self.forzado(t))
        if not cand:
            cand = [i for i in range(self.n) if self.alive[i]][:40]
        c = np.array(cand)
        sc = self.s_eq[t][c] + self.rng.gumbel(0, self.sigma, size=len(c))
        return int(c[np.argmin(sc)])

    def tomar(self, t, i):
        self.alive[i] = False
        self.cnt[t][self.pos[i]] += 1
        self.roster[t].append(self.p[i])


def diagnostico(pool, rng_seed, sigma, qb_bonus, idp_pen, n=25):
    """QBs en R1-R3 y ronda del primer IDP — las dos métricas calibrables."""
    qbs, primer_idp = [], []
    for s in range(n):
        rng = np.random.default_rng(rng_seed + s)
        d = Draft(pool, rng, sigma, qb_bonus, idp_pen)
        q, pi = 0, None
        for gp, t in enumerate(orden_snake(), 1):
            ronda = (gp - 1) // EQUIPOS + 1
            i = d.pick_rival(t, ronda)
            if i is None:
                continue
            if ronda <= 3 and d.pos[i] == 'QB':
                q += 1
            if pi is None and d.pos[i] in IDP:
                pi = ronda
            d.tomar(t, i)
        qbs.append(q); primer_idp.append(pi or 99)
    return float(np.mean(qbs)), float(np.median(primer_idp))


def calibrar(pool, obj_qb, obj_idp, sigma=12.0):
    """Busca (qb_bonus, idp_pen) que reproducen el comportamiento objetivo."""
    qb_b = 0.0
    for _ in range(14):
        q, _i = diagnostico(pool, 500, sigma, qb_b, 0.0, n=12)
        if abs(q - obj_qb) <= 1.0:
            break
        qb_b += (obj_qb - q) * 2.5
    pen = 0.0
    for _ in range(14):
        _q, ri = diagnostico(pool, 700, sigma, qb_b, pen, n=12)
        if abs(ri - obj_idp) <= 0.7:
            break
        pen += (obj_idp - ri) * 12
        pen = max(pen, 0.0)
    return qb_b, pen


def survival(pool, mis_picks, sims=120, seed=11, sigma=12.0, qb_bonus=0.0, idp_pen=0.0):
    """P(jugador disponible) en cada uno de mis turnos, con la sala jugando
    y yo tomando greedy (aproximación: mi pick afecta poco al resto)."""
    n = len(pool)
    cont = np.zeros((len(mis_picks), n))
    picks = orden_snake()
    yo = MI_PICK - 1
    for s in range(sims):
        rng = np.random.default_rng(seed + s)
        d = Draft(pool, rng, sigma, qb_bonus, idp_pen)
        k = 0
        for gp, t in enumerate(picks, 1):
            ronda = (gp - 1) // EQUIPOS + 1
            if t == yo:
                cont[k] += d.alive
                k += 1
                cand = d.candidatos(yo, ronda, d.forzado(yo), limite=250)
                i = int(max(cand, key=lambda i: d.vbd[i])) if cand else None
            else:
                i = d.pick_rival(t, ronda)
            if i is not None:
                d.tomar(t, i)
    return cont / sims


def e_mejor(vbd, surv):
    """E[max VBD entre los que sobrevivan], orden descendente de vbd."""
    o = np.argsort(-vbd)
    q = 1.0
    e = 0.0
    for i in o:
        s = surv[i]
        if s <= 0:
            continue
        e += vbd[i] * s * q
        q *= (1 - s)
        if q < 1e-4:
            break
    return e


def politica_lookahead(d, yo, ronda, k, mis_picks, SURV, forzar=None):
    cand = d.candidatos(yo, ronda, d.forzado(yo), limite=250)
    if not cand:
        return None
    if callable(forzar):
        forzar = forzar(d, cand)
    if forzar:
        c2 = [i for i in cand if d.pos[i] == forzar]
        if c2:
            return max(c2, key=lambda i: d.vbd[i])
    if k + 1 >= len(mis_picks):
        return max(cand, key=lambda i: d.vbd[i])
    porpos = defaultdict(list)
    for i in cand:
        porpos[d.pos[i]].append(i)
    opciones = []                 # (g, i) — finalistas entre posiciones
    for p, idxs in porpos.items():
        idxs.sort(key=lambda i: -d.vbd[i])
        ahora = d.vbd[idxs[0]]
        idx = np.array(idxs)
        # supervivencia al PRÓXIMO turno mío, condicionada a que sigan vivos
        sv = SURV[k + 1][idx] / np.maximum(SURV[k][idx], 1e-6)
        sv = np.clip(sv * d.alive[idx], 0, 1)
        luego = e_mejor(d.vbd[idx], sv)
        opciones.append((ahora - luego, idxs[0]))
        # alternativa de la MISMA posición casi empatada (mismo `luego`):
        # entra al desempate por byes con su ganancia ajustada
        if len(idxs) > 1 and ahora - d.vbd[idxs[1]] <= UMBRAL_BYE:
            opciones.append((ahora - luego - (ahora - d.vbd[idxs[1]]), idxs[1]))
    # 🔄 DESEMPATE POR BYES (pedido de Andrés, 1-sep): entre opciones a ≤5 pts
    # de la mejor ganancia marginal, evitar apilar un TERCER titular ofensivo
    # en la misma semana de bye (medido: un 2-stack lo cubre la banca; el
    # 3/4-stack tipo "4 titulares bye 11" es el que regala una semana).
    g_max = max(g for g, i in opciones)
    finalistas = [(g, i) for g, i in opciones if g >= g_max - UMBRAL_BYE]
    if len(finalistas) > 1:
        mis_byes = defaultdict(int)
        for j in d.roster[yo]:
            if j['pos'] in OFE and j.get('bye'):
                mis_byes[j['bye']] += 1

        def llave(gi):
            g, i = gi
            b = d.p[i].get('bye') if d.pos[i] in OFE else 0
            apila = max(0, mis_byes.get(b, 0) - 1) if b else 0
            return (apila, -g)
        return min(finalistas, key=llave)[1]
    return finalistas[0][1]


ESTRATEGIAS = {
    'greedy': None,
    'lookahead': None,
    'qb-qb': ['QB', 'QB'],
    'rb-rb': ['RB', 'RB'],
    'qb-rb': ['QB', 'RB'],
    'rb-qb': ['RB', 'QB'],
    'wr-qb': ['WR', 'QB'],
}


def correr(pool, SURV, mis_picks, sims=200, seed=900, sigma=12.0,
           qb_bonus=0.0, idp_pen=0.0, estrategias=None):
    yo = MI_PICK - 1
    picks = orden_snake()
    ESTR = estrategias or ESTRATEGIAS
    res = {e: [] for e in ESTR}
    detalle = {e: defaultdict(lambda: defaultdict(int)) for e in ESTR}
    picks_det = {e: defaultdict(lambda: defaultdict(int)) for e in ESTR}
    for s in range(sims):
        for est, forz in ESTR.items():
            rng = np.random.default_rng(seed + s)      # PAREADO: misma sala
            d = Draft(pool, rng, sigma, qb_bonus, idp_pen)
            k = 0
            for gp, t in enumerate(picks, 1):
                ronda = (gp - 1) // EQUIPOS + 1
                if t == yo:
                    f = forz[k] if forz and k < len(forz) else None
                    if est == 'greedy':
                        cand = d.candidatos(yo, ronda, d.forzado(yo), limite=250)
                        i = int(max(cand, key=lambda i: d.vbd[i])) if cand else None
                    else:
                        i = politica_lookahead(d, yo, ronda, k, mis_picks, SURV, f)
                    if i is not None:
                        detalle[est][ronda][d.pos[i]] += 1
                        picks_det[est][ronda][d.p[i]['nombre']] += 1
                    k += 1
                else:
                    i = d.pick_rival(t, ronda)
                if i is not None:
                    d.tomar(t, i)
            res[est].append(valor_roster({j['nombre']: j for j in d.roster[yo]}))
    return {e: np.array(v) for e, v in res.items()}, detalle, picks_det


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=150)
    ap.add_argument('--sigma', type=float, default=12.0)
    args = ap.parse_args()
    pool = preparar()
    mis_picks = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
    print(f'pool {len(pool)} · mis picks {mis_picks}')
    print('estimando supervivencia...', flush=True)
    SURV = survival(pool, mis_picks, sims=max(60, args.sims // 2), sigma=args.sigma)
    print('comparando estrategias (pareado)...', flush=True)
    res, det = correr(pool, SURV, mis_picks, sims=args.sims, sigma=args.sigma)
    base = res['greedy']
    print(f"\n{'estrategia':12}{'E[VBD titular]':>16}{'sd':>8}{'Δ vs greedy':>13}{'gana %':>9}")
    for e, v in sorted(res.items(), key=lambda kv: -kv[1].mean()):
        print(f"{e:12}{v.mean():>16.0f}{v.std():>8.0f}{v.mean()-base.mean():>+13.0f}"
              f"{(v > base).mean()*100:>8.0f}%")
    print('\nQué toma la mejor política por ronda (frecuencia %):')
    mejor = max(res, key=lambda e: res[e].mean())
    for r in range(1, RONDAS + 1):
        d = det[mejor][r]
        tot = sum(d.values()) or 1
        top = sorted(d.items(), key=lambda kv: -kv[1])[:3]
        print(f"  R{r:>2}: " + '  '.join(f"{p} {c/tot*100:.0f}%" for p, c in top))
