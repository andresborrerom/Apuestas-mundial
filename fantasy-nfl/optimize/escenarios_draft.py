"""Compara estrategias de draft (pick 5) bajo los 4 escenarios de sala.

Los DOS supuestos vivos del modelo de sala se calibran contra métricas
medidas en la historia de la liga:
  A) sala tipo 1QB (16 QBs en R1-R3)  — si el OP no cambia sus hábitos
  B) base (24)                        — adaptación parcial al superflex
  C) voraz (30)                       — 2 QBs por equipo, corrida total
  D) voraz + IDP-aware (1er IDP R5)   — la sala VE la proyección de tackles

La recomendación solo vale si SOBREVIVE los 4. Comparación PAREADA:
misma semilla de sala para todas las estrategias.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.plan_draft import (preparar, calibrar, correr, survival,
                                 ESTRATEGIAS, diagnostico)
from optimize.sala import orden_snake, MI_PICK, EQUIPOS

RAIZ = Path(__file__).resolve().parent.parent
ESC = {'A conservador (16)': (16, 10), 'B MEDIDO (20)': (20, 10),
       'C alto (26)': (26, 10), 'D medido + IDP-aware': (20, 5)}
SIMS_SURV, SIMS_EST = 30, 40

if __name__ == '__main__':
    pool = preparar()
    mis = [gp for gp, t in enumerate(orden_snake(), 1) if t == MI_PICK - 1]
    salida = {}
    for nom, (oq, oi) in ESC.items():
        qb_b, pen = calibrar(pool, oq, oi)
        q, ri = diagnostico(pool, 1234, 12.0, qb_b, pen, n=15)
        print(f"\n===== {nom} (qb_bonus={qb_b:.0f}, idp_pen={pen:.0f}) "
              f"-> QBs R1-3 {q:.1f}, 1er IDP R{ri:.0f} =====", flush=True)
        SURV = survival(pool, mis, sims=SIMS_SURV, sigma=12.0,
                        qb_bonus=qb_b, idp_pen=pen)
        res, det, pdet = correr(pool, SURV, mis, sims=SIMS_EST, sigma=12.0,
                                qb_bonus=qb_b, idp_pen=pen)
        base = res['greedy']
        print(f"{'estrategia':12}{'E[VBD]':>9}{'sd':>7}{'Δ greedy':>10}")
        for e, v in sorted(res.items(), key=lambda kv: -kv[1].mean()):
            print(f"{e:12}{v.mean():>9.0f}{v.std():>7.0f}{v.mean()-base.mean():>+10.0f}",
                  flush=True)
        mejor = max(res, key=lambda e: res[e].mean())
        salida[nom] = {
            'qb_bonus': qb_b, 'idp_pen': pen,
            'medias': {e: float(v.mean()) for e, v in res.items()},
            'mejor': mejor,
            'plan': {r: sorted(det[mejor][r].items(), key=lambda kv: -kv[1])[:3]
                     for r in sorted(det[mejor])},
            'nombres': {r: sorted(pdet[mejor][r].items(), key=lambda kv: -kv[1])[:5]
                        for r in sorted(pdet[mejor])},
        }
        json.dump(salida, open(RAIZ / 'data' / 'escenarios_draft.json', 'w'),
                  ensure_ascii=False, indent=1)
    print('\n=== RESUMEN: media por estrategia y escenario ===')
    ests = list(ESTRATEGIAS)
    print(f"{'estrategia':12}" + ''.join(f"{n:>14}" for n in ESC))
    for e in ests:
        print(f"{e:12}" + ''.join(f"{salida[n]['medias'][e]:>14.0f}" for n in ESC))
