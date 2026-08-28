"""FASE A del backtest — ¿mi tablero ordena mejor que el mercado?

Es la tesis fundacional, nunca probada: "el edge es aritmético, re-puntuar
las estadísticas crudas bajo NUESTRAS reglas gana".

Para cada temporada Y de 2021 a 2025:
  MERCADO  = ECR superflex de FantasyPros, último snapshot de pretemporada
             (lo que los expertos decían ANTES de que empezara Y).
  MÍO      = proyección construida SOLO con datos hasta Y-1: puntos por juego
             bajo nuestras reglas × E[juegos] del modelo de celdas (entrenado
             también solo hasta Y-1). Sin mirar Y por ningún lado.
  HÍBRIDO  = el mío, con el ECR del mercado rellenando a los NOVATOS (que mi
             proyección no puede ver porque no tienen historia).
  VERDAD   = puntos REALES de Y bajo nuestras reglas (model/scoring_nflverse).

Unión por fantasypros_id (el `id` del ECR ES el fantasypros_id del crosswalk;
NUNCA por nombre: hay homónimos y ya nos costó una vez).

Métricas: correlación de rangos y — la que importa — cuánta producción REAL
captura cada tablero en sus primeros K puestos (los picks que de verdad
deciden un draft).
"""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import duckdb
from model.scoring import cargar_reglas, puntos
from model.scoring_nflverse import temporadas, POSID

RAIZ = Path(__file__).resolve().parent.parent
ECR_PARQUET = ('/tmp/claude-0/-home-user-Apuestas-mundial/'
               'd76ca134-7088-56fe-a905-16046e9d8c41/scratchpad/ecr.parquet')
PAGINA = '/nfl/rankings/ppr-superflex-cheatsheets.php'
OFE = ('QB', 'RB', 'WR', 'TE')


def mercado(con, año):
    """ECR superflex, último snapshot antes del 10-sep de `año` -> gsis_id."""
    q = con.execute(f"""
        with snap as (
          select max(scrape_date) d from read_parquet('{ECR_PARQUET}')
          where fp_page='{PAGINA}' and year(cast(scrape_date as date))={año}
            and cast(scrape_date as date) < date '{año}-09-10')
        select x.gsis_id, e.player, e.pos, e.ecr
        from read_parquet('{ECR_PARQUET}') e
        join xwalk_ids_nflverse x on cast(e.id as double) = x.fantasypros_id
        where e.fp_page='{PAGINA}' and e.scrape_date=(select d from snap)
          and x.gsis_id is not null
        order by e.ecr
    """).fetchall()
    return [(g, n, p, r) for g, n, p, r in q]


def eg_celdas(con, hasta):
    """E[fracción de temporada jugada] por (pos,tier,lesión), solo datos < hasta."""
    rows = con.execute("""
      with j as (select player_id, position, season, count(distinct week) g,
                   sum(coalesce(fantasy_points_ppr,0)) fp,
                   sum(coalesce(def_tackles_solo,0)+coalesce(def_tackle_assists,0)) tkl
                 from fact_player_week where season_type='REG' group by 1,2,3),
      r as (select *, lag(g) over w gp, lag(fp) over w fpp, lag(tkl) over w tklp,
                   lag(season) over w sp
            from j window w as (partition by player_id order by season))
      select position, season, g, gp, fpp, tklp,
             rank() over (partition by position, season order by fpp/nullif(gp,0) desc) rk
      from r where gp>=8 and sp=season-1 and season>=2011 and season < ?
    """, [hasta]).fetchall()
    acc = defaultdict(list)
    for pos, ss, g, gp, fpp, tklp, rk in rows:
        sg = 17 if ss >= 2021 else 16
        tier = ('A' if (rk or 99) <= 12 else 'B') if pos in ('QB', 'TE') else \
               ('A' if (rk or 99) <= 24 else 'B') if pos in ('RB', 'WR') else 'B'
        les = 'les' if gp <= (17 if ss - 1 >= 2021 else 16) - 4 else 'ok'
        acc[(pos, tier, les)].append(g / sg)
    return {k: sum(v) / len(v) for k, v in acc.items() if len(v) >= 8}


def mi_tablero(T, con, año, items):
    """Proyección de `año` usando SOLO datos de año-1."""
    EG = eg_celdas(con, año)
    prev = {}
    for (pid, y), (nom, pos, raw) in T.items():
        if y == año - 1 and pos in OFE:
            g = raw.get(210, 0)
            if g >= 8:
                pts = puntos({str(k): v for k, v in raw.items()}, POSID[pos], items)
                prev[pid] = (pos, pts, g, pts / g)
    # tier por rango de puntos-por-juego del año previo
    porpos = defaultdict(list)
    for pid, (pos, pts, g, pg) in prev.items():
        porpos[pos].append((pg, pid))
    rk = {}
    for pos, l in porpos.items():
        for i, (_, pid) in enumerate(sorted(l, reverse=True)):
            rk[pid] = i + 1
    out = {}
    sg_prev = 17 if año - 1 >= 2021 else 16
    for pid, (pos, pts, g, pg) in prev.items():
        tier = ('A' if rk[pid] <= 12 else 'B') if pos in ('QB', 'TE') else \
               ('A' if rk[pid] <= 24 else 'B')
        les = 'les' if g <= sg_prev - 4 else 'ok'
        frac = EG.get((pos, tier, les)) or EG.get((pos, tier, 'ok')) or 0.82
        out[pid] = (pos, pg * 17 * frac)
    return out


def real(T, año, items):
    out = {}
    for (pid, y), (nom, pos, raw) in T.items():
        if y == año and pos in OFE:
            out[pid] = (nom, pos, puntos({str(k): v for k, v in raw.items()},
                                         POSID[pos], items))
    return out


def spearman(pares):
    n = len(pares)
    if n < 3:
        return 0.0
    a = sorted(range(n), key=lambda i: pares[i][0])
    b = sorted(range(n), key=lambda i: pares[i][1])
    ra, rb = [0] * n, [0] * n
    for r, i in enumerate(a): ra[i] = r
    for r, i in enumerate(b): rb[i] = r
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n * n - 1))


if __name__ == '__main__':
    con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
    items = cargar_reglas()
    print('cargando temporadas reales bajo nuestras reglas...', flush=True)
    T = temporadas(2019, 2025)
    KS = (24, 48, 96)
    tot = defaultdict(lambda: defaultdict(float))
    for año in range(2021, 2026):
        mk = mercado(con, año)
        mio = mi_tablero(T, con, año, items)
        rl = real(T, año, items)
        univ = [(g, n, p, r) for g, n, p, r in mk if g in rl]
        novatos = [g for g, n, p, r in univ if g not in mio]
        # tres tableros sobre el MISMO universo
        rank_mk = {g: i for i, (g, n, p, r) in enumerate(univ)}
        rank_mio = {g: i for i, g in enumerate(sorted(
            [g for g, *_ in univ if g in mio], key=lambda g: -mio[g][1]))}
        # híbrido: el mío, INTERCALANDO a los novatos en el puesto que les da
        # el mercado (imputo sus puntos con los que mi tablero asigna a ese
        # puesto). El bug anterior los mandaba al final y nunca entraban.
        mis_pts = sorted((mio[g][1] for g in mio), reverse=True)
        def pts_hib(g):
            if g in mio:
                return mio[g][1]
            r = rank_mk[g]
            return mis_pts[min(r, len(mis_pts) - 1)] if mis_pts else 0.0
        hib = sorted([g for g, *_ in univ], key=lambda g: -pts_hib(g))
        rank_hib = {g: i for i, g in enumerate(hib)}
        real_pts = {g: rl[g][2] for g, *_ in univ}
        print(f"\n===== {año} · universo {len(univ)} (novatos sin historia: {len(novatos)}) =====")
        for nom, rk in (('mercado (ECR)', rank_mk), ('mío', rank_mio), ('híbrido', rank_hib)):
            comunes = [g for g in rk if g in real_pts]
            rho = spearman([(rk[g], -real_pts[g]) for g in comunes])
            fila = f"  {nom:16} rho={rho:+.3f}"
            for K in KS:
                topk = sorted(comunes, key=lambda g: rk[g])[:K]
                fila += f" · top{K}={sum(real_pts[g] for g in topk):>7.0f}"
                tot[nom][K] += sum(real_pts[g] for g in topk)
            tot[nom]['rho'] += rho
            print(fila, flush=True)
    print("\n===== AGREGADO 5 TEMPORADAS =====")
    print(f"  {'tablero':16}{'rho medio':>11}" + ''.join(f"{'top'+str(K):>11}" for K in KS))
    for nom in ('mercado (ECR)', 'mío', 'híbrido'):
        print(f"  {nom:16}{tot[nom]['rho']/5:>+11.3f}"
              + ''.join(f"{tot[nom][K]:>11.0f}" for K in KS))
