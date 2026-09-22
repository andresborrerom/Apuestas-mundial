# Prompt de arranque — Sistema de decisión para fantasy football (ESPN)

> Pegar este documento completo como primer mensaje en Claude Code, dentro de un repo vacío.

---

## 1. Contexto y objetivo

Estoy construyendo un sistema cuantitativo de apoyo a la decisión para ganar mi liga de fantasy football de la NFL. No quiero un script suelto: quiero un sistema con capas separadas, auditable y con backtest honesto.

Mi perfil: matemático con maestría en Data Science, trabajo en investigación cuantitativa de portafolios. Trátame como tal. Comunicación directa y técnica, en español, sin relleno. Prefiero código funcional y bien estructurado sobre perfección arquitectónica prematura.

**El draft es el lunes 7 de septiembre de 2026, 7:00 PM.** La temporada arranca el 9 de septiembre. Eso fija las prioridades: lo que no sirva para el draft se construye después.

---

## 2. Parámetros de la liga

| Parámetro | Valor |
|---|---|
| Plataforma | ESPN (liga **privada** — requiere cookies) |
| Equipos | 16 |
| Draft | Snake, 7 sep 2026, **45 seg por pick**, orden fijado por el comisionado |
| Mi pick | Ronda 1, pick 10 |
| Trade de picks | No permitido |
| Keepers | **No** (2026 y 2027) — redraft puro |
| Universo | Todos los jugadores NFL |
| Waivers | FAAB continuo. Presupuesto **9999**, oferta mínima 1, sin límite de adquisiciones |
| Procesamiento waivers | Dom, Lun, Mié, Jue, Vie, Sáb a las 11:00 AM ET |
| Desempate FAAB | Se reinicia cada semana al orden inverso de la tabla |
| Alineación | Se bloquea individualmente al inicio de cada partido |
| Temporada regular | Matchups de 1 semana, sin desempate, sin ventaja de local |
| Playoffs | **8 equipos** (de 16), matchups de **1 semana**, sin reseeding |
| Siembra playoffs | Desempate por Total Points For |
| Trades | Sin límite, deadline 2 dic, revisión 1 día, 6 votos para vetar |

### Alineación titular (13 slots)

```
QB, RB, RB, WR, WR, TE, FLEX, OP, LB, DL, DB, D/ST, K
```

- `OP` = Offensive Player en nomenclatura ESPN → **slot superflex** (admite QB)
- `FLEX` = RB/WR/TE
- Banca: ~5 slots + 1 IR *(confirmar número exacto vía API)*

### Secuencia de mis picks (snake, 16 equipos, pick 10)

```
R1: 10   R2: 23   R3: 42   R4: 55   R5: 74   R6: 87   R7: 106  R8: 119 ...
```

---

## 3. Reglas de scoring (leídas de la app — validar todas contra la API)

### Rushing
| Concepto | Pts |
|---|---|
| Cada 10 yardas terrestres (RY10) | 1 |
| TD terrestre (RTD) | 6 |
| Bonus TD terrestre 40+ yd (RTD40) | +1 |
| Bonus TD terrestre 50+ yd (RTD50) | +2 |
| Juego de 100-199 yd terrestres (RY100) | +2 |
| Juego de 200+ yd terrestres (RY200) | +3 |

### Receiving
| Concepto | Pts |
|---|---|
| Cada 10 yardas de recepción (REY10) | 1 |
| **Cada recepción (REC)** | **1** (PPR completo) |
| TD de recepción (RETD) | 6 |
| Bonus TD recepción 40+ yd (RETD40) | +1 |
| Bonus TD recepción 50+ yd (RETD50) | +2 |
| Juego de 100-199 yd recibiendo (REY100) | +2 |
| Juego de 200+ yd recibiendo (REY200) | +3 |

### Passing
**No capturado en pantalla. Extraer de la API.** Lo único confirmado por mí: **TD de pase = 6 puntos** (no el default de 4). Faltan: tasa de yardas de pase, penalización por intercepción, posibles bonos por juego de 300/400 yardas.

### Kicking
| Concepto | Pts |
|---|---|
| PAT anotado / fallado | 1 / −1 |
| FG 0-39 yd anotado / fallado | 3 / −2 |
| FG 40-49 yd anotado / fallado | 4 / −1 |
| FG 50+ yd | **No capturado — extraer de API** |

### Team Defense / Special Teams
| Concepto | Pts |
|---|---|
| Sack | 1 |
| Intercepción | 3 |
| Fumble recuperado | 3 |
| Safety | 2 |
| Punt/PAT/FG bloqueado | 2 |

**No aparecen escalones de puntos permitidos ni yardas permitidas.** Confirmar por API. Si es correcto, el D/ST es scoring puramente de eventos.

### Miscellaneous (aplica transversalmente)
| Concepto | Pts |
|---|---|
| Fumble perdido (FUML) | −2 |
| TD de retorno de intercepción | 6 |
| TD de retorno de fumble | 6 |
| TD de retorno de punt/FG bloqueado | 6 |

### Defensive Players (IDP)
| Concepto | Pts |
|---|---|
| Tackle total (TK) | 1 |
| Tackle asistido (TKA) | 0.5 |
| Stuff / TFL (SF) | 1 |
| Pase defendido (PD) | 1 |
| Fumble forzado (FF) | 2 |

**No aparecen puntos por sack ni por intercepción para jugadores defensivos individuales.** Esta es la ambigüedad más importante de todo el proyecto — resolverla es la primera tarea. Ver §5.

---

## 4. Tesis central

**Mi edge no viene de tener mejores proyecciones que el mercado. Viene de recalcular las mismas proyecciones bajo MIS reglas.**

Todo ADP público, todo ranking de ESPN y todo mock draft asume 4 puntos por TD de pase, scoring IDP con sacks, y ninguna asume mi combinación de superflex + 16 equipos. Mis 15 rivales van a draftear con listas calculadas para otro juego. El edge es aritmético, y por eso es fiable.

### Cuatro hipótesis a cuantificar, no a asumir

**H1 — El QB es la posición dominante.**
16 equipos × 2 slots de QB (QB + OP) agota los 32 QB titulares de la NFL. El baseline de replacement es un backup real. Con TDs de pase a 6 puntos, el spread QB1 → QB32 debería superar al de cualquier otra posición sobre su baseline.

**H2 — El scoring premia la cola derecha, no la media.**
Los bonos por juego de 100/200 yardas y por TD de 40+/50+ yardas pagan explosividad. Dos jugadores con la misma proyección de media no valen lo mismo: **el de mayor varianza vale más**. Cuantificar el valor esperado del componente de bonos por jugador; debería ser materialmente distinto entre perfiles de alto aDOT y perfiles de volumen corto.

**H3 — La estructura de playoffs refuerza H2.**
8 de 16 equipos clasifican, y los matchups de playoffs son de **1 sola semana sin reseeding**. Clasificar es barato; el título exige ganar tres eventos consecutivos de una semana. Cuando hay que ganar tres volados, el techo vale más que el piso. La función objetivo del draft es **maximizar P(campeonato)**, no puntos esperados de temporada — y bajo esta estructura eso favorece varianza.

**H4 — IDP es un juego de volumen de tackles, y el DL es el slot escaso.**
Si no hay puntos por sack, los edge rushers colapsan en valor y los linebackers de tres downs dominan. El slot de DL exige linemen con volumen de tackles (interiores contra la carrera), no pass rushers. Esto invierte los rankings IDP públicos por completo. Aun así, con 1 slot por posición y 16 equipos, el baseline es LB16/DL16/DB16 y el spread sobre baseline debería seguir siendo chico frente al costo de oportunidad de un pick temprano.

### Principio de modelado transversal

Separar **oportunidad** de **eficiencia**. Snaps, targets, carries y snaps defensivos son persistentes y predecibles. Yardas por target y tasa de TD revierten con fuerza a la media. Proyectar oportunidad; aplicar eficiencia regularizada con shrinkage hacia la media posicional.

---

## 5. Tarea 0 — antes que nada

Script mínimo que valide la conexión ESPN e imprima el diccionario **completo** de settings y scoring. Objetivos específicos, en orden de prioridad:

1. **¿Cómo puntúa el sack para un jugador defensivo individual?** ¿Está incluido dentro de "Stuffs" (TFL)? ¿Tiene su propio ítem no visible en la app? Esto decide toda la valuación IDP.
2. **¿Hay puntos por intercepción para IDP?**
3. Scoring completo de passing (yardas, INT, bonos).
4. **¿El D/ST tiene escalones de puntos/yardas permitidas?**
5. FG de 50+ yardas.
6. **¿Los bonos de yardas acumulan?** Un juego de 210 yardas, ¿suma 2+3=5 o solo 3? Verificar contra box scores reales.
7. Tamaño exacto de banca e IR.

### Autenticación
- Librería: `espn-api` (cwendt94) → `from espn_api.football import League`
- `League(league_id=..., year=2026, espn_s2='...', swid='{...}')`
- El `swid` va **con** llaves `{}`; el `espn_s2` es un token largo sin llaves
- Credenciales en `.env`, **nunca en el repo**. `.env` en `.gitignore` desde el primer commit
- Las cookies caducan: aislar la autenticación en un módulo con manejo de errores claro y un comando de diagnóstico

---

## 6. Arquitectura — tres capas, estrictamente separadas

**Capa 1 — Ingesta y modelo de datos.** Hechos crudos, granularidad jugador-semana. **Nunca importar puntos de fantasy precalculados.**

**Capa 2 — Proyección.** Puntos esperados como **distribución** (media, sd, cuantiles). Dada H2 y H3, la distribución no es un lujo: es el núcleo del modelo.

**Capa 3 — Optimización y decisión.** Draft (VBD + tiers) y después alineación semanal y política de FAAB.

---

## 7. Modelo de datos

### Capa NFL — fuente: `nfl_data_py` / nflverse

- `dim_player` — id nflverse, nombre, posición, equipo, edad, experiencia
- `dim_team`
- `dim_game` — semana, local/visitante, **spread y total O/U de Vegas**, techo/aire libre, clima. *(El total implícito de Vegas es el mejor predictor único del entorno de puntos.)*
- `fact_player_week_off` — snaps, snap_share, routes run, targets, target_share, air yards, aDOT, carries, red zone touches, goal-line carries, yardas, TDs, recepciones. **Además: yardas por acarreo/recepción individual, para poder computar los bonos de TD de 40+/50+ y los umbrales de 100/200 yardas** (los bonos requieren granularidad de jugada, no agregados de temporada)
- `fact_player_week_def` — snaps defensivos, tackles solo, tackles asistidos, sacks, TFL, QB hits, pases defendidos, INT, fumbles forzados/recuperados
- `dim_scoring_rules` — **tabla crítica.** El scoring de mi liga como configuración parametrizada, cargada desde el volcado de la API. Los puntos se derivan siempre desde volumen crudo × esta tabla

### Capa liga (ESPN) — la que casi nadie construye
- `dim_manager` — mis 15 rivales
- `fact_roster_week`
- `fact_matchup`
- `fact_transaction` — FAAB gastado, por quién, en qué jugador, en qué semana

Permite modelar rivales: necesidad posicional, FAAB restante y patrón histórico de puja. **Modelar el FAAB siempre en porcentaje del presupuesto, nunca en unidades** — el presupuesto de 9999 es arbitrario y las unidades no son comparables con nada externo.

### Capa modelo
- `proj_player_week` — media, sd, cuantiles, **versionada por fecha de corte** (sin esto no hay backtest honesto)
- `fact_decision` vs `fact_counterfactual` — lo que hice vs el óptimo ex-post. Puntos dejados en banca, semana a semana

---

## 8. Plan de fases

### Fase 1 — Fundación (inmediata)
1. Tarea 0 completa: conexión validada + volcado de scoring resuelto
2. Ingesta nflverse, mínimo 2021–2025
3. **Motor de scoring parametrizado**, incluyendo bonos de umbral y de jugada larga
4. **Validación:** recalcular puntos de 2025 bajo mis reglas y cuadrar contra box scores reales de mi liga en ESPN, jugador por jugador. Si no cuadra al decimal, nada de lo que sigue sirve

### Fase 2 — Draft (entregar antes del 7 de septiembre)
1. Proyecciones 2026 por jugador-temporada, con distribución completa
2. **VBD con baselines derivados de MI estructura**: 16 equipos, superflex, 1 slot por posición IDP
3. Descomponer el valor proyectado en componente base + componente de bonos, para exponer H2
4. Agrupación en tiers (el corte de tier decide un pick, no el ranking ordinal)
5. Comparación de mi valuación vs ADP de consenso → **tabla de arbitraje**: dónde el mercado regala valor y dónde estoy pagando de más
6. **Entregable final: hoja de tiers imprimible, legible de un vistazo.** Restricción dura: 45 segundos por pick. No sirve nada interactivo ni que requiera computar durante el draft. Las reglas de decisión se pre-deciden y se escriben antes del 7 de septiembre

### Fase 3 — Temporada (después del draft, no ahora)
- FAAB con modelado de rivales, en % de presupuesto
- Start/sit optimizando **P(ganar el matchup)**, no puntos esperados
- Ajuste de política según posición en la tabla: clasificar es barato (8 de 16), así que la política debe virar hacia maximizar siembra y techo una vez asegurado el puesto
- Tracking de decisiones vs contrafactual

---

## 9. Stack y convenciones

- Python. `nfl_data_py`, `espn-api`, `pandas`, `polars` si el volumen lo pide
- Persistencia: DuckDB o SQLite (arrancar simple; el volumen es chico)
- Todo parámetro de liga en un único archivo de configuración versionado
- Tests sobre el motor de scoring, obligatorios, con casos que cubran los bonos de umbral
- Estructura clara: `ingest/`, `model/`, `optimize/`, `config/`, `tests/`

---

## 10. Qué NO hacer

- No importar puntos de fantasy precalculados de ninguna fuente
- No asumir ningún valor de scoring que no esté confirmado por la API
- No construir Fase 3 antes de que Fase 1 esté validada
- No proyectar eficiencia sin shrinkage
- No usar ADP de consenso como valuación — solo como precio de mercado
- No usar rankings IDP públicos: están calculados para scoring con sacks
- No mezclar las tres capas en el mismo módulo

---

## 11. Primer paso

No escribas código todavía. Primero:

1. Propone la estructura de directorios y el esquema de tablas concreto (DDL)
2. Señala qué supuestos míos te parecen débiles o mal planteados — en particular, critica H2 y H3: ¿el argumento de que la varianza vale más bajo esta estructura de playoffs resiste, o estoy sobreajustando una intuición?
3. Identifica el riesgo técnico más grande de la Fase 1

Después de que yo valide eso, arrancamos con la Tarea 0.
