"""Cierre del plan: (1) sensibilidad de baselines — ¿WR-WR es artefacto del
split del flex? (2) disponibilidad real en mis picks 5 y 28 (3) qué toma la
política ganadora ronda por ronda, con nombres.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from optimize.proyeccion_v2 import proyectar_v2, vbd2
from optimize.vbd import BASE
from optimize.plan_draft import preparar, calibrar, correr, survival
from optimize.sala import orden_snake, MI_PICK
import optimize.vbd as V
import optimize.proyeccion_v2 as P2

RAIZ = Path(__file__).resolve().parent.parent

print('=== 1. SENSIBILIDAD DE BASELINES (split del flex RB/WR) ===', flush=True)
proys = proyectar_v2()
VAR = {'60/40 RB (usado): RB26/WR38': dict(BASE),
       '50/50: RB24/WR40': dict(BASE, RB=24, WR=40),
       '80/20 RB: RB29/WR35': dict(BASE, RB=29, WR=35),
       'flex 100% RB: RB32/WR32': dict(BASE, RB=32, WR=32)}
orig = dict(BASE)
for nom, b in VAR.items():
    V.BASE.clear(); V.BASE.update(b)
    P2.BASE = V.BASE
    rk = vbd2([dict(r) for r in proys])
    top = ', '.join(f"{r['nombre'].split()[-1]}({r['pos']})" for r in rk[:8])
    nwr = sum(1 for r in rk[:10] if r['pos'] == 'WR')
    nrb = sum(1 for r in rk[:10] if r['pos'] == 'RB')
    print(f"  {nom:28} top8: {top}   [top10: {nwr} WR / {nrb} RB]", flush=True)
V.BASE.clear(); V.BASE.update(orig)

print('\n=== 2. DISPONIBILIDAD EN MIS PICKS (escenario C voraz) ===', flush=True)
pool = preparar()
mis = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
qb_b, pen = calibrar(pool, 30, 10)
SURV = survival(pool, mis, sims=60, qb_bonus=qb_b, idp_pen=pen)
idx = {j['nombre']: i for i, j in enumerate(pool)}
print(f"{'jugador':22}{'pos':>4}{'VBD':>6}{'P(vivo p5)':>12}{'P(vivo p28)':>12}")
for j in sorted(pool, key=lambda j: -j['vbd'])[:26]:
    i = idx[j['nombre']]
    print(f"{j['nombre'][:22]:22}{j['pos']:>4}{j['vbd']:>6.0f}"
          f"{SURV[0][i]*100:>11.0f}%{SURV[1][i]*100:>11.0f}%", flush=True)

print('\n=== 3. PLAN RONDA A RONDA (política WR-WR) ===', flush=True)
ESC = {'B base': (24, 10), 'C voraz': (30, 10), 'D voraz+IDP': (30, 5)}
plan = {}
for nom, (oq, oi) in ESC.items():
    qb, pn = calibrar(pool, oq, oi)
    S = survival(pool, mis, sims=30, qb_bonus=qb, idp_pen=pn)
    res, det, pdet = correr(pool, S, mis, sims=60, qb_bonus=qb, idp_pen=pn,
                            estrategias={'wr-wr': ['WR', 'WR']})
    plan[nom] = {'valor': float(res['wr-wr'].mean()),
                 'pos': {r: sorted(det['wr-wr'][r].items(), key=lambda kv: -kv[1])
                         for r in sorted(det['wr-wr'])},
                 'nombres': {r: sorted(pdet['wr-wr'][r].items(), key=lambda kv: -kv[1])[:5]
                             for r in sorted(pdet['wr-wr'])}}
    print(f"\n-- {nom} (E[VBD]={res['wr-wr'].mean():.0f}) --", flush=True)
    for r in sorted(det['wr-wr']):
        tot = sum(det['wr-wr'][r].values()) or 1
        pos = '  '.join(f"{p} {c*100//tot}%" for p, c in
                        sorted(det['wr-wr'][r].items(), key=lambda kv: -kv[1])[:2])
        nm = ', '.join(n for n, _ in sorted(pdet['wr-wr'][r].items(),
                                            key=lambda kv: -kv[1])[:3])
        print(f"  R{r:>2} [{pos:20}] {nm[:64]}", flush=True)
    json.dump(plan, open(RAIZ / 'data' / 'plan_wrwr.json', 'w'),
              ensure_ascii=False, indent=1)
