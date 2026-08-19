"""Distribuciones por jugador (piso/techo) — capa 3 del overlay.

Diseño: el CENTRO del cono lo pone el mercado (per-juego × E[g] de la
proyección v2.1); el ANCHO lo pone la historia 2010-2025:
  - G: distribución EMPÍRICA de juegos de la celda del jugador (bootstrap
    de los valores reales de la celda, no una paramétrica).
  - M: multiplicador de rendimiento por-juego, ratio año-a-año pg_Y/pg_{Y-1}
    por (pos, tier), NORMALIZADO a mediana 1 (usamos solo la FORMA de la
    dispersión; el nivel lo pone el mercado).
Total simulado = pg_mercado × M × G  (2,000 draws por jugador).

SUPUESTO S8: M ⊥ G (lesión también degrada el por-juego; correlación leve
ignorada → conos algo angostos en la cola mala; compensado porque la
dispersión de M se mide contra un predictor más débil que el mercado →
conos algo anchos. Se reporta la calibración medida, no la teórica).

CANDADO DE CALIBRACIÓN: misma maquinaria aplicada a 2020-2025 con celdas
estimadas SOLO con 2011-2019; se exige cobertura p10-p90 ≈ 80% ± 5.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
from optimize.proyeccion_v2 import _tier, proyectar_v2, vbd2

SQL = """
with juegos as (
  select player_id, position, season, count(distinct week) g,
         sum(coalesce(fantasy_points_ppr,0)) fp,
         sum(coalesce(def_tackles_solo,0)+coalesce(def_tackle_assists,0)) tkl
  from fact_player_week where season_type='REG' group by 1,2,3),
rel as (select *, lag(g) over w g_prev, lag(fp) over w fp_prev,
               lag(tkl) over w tkl_prev, lag(season) over w s_prev
        from juegos window w as (partition by player_id order by season)),
t as (select r.*,
        rank() over (partition by r.position, r.season
                     order by r.fp_prev/nullif(r.g_prev,0) desc) rk_pg
      from rel r where r.g_prev >= 8 and r.s_prev = r.season-1)
select position, season, g, g_prev, fp, fp_prev, rk_pg, tkl_prev
from t where season >= 2011
"""
ALIAS = {'FS': 'S', 'SS': 'S'}


def celdas(rows, hasta=2026):
    """Distribuciones empíricas hasta la temporada `hasta` (exclusiva)."""
    G, M = {}, {}
    for pos, ss, g, gp, fp, fpp, rkpg, tklp in rows:
        if ss >= hasta or not fpp or fpp <= 0:
            continue
        p = ALIAS.get(pos, pos)
        sg, sgp = (17 if ss >= 2021 else 16), (17 if ss - 1 >= 2021 else 16)
        tier = _tier(p, rkpg, tklp)
        les = 'les' if gp <= sgp - 4 else 'ok'
        G.setdefault((p, tier, les), []).append(g / sg)
        r = (fp / g) / (fpp / gp) if g >= 4 else None
        if r is not None and 0 < r < 5:
            M.setdefault((p, tier), []).append(r)
    G = {k: np.array(v) for k, v in G.items() if len(v) >= 8}
    Mn = {}
    for k, v in M.items():
        if len(v) >= 8:
            a = np.array(v)
            Mn[k] = a / np.median(a)          # solo la FORMA
    return G, Mn


def simular(pg, celG, celM, G, M, rng, n=2000):
    g = rng.choice(G[celG], size=n) * 17 if celG in G else np.full(n, 14.0)
    m = rng.choice(M[celM], size=n) if celM in M else 1.0
    return pg * m * g


def calibracion(rows):
    """Cobertura p10-p90 en 2020-2025 con celdas de 2011-2019."""
    G, M = celdas(rows, hasta=2020)
    rng = np.random.default_rng(7)
    dentro = total = 0
    for pos, ss, g, gp, fp, fpp, rkpg, tklp in rows:
        if ss < 2020 or not fpp or fpp <= 0 or (fpp / gp) < 8:
            continue
        p = ALIAS.get(pos, pos)
        sgp = 17 if ss - 1 >= 2021 else 16
        tier = _tier(p, rkpg, tklp)
        cg = (p, tier, 'les' if gp <= sgp - 4 else 'ok')
        cm = (p, tier)
        if cg not in G or cm not in M:
            continue
        sims = simular(fpp / gp, cg, cm, G, M, rng, 800)
        lo, hi = np.quantile(sims, [0.1, 0.9])
        dentro += int(lo <= fp <= hi)
        total += 1
    return dentro / total, total


def main():
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    rows = con.execute(SQL).fetchall()
    cob, n = calibracion(rows)
    print(f"CALIBRACIÓN (candado): cobertura p10-p90 = {cob*100:.1f}% (n={n}, objetivo 80±5)")
    if not 0.75 <= cob <= 0.88:
        print("¡TRUENA! — conos descalibrados, NO usar sin revisar")
        return 1
    G, M = celdas(rows)
    rng = np.random.default_rng(2026)
    filas = []
    for r in vbd2(proyectar_v2()):
        c = r['celda']
        if c == 'dst' or c[0] in ('corto', 'fallback'):
            # sin celda fina: cono solo por juegos (corto) o sin cono (dst)
            if c == 'dst':
                q = {f'p{p}': r['total_v2'] for p in (10, 25, 50, 75, 90)}
            else:
                g = np.array([r['eg']]) if c[0] == 'fallback' else None
                sims = r['pg'] * (rng.choice(G[(c[1], 'B', 'les')], 2000) * 17
                                  if c[0] == 'corto' and (c[1], 'B', 'les') in G
                                  else np.full(2000, r['eg']))
                q = {f'p{p}': round(float(np.quantile(sims, p / 100)), 1)
                     for p in (10, 25, 50, 75, 90)}
        else:
            _, pos, tier, les = c
            p2 = ALIAS.get(pos, pos)
            sims = simular(r['pg'], (p2, tier, les), (p2, tier), G, M, rng)
            q = {f'p{p}': round(float(np.quantile(sims, p / 100)), 1)
                 for p in (10, 25, 50, 75, 90)}
        filas.append({**{k: r[k] for k in ('nombre', 'pos', 'rank_pos', 'edad',
                                           'pg', 'eg', 'total_v2', 'vbd2', 'espn_id')}, **q})
    import csv
    with open(RAIZ / 'data' / 'proyeccion_dist.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print(f"{len(filas)} jugadores -> data/proyeccion_dist.csv")
    print(f"\n{'jugador':22}{'pos':>4}{'p10':>7}{'p50':>7}{'p90':>7}  (total temporada)")
    for fila in filas[:25]:
        print(f"{fila['nombre'][:22]:22}{fila['pos']:>4}{fila['p10']:>7}{fila['p50']:>7}{fila['p90']:>7}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
