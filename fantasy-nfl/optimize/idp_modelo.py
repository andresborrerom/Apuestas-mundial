"""MODELO DE DATOS IDP — ¿se puede elegir semana a semana con el contrincante?

Andrés (15-sep): "¿no hubo nada que nos ayudara a usar el contrincante para
escoger semana a semana? Olvídate de mis sugerencias, montemos modelo de datos".

Tiene razón en el reclamo. `idp_semanal.py` probó UNA variable del rival —los
puntos de fantasy que su ofensiva concede a la posición— y concluyó sobre
TODAS. Esto prueba el conjunto completo de lo que se puede saber antes del
kickoff, y deja que un modelo decida qué sirve, en vez de decidirlo yo.

FEATURES (todas conocidas ANTES del kickoff; nada del partido en curso):
  jugador   tasa propia (17 jornadas), juegos de historia
  rival     jugadas/juego, carreras/juego, pases/juego, sacks permitidos/juego,
            EPA de pase y de carrera, y puntos IDP concedidos a la posición
  contexto  spread DESDE EL LADO DEL DEFENSOR (+ = su equipo es underdog),
            total de Vegas, local/visitante, descanso, juego divisional
  propio    jugadas defensivas que enfrenta su equipo por juego

El `spread` es la prueba directa de MI PROPIA tesis de guion de partido
("underdog -> el rival corre con ventaja -> más tacleadas"), que usé para
recomendar DTs y nunca había validado.

MÉTODO
  Corte temporal estricto: entrena 2021-2024, prueba 2025-2026. Nunca se
  entrena con el futuro. Las medias del rival y del jugador son acumuladas
  hasta la semana ANTERIOR.
  Se comparan: (a) la tasa propia sola —el campeón actual—, (b) ridge sobre
  todas las features, (c) gradient boosting.

MÉTRICA QUE MANDA: no es el MAE, es la decisión. "Si cada semana elijo los
K mejores según el modelo, ¿anoto más que eligiendo por tasa propia?" Un
modelo puede bajar el MAE y no cambiar ni una elección.

    python optimize/idp_modelo.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import duckdb
import numpy as np

from optimize.idp_semanal import base, VENTANA_JUGADOR

D = RAIZ / 'data' / 'nflverse'
ENTRENA_HASTA = 2024        # 2025-2026 queda intacto para probar
MIN_HIST = 4                # jornadas mínimas de historia del jugador


def tabla(con):
    """Une jugador-semana con rival, contexto de Vegas y equipo propio."""
    base(con)
    con.execute(f"""
      create or replace table eqw as
        select * from read_parquet('{D}/equipo_*.parquet')""")
    con.execute(f"""
      create or replace table jg as
        select game_id, season, week, home_team, away_team, spread_line,
               total_line, away_rest, home_rest, div_game
        from read_parquet('{D}/juegos.parquet')""")

    # medias ACUMULADAS del rival hasta la semana anterior (sin fuga)
    con.execute("""
      create or replace table riv as
      select season, week, team,
             avg(pases+carreras) over w o_jugadas,
             avg(carreras)       over w o_carreras,
             avg(pases)          over w o_pases,
             avg(sacks_perm)     over w o_sacks,
             avg(epa_pase)       over w o_epa_pase,
             avg(epa_carrera)    over w o_epa_carrera,
             count(*)            over w o_n
      from eqw
      window w as (partition by team order by season, week
                   rows between unbounded preceding and 1 preceding)""")

    # jugadas defensivas que enfrenta cada equipo (= ofensiva del rival)
    con.execute("""
      create or replace table def_prop as
      select season, week, opponent_team equipo,
             avg(pases+carreras) over w d_jugadas_enfrenta
      from eqw
      window w as (partition by opponent_team order by season, week
                   rows between unbounded preceding and 1 preceding)""")

    # puntos IDP que cada ofensiva concede a cada grupo, acumulado previo
    con.execute("""
      create or replace table conc as
      select season, week, rival, grupo,
             avg(fp_eq) over w o_fp_concede, count(*) over w c_n
      from (select season, week, rival, grupo, sum(fp) fp_eq
            from semanal where grupo is not null group by 1,2,3,4)
      window w as (partition by rival, grupo order by season, week
                   rows between unbounded preceding and 1 preceding)""")

    con.execute(f"""
      create or replace table X as
      with s as (select * from semanal where grupo is not null and season>=2021),
      pj as (
        select season, week, player_id, nombre, grupo, team, rival, fp,
               avg(fp) over v p_tasa, count(*) over w p_n
        from s
        window v as (partition by player_id order by season, week
                     rows between {VENTANA_JUGADOR} preceding and 1 preceding),
               w as (partition by player_id order by season, week
                     rows between unbounded preceding and 1 preceding))
      select pj.*,
             r.o_jugadas, r.o_carreras, r.o_pases, r.o_sacks,
             r.o_epa_pase, r.o_epa_carrera,
             c.o_fp_concede,
             d.d_jugadas_enfrenta,
             case when g.home_team = pj.team then 1 else 0 end es_local,
             -- spread DESDE EL LADO DEL DEFENSOR: + = su equipo es underdog
             case when g.home_team = pj.team then -g.spread_line
                  else g.spread_line end spread_def,
             g.total_line, g.div_game,
             case when g.home_team = pj.team then g.home_rest else g.away_rest end descanso
      from pj
      join riv r on (pj.season,pj.week,pj.rival)=(r.season,r.week,r.team)
      join conc c on (pj.season,pj.week,pj.rival,pj.grupo)
                   =(c.season,c.week,c.rival,c.grupo)
      join def_prop d on (pj.season,pj.week,pj.team)=(d.season,d.week,d.equipo)
      join jg g on pj.season=g.season and pj.week=g.week
                 and (g.home_team=pj.team or g.away_team=pj.team)
      where pj.p_n >= {MIN_HIST} and pj.p_tasa is not null
        and r.o_n >= 4 and c.c_n >= 4 and g.spread_line is not null""")
    return con.execute("select count(*) from X").fetchone()[0]


FEATS = ['p_tasa', 'o_jugadas', 'o_carreras', 'o_pases', 'o_sacks',
         'o_epa_pase', 'o_epa_carrera', 'o_fp_concede', 'd_jugadas_enfrenta',
         'es_local', 'spread_def', 'total_line', 'div_game', 'descanso']


def datos(con, grupo=None):
    f = f"and grupo='{grupo}'" if grupo else ""
    cols = ", ".join(FEATS)
    q = f"select season, week, nombre, grupo, fp, {cols} from X where 1=1 {f}"
    df = con.execute(q).df().dropna()
    tr = df[df.season <= ENTRENA_HASTA]
    te = df[df.season > ENTRENA_HASTA]
    return df, tr, te


def acierto_decision(te, col, k=5):
    """La métrica que manda: puntos reales promedio de los K que el criterio
    `col` habría elegido cada semana, dentro de cada grupo posicional."""
    tot, n = 0.0, 0
    for _, g in te.groupby(['season', 'week', 'grupo']):
        if len(g) < k * 2:
            continue
        tot += g.nlargest(k, col).fp.mean()
        n += 1
    return (tot / n) if n else float('nan'), n


def main():
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import RidgeCV
    from sklearn.preprocessing import StandardScaler

    con = duckdb.connect()
    n = tabla(con)
    df, tr, te = datos(con)
    print(f"=== MODELO DE DATOS IDP ===")
    print(f"observaciones: {n:,} · entrena {tr.season.min()}-{ENTRENA_HASTA} "
          f"({len(tr):,}) · prueba {ENTRENA_HASTA+1}-2026 ({len(te):,})")
    print(f"features: {len(FEATS)}\n")

    Xtr, ytr = tr[FEATS].values, tr.fp.values
    Xte, yte = te[FEATS].values, te.fp.values
    sc = StandardScaler().fit(Xtr)
    ridge = RidgeCV(alphas=np.logspace(-2, 3, 20)).fit(sc.transform(Xtr), ytr)
    gbm = HistGradientBoostingRegressor(
        max_iter=400, learning_rate=0.05, max_depth=5,
        early_stopping=True, random_state=0).fit(Xtr, ytr)

    te = te.copy()
    te['pred_base'] = te.p_tasa
    te['pred_ridge'] = ridge.predict(sc.transform(Xte))
    te['pred_gbm'] = gbm.predict(Xte)

    print(f"{'predictor':16}{'MAE':>9}{'vs base':>10}{'corr':>9}")
    mae_b = np.abs(te.pred_base - yte).mean()
    for et, c in (('tasa propia', 'pred_base'), ('ridge', 'pred_ridge'),
                  ('gbm', 'pred_gbm')):
        m = np.abs(te[c] - yte).mean()
        r = np.corrcoef(te[c], yte)[0, 1]
        print(f"{et:16}{m:>9.4f}{(mae_b-m)/mae_b:>+9.2%}{r:>9.4f}")

    print(f"\n=== LA MÉTRICA QUE MANDA: ¿cambia la ELECCIÓN? ===")
    print("puntos reales promedio de los K elegidos cada semana y grupo")
    print(f"{'K':>4}{'tasa propia':>14}{'ridge':>11}{'gbm':>11}{'mejor gbm':>12}")
    for k in (1, 3, 5):
        a, nsem = acierto_decision(te, 'pred_base', k)
        b, _ = acierto_decision(te, 'pred_ridge', k)
        c, _ = acierto_decision(te, 'pred_gbm', k)
        print(f"{k:>4}{a:>14.3f}{b:>11.3f}{c:>11.3f}{(c-a):>+12.3f}")
    print(f"   (sobre {nsem} combinaciones semana x grupo en 2025-2026)")

    print(f"\n=== ¿QUÉ PESA? (ridge, features estandarizadas) ===")
    for f_, w in sorted(zip(FEATS, ridge.coef_), key=lambda x: -abs(x[1])):
        print(f"   {f_:22}{w:>+8.4f}")

    print(f"\n=== POR GRUPO (gbm vs tasa propia, MAE) ===")
    for g in ('DL', 'LB', 'DB'):
        _, trg, teg = datos(con, g)
        if len(teg) < 500:
            continue
        gb = HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                           max_depth=5, early_stopping=True,
                                           random_state=0).fit(trg[FEATS], trg.fp)
        mb = np.abs(teg.p_tasa - teg.fp).mean()
        mg = np.abs(gb.predict(teg[FEATS]) - teg.fp).mean()
        print(f"   {g:4} n={len(teg):>6,}  base {mb:.4f} → gbm {mg:.4f}  "
              f"({(mb-mg)/mb:+.2%})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
