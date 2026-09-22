"""Validación final PAREADA de las estrategias punteras + plan detallado.

Verifica al verificador: más simulaciones, tasa de victoria pareada (no solo
medias) y el detalle de qué jugadores toma la política ganadora en cada
ronda bajo cada escenario de sala.
"""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.plan_draft import preparar, calibrar, correr, survival
from optimize.sala import orden_snake, MI_PICK

RAIZ = Path(__file__).resolve().parent.parent
ESC = {'A conservador (16)': (16, 10), 'B MEDIDO (20)': (20, 10),
       'C alto (26)': (26, 10), 'D medido + IDP-aware': (20, 5)}
FINALISTAS = {'lookahead': None, 'wr-qb': ['WR', 'QB'], 'rb-rb': ['RB', 'RB'],
              'qb-rb': ['QB', 'RB'], 'wr-wr': ['WR', 'WR']}
SIMS = 100

if __name__ == '__main__':
    pool = preparar()
    mis = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
    agr = defaultdict(list)
    salida = {}
    for nom, (oq, oi) in ESC.items():
        qb_b, pen = calibrar(pool, oq, oi)
        SURV = survival(pool, mis, sims=30, qb_bonus=qb_b, idp_pen=pen)
        res, det, pdet = correr(pool, SURV, mis, sims=SIMS, qb_bonus=qb_b,
                                idp_pen=pen, estrategias=FINALISTAS)
        ref = res['lookahead']
        print(f"\n===== {nom} =====", flush=True)
        print(f"{'estrategia':12}{'E[VBD]':>9}{'Δ vs look':>11}{'gana pareado':>14}")
        for e, v in sorted(res.items(), key=lambda kv: -kv[1].mean()):
            print(f"{e:12}{v.mean():>9.0f}{v.mean()-ref.mean():>+11.0f}"
                  f"{(v > ref).mean()*100:>13.0f}%", flush=True)
        for e, v in res.items():
            agr[e].append(v.mean())
        mejor = max(res, key=lambda e: res[e].mean())
        salida[nom] = {
            'qb_bonus': qb_b, 'idp_pen': pen, 'mejor': mejor,
            'medias': {e: float(v.mean()) for e, v in res.items()},
            'plan_pos': {r: sorted(det['lookahead'][r].items(), key=lambda kv: -kv[1])[:3]
                         for r in sorted(det['lookahead'])},
            'plan_nombres': {r: sorted(pdet['lookahead'][r].items(),
                                       key=lambda kv: -kv[1])[:6]
                             for r in sorted(pdet['lookahead'])},
        }
        json.dump(salida, open(RAIZ / 'data' / 'plan_draft.json', 'w'),
                  ensure_ascii=False, indent=1)
    print('\n=== ROBUSTEZ: media a través de los 4 escenarios ===')
    for e, v in sorted(agr.items(), key=lambda kv: -np.mean(kv[1])):
        print(f"  {e:12} media {np.mean(v):>6.0f} · peor escenario {min(v):>6.0f}")
