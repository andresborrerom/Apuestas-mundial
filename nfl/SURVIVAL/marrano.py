"""
El "marrano": cuantificar la intuición del usuario para Survival.

Intuición: no basta identificar favoritos — hay que identificar al MARRANO
(el equipo tan malo que cuando gana hace fiesta). Contra el marrano puedes
usar rivales MEDIANOS (no élite) y aún así llevar P(gana) alta, guardando
los equipos élite para semanas flacas. Este script la vuelve medible:

  1. ¿Quiénes son los marranos de cada temporada? (implied win prob promedio
     del mercado, calculada SOLO con las semanas ya jugadas — sin futuro).
  2. ¿Cuánta P(gana) te da un rival mediano contra un marrano vs la que te
     da un élite contra un rival normal?
  3. ¿Qué tan seguido el marrano "hace fiesta" (gana siendo p<=25%)?
     ¿Coincide con lo que dice el mercado? (calibración de la fiesta)

Uso:  python nfl/SURVIVAL/marrano.py
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from nfl import datos, probabilidades as prob  # noqa: E402

N_MARRANOS = 5   # "marranos" = los 5 peores de la liga a esa altura
N_ELITE = 5      # "élite" = los 5 mejores


def fuerza_hasta_semana(partidos_temporada, semana):
    """Fuerza de mercado de cada equipo con lo jugado ANTES de `semana`.

    Fuerza = promedio de su P(gana) implícita del moneyline en sus partidos
    de las semanas < semana. Sin datos (semana 1-2) devuelve None.
    """
    ps = defaultdict(list)
    for p in partidos_temporada:
        if p["week"] >= semana or p["ml_home"] is None:
            continue
        p_home = prob.p_local_moneyline(p["ml_home"], p["ml_away"])
        ps[p["home"]].append(p_home)
        ps[p["away"]].append(1 - p_home)
    if not ps:
        return None
    return {eq: float(np.mean(v)) for eq, v in ps.items()}


def clasificar(fuerza):
    """Devuelve (set marranos, set élite) según la fuerza de mercado."""
    orden = sorted(fuerza, key=fuerza.get)
    return set(orden[:N_MARRANOS]), set(orden[-N_ELITE:])


def main():
    partidos = datos.cargar_partidos(temporadas=set(range(2011, 2026)))

    por_temp = defaultdict(list)
    for p in partidos:
        por_temp[p["season"]].append(p)

    # picks posibles: (p_gana del que pega, tier del que pega, rival marrano?)
    vs_marrano_mediano = []   # mediano/cualquiera-no-élite vs marrano
    vs_normal_elite = []      # élite vs rival no-marrano
    fiestas = []              # (p_marrano, gano_marrano)
    top1_semana, top_marrano_semana = [], []

    for temp, ps in sorted(por_temp.items()):
        semanas = datos.por_semana(ps)
        for (s, w), juegos in semanas.items():
            if w < 4:        # antes de la semana 4 no hay señal estable
                continue
            fuerza = fuerza_hasta_semana(ps, w)
            marranos, elite = clasificar(fuerza)
            mejores = []          # mejor pick de la semana (para top-1)
            mejores_vs_marrano = []
            for j in juegos:
                if j["ml_home"] is None:
                    continue
                p_home = prob.p_local_moneyline(j["ml_home"], j["ml_away"])
                for eq, rival, p_eq, gano in [
                        (j["home"], j["away"], p_home, j["result"] > 0),
                        (j["away"], j["home"], 1 - p_home, j["result"] < 0)]:
                    mejores.append(p_eq)
                    if rival in marranos:
                        mejores_vs_marrano.append(p_eq)
                        if eq not in elite:
                            vs_marrano_mediano.append((p_eq, gano))
                        # la fiesta del marrano: pierde el que pega
                        fiestas.append((1 - p_eq, j["empate"] or not gano))
                    elif eq in elite:
                        vs_normal_elite.append((p_eq, gano))
            if mejores:
                top1_semana.append(max(mejores))
            if mejores_vs_marrano:
                top_marrano_semana.append(max(mejores_vs_marrano))

    print("=" * 72)
    print(f"EL MARRANO — 2011-2025, marranos = bottom-{N_MARRANOS} por fuerza "
          f"de mercado\n(fuerza calculada solo con semanas ya jugadas; "
          f"análisis desde semana 4)")
    print("=" * 72)

    a = np.array(vs_marrano_mediano)
    b = np.array(vs_normal_elite)
    print(f"\nPicks NO-élite contra marrano:  n={len(a)}, "
          f"P(gana) media={a[:, 0].mean():.3f}, "
          f"ganó de verdad={a[:, 1].mean():.3f}")
    print(f"Picks élite vs rival no-marrano: n={len(b)}, "
          f"P(gana) media={b[:, 0].mean():.3f}, "
          f"ganó de verdad={b[:, 1].mean():.3f}")

    a75 = a[a[:, 0] >= 0.72]
    print(f"\nPicks no-élite vs marrano con p>=72%: n={len(a75)}, "
          f"p media={a75[:, 0].mean():.3f}, ganó={a75[:, 1].mean():.3f}")

    print(f"\nMejor pick de la semana (todas): "
          f"p media={np.mean(top1_semana):.3f}")
    print(f"Mejor pick 'contra marrano':     "
          f"p media={np.mean(top_marrano_semana):.3f} "
          f"(disponible en {len(top_marrano_semana)}/{len(top1_semana)} "
          f"semanas)")

    f = np.array(fiestas)
    print(f"\nLA FIESTA DEL MARRANO (no perder = ganar o empatar):")
    for lo, hi in [(0.0, 0.15), (0.15, 0.25), (0.25, 0.35), (0.35, 0.5)]:
        m = f[(f[:, 0] >= lo) & (f[:, 0] < hi)]
        if len(m):
            print(f"  p_marrano {lo:.2f}-{hi:.2f}: mercado dice "
                  f"{m[:, 0].mean():.3f}, fiesta real {m[:, 1].mean():.3f} "
                  f"(n={len(m)})")
    print("\n=> Si 'fiesta real' ≈ 'mercado dice', el mercado YA precia bien "
          "al marrano:\n   la ventaja no es de probabilidad, es ESTRUCTURAL "
          "(ahorrar élites para otras semanas).")


if __name__ == "__main__":
    main()
