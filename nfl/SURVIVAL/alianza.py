"""
Survival con N=14 y alianza de 2: ¿cuánto vale coordinarse con un amigo?

La observación clave: dos jugadores que usan la MISMA estrategia sin
coordinar toman el MISMO pick todas las semanas → rutas 100% correlacionadas
(mueren juntos; la "alianza" no diversifica nada). Coordinados pueden
forzarse a rutas distintas: cada semana el aliado B toma su mejor opción
EXCLUYENDO el pick de A esa semana. Eso cuesta un poco de p por semana y
compra que no los mate el mismo upset.

Configs medidas (walk-forward 2011-2025, pool de 14 = $4.2M de pozo):
  solo          — yo marrano, 13 rivales field. (Referencia por cabeza.)
  descoordinada — A y B marrano idénticos, 12 rivales. (El costo de NO
                  hablarse: banca compartida, misma ruta.)
  coordinada    — A marrano; B marrano excluyendo el pick de A cada semana,
                  12 rivales. (Banca compartida, rutas distintas.)

Reporte: E[neto] POR CABEZA en aportes y COP, y P(la banca cobra algo).

Uso:  python nfl/SURVIVAL/alianza.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos  # noqa: E402
from nfl.SURVIVAL import estrategias as est, simulador as sim  # noqa: E402
from nfl.SURVIVAL.backtest_survival import (  # noqa: E402
    TEMPORADAS, preparar_temporada)

APORTE_COP = 300_000
THETAS = [10, 25, 50]
SIMS = 400


def trayectoria_pareja(semanas_ops, semanas_juegos, fuerza_w):
    """A marrano; B marrano excluyendo el pick de A esa semana.

    Devuelve (elim_A, elim_B) con las reglas oficiales (2 vidas c/u).
    """
    usados_a, usados_b = set(), set()
    vidas_a, vidas_b = 2, 2
    elim_a = elim_b = None
    for w in sorted(semanas_ops):
        ops = semanas_ops[w]
        fuerza = fuerza_w.get(w)
        pick_a = None
        if vidas_a > 0:
            pick_a = est.marrano(ops, usados_a, fuerza=fuerza)
            if pick_a is None:
                vidas_a -= 1
            else:
                usados_a.add(pick_a)
                if not sim.resultado_pick(pick_a, semanas_juegos[w]):
                    vidas_a -= 1
            if vidas_a == 0 and elim_a is None:
                elim_a = w
        if vidas_b > 0:
            # B evita el pick de A SOLO esta semana (puede usarlo después)
            ops_b = [o for o in ops if o[0] != pick_a] if pick_a else ops
            pick_b = est.marrano(ops_b, usados_b, fuerza=fuerza)
            if pick_b is None:
                vidas_b -= 1
            else:
                usados_b.add(pick_b)
                if not sim.resultado_pick(pick_b, semanas_juegos[w]):
                    vidas_b -= 1
            if vidas_b == 0 and elim_b is None:
                elim_b = w
        if vidas_a == 0 and vidas_b == 0:
            break
    return elim_a, elim_b


def cobro_banca(elims_nuestras, elims_field):
    """Neto TOTAL de la banca (en aportes) con las reglas de cierre."""
    todos = np.concatenate([elims_field, elims_nuestras])
    pozo = len(todos)
    max_e = todos.max()
    ganan = np.isinf(todos) if np.isinf(max_e) else (todos == max_e)
    n_nuestros = len(elims_nuestras)
    nuestras_ganan = ganan[-n_nuestros:].sum()
    return pozo * nuestras_ganan / ganan.sum() - n_nuestros


def main():
    partidos = datos.cargar_partidos()
    rng = np.random.default_rng(7)

    solos, parejas, prep = {}, {}, {}
    for t in TEMPORADAS:
        prep[t] = preparar_temporada(partidos, t)
        sj, so, elo_w, fz_w = prep[t]
        elim, _ = sim.trayectoria_estrategia("marrano", so, sj, sj,
                                             elo_w, fz_w)
        solos[t] = np.inf if elim is None else elim
        ea, eb = trayectoria_pareja(so, sj, fz_w)
        parejas[t] = (np.inf if ea is None else ea,
                      np.inf if eb is None else eb)

    print("Rutas de la pareja coordinada (elim A / elim B; inf=vivo):")
    distintas = sum(1 for t in TEMPORADAS
                    if parejas[t][0] != parejas[t][1])
    print("  " + "  ".join(f"{t}:{parejas[t][0]:.0f}/{parejas[t][1]:.0f}"
                           for t in TEMPORADAS))
    print(f"  temporadas donde A y B caen en semana DISTINTA: "
          f"{distintas}/{len(TEMPORADAS)}\n")

    print("=" * 72)
    print(f"POOL DE 14 (pozo $4.2M) — E[neto] POR CABEZA, {SIMS} sims")
    print("=" * 72)
    for theta in THETAS:
        field = {}
        for t in TEMPORADAS:
            sj, so = prep[t][0], prep[t][1]
            trays = [sim.trayectoria_field(so, sj, theta, rng)
                     for _ in range(SIMS)]
            field[t] = np.array([np.inf if e is None else e for e in trays])

        res = {}
        for nombre, n_field, elims_fn in [
                ("solo", 13, lambda t: np.array([solos[t]])),
                ("descoordinada", 12,
                 lambda t: np.array([solos[t], solos[t]])),
                ("coordinada", 12, lambda t: np.array(parejas[t]))]:
            netos, cobra = [], []
            for t in TEMPORADAS:
                nuestras = elims_fn(t)
                for _ in range(SIMS // 4):
                    muestra = rng.choice(field[t], size=n_field,
                                         replace=True)
                    g = cobro_banca(nuestras, muestra)
                    netos.append(g / len(nuestras))     # por cabeza
                    cobra.append(g > -len(nuestras))
            res[nombre] = (np.mean(netos), np.mean(cobra))

        etiqueta = {10: "casual", 25: "normal", 50: "afilado"}[theta]
        print(f"\n--- field theta={theta} ({etiqueta}) ---")
        for nombre, (neto, pc) in res.items():
            print(f"  {nombre:<14} {neto:+6.2f} aportes/cabeza "
                  f"(${neto * APORTE_COP / 1e6:+.2f}M) "
                  f" P(banca cobra)={100 * pc:.1f}%")


if __name__ == "__main__":
    main()
