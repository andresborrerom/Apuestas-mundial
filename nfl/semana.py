"""
El comando de cada semana de la temporada 2026: picks recomendados.

Imprime, para la próxima semana con líneas publicadas:
  - PICK'EM: el favorito de cada partido (EV-máx para los pots) y los 1-2
    coin-flips candidatos a voltear (la jugada de la Batalla Semanal).
  - SURVIVAL: el pick de la heurística marrano (validada walk-forward
    2011-2025) + las 3 mejores alternativas con su P(gana).

Antes de correr, refrescar los datos (las líneas se mueven):
  curl -sSL -o nfl/datos/games.csv \
      https://github.com/nflverse/nfldata/raw/master/data/games.csv

Uso:
  python nfl/semana.py                # próxima semana pendiente
  python nfl/semana.py --week 3       # una semana específica de 2026
  python nfl/semana.py --usados KC,PHI  # equipos ya quemados en Survival

Los equipos quemados también se leen de `nfl/SURVIVAL/usados_2026.txt`
(uno por línea; ahí se anota el pick que de verdad se metió cada semana).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nfl import datos, probabilidades as prob  # noqa: E402
from nfl.SURVIVAL import estrategias as est  # noqa: E402
from nfl.SURVIVAL.marrano import fuerza_hasta_semana  # noqa: E402

TEMPORADA = 2026


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--usados", type=str, default="",
                    help="equipos ya usados en Survival, ej: KC,PHI")
    args = ap.parse_args()
    usados = {e.strip().upper() for e in args.usados.split(",") if e.strip()}
    ruta_usados = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "SURVIVAL", "usados_2026.txt")
    if os.path.exists(ruta_usados):
        with open(ruta_usados) as f:
            usados |= {ln.strip().upper() for ln in f
                       if ln.strip() and not ln.startswith("#")}

    jugados = datos.cargar_partidos()          # todo lo jugado, para Elo
    elo = prob.Elo()
    for p in sorted(jugados, key=lambda x: (x["season"], x["week"],
                                            x["gameday"])):
        elo.actualizar(p)

    temporada = datos.cargar_partidos(temporadas={TEMPORADA},
                                      solo_jugados=False)
    semanas = {w: js for (_s, w), js in datos.por_semana(temporada).items()}
    if args.week:
        w = args.week
    else:
        w = min(wk for wk, js in semanas.items()
                if any(j["result"] is None and j["ml_home"] for j in js))
    juegos = [j for j in semanas[w] if j["ml_home"] is not None]
    if not juegos:
        print(f"Semana {w}: sin líneas publicadas aún. Refresca games.csv.")
        return

    print(f"NFL {TEMPORADA} — SEMANA {w} ({len(juegos)} partidos con línea)")

    # ---------------- PICK'EM -------------------------------------------
    print("\n== PICK'EM (favorito en todo; ★ = los 3 coin-flips a voltear —"
          "\n   política m3 validada en nfl/PICKEM/temporada.py)")
    filas = []
    for j in juegos:
        ph = prob.p_local_moneyline(j["ml_home"], j["ml_away"])
        fav, p = (j["home"], ph) if ph >= 0.5 else (j["away"], 1 - ph)
        filas.append((p, fav, j))
    filas.sort()
    for i, (p, fav, j) in enumerate(filas):
        marca = " ★ (pick al rival)" if i < 3 else ""
        print(f"  {j['away']:>3} @ {j['home']:<3} -> {fav:<3} "
              f"({100 * p:.0f}%){marca}")

    # ---------------- SURVIVAL ------------------------------------------
    jugados_2026 = [p for p in jugados if p["season"] == TEMPORADA]
    fuerza = fuerza_hasta_semana(jugados_2026, w) if w >= 4 else None
    if not fuerza:
        equipos = {p[k] for p in temporada for k in ("home", "away")}
        fuerza = {eq: elo._get(eq) for eq in equipos}

    ops = est.opciones_semana(juegos)
    pick = est.marrano(ops, usados, fuerza=fuerza)
    orden_f = sorted(fuerza, key=fuerza.get)
    marranos = set(orden_f[:est.N_MARRANOS])
    elite = set(orden_f[-est.N_ELITE:])

    print(f"\n== SURVIVAL (heurística marrano; usados: "
          f"{','.join(sorted(usados)) or 'ninguno'})")
    print(f"  marranos actuales: {', '.join(sorted(marranos))}")
    print(f"  élite (guardar):   {', '.join(sorted(elite))}")
    print(f"  PICK: {pick}")
    print("  alternativas (p estricta, sin empate):")
    libres = sorted(((p, eq, riv) for eq, riv, p in ops
                     if eq not in usados), reverse=True)
    for p, eq, riv in libres[:5]:
        etiq = ("vs MARRANO" if riv in marranos else "") + \
               (" [élite: guardar]" if eq in elite else "")
        print(f"    {eq:<3} vs {riv:<3} {100 * p:5.1f}%  {etiq}")


if __name__ == "__main__":
    main()
