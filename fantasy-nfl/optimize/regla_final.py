"""Regla FINAL del draft: ¿fija (WR-WR) o condicional al estado de la sala?

La validación mostró que WR-WR gana 85-92% pareado en B/C/D (la sala se
traga los QBs) pero PIERDE en A (si los QB élite siguen vivos en mi pick 28).
Una regla condicional debería capturar ambos mundos:

  R1 (pick 5):  el mejor WR disponible.
  R2 (pick 28): QB si sobrevive uno de VBD >= UMBRAL; si no, WR.

Se prueban varios umbrales contra las alternativas fijas, pareado, en los
4 escenarios de sala.
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.plan_draft import preparar, calibrar, correr, survival
from optimize.sala import orden_snake, MI_PICK

ESC = {'A sala-1QB': (16, 10), 'B base': (24, 10),
       'C voraz': (30, 10), 'D voraz+IDP': (30, 5)}


def cond(umbral):
    """Devuelve 'QB' si hay un QB disponible con VBD >= umbral, si no 'WR'."""
    def f(d, cand):
        mejor = max((d.vbd[i] for i in cand if d.pos[i] == 'QB'), default=-1e9)
        return 'QB' if mejor >= umbral else 'WR'
    return f


ESTR = {'wr-wr': ['WR', 'WR'],
        'wr-cond110': ['WR', cond(110)],
        'wr-cond125': ['WR', cond(125)],
        'wr-cond140': ['WR', cond(140)],
        'wr-qb': ['WR', 'QB']}

if __name__ == '__main__':
    pool = preparar()
    mis = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
    agr = defaultdict(list)
    for nom, (oq, oi) in ESC.items():
        qb_b, pen = calibrar(pool, oq, oi)
        S = survival(pool, mis, sims=30, qb_bonus=qb_b, idp_pen=pen)
        res, det, pdet = correr(pool, S, mis, sims=100, qb_bonus=qb_b,
                                idp_pen=pen, estrategias=ESTR)
        ref = res['wr-wr']
        print(f"\n===== {nom} =====")
        print(f"{'estrategia':13}{'E[VBD]':>9}{'Δ wr-wr':>10}{'gana pareado':>14}")
        for e, v in sorted(res.items(), key=lambda kv: -kv[1].mean()):
            print(f"{e:13}{v.mean():>9.0f}{v.mean()-ref.mean():>+10.0f}"
                  f"{(v > ref).mean()*100:>13.0f}%", flush=True)
            agr[e].append(v.mean())
    print('\n=== ROBUSTEZ (4 escenarios) ===')
    for e, v in sorted(agr.items(), key=lambda kv: -np.mean(kv[1])):
        print(f"  {e:13} media {np.mean(v):>6.0f} · peor {min(v):>6.0f}")
