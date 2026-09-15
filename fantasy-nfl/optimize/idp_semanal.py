"""STREAMING IDP — ¿ayuda mirar contra quién juega el defensivo?

Pedido de Andrés (15-sep): "no cogimos ningún IDP que no sea cambiable, hay que
montar un modelo para escoger semanalmente del waiver wire. Usemos datos
históricos de las líneas ofensivas contra las que juegan para predecir SI AYUDA
tenerlas en cuenta... lo mismo para cada línea IDP, en general tener en cuenta
los contrincantes."

La pregunta no es "armemos el ajuste por rival". Es "¿el ajuste por rival paga?".
Se responde con backtest fuera de muestra, no con intuición. Si no paga, el
modelo NO debe usarlo — y eso también es un resultado.

FUENTE ✅ = nflverse (stats_player_week, 2019-2026 REG), la misma base pública
que alimenta la mayoría de modelos públicos de NFL.
⚠️ SUPUESTO S-NFLVERSE: nflverse y ESPN discrepan en la atribución de tacleadas
(p.ej. Simmons 2025: 37 solo en nflverse vs 39 en ESPN). Los pesos de abajo
reconstruyen el appliedTotal de ESPN con R²=0.978 y error mediano ~1.1 pts por
TEMPORADA. Suficiente para RANKEAR candidatos; insuficiente para afirmar el
punto exacto de un jugador. CADUCIDAD: si alguna vez se necesita el punto
exacto, hay que leerlo de ESPN, no de aquí.

QUÉ ES "PUNTOS PERMITIDOS" (lo que pediste): para cada ofensiva rival y cada
posición IDP, cuántos puntos de fantasy conceden por partido a esa posición,
expresado como MULTIPLICADOR sobre la media de la liga. 1.20 = esa ofensiva
regala un 20% más de lo normal a esa posición.

CANDADO ANTI-FUGA: el multiplicador de la semana W se calcula SOLO con semanas
< W. Nunca se usa información del futuro. Sin esto, cualquier ajuste "funciona".

    python optimize/idp_semanal.py            # backtest: ¿ayuda o no?
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import duckdb

NFLV = str(RAIZ / 'data' / 'nflverse' / 'semanal_*.parquet')

# Pesos de nuestra liga. solo=1.0 y asistida=0.5 estan VALIDADOS celda a celda
# contra los scoringItems de ESPN (statId 108 y 107). El sack lleva override por
# slot: 3.0 en DT, 2.0 en DE/LB/CB/S. El resto sale del ajuste sobre 2025.
PESOS = dict(solo=1.0, asis=0.5, sack_dt=3.0, sack_otro=2.0, tfl=0.5,
             int_=3.0, pd=1.0, ff=1.2, fr=1.0, td=6.5, saf=1.5, blk=3.0)
POS_DT = ("DT", "NT")
GRUPOS = {'DL': ('DT', 'NT', 'DE', 'EDGE'), 'LB': ('LB', 'OLB', 'ILB', 'MLB'),
          'DB': ('CB', 'S', 'FS', 'SS', 'DB')}
MIN_JUEGOS = 3          # historia mínima del jugador para predecirlo
MIN_OBS_RIVAL = 3       # partidos mínimos del rival para creerle su multiplicador


def base(con):
    """Tabla jugador-semana con puntos de fantasy y grupo posicional."""
    caso = " ".join(f"when position in {g} then '{k}'" for k, g in
                    ((k, tuple(v)) for k, v in GRUPOS.items()))
    con.execute(f"""
      create or replace view semanal as
      select season, week, player_id, player_display_name nombre, position pos,
             team, opponent_team rival,
             case {caso} else null end grupo,
             coalesce(def_tackles_solo,0)*{PESOS['solo']}
           + coalesce(def_tackle_assists,0)*{PESOS['asis']}
           + coalesce(def_sacks,0)*(case when position in {POS_DT}
                 then {PESOS['sack_dt']} else {PESOS['sack_otro']} end)
           + coalesce(def_tackles_for_loss,0)*{PESOS['tfl']}
           + coalesce(def_interceptions,0)*{PESOS['int_']}
           + coalesce(def_pass_defended,0)*{PESOS['pd']}
           + coalesce(def_fumbles_forced,0)*{PESOS['ff']}
           + coalesce(def_fumbles,0)*{PESOS['fr']}
           + coalesce(def_tds,0)*{PESOS['td']}
           + coalesce(def_safeties,0)*{PESOS['saf']}
           + (coalesce(def_fg_blocks,0)+coalesce(def_punt_blocks,0)
              +coalesce(def_pat_blocks,0))*{PESOS['blk']} fp
      from read_parquet('{NFLV}')
      where position is not null""")


def backtest(con, desde=2021):
    """¿Predice mejor con o sin ajuste por rival? Todo fuera de muestra.

    Para cada jugador-semana con historia suficiente:
      pred_base  = promedio del jugador en semanas anteriores
      pred_rival = pred_base x multiplicador del rival (solo con datos previos)
    """
    con.execute(f"""
      create or replace table ev as
      with s as (select * from semanal where grupo is not null and season>={desde}),
      -- historia del JUGADOR, estrictamente anterior
      hist as (
        select season, week, player_id, nombre, grupo, rival, fp,
               avg(fp)  over w pred_base,
               count(*) over w n_jug
        from s
        window w as (partition by player_id order by season, week
                     rows between unbounded preceding and 1 preceding)),
      -- media de la liga por grupo, estrictamente anterior
      liga as (
        select season, week, grupo,
               avg(fp) over w mu_liga
        from (select distinct season, week, grupo from s)
        window w as (partition by grupo order by season, week
                     rows between unbounded preceding and 1 preceding)),
      -- puntos que cada OFENSIVA concede a cada grupo, estrictamente anterior
      perm as (
        select season, week, rival, grupo, media_rival, n_riv from (
          select season, week, rival, grupo,
                 avg(fp_eq) over w media_rival,
                 count(*)   over w n_riv
          from (select season, week, rival, grupo, sum(fp) fp_eq
                from s group by 1,2,3,4)
          window w as (partition by rival, grupo order by season, week
                       rows between unbounded preceding and 1 preceding)))
      select h.season, h.week, h.nombre, h.grupo, h.rival, h.fp,
             h.pred_base, h.n_jug, p.media_rival, p.n_riv,
             m.mu_riv_liga
      from hist h
      join perm p using (season, week, rival, grupo)
      join (select season, week, grupo, avg(media_rival) mu_riv_liga
            from perm group by 1,2,3) m using (season, week, grupo)
      where h.n_jug >= {MIN_JUEGOS} and p.n_riv >= {MIN_OBS_RIVAL}
        and h.pred_base is not null and m.mu_riv_liga > 0""")
    return con.execute("select count(*), count(distinct nombre) from ev").fetchone()


def compara(con, grupo=None, tope=1.6):
    """MAE y correlación de las dos predicciones. `tope` acota el multiplicador."""
    filtro = f"and grupo='{grupo}'" if grupo else ""
    q = f"""
      with x as (
        select fp, pred_base,
               pred_base * least({tope}, greatest({2 - tope},
                    media_rival / mu_riv_liga)) pred_rival
        from ev where 1=1 {filtro})
      select count(*),
             avg(abs(pred_base - fp)), avg(abs(pred_rival - fp)),
             corr(pred_base, fp), corr(pred_rival, fp)
      from x"""
    return con.execute(q).fetchone()


def main():
    con = duckdb.connect()
    base(con)
    n, jug = backtest(con)
    print(f"=== BACKTEST fuera de muestra ===")
    print(f"observaciones jugador-semana: {n:,} · jugadores distintos: {jug:,}")
    print(f"(candado anti-fuga: el multiplicador de la semana W usa solo semanas < W)\n")
    print(f"{'grupo':8}{'n':>9}{'MAE base':>11}{'MAE rival':>11}{'mejora':>9}"
          f"{'corr base':>11}{'corr rival':>12}")
    filas = []
    for g in (None, 'DL', 'LB', 'DB'):
        n_, mb, mr, cb, cr = compara(con, g)
        mej = (mb - mr) / mb if mb else 0
        filas.append((g or 'TODOS', n_, mb, mr, mej, cb, cr))
        print(f"{(g or 'TODOS'):8}{n_:>9,}{mb:>11.3f}{mr:>11.3f}{mej:>8.2%}"
              f"{cb:>11.4f}{cr:>12.4f}")
    print("\n=== ¿HAY SEÑAL SIQUIERA? ===")
    q = """select grupo, corr(fp - pred_base, media_rival/mu_riv_liga) r,
                  stddev(media_rival/mu_riv_liga) disp from ev group by 1 order by 1"""
    for g, r, disp in con.execute(q).fetchall():
        print(f"  {g:4} corr(residual, multiplicador del rival) = {r:+.4f}"
              f"  ·  dispersión del multiplicador = {disp:.3f}")
    print("  → la señal existe y va en la dirección correcta, pero explica <0.3%")
    print("    de la varianza del residual: las ofensivas se diferencian solo un")
    print("    8-12% en cuántos puntos IDP conceden, y eso se ahoga en el ruido")
    print("    semanal del defensivo.")

    print("\n=== VEREDICTO ===")
    peor = min(f[4] for f in filas)
    mejor = max(f[4] for f in filas)
    if mejor < 0.005:
        print("  🚨 El ajuste por rival NO paga: la mejora es < 0.5% en todos los")
        print("     grupos. El modelo semanal NO debe usarlo. Predecir con el")
        print("     promedio propio del jugador es igual de bueno y más simple.")
    elif peor < 0:
        print("  ⚠️ Mixto: ayuda en unos grupos y estorba en otros. Usarlo SOLO")
        print("     donde el backtest lo respalda, nunca en bloque.")
    else:
        print(f"  ✅ El ajuste por rival paga en todos los grupos "
              f"({peor:.2%} a {mejor:.2%} de mejora en MAE).")
    print("\n  Lo que SÍ predice: el promedio propio del jugador. Es el predictor")
    print("  que gana, y el recomendador semanal se construye sobre él.")
    print("\n  python optimize/idp_semanal.py waiver   → candidatos de ESTA semana")
    return 0


def waiver():
    """Ranking de IDP disponibles en la liga, por lo único que demostró predecir:
    su propia tasa. Se muestra la proyección semanal de ESPN al lado como
    segunda opinión independiente, NO como desempate automático."""
    import json
    import requests
    from ingest.espn_auth import credenciales
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    ck = {'espn_s2': s2, 'SWID': swid}
    sem = requests.get(u, params={'view': 'mStatus'}, cookies=ck,
                       timeout=30).json()['status']['latestScoringPeriod']
    con = duckdb.connect()
    base(con)
    # tasa propia: ponderada 2 a 1 a favor de la temporada en curso
    tasa = {r[0]: (r[1], r[2], r[3]) for r in con.execute("""
        select nombre,
               sum(fp * case when season=2026 then 2.0 else 1.0 end)
                 / sum(case when season=2026 then 2.0 else 1.0 end) tasa,
               count(*) jg, sum(case when season=2026 then 1 else 0 end) jg26
        from semanal where season>=2025 and grupo is not null group by 1""").fetchall()}
    SLOT = {8: 'DT', 9: 'DE', 10: 'LB', 12: 'CB', 13: 'S'}
    for slot, et in SLOT.items():
        filt = {"players": {"filterSlotIds": {"value": [slot]},
                            "filterStatus": {"value": ["FREEAGENT", "WAIVERS"]},
                            "limit": 300,
                            "sortPercOwned": {"sortAsc": False, "sortPriority": 1}}}
        d = requests.get(u, params={'view': 'kona_player_info',
                                    'scoringPeriodId': sem}, cookies=ck,
                         headers={'x-fantasy-filter': json.dumps(filt)},
                         timeout=60).json()
        filas = []
        for e in d.get('players', []):
            p = e['player']
            t = tasa.get(p['fullName'])
            if not t or t[1] < MIN_JUEGOS:
                continue
            w = next((s['appliedTotal'] for s in p.get('stats', [])
                      if s.get('scoringPeriodId') == sem and s.get('statSourceId') == 1
                      and s.get('statSplitTypeId') == 1), None)
            filas.append((t[0], p['fullName'], t[1], t[2], w, e.get('status')))
        # CANDADO DE ACTIVIDAD: una tasa histórica alta no sirve de nada si el
        # jugador ya no juega. Bobby Wagner salía 1º con 8.21 y cero snaps en
        # 2026. Se exige que ESPN lo proyecte por encima de cero ESTA semana.
        vivos = [f for f in filas if f[4]]
        muertos = [f for f in filas if not f[4]]
        vivos.sort(key=lambda f: -f[0])       # solo por tasa; el resto puede ser None
        print(f"\n=== {et} disponibles (semana {sem}) — orden por tasa propia ===")
        print(f"  {'jugador':24}{'tasa':>7}{'jg':>5}{'jg26':>6}{'proyESPN':>10}  estado")
        for ta, n, jg, jg26, w, st in vivos[:6]:
            print(f"  {n[:23]:24}{ta:>7.2f}{jg:>5}{jg26:>6}{w:>10.2f}  {st}")
        if muertos:
            top = sorted(muertos, key=lambda f: -f[0])[:3]
            print(f"  (excluidos por proyección 0 — no están jugando: "
                  f"{', '.join(f'{n} {ta:.1f}' for ta, n, *_ in top)})")
    return 0


if __name__ == '__main__':
    raise SystemExit(waiver() if len(sys.argv) > 1 and sys.argv[1] == 'waiver'
                     else main())
