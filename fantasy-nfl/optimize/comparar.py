"""¿Regla validada o motor? Cuando discrepan, se MIDE — no se opina.

Desde el estado REAL del draft, juega el resto muchas veces con cada
candidato en el pick actual (misma semilla de sala para todos = pareado) y
compara el VALOR FINAL del equipo titular. Es la misma disciplina que eligió
la regla, pero condicionada a este tablero concreto.
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.plan_draft import politica_lookahead, e_mejor
from optimize.sala import EQUIPOS, RONDAS, MI_PICK, valor_roster

RAIZ = Path(__file__).resolve().parent.parent


def survival_desde(est, pool, hechos, sims=40, seed=101):
    """P(disponible) en cada uno de mis turnos restantes, desde el estado real."""
    n = len(hechos)
    mios = [p for p in est.mis_picks if p > n]
    cont = np.zeros((len(mios), len(pool)))
    for s in range(sims):
        rng = np.random.default_rng(seed + s)
        d = est.cargar_estado(rng)
        k = 0
        for gp in range(n + 1, EQUIPOS * RONDAS + 1):
            t = est.secuencia[gp - 1]
            ronda = (gp - 1) // EQUIPOS + 1
            if t == MI_PICK - 1:
                cont[k] += d.alive
                k += 1
                cand = d.candidatos(t, ronda, d.forzado(t), limite=200)
                i = int(max(cand, key=lambda i: d.vbd[i])) if cand else None
            else:
                i = d.pick_rival(t, ronda)
            if i is not None:
                d.tomar(t, i)
    return cont / sims, mios


def jugar(est, pool, hechos, primero, SURV, mios, seed):
    """Juega el resto del draft tomando `primero` ahora y lookahead después."""
    rng = np.random.default_rng(seed)
    d = est.cargar_estado(rng)
    yo = MI_PICK - 1
    n = len(hechos)
    mio = []
    k = 0
    for gp in range(n + 1, EQUIPOS * RONDAS + 1):
        t = est.secuencia[gp - 1]
        ronda = (gp - 1) // EQUIPOS + 1
        if t == yo:
            if k == 0 and primero is not None:
                i = primero if d.alive[primero] else None
            else:
                i = politica_lookahead(d, yo, ronda, k, mios, SURV)
            if i is not None:
                mio.append(pool[i])
            k += 1
        else:
            i = d.pick_rival(t, ronda)
        if i is not None:
            d.tomar(t, i)
    # sumar lo que ya tenía antes de esta decisión
    previos = [pool[i] for i in est.mis]
    roster = {j['nombre']: j for j in previos + mio}
    return valor_roster(roster)


def comparar(est, pool, hechos, candidatos, sims=60, seed=500):
    SURV, mios = survival_desde(est, pool, hechos)
    res = {}
    for nombre, idx in candidatos.items():
        vals = [jugar(est, pool, hechos, idx, SURV, mios, seed + s) for s in range(sims)]
        res[nombre] = np.array(vals)
    base = list(res)[0]
    print(f"\n COMPARACIÓN PAREADA DESDE ESTE TABLERO ({sims} drafts completos c/u)")
    print(f" {'opción':26}{'valor final':>13}{'sd':>7}{'vs 1ª':>9}{'gana':>8}")
    ref = res[base]
    for nom, v in sorted(res.items(), key=lambda kv: -kv[1].mean()):
        print(f" {nom:26}{v.mean():>13.0f}{v.std():>7.0f}{v.mean()-ref.mean():>+9.0f}"
              f"{(v > ref).mean()*100:>7.0f}%")
    return res
