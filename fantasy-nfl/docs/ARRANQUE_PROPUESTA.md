# Propuesta de arranque (§11 del prompt) — para validar ANTES de codear

## 1. Estructura de directorios

```
fantasy-nfl/
├── config/
│   └── liga.yaml            # ÚNICO archivo de parámetros (slots, picks, FAAB, fechas)
├── ingest/
│   ├── espn_auth.py         # auth aislada + comando de diagnóstico (cookies caducas)
│   ├── espn_dump.py         # Tarea 0: settings+scoring COMPLETOS, 2025 y 2026, a JSON versionado
│   ├── espn_league.py       # rosters, matchups, transacciones → capa liga
│   ├── nflverse.py          # pbp + weekly + snap counts + depth charts 2021-2025
│   └── ids_crosswalk.py     # nflverse gsis_id ↔ espn_id (el riesgo #1, ver §4)
├── model/
│   ├── scoring.py           # motor parametrizado: volumen crudo × dim_scoring_rules
│   ├── validate_scoring.py  # CANDADO: recalcular 2025 vs box scores ESPN, al decimal
│   └── proyeccion.py        # oportunidad × eficiencia-shrunk → distribución
├── optimize/
│   ├── vbd.py               # baselines de MI estructura + descomposición base/bonos
│   ├── tiers.py             # clustering en tiers + tabla de arbitraje vs ADP
│   └── draft_sheet.py       # genera la hoja imprimible (el artefacto final)
├── tests/
│   └── test_scoring.py      # casos con bonos de umbral, acumulación, jugada larga
├── db/  (duckdb, gitignored) ── data/ (parquet crudo, gitignored)
└── docs/  (LIBRO_SUPUESTOS.md, DECISIONES.md, este archivo)
```

`.env` con `ESPN_S2`/`SWID` en `.gitignore` desde el commit 1.

## 2. Esquema de tablas (DDL DuckDB, resumido a lo decisivo)

```sql
-- ===== capa 1: hechos =====
CREATE TABLE dim_player (
  player_id TEXT PRIMARY KEY,      -- gsis_id nflverse (canónico)
  espn_id INTEGER,                 -- via xwalk; NULL hasta verificar
  name TEXT, pos_fantasy TEXT,     -- QB/RB/WR/TE/K/LB/DL/DB (slot de MI liga)
  pos_nfl TEXT,                    -- EDGE/DT/S/CB/... (la fina decide H4)
  team TEXT, birth DATE, entry_year INT);

CREATE TABLE dim_game (
  game_id TEXT PRIMARY KEY, season INT, week INT, home TEXT, away TEXT,
  kickoff TIMESTAMP, spread_close DOUBLE, total_close DOUBLE,
  roof TEXT, temp DOUBLE, wind DOUBLE);

CREATE TABLE fact_player_week_off (
  season INT, week INT, player_id TEXT, game_id TEXT,
  snaps INT, snap_share DOUBLE, routes INT,
  targets INT, target_share DOUBLE, air_yards DOUBLE, adot DOUBLE,
  carries INT, rz_touches INT, gl_carries INT,
  pass_att INT, pass_cmp INT, pass_yds INT, pass_td INT, pass_int INT,
  rush_yds INT, rush_td INT, rec INT, rec_yds INT, rec_td INT, fumbles_lost INT,
  -- pre-agregados desde play-by-play (los bonos 40+/50+ exigen jugada):
  rush_td_40p INT, rush_td_50p INT, rec_td_40p INT, rec_td_50p INT,
  PRIMARY KEY (season, week, player_id));
-- Nota: los umbrales 100/200 son por JUEGO → se derivan del agregado semanal.
-- Los TD 40+/50+ NO → por eso las columnas pre-agregadas desde pbp.

CREATE TABLE fact_player_week_def (
  season INT, week INT, player_id TEXT, game_id TEXT,
  def_snaps INT, tk_solo INT, tk_ast INT, sacks DOUBLE, tfl INT,
  qb_hits INT, pd INT, ints INT, ff INT, fr INT,
  PRIMARY KEY (season, week, player_id));

CREATE TABLE dim_scoring_rules (        -- LA TABLA CRÍTICA
  ruleset TEXT,                         -- 'espn_2026', 'espn_2025' (P8)
  espn_stat_id INT,                     -- id crudo del dump (trazabilidad)
  stat_code TEXT,                       -- nuestro código legible
  points DOUBLE, per_units DOUBLE,      -- ej. yardas: points=1, per=10
  PRIMARY KEY (ruleset, espn_stat_id));

-- ===== capa liga =====
CREATE TABLE dim_manager (manager_id INT PRIMARY KEY, name TEXT, team_name TEXT);
CREATE TABLE fact_roster_week (season INT, week INT, manager_id INT,
  espn_player_id INT, slot TEXT, PRIMARY KEY (season, week, manager_id, espn_player_id));
CREATE TABLE fact_matchup (season INT, week INT, mgr_a INT, mgr_b INT,
  pts_a DOUBLE, pts_b DOUBLE, es_playoff BOOL, PRIMARY KEY (season, week, mgr_a));
CREATE TABLE fact_transaction (ts TIMESTAMP, season INT, week INT, manager_id INT,
  tipo TEXT, espn_player_id INT, faab_bid INT, faab_pct DOUBLE, gano BOOL);

-- ===== capa modelo =====
CREATE TABLE proj_player_week (
  asof DATE, season INT, week INT, player_id TEXT,
  mean DOUBLE, sd DOUBLE, p10 DOUBLE, p25 DOUBLE, p50 DOUBLE, p75 DOUBLE, p90 DOUBLE,
  mean_base DOUBLE, mean_bonus DOUBLE,   -- descomposición H2 explícita
  model_ver TEXT, PRIMARY KEY (asof, season, week, player_id));

CREATE TABLE xwalk_player_ids (player_id TEXT, espn_id INT,
  metodo TEXT, confianza DOUBLE, verificado BOOL, PRIMARY KEY (player_id));

CREATE TABLE fact_decision (season INT, week INT, tipo TEXT, detalle JSON, ts TIMESTAMP);
CREATE TABLE fact_counterfactual (season INT, week INT, pts_dejados_banca DOUBLE, detalle JSON);
```

## 3. Crítica a las hipótesis (lo pedido: especialmente H2 y H3)

### H1 (QB dominante) — de pie, con dos matices
El argumento aritmético es correcto: 32 slots de QB posibles = oferta titular
completa, baseline = backup real, y 6 pts/TD amplifica el spread. Matices:
**(a)** el baseline del slot OP no es QB32: es `max(QB_marginal, FLEX_marginal)`
— si los últimos QBs proyectan menos que el mejor RB/WR disponible, el slot se
llena con flex y el spread efectivo se acorta. Se calcula, no se asume.
**(b)** el edge se captura solo si el TIMING del draft es correcto: con 15
rivales usando listas estándar (4 pt/TD, no superflex), la corrida de QBs
puede empezar tarde — pagar precio de pánico temprano regala parte del edge.
El modelo de supervivencia por pick (con ADP público como comportamiento
rival, no como valor) es parte del entregable de Fase 2.

### H2 (el scoring premia la cola) — VÁLIDA pero mal enunciada: son dos hipótesis
- **H2a (convexidad → corrección de MEDIA): correcta y aritmética.** Los bonos
  son un payoff convexo en yardas de juego y de jugada. Por Jensen, dos
  jugadores con la misma media de yardas NO tienen la misma media de PUNTOS:
  el de distribución más dispersa/sesgada cobra más bonos esperados. Esto es
  una corrección al valor ESPERADO — computable exacto con distribuciones
  por juego y por jugada (por eso el pbp en Capa 1). No es "preferir varianza":
  es calcular bien la media bajo TUS reglas. Robusta, se cuantifica en Fase 2.
- **H2b (la varianza es valiosa per se): NO se sigue de H2a**, pertenece a H3
  y ahí tiene problemas (abajo). Ojo con la magnitud antes de enamorarse del
  relato: mi prior es que la diferencia de E[bonos] entre un perfil aDOT-alto
  y uno de volumen corto es real pero chica (~0.5-1.5 pts/sem sobre medias de
  15-20). Con PPR completo, el receptor de volumen recupera por recepciones lo
  que cede en bonos. **Medirlo antes de dejar que decida un pick.**

### H3 (playoffs → techo) — LA MÁS DÉBIL: tres objeciones cuantificables
1. **El desempate de siembra es Total Points For = un objetivo de MEDIA.**
   La estructura que citas como pro-varianza premia explícitamente la media
   acumulada: mejor siembra ⇒ rival más débil en QF (sin reseeding, el
   bracket se fija por siembra). La mitad del argumento se cae sola aquí.
2. **La varianza favorece al UNDERDOG del matchup, no al favorito.** Tu tesis
   central es que tendrás un edge aritmético ⇒ serás favorito en la mayoría
   de tus semanas de playoffs ⇒ **querrás MENOS varianza, no más**. H3 solo
   aplica si llegas como underdog — y si el plan es llegar como underdog,
   el problema es otro. La preferencia por varianza es CONDICIONAL al spread
   del matchup, y eso se decide semana a semana en start/sit (Fase 3), no
   comprando varianza cara en el draft.
3. **Confunde varianza semanal con upside de temporada.** Lo que sí gana
   títulos en el draft es el sesgo derecho a nivel TEMPORADA (el breakout
   que devuelve 3 rondas de valor), no el receptor búmeran de aDOT alto.
   Son activos distintos: el primero se busca en rondas medias/tardías
   (ambigüedad de rol con camino a volumen), el segundo cobra bonos H2a que
   ya están en la media corregida.
   **Reformulación propuesta:** función objetivo del draft = maximizar
   E[puntos bajo MIS reglas] (que ya incluye H2a) + premio explícito por
   upside de temporada en picks tardíos; la palanca de varianza semanal se
   ejerce en start/sit de playoffs. Se valida con el simulador de temporada
   completo (temporada + siembra por TPF + bracket): si el premio óptimo por
   varianza en el draft resulta >0 materialmente, lo adoptamos — pero que lo
   diga la simulación, no la intuición. (Tu instinto anti-sobreajuste aquí
   está bien calibrado.)

### H4 (IDP sin sacks) — probablemente correcta a medias, y la trampa está en el detalle
La conclusión "LB de volumen > edge rushers" es plausible, PERO: **un sack es
también un tackle solo y un TFL**. Si ESPN acredita TK(1) + SF(1) al sackear
— comprobable en Tarea 0 con el box score de un edge en tu liga 2025 — el
sack implícitamente vale ~2 pts aunque no exista el ítem "sack". Eso NO
invierte los rankings públicos "por completo": los recorta. El orden real
saldrá del motor validado. El punto del baseline chico (1 slot × posición,
spread bajo vs costo de oportunidad) es correcto y además coherente con H1:
los picks tempranos van a QB/flex, IDP se resuelve tarde — salvo que el
motor muestre un outlier tipo LB con 120+ tackles proyectados cuyo spread
sobre LB16 compita con un WR3.

## 4. Riesgo técnico #1 de Fase 1

**El cruce de identidades y semánticas ESPN ↔ nflverse**, en dos capas:
1. **`espn_stat_id` → estadística real.** El diccionario de stat IDs de ESPN
   no está documentado oficialmente; la comunidad lo tiene reverse-engineered
   incompleto para ítems exóticos (RY100, RETD50, acumulación de umbrales,
   buckets de FG). Un ID mal mapeado = motor que valida en el agregado y
   falla en el detalle. Mitigación: el candado de Fase 1.4 no es opcional —
   recalcular 2025 COMPLETO contra los box scores de la liga al decimal, y
   resolver P4/P1 empíricamente buscando en el histórico de la liga juegos
   con 200+ yardas y jugadores con sacks.
2. **`espn_id` ↔ `gsis_id` (jugadores).** No hay crosswalk oficial; el match
   por nombre es un campo minado (Jr./III, D.J./DJ, traspasos, IDP con nombres
   comunes). Mitigación: xwalk con múltiples métodos (nflverse ids table trae
   espn_id parcial + fuzzy sobre nombre-equipo-posición), columna de
   `confianza`, y verificación 1:1 obligatoria para todo jugador que entre
   al top-250 del draft board.

Riesgos secundarios: cookies ESPN caducas (auth aislada + diagnóstico, ya
en diseño); estado de mantenimiento de `nfl_data_py` en 2026 (verificar en
Tarea 0; fallback: leer los parquet de nflverse-data directo); y P8 (si el
scoring 2026 difiere del 2025, la validación usa las reglas de SU año).

## 5. Calendario propuesto (hoy: 10-ago; draft: 7-sep)

- **10-14 ago:** Tarea 0 + ingesta nflverse + dump de reglas 2025/2026.
- **15-20 ago:** motor de scoring + CANDADO al decimal contra 2025.
- **21-31 ago:** proyecciones 2026 con distribución + VBD/tiers + arbitraje.
- **1-5 sep:** hoja de draft + SIMULACROS cronometrados (45 s/pick) + reglas
  de decisión escritas. El simulacro es el candado del artefacto final.
- **7 sep:** draft. **9 sep:** arranca Fase 3.
