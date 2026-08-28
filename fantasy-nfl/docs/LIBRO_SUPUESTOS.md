# Libro de Supuestos — fantasy-nfl

> Regla de oro (CLAUDE.md II.4): un supuesto cuya fuente está disponible es un
> BUG. Esta lista arranca con PENDIENTES DE FUENTE (bloqueantes de Tarea 0),
> no con supuestos: nada de esto se asume, todo se extrae de la API.

## PENDIENTES DE FUENTE (bloqueantes — Tarea 0)
| # | Ítem | Fuente | Bloquea |
|---|---|---|---|
| P1 | ¿Sack puntúa para IDP? ¿Va implícito en TK+SF? | dump API + box score real de un jugador con sacks | TODA la valuación IDP (H4) |
| P2 | ¿INT puntúa para IDP? | dump API | valuación DB |
| P3 | Passing completo (yds/pt, INT, bonos 300/400) | dump API | valuación QB (H1) |
| P4 | ¿Bonos de yardas acumulan? (210 yd = 2+3 ó 3) | box score real con juego de 200+ | motor de scoring |
| P5 | D/ST: ¿escalones de pts/yds permitidos? | dump API | valuación D/ST |
| P6 | FG 50+ | dump API | valuación K |
| P7 | Banca e IR exactos | dump API | profundidad del draft |
| P8 | ¿Settings 2025 == 2026? | dump de AMBAS temporadas | la validación al decimal usa las reglas del año validado |
| P9 | Semántica de "OP" (¿admite QB/RB/WR/TE?) y de FLEX | dump API (lineupSlotCounts) | baselines VBD |

## SUPUESTOS DEL CANAL (CLAUDE.md III.10 — la última milla)
- El draft se opera EN la sala de ESPN con 45 s/pick: la hoja impresa es el
  artefacto final. Su candado: simulacro de draft completo contra la hoja
  ANTES del 7-sep (¿se decide un pick en <45 s con ella? ¿sobrevive picks
  fuera de guion?). El "recibo" del draft = roster final en ESPN vs plan.

## DISCREPANCIAS DETECTADAS (fuente vs prompt)
| # | Ítem | Prompt dice | App dice (screenshot 10-ago) | Resolución |
|---|---|---|---|---|
| D1 | Número de equipos | 16 | **14** ("Peace and Love", ID 2107128204) | El dump 2026 manda. Si son 14: cambian TODOS los baselines (28 slots QB, no 32), la secuencia snake (R2=pick 19, no 23) y la estructura de playoffs (¿8 de 14?). H1 se recalcula. |
| D2 | Máx QBs rosterables | no mencionado | "QB 1 (4 max)" | Relevante para estrategia de acaparar QBs en superflex: techo de 4 |

## RESOLUCIONES TAREA 0 (dump crudo 2026, 10-ago — config/espn_settings_2026.json)
| # | Resolución | Valor |
|---|---|---|
| P1 | ✅ **El sack IDP SÍ puntúa: +2.0** (override por posición DE/LB/DL/CB/S; D/ST +1) | **La premisa de H4 es FALSA** |
| P2 | ✅ INT IDP = +3.0 (override) | — |
| P3 | ✅ Passing: **1 pt / 25 yds** (¡no /10!), TD +6, INT **−3**, 300-399 +3, 400+ +4, **+0.1 por pase completado** | recalcula H1 |
| P5 | ✅ D/ST **SÍ tiene escalones de puntos permitidos**: 0→+20, 1-6→+7, 7-13→+4, 14-17→+1, 18-21→+1, 22-27→0, 28-34→−1, 35-45→−4, 46+→−4. Sin escalones de yardas | el screenshot del prompt estaba incompleto |
| P6 | ✅ FG 50+ = **+5** (0-39: +3/−2, 40-49: +4/−1, PAT +1/−1) | — |
| P7 | ✅ **Banca = 4** + IR 1 (¡finísima para 16 equipos!) | cambia estrategia de profundidad |
| P9 | ✅ Slots: QB,RB×2,WR×2,TE,FLEX,OP,LB,DL,DB,D/ST,K + BE×4 + IR | confirma 13 titulares |
| P8 | ✅ **La liga NO existió en 2025** (404) → no hay box scores propios para el candado de Fase 1.4 | plan B de validación (abajo) |

## NUEVOS PENDIENTES
| # | Ítem | Cómo se resuelve |
|---|---|---|
| P4 | ¿Bonos de umbral acumulan? (210 yd = 2+3 ó 3) | box score real (semana 1) o liga vieja del usuario |
| P10 | Semántica de tackles: 109 "Total Tackles" +1 Y 107 "Assisted" +0.5 — ¿un asistido paga 1.5? ¿el solo está dentro de 109? | validación empírica contra box score IDP |
| P11 | ¿El sack alimenta también TK(109) y Stuff(112)? (sack = ¿2+1+1=4 efectivos?) | ídem — decide el valor real de los edge |
| P12 | Mapa exacto de position-ids en overrides (9..13) | objeto player de la API (defaultPositionId) |
| D1 | 14 equipos hoy; usuario confirma que serán 16 | **tripwire pre-draft**: re-dump y verificar size=16 |

## PLAN B DE VALIDACIÓN (sin historia de liga propia)
1. Suite sintética exhaustiva del motor (todos los ítems, bordes de umbral).
2. ¿Andrés participa en OTRA liga ESPN con historia? → validar el motor contra
   sus box scores reales (pregunta de segundos).
3. Semana 1 (9-sep) = validación en caliente jugador por jugador, a 2 días del
   draft NO sirve para el draft → por eso 1 y 2 son críticos antes.

## VALIDACIÓN DEL MOTOR (10-ago) — vía kona_player_info
**Descubrimiento clave:** la API de la liga 2026 expone la temporada REAL 2025
de cada jugador YA PUNTUADA por ESPN bajo NUESTRAS reglas (statSourceId=0,
seasonId=2025, appliedTotal) + stats crudas por statId. Eso reemplaza (y
supera) la validación contra liga vieja: mismo ruleset, matemática de ESPN.

Reconstrucción exacta (fórmula: Σ raw[statId] × pts_override[posId]):
| Jugador | ESPN | Motor | |
|---|---|---|---|
| Myles Garrett (DE) | 136.5 | 136.5 | ✅ |
| Maxx Crosby (DE) | 143.5 | 143.5 | ✅ |
| Jahmyr Gibbs (RB) | 370.0 | 370.0 | ✅ |
| Puka Nacua (WR) | 380.0 | 380.0 | ✅ |

## RESOLUCIONES P4 / P10 / P11
- **P10 ✅**: "Total Tackles"(+1) y "Assisted"(+0.5) aplican AMBOS → tackle
  solo = 1.0, asistido = 1.5 efectivo.
- **P11 ✅**: el sack vive DENTRO de los crudos de tackle y stuff además de su
  ítem propio → **sack ≈ 4 pts efectivos** (2 sack + 1 tackle + 1 stuff).
  Garrett (23 sacks) hizo 136.5: los edge élite compiten con LB de volumen.
  H4 queda INVERTIDA respecto al prompt.
- **P4 ✅ (semántica de labels + crudos de Gibbs)**: bonos de TD apilan por
  definición (50+ ⊂ 40+: un TD de 50+ paga 1+2=3); los umbrales de juego son
  RANGOS DISJUNTOS (100-199 vs 200+): un juego de 210 yd paga SOLO +3 (no 2+3).
  Cross-check final vs game-log nflverse en el candado masivo de Fase 1.
- **CANDADO DE FASE 1 definido**: reconstruir el appliedTotal 2025 de TODOS
  los jugadores relevantes (~top 400 + IDP) y exigir cuadre al decimal; luego
  el mismo motor sobre stats nflverse debe reproducir los crudos de ESPN.
- Liga vieja COLOMBIAN UNDERDOGS: ya NO necesaria para validación (reglas
  distintas < validación con reglas exactas). Queda como opcional.

## CORRECCIÓN a P5 (11-ago, validada vs Texans D/ST 140.0)
Los escalones de points-allowed (89-92, 121-125) existen en la config con
puntos base PERO el override de la posición 16 los anula: **el D/ST paga
SOLO eventos** (sack 1, INT 3, FR 3, safety 2, bloqueo 2, TD retorno 6).
El prompt original tenía razón; mi lectura del dump del 10-ago aplicó los
puntos base sin el override. Causa raíz: sintetizar sin correr el desglose
por posición. Regla: todo reporte de scoring sale del DESGLOSE del motor
validado, no de leer la tabla a ojo.

## EVENTO MAYOR 12-ago: tripwire cazó re-configuración COMPLETA de la liga
- **size 14→16 ✅** (D1 resuelta: los 16 están, payouts los nombra a todos)
- **Scoring v1 (55 items) → v2 (75)**: first downs +0.2, INC −0.05, sacked −0.1,
  2pt divididos, FG realista (60+ = +6, corto fallado −3), **Solo Tackle +1.5
  ADEMÁS del Total +1 → solo=2.5 efectivo, asistido=1.5**; FF 2→1; sack IDP
  sigue 2 (override); **D/ST v2: escalones de PA SÍ pagan (shutout +20, 46+ =
  −6) + <100 yardas +5 + hay items de MARGEN DE VICTORIA (161-166, hasta +10)**
  → verificar a quién acreditan (¿D/ST?) con box scores del corpus v2.
- **Roster nuevo: QB/RB/RBWR×2/WR/TE/OP/DT/DE/LB/CB/S/DST/K + BE4 + IR** —
  5 slots IDP por posición específica (DT es el cuello de botella: 16 titulares
  interiores). Baselines VBD a rehacer por completo.
- **Motor re-validado bajo v2: 1801/1801 al decimal.** Tripwire re-baselined.
- ⚠️ DISCREPANCIA VIVA: draft = 27-ago según Andrés; el app dice 8-sep.
  Gobierna la palabra de Andrés para el plan; tripwire vigila el campo.
- Corrección de mi corrección: "D/ST solo eventos" era cierto en v1; v2 lo
  cambió. Sin tripwire habríamos valuado D/ST con reglas muertas.

## 13-ago: discrepancia de fecha RESUELTA
27-ago = sorteo del ORDEN; draft = 7-sep (app tenía razón desde el inicio;
ambas fuentes cuadran). Hito nuevo en el plan: 27-ago llega el pick.

## 13-ago: S1 (baseline QB) CONFIRMADO por Andrés + cambio de tackles EN EL AIRE
- **S1 resuelto ✅ (dato de Andrés):** la liga suele alinear ~30 QBs y los
  managers prefieren gastar banca en QB suplente antes que alinear 1 solo.
  Baseline QB30 pasa de ⚠️ SUPUESTO a dato del dueño de la liga. La
  sensibilidad QB28/QB32 queda como colchón, ya no como incógnita central.

SUPUESTO/INCÓGNITA #T1: regla de tackles POST-cambio del commish
- QUÉ: en el chat de la liga preguntaron por el doble pago (Solo 1.5 + Total
  1.0 = 2.5 por solitaria). Commish: "creo que toca quitar el total. es decir
  solo 1 punto". La frase es AMBIGUA (3 lecturas):
    A) quitar Total, queda Solo 1.5  → solitaria 1.5 / asistida 0
    B) quitar Solo, queda Total 1.0  → toda tacleada 1.0
    C) "Solo, 1 punto": quitar Total y bajar Solo a 1.0 → 1.0 / 0
- POR QUÉ NO HAY INFO: decisión futura de un tercero → ❓ INCOGNOSCIBLE.
- COSTO SI ESTÁ MAL: LB top pierde 37-59 pts de VBD según lectura (Cashman
  390→209/239/159 proj). NO cambia el top-10 global (QB/RB/WR intactos) pero
  mueve a los IDP 1-2 rondas más tarde y en C el DT1 pasa a ser el 1er IDP.
- SENSIBILIDAD: corrida completa en scratchpad/escenarios_tackle.py (13-ago).
  Veredicto: la decisión de las rondas 1-3 NO cambia; la estrategia IDP sí.
- CADUCIDAD: cuando el commish edite la config, check_settings.py TRUENA →
  ese día se re-acepta baseline, se re-valida el candado masivo y se regenera
  vbd. NO draftear IDP con tabla vieja si el tripwire sonó.

## 19-ago: tres pendientes del reglamento v2 RESUELTOS (corpus + candado)
- **Margen de victoria (161-166): INERTES ✅.** Configurados (+10…+1, DB
  excluido) pero NINGÚN jugador/D/ST acumula esos statIds en todo el corpus
  (2,000 jugadores, 2025 real y 2026 proyectado). Prueba fuerte: el candado
  reproduce el appliedTotal de ESPN 1801/1801 sin que aporten un punto.
  Residual: cross-check contra el boxscore real de la semana 1 (candado
  semanal ya planeado).
- **Semántica de tackles ✅ (107+108=109 exacto en Garrett/Crosby/Cashman):**
  107 asistidas (+0.5) · 108 solitarias (+1.5) · 109 total (+1.0) →
  solitaria 2.5, asistida 1.5 efectivas.
- **Sack v2 ✅:** ítem 99 (+2 DL/LB) + solitaria arrastrada (2.5) = ~4.5
  efectivo. El "stuff" ya no suma al sack de jugador: el ítem 97 solo lo
  acumulan los D/ST (v1 pagaba 112; v2 lo eliminó).
- **Tests reescritos a v2: 13/13** con fixtures = appliedTotal reales
  (Garrett 183.0, Crosby 185.5, Cashman 284.0, Texans D/ST 211.0).
- **Corrección a la ficha T1 (causa raíz + regla):** en la prosa de los
  escenarios de tackles describí la asistida sin el ítem 107 (dije "asistida
  0" en A/C; es 0.5, y en B quedaría 1.5 > solitaria 1.0 — lectura B luce
  perversa e improbable). Los NÚMEROS de la tabla no cambian (el motor corrió
  con todos los ítems); solo la anotación verbal era incompleta. Regla: toda
  descripción de reglas sale del desglose por ítem del motor, incluso en
  prosa de escenarios.

## 19-ago: PROYECCIÓN v2 — overlay de partidos jugados (VALIDADO walk-forward)
- **Sesgo del mercado MEDIDO ✅:** ~100% de jugadores relevantes proyectados
  a 17 juegos (statId 210 = games played, verificado con Crosby 15/Cashman 13
  reales 2025). Realidad 2022-2025: élite ~14, P(16+) ~50%.
- **Factor VALIDADO 📊:** per-juego × E[g|pos,tier,edad] reduce MAE 21.9% vs
  ×17 en walk-forward 2023/24/25 (n=675), mejora los 3 años sin excepción.
- **Auditoría del propio modelo (III.12):** probé 2 variantes "mejores"
  (tier por-juego; + flag lesión) contra el simple en comparación PAREADA
  (n=585): M1 54.4 vs M3 54.6 vs M2 54.8 — indistinguibles. Se queda M1
  (el validado). La intuición de que sobre-castigaba a élites lesionados
  (Lamar/Burrow E[g]=9.6) NO sobrevivió la verificación → no se parchea.
- SUPUESTO S4: eficiencia por-juego del mercado insesgada (no testeable sin
  archivo de proyecciones históricas; solo corregimos el componente probado).
- SUPUESTO S5: E[g] por grupo (pos, tier producción 2025 bajo nuestras
  reglas, edad≥29); rookies QB por ronda draft (13.3/7.2/5.1), resto media
  posicional. Élites con 2025 corto quedan en tier B: en la hoja de draft se
  reportan con RANGO (E[g] tier B vs tier A), no punto único.
- SUPUESTO S6: D/ST E[g]=17; K default 16 si falta data.
- Fórmula: VBD2 = E[g] × (pg − pg_baseline) — un juego perdido cuesta la
  ventaja sobre el reemplazo, no los puntos completos. Motor lineal → escalar
  total por E[g]/g_proj es exacto.
- Salida: optimize/proyeccion_v2.py → data/vbd_v2.csv (1,231 jugadores).

## 19-ago (2): historia extendida a 2010-2025 + modelo jerárquico (pedido de Andrés)
- Andrés: "el modelo tiene que ir mucho más allá de 2023" → ingesta extendida
  a 287,184 jugador-semanas (16 temporadas, ingest/nflverse_extend.py).
  Pre-2021 se normaliza por temporada de 16 juegos (fracción perdida).
- **Estudio de ventana (pareado, test 2014-2025, n=2,771):** el factor es
  ESTACIONARIO — mejora +12% a +28% los 12 años, y da igual entrenar con
  toda la historia que con 3-5 años (MAE 56.2/56.0/56.0). Se usa TODA la
  muestra: no cambia el agregado pero habilita celdas finas con n>=8.
- **"Condicionado a quiénes se parecían a ellos" (Andrés):** con n grande,
  el modelo fino (pos, tier POR-JUEGO, lesión 4+ previa) ya no pierde vs el
  grueso (55.7-55.8 vs 56.0 pareado) y corrige los casos de decisión:
  QB élite-pj lesionado (n=21): 13.7 juegos → Burrow 13.7, no 9.6.
  QB mediocre-pj lesionado (n=130): 8.6 → esa celda contaminaba a los élite.
- **Celda 'corto' nueva (auditoría propia):** jugó 1-7 juegos siendo titular
  → QB 9.1 (n=24, mediana ≤7!), RB 10.1, WR 11.8, TE 11.7. Antes caían a un
  fallback "sano" demasiado generoso (Daniels 7 juegos ahora E[g]=9.1).
- **Casos frontera declarados (van con RANGO en la hoja de draft, no punto):**
  Lamar (QB #16 por-juego 2025, a 4 puestos del tier A: 8.6 vs 13.7) y
  Bo Nix (#13 por-juego, a 1 del tier A: 12.6 vs 14.9). No se doblan los
  cortes para nombres propios: eso sería overfitting con cara de favor.
- Dato curioso auditado: hay DOS "Lamar Jackson" en el corpus (el QB y un
  DB retirado con applied=0); no era duplicado, son ids distintos.

## 19-ago (3): capa de DISTRIBUCIONES (piso/techo) — CALIBRADA ✅
- Diseño: centro del cono = mercado (pg × E[g] v2.1); ancho = historia:
  G bootstrap de juegos reales de la celda + M forma de la dispersión
  año-a-año del por-juego por (pos, tier), mediana normalizada a 1.
- SUPUESTO S8: M ⊥ G (correlación lesión→rendimiento ignorada; sesgo
  compensado por medir M contra predictor débil). Se valida por RESULTADO:
- **CANDADO DE CALIBRACIÓN: p10-p90 cubre el 81.9% de los casos reales
  2020-2025 (n=967) con celdas estimadas solo con 2011-2019.** Dentro del
  objetivo 80±5. El script TRUENA y se niega a generar el CSV si se sale.
- Salida: optimize/distribuciones.py → data/proyeccion_dist.csv (p10/p25/
  p50/p75/p90 por jugador).
- Lecturas clave: el PISO de Allen (p10=235) supera la MEDIANA de casi
  todos los RB/WR → argumento cuantificado del QB temprano. Nix y Dart:
  p10 de 84-87 (cola de banca visible). Los RB élite tienen conos anchos
  (Gibbs p10=137 / p90=530): la ronda 1 RB es más lotería que la ronda 1 QB.

## 27-ago: SORTEO + 🚨 TRIPWIRE (roster v3) + simulador de sala
### Orden del sorteo (por chat de Andrés) y ⚠️ DISCREPANCIA CON LA APP
Orden dictado: 1 Ferchos · 2 Jaime · 3 Nich · 4 Luisca · **5 POCHO** · 6 Diego
(+1000 waiver) · 7 Santi A · 8 Sergio · 9 Brian · 10 Rodrigo · 11 Gabriel ·
12 SteveO · 13 Esguerra · 14 Kike · 15 James B · 16 Santi Gut.
- ⚠️ **La app AÚN NO tiene ese orden**: `pickOrder` = ids 1..17 en orden
  (default), lo que pone a 'No Team for Old Men' (id 10 = Pocho) en el
  puesto **9**, no en el 5. El plan entero depende de esto.
- BLOQUEO (V.18): antes del draft hay que VER en la app que Pocho está 5º.
  El tripwire ya vigila `pickOrder` y `mi_pick` y truena cuando el commish
  cargue el sorteo → ese día se re-corre el plan con el pick real.
- ✅ verificado en la app: 18 rondas (288 picks), SNAKE, 45s, fecha
  2026-09-07 19:00 COL, mi teamId = 10.

### 🚨 TRIPWIRE SONÓ: roster v2 → v3 (el commish cambió la alineación)
- **RB/WR flex 2 → 1 · WR 1 → 2** (scoring IDÉNTICO: 75 ítems, motor sigue
  validado 1801/1801 y tests 13/13).
- Consecuencia en baselines (titulares semanales de 16 equipos):
  RB 35 → **26** · WR 29 → **38** (QB sigue 30 ✅ confirmado por Andrés).
  Efecto: la WR se volvió MÁS valiosa y la RB menos. Tablero re-generado:
  Nacua #2, Chase #5, JSN #9 suben; Gibbs #4, Bijan #8, McCaffrey #12 bajan.
- Sin el tripwire habríamos llevado al draft un tablero con reglas muertas
  (repetición exacta de la cicatriz #5 del Mundial). Snapshot re-aceptado.

### BUG PROPIO detectado y corregido: conos degenerados en IDP/K
- nflverse solo calcula `fantasy_points` para OFENSIVA; IDP y K salían en 0
  → mi filtro `fp>0` descartaba TODAS sus filas → las celdas quedaban vacías
  → los conos salían con piso = techo (Cashman "321/321": riesgo cero, falso).
- Fix: métrica de producción POR GRUPO (ofensiva = PPR; IDP = tacleadas
  ponderadas 2.5/1.5; K = FG convertidos). Calibración ahora por grupo:
  ofensiva 82.6% (n=967) · IDP 79.1% (n=2043) · global 80.3% (n=3010).
- El modelo de E[juegos] NO estaba afectado (no filtra por producción).
- Regla nueva: toda métrica importada se verifica POR GRUPO de posición
  antes de usarse como filtro — un 0 puede significar "no aplica", no "malo".

## 27-ago (2): H1 REFUTADA + bug de homónimos + regla de draft validada
### ✅ HALLAZGO MAYOR: el slot OP NO es superflex de QB
`eligibleSlots` de Puka Nacua (WR) incluye el slot **7 (OP)**; también RB y
TE. El OP admite CUALQUIER ofensivo → **no hay obligación de tener 2 QBs**.
- Refuta la premisa de H1 del prompt fundacional ("el QB manda porque el OP
  obliga a un segundo QB"). El QB sigue siendo la posición de más puntos,
  pero la liga solo EXIGE uno; el 2º QB es opcional y compite con un WR.
- El baseline QB30 SIGUE válido: mide cuántos QB se alinean de hecho
  (Andrés: "~30"), que es conducta de la sala, no obligación del roster.
- Mi simulador forzaba 2 QBs por equipo (OBLIG QB=2). Corregido a mínimos
  por posición (12) + mínimo de 7 ofensivos totales = 14 titulares.

### BUG: unión por NOMBRE con 8 homónimos en el corpus
`adp[fullName]` hacía que el homónimo sobreescribiera al bueno:
**Justin Jefferson WR ADP 12.2 → 170.5 (un LB)**, Lamar Jackson QB 39.2 →
169.6 (un CB), Chris Jones, Byron Young, etc. La sala simulada los ignoraba
por completo → curvas de disponibilidad falsas. Fix: unir SIEMPRE por
espn_id. Regla nueva: ninguna unión por nombre entre fuentes; si no hay id,
se declara y se verifica la unicidad antes de usarla.

### REGLA FINAL DEL DRAFT (validada pareada, 100 drafts × 4 escenarios)
> pick 5 = mejor WR · pick 28 = QB si sobrevive uno con VBD ≥ 110, si no WR.
- media 756 · peor escenario 717 (vs WR-WR fijo 744/666; QB-RB 655/571).
- Nunca pierde contra WR-WR y gana 92% pareado cuando no hay corrida de QB.
- Sensibilidad del split de flex (60/40, 50/50, 80/20, 100/0): Nacua es #2
  del tablero en todas; la decisión del pick 5 no depende del supuesto.
- 🚨 BLOQUEO ACTIVO: la app aún muestra el orden default (Pocho 9º). No se
  draftea sin confirmar el pick 5 en la app; el tripwire vigila pickOrder.

## 27-ago (3): CORRECCIÓN de Andrés — la liga vieja YA era superflex
- Andrés: "los 17 QBs es porque era liga con superflex, hasta 2 QBs".
  ✅ VERIFICADO en los settings rescatados (fuente, no memoria):
    2023: "Quarterback / Running Back / Wide Receiver / Tight End: 1" → SÍ
    2024: sin ese slot → NO
    2025: SÍ
  QBs en R1-R3: 2023 = 21/16 eq (1.31/eq) · 2025 = 17/14 (1.21) · 2024 = 5/16
  (0.31). **El "año anómalo 2024" que yo había marcado NO era anomalía: era
  el año sin OP.** La conducta de la sala sigue la regla con precisión —
  validación fuerte del modelo de sala.
- Consecuencia: mi grilla de escenarios estaba MAL CENTRADA (yo asumí que el
  centro era 24-30 QBs). El centro medido para 2026 (16 eq) es ~20.
  Nueva grilla: 16 / **20 (medido)** / 26 / 20+IDP-aware.
- **La recomendación NO cambió** al recalibrar: wr-cond110 sigue ganando
  (media 708, peor 668) e iguala a WR-WR salvo en el conservador (+50).
- Nota metodológica: el error no cambió la decisión porque la regla es
  CONDICIONAL — se adapta al estado real de la sala en vez de apostar a un
  escenario. Esa es la razón de preferir reglas condicionales a fijas.

## Cómo se usa el ADP (y por qué su sesgo 1QB no contamina)
- El ADP de ESPN es de su población general (12 eq, 1 QB, sin IDP). **NO
  entra en nuestra valuación** (VBD sale 100% de stats crudas × motor
  validado × baselines del roster real).
- Se usa SOLO para modelar el tablero del RIVAL: score = 0.55×rank_ADP +
  0.45×rank_proyección (lo que la app les muestra puntuado con las reglas).
- El sesgo 1QB se corrige con `qb_bonus`, que desplaza el BLOQUE de QBs de
  forma uniforme (preserva su orden relativo, que el ADP sí acierta) hasta
  reproducir la conducta MEDIDA de esta sala (~20 QBs en R1-R3). Es mejor
  ancla que un ADP superflex genérico: es ESTA sala, no la población.
- Los IDP no tienen ADP útil → entran por proyección + `idp_pen` calibrado
  al "primer IDP en ronda 10" medido en 2023-2025.

## 28-ago: ✅ BLOQUEO LEVANTADO — orden cargado y verificado en la app
- `pickOrder` = [13,7,1,17,10,2,15,4,16,3,11,8,14,12,9,5]; teamId 10 (Pocho)
  en posición **5** ✅. `draftDetail` da mis 18 picks globales idénticos a los
  que calculaba mi snake → validación cruzada de la implementación.
- **Modelo de sala POR ASIENTO** (pedido de Andrés: "¿usas la historia de cada
  uno?"). Antes los 15 rivales eran clones. Ahora cada asiento lleva su avidez
  medida de QB/IDP en las temporadas COMPARABLES (con slot OP: 2021, 2022,
  2023, 2025 — 2024 no lo tenía). Pesos normalizados a media 1: redistribuyen,
  no inflan la calibración agregada (19-20 QBs en R1-R3).
  Extremos: Luis Carlos 1.39 (1er QB siempre en R1) · Brian 0.66 (R4.8).
- **Regla revalidada con perfiles individuales: NO cambia.** wr-cond110 media
  707, peor 673 (vs wr-wr 693/665, wr-qb 664/628). Tercera vez que la
  recomendación sobrevive un cambio del modelo — por ser condicional.
- ⚠️ SUPUESTO NUEVO (asientos 4 y 16): 14/16 asientos se auto-verifican con
  los nombres de equipo de la app. Faltan dos: el asiento 4 es "Amanecera y
  veremos" (esperaba a Luis Carlos = "The Nest" en 2025) y el 16 es "The
  Nest". COSTO SI ESTÁ MAL: el asiento 4 pica justo antes de mí y Luis Carlos
  es el más ávido de QB (w=1.39) — afecta quién sobrevive a mi pick 5.
  CADUCIDAD: preguntado a Andrés; si no responde, se verifica el día del
  draft con los primeros picks reales.

## 28-ago (2): asientos 4 y 16 RESUELTOS ✅ — mapeo 16/16 cerrado
Andrés confirma: "Amanecera y veremos" (asiento 4) = Luis Carlos, que solo
renombró su equipo (era "The Nest" en 2025); "The Nest" (asiento 16) es Santi
Gut, nuevo. El ASIENTOS de managers.py ya era correcto — no hay cambio de
código. Queda como ejemplo de por qué se verifica en vez de asumir: la
coincidencia de nombre de equipo era una pista FALSA (dos equipos distintos
con el mismo nombre en años distintos).
NO QUEDAN SUPUESTOS ABIERTOS sobre la estructura del draft. El único ítem
vivo del reglamento es la ficha T1 (cambio de tackles del commish), vigilada
por el tripwire.

## 28-ago (3): AUDITORÍA COMPLETA DEL REGLAMENTO (pedido de Andrés)
Andrés: "revisa qué reglas locales tiene nuestra liga; recuerda que los TD de
QB valen 6 así sean de pase". ✅ Confirmado (statId 4 = 6.0) y auditados los
75 ítems, identificando cada uno EMPÍRICAMENTE. Doc: docs/REGLAMENTO.md.
- 🔴 **HALLAZGO NUEVO — el FG de 50+ paga DOBLE**: los ítems 74 ("FG 50+",
  5 pts) y 198 ("FG 50-59", 5 pts) SE SUMAN → un FG de 50-59 vale **10 pts**;
  uno de 60+ vale 74(5)+201(6) = **11 pts**. Verificado con Aubrey: 113 de
  sus 235 puntos de 2025 salieron solo de FG de 50+. El motor ya lo aplicaba
  (por eso el candado cuadraba), pero NADIE lo había leído: el pateador de
  pierna larga vale mucho más de lo que dice cualquier ranking público.
- Peso de las reglas NO estándar sobre los puntos reales de 2025:
  LB 47% · DT 46% · S 44% · CB 40% · DE 40% · **QB 33%** · K 19% ·
  RB 9% · WR 8% · TE 6%. Ahí vive el edge aritmético de la tesis.
- Mapeo de kickers resuelto: 80=FG 0-39 · 77=40-49 · 198=50-59 · 201=60+ ·
  74=50+ (acumulativo) · 86=PAT · 76/79/82/200/203=fallos por tramo.
- Confirmado además: TD de pase 6 (estándar 4) · INT lanzada −3 (estándar −2)
  · completos +0.1 / incompletos −0.05 · primeros downs +0.2 (las tres, muy
  raras) · sack recibido −0.1.

## 28-ago (4): ARCHIVO PROPIO iniciado + corrección sobre ADP superflex
- ⚠️ **CORRECCIÓN a Andrés (asumió que teníamos ADP superflex histórico):**
  NO EXISTE. Verificado: FFC solo tiene standard/ppr/half-ppr/**2qb**/dynasty
  (`format=superflex` → HTTP 400); FantasyPros redirige sus URLs de ADP
  superflex al ADP general (302). Lo único superflex histórico es **ECR**
  (ranking de expertos, no mercado), 2021-2025, vía DynastyProcess.
  → Ventana de validación: ECR superflex 2021-2025 como tablero de mercado;
  ADP 2QB 2014-2025 como chequeo de robustez, declarado como PROXY.
- Novatos: el hueco NO es del mercado (su ADP/ECR sí los incluye) sino de MI
  proyección, que se construye del año anterior y por tanto no puede rankear
  a un novato. Solución acordada: tablero híbrido (mi proyección donde hay
  datos + ranking de mercado para novatos).
- **ARCHIVO ARRANCADO** (ingest/archivo.py): snapshot fechado y hasheado de
  ESPN (1,403 proyecciones + rankings + ADP + crudos), FantasyPros ECR
  superflex (14,492 filas) y FFC ADP 2QB (246). Primer corte: 2026-08-28.
  Motivo: no existe archivo público auditable de proyecciones históricas;
  en dos temporadas tendremos el track record que nadie publica.
- Triangulación 2026 (tres fuentes independientes del mercado superflex):
  diferencia mediana ESPN vs FantasyPros = 10 puestos en el top-80.
  FantasyPros adelanta a los QB de segunda línea (Caleb #8 vs ESPN #38,
  Herbert #10 vs #39, Goff #30 vs #79) — **y NUESTRO tablero coincide con
  FantasyPros, no con ESPN** (Caleb #20, Herbert #17, Goff #19). Dos rutas
  independientes llegando a lo mismo.

## 28-ago (5): FASE A DEL BACKTEST — resultados, con malas noticias propias
### ✅ La tesis fundacional SE VALIDA (2025, prueba directa)
Re-puntuar las proyecciones crudas de ESPN con NUESTRAS reglas vs el ECR
superflex del mercado, calificado contra los puntos REALES de 2025:
  mercado ECR ......... rho 0.730 · top24 7,121 · top48 13,947
  ESPN re-puntuada .... rho 0.768 · top24 7,827 (+9.9%) · top48 14,674 (+5.2%)
El edge aritmético es REAL y medible. Primera vez que se prueba.

### 🚨 MALA NOTICIA: nuestra corrección de juegos EMPEORA el ordenamiento
  + corrección de juegos ... rho 0.760 · top24 7,369 (−458) · top48 13,640 (−1,034)
Causa raíz: la validamos con la métrica EQUIVOCADA. El walk-forward midió
MAE del TOTAL de puntos (−21.9%, cierto), pero para draftear lo que importa
es el ORDEN, no el nivel. Un recorte que mejora el nivel puede empeorar el
orden si el recorte varía por celda con ruido. Regla nueva: **validar cada
capa contra la métrica de la DECISIÓN, no contra una métrica cómoda.**

### 🚨 Y mi métrica también estaba sesgada (auto-auditoría)
"Puntos capturados en el top-K" premia a los tableros que cargan de QB. El
tablero re-puntuado sin corrección pone **24 QBs en su top-24** — captura
mucho VBD (3,973 vs 3,169 del mercado) pero sería un desastre en un draft
real, donde solo se alinean 1-2 QB. El top-24 REAL por VBD tuvo 14 QB / 5 RB
/ 4 WR / 1 TE. → Ninguna métrica sin restricción de roster decide esto:
**solo la Fase B (simular drafts con roster real y calificar con puntos
reales) resuelve qué tablero y qué política sirven.**

### ⚠️ CONSECUENCIA GRAVE: la recomendación WR-primero queda EN DUDA
La regla WR-cond110 se eligió simulando con NUESTRO tablero (el corregido).
Si la corrección de juegos deshinfla a los QB de más, la función de valor de
esa simulación estaba sesgada y la conclusión puede darse vuelta. NO se
draftea con la regla actual hasta que la Fase B se pronuncie.

### Backtest proxy 5 temporadas (2021-2025, tablero del año anterior)
  mercado ECR .. rho 0.739 · top24 37,856 · top48 67,775 · top96 115,839
  mío .......... rho 0.705 · top24 38,778 · top48 66,120 · top96 109,387
  híbrido ...... rho 0.718 · top24 39,303 · top48 66,058 · top96 111,299
Patrón: nuestro tablero gana en la ÉLITE (top-24: +3.8% el híbrido) y pierde
en PROFUNDIDAD (el mercado ve novatos, lesiones y cambios de equipo).
Bug propio corregido en el camino: el híbrido mandaba a los novatos al final
en vez de intercalarlos en su puesto de mercado.

## 28-ago (6): 🚨 HALLAZGO MAYOR — a nivel ROSTER, ningún tablero predice
Andrés pidió dar valor a la banca. Al intentar CALIBRARLO (no inventarlo)
apareció algo mucho más grande.

### La maquinaria está bien: prueba del oráculo
Usando como tablero los PUNTOS REALES de la temporada, la correlación entre
valor proyectado del roster y puntos reales es **0.93** (2023, 2024, 2025).
El simulador de liga funciona.

### Pero los tableros no predicen el resultado de un ROSTER
Correlación (192 rosters por año) entre valor proyectado y puntos reales:
| tablero | 2023 | 2024 | 2025 |
|---|---|---|---|
| oráculo | +0.94 | +0.93 | +0.94 |
| mercado (ECR condicionado a nuestras reglas) | +0.21 | +0.17 | +0.10 |
| proxy (año anterior) | +0.21 | **−0.22** | +0.08 |
| **NUESTRO SISTEMA REAL (ESPN re-puntuada)** | — | — | **+0.16** |

R² ≈ 0.02-0.04: el tablero explica entre el 2% y el 4% de la variación del
resultado de un equipo. Coherente con la evidencia externa (proyecciones
explican 14-26% a nivel JUGADOR; al agregar 7 titulares y repartir el talento
entre 16 equipos, casi todo se cancela).

### 🚨 Y peor: optimizar duro sobre un tablero ruidoso HACE DAÑO
En el draft 2024 examinado, mi equipo (política motor) tenía el valor
proyectado MÁS ALTO de los 16 (787 vs media ~350) y terminó **por debajo del
promedio** en puntos reales. Es sobreajuste al ruido: la política explota los
errores del tablero, no su señal.

### Consecuencias que hay que asumir
1. La calibración de δ (valor de la banca) NO se puede hacer con esta señal:
   con correlaciones de 0.1-0.2 el óptimo es indistinguible de 0. Queda
   ⚠️ ABIERTO. (Además había un bug: con VBD la banca suele ser negativa, así
   que sumarla con δ>0 restaba; hay que pisar en 0 antes de ponderar.)
2. Las diferencias entre POLÍTICAS van a ser pequeñas frente al ruido. La
   comparación pareada sigue siendo válida, pero hay que reportar intervalos,
   no puntos, y aceptar que el resultado puede ser "empatan".
3. Para el draft real: **la humildad es el hallazgo**. El tablero sirve para
   evitar errores grandes (no tomar al RB #40 en la ronda 2), no para exprimir
   ventajas de 5 puntos. Y perseguir el máximo del tablero es contraproducente.

---

## 28-ago (7): ⛏️ AUTOPSIA DEL "FRACASO" — eran DOS errores míos, no del método

Andrés no entendió el reporte anterior y con razón: mezclé unidades y saqué
la conclusión equivocada. Se rehizo la medición. Correcciones:

### ❌ Error 1 — comparé peras con manzanas (unidades)
Reporté "valor proyectado 787, puntos reales 1268" como si fueran la misma
vara. No lo son:
- **787 = VBD proyectado** (valor sobre el reemplazo, sumado sobre 7 slots).
  Es una medida RELATIVA; su cero es arbitrario.
- **1268 / 1400 = puntos reales** de temporada. Medida ABSOLUTA.
Sumar VBD entre posiciones y compararlo contra puntos crudos produce una
paradoja de Simpson: un QB con VBD 0 hace ~300 pts y un TE con VBD 0 hace
~120. Por eso salía correlación NEGATIVA (−0.28). Medido manzana con manzana
(VBD proyectado vs VBD real) el signo se corrige.

### ✅ La hipótesis de Andrés era correcta: "787 será porque es solo ofensiva"
Sí — y también el número de puntos. Medido sobre 2025 con nuestras reglas:

| bloque | pts del equipo promedio, temporada completa |
|---|---|
| 7 slots ofensivos (QB/RB/RBWR×2/WR/TE/OP) | ~1847 |
| 5 slots IDP (DT/DE/LB/CB/S) | ~743 |
| **IDP como % de ofensiva+IDP** | **29%** |

La simulación da ~1400 por equipo = 7 slots × 14 semanas. Escalado a 17
semanas y sumando IDP+K+DST da ~2400, que cae dentro del PF real de la liga
en 2025 (**2258 – 2585**, standings rescatados). **La simulación no está
baja por un bug: le faltan slots a propósito.**

⚠️ PENDIENTE DE CORROBORAR (no puedo yo): Andrés recuerda "~1400 puntos
reales" el año pasado. El PF histórico de esta liga es 2100-2600 desde 2021.
Solo rescatamos el top-3 de cada temporada, así que su PF 2025 no está en
nuestros datos. **Necesito que confirme de dónde sale ese 1400** (¿otra app?
¿otra métrica?) antes de usarlo para calibrar nada.

### 🚨 Error 2 — EL HALLAZGO DE VERDAD: mi tablero proxy es el eslabón malo
Al medir cada tablero por separado sobre el universo de 260 jugadores que se
draftean, contra puntos reales:

| tablero | jugador r | rho | ROSTER r |
|---|---|---|---|
| **ESPN pretemporada + nuestras reglas** (2025) | **+0.750** | **+0.745** | **+0.335** |
| mercado ECR condicionado a nuestras reglas | +0.706 | +0.702 | +0.280 |
| mi proxy histórico (ppg año anterior × E[juegos]) | +0.639 | +0.643 | +0.040 |

Y no es un año suelto — el mercado le gana a mi proxy en **5 de 5**
temporadas (rho: 2021 .721/.609 · 2022 .711/.623 · 2023 .606/.503 ·
2024 .725/.615 · 2025 .702/.643).

**Entonces "ningún tablero predice" era FALSO.** El mercado sí predice
(+0.28 a nivel roster) y ESPN+nuestras reglas predice más (+0.335). Lo que
no predice es el proxy que yo construí para el backtest.

### 🔁 CORRECCIÓN DE LA FASE A (me equivoqué y lo reporto yo)
En la Fase A concluí "mi tablero le gana al mercado (rho 0.768 vs 0.730)".
**Está mal.** Ese número salió de un universo distinto (todo el ECR con datos
reales, ~500 jugadores) y de "puntos capturados en el top-K", métricas que
premian acertar en la cola. Sobre los 260 que de verdad se draftean, el
mercado gana siempre. Causa raíz: mi proxy solo sabe puntos-por-juego del año
pasado — es ciego a novatos, cambios de equipo, lesiones, entrenadores y
línea ofensiva; el consenso los incorpora. Regla nueva: **medir siempre sobre
el universo que se va a draftear, no sobre todo el corpus.**

### ✅ Lo que NO se contamina: el tablero del 7-sep
`optimize/vbd.py` ya construye el tablero como proyección **ESPN de
pretemporada re-puntuada con nuestras reglas** — justo el que mide mejor. El
proxy defectuoso solo existe dentro del backtest, porque no hay proyecciones
ESPN archivadas de 2021-2024 (motivo exacto por el que nació `ingest/archivo.py`).

Candado sobre esa proyección ESPN 2025 (¿estará actualizada en vivo y por eso
mide tan bien?): **corr(juegos proyectados, juegos reales) = 0.204**. Si ESPN
la hubiera refrescado durante la temporada sería ~1.0. ✅ Es de pretemporada.

### Cambios aplicados
- `backtest_liga.py`: default de `--tableros` pasa de `hibrido` a `mercado`.
- Encabezado del archivo documenta el sesgo de unidades y la tabla de arriba.
- El párrafo anterior "🚨 ningún tablero predice" queda **superado**: valía
  para el proxy, no para el sistema real.

---

## 28-ago (8): SIMULADOR DE LIGA COMPLETA — y los tres errores que lo frenaron

Andrés: *"olvida los puntos que te dije, los tuyos son mejores. Es que yo solo
hablaba de temporada regular. Pero confía en lo que tú ves en la historia de
la liga. Nada mejor que eso para comparar."*

Ficha del "1400" → **CERRADA**: era temporada regular y no contradice nada.
La fuente para calibrar pasa a ser la historia de la liga.

### Lo que se construyó
- `model/posiciones.py` — la posición la manda ESPN, no nflverse.
- `model/scoring_kdst.py` + `model/validar_kdst.py` — K y D/ST desde nflverse.
- `optimize/liga.py` — 16 equipos, **14 titulares**, 18 rondas, `Config`
  parametrizable para reproducir también la liga de NFL.com.
- `optimize/drafts_reales.py` — los drafts REALES puntuados con nuestras reglas.
- `optimize/calibrar_liga.py` — el candado de liga.
- `optimize/politicas.py` y `optimize/meta_politica.py`.

### 🚨 Error A — el mapeo de posiciones (silencioso y grande)
nflverse etiqueta a los safeties como `SAF`; el mapeo viejo buscaba `S`/`FS`/
`SS`. La posición S salía con **n=6 en vez de 161**. Y no es solo eso: sobre
los 1.485 jugadores con tacleadas de 2025, nflverse dice `LB` donde ESPN dice
`DE` en **85 casos** y `DE` donde ESPN dice `DT` en **42**. La liga da un slot
a cada una, así que clasificar mal a un edge rusher corre la línea base de dos
posiciones a la vez. Regla: **la posición la manda ESPN**, vía crosswalk.

### 🚨 Error B — el pateador cobra tacleadas
El candado contra el appliedTotal real daba un sesgo NEGATIVO en todos los
pateadores. Riley Patterson: −9.0 exacto = 3 solos (4.5) + 1 asistida (0.5) +
4 totales (4.0). Además ESPN cuenta el **FG bloqueado como fallado** y nflverse
lo lleva en columna aparte. Con las dos correcciones: **MAE 0.35 · mediana 0.00
· 93% dentro de ±1**.

### 🚨 Error C — los rivales estaban usando NUESTRO tablero
El más caro de los tres. En el simulador los 15 rivales picaban por nuestro
VBD, y salían **25 QB y dos pateadores dentro de los primeros 112 picks**. La
sala real toma K en la ronda 13.4 y los IDP en la 14-15: **no usan VBD**. Ahora
van por el ECR ofensivo y sólo cubren las casillas defensivas cuando la
aritmética los obliga.

**Esto no es un detalle de implementación: es de dónde sale nuestra ventaja.**
Si la sala ignora a los IDP hasta el final y bajo nuestras reglas un LB del
montón vale ~270 puntos de temporada, tomarlos antes tiene precio medible.

Efecto de la corrección sobre el candado de nivel: de **−16.4% a −1.2%**.

### ✅ CANDADO DE LIGA — cómo quedó
Comparación contra los **drafts reales** de la sala (98-99% de los picks
ofensivos emparejados por nombre+posición), puntuados con nuestro reglamento,
contra simulaciones de la MISMA configuración de cada año:

| candado | resultado | veredicto |
|---|---|---|
| NIVEL (media del bloque ofensivo) | −1.2% (rango −4% a +3%) | ✅ |
| DISPERSIÓN (1º/3º, adimensional) | conserva el 138% de la real | ✅ |
| CALENDARIO ofensivo | desvío 0.50 rondas | ✅ |
| ESTRUCTURA (slots obligatorios) | 0/640 sin llenar | ✅ |

**Dos comparaciones que probé antes y eran INVÁLIDAS** (quedan escritas):
1. Contra el PF de `historia_standings.csv` → +40%. Ese PF es de NFL.com con
   el reglamento de NFL.com. Dos varas distintas.
2. Contra un "equipo del medio" armado con el 8º mejor de cada posición según
   los appliedTotal reales → −13%. Eso es un **oráculo**: nadie draftea al que
   RESULTÓ ser el 8º.

### 📊 HALLAZGO CON CONSECUENCIA DIRECTA EN EL DRAFT
Estabilidad año-a-año (rho entre los puntos de Y−1 y los de Y, mismos
jugadores, bajo nuestras reglas, promedio de 2022-2025):

| pos | rho | | pos | rho |
|---|---|---|---|---|
| WR | 0.69 | | LB | 0.58 |
| TE | 0.67 | | CB | 0.53 |
| RB | 0.65 | | DT | 0.52 |
| QB | 0.61 | | DE | 0.50 |
| | | | S | 0.46 |
| | | | **K** | **0.27** |
| | | | **D/ST** | **0.18** |

- La ofensiva es MÁS predecible que el IDP, no menos.
- **El pateador y la defensa son casi ruido puro.** El año anterior no dice
  nada de ellos. Se toman al final porque no hay forma de saber — y por eso
  gastar un pick temprano ahí es tirarlo.

### ⚠️ SUPUESTO S-IDP (vivo)
- QUÉ: en el backtest, el tablero de IDP/K/DST es "puntos del año anterior
  bajo nuestras reglas". No existe ECR ni ADP público de IDP.
- POR QUÉ NO HAY INFO: se buscó (FantasyPros no publica IDP superflex
  histórico; FFC no tiene IDP).
- COSTO SI ESTÁ MAL: el backtest subestima lo que un buen tablero de IDP
  puede dar, porque el insumo tiene rho 0.5 y no 0.75.
- SENSIBILIDAD: sesga **en contra** de las políticas que toman IDP temprano.
  Es el lado conservador.
- CADUCIDAD: el 7-sep tendremos la proyección ESPN 2026 de IDP, que sí
  incorpora noticias. Verificar entonces cuánto mejora.

### ⚠️ SESGO DECLARADO (vivo)
El simulador se queda con el roster del draft: no hay waivers, ni cambios, ni
streaming. En la liga real se ficha toda la temporada. Consecuencia: las
diferencias entre POLÍTICAS se ven más chicas de lo que serían de verdad.
Sesga hacia "empatan" — el lado conservador.

---

## 28-ago (9): RESULTADO DEL BACKTEST DE POLÍTICAS — el motor aguanta

4 temporadas (2021, 2022, 2023, 2025) × 300 simulaciones × 5 políticas, sobre
el simulador de liga completa ya calibrado. Comparación PAREADA: misma
semilla ⇒ mismo comportamiento de los 15 rivales y mismo calendario, así que
la única diferencia es mi decisión.

### Distribución completa del dinero (1.200 temporadas por política)
| política | E[$] | p10 | p50 | p90 | último | sin premio | top-8 | campeón |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| greedy | 498 | 80 | 170 | 1430 | 6.5% | 60% | 40% | 2.2% |
| **motor** | **967** | 100 | 780 | 2300 | 2.8% | 32% | 68% | 9.5% |
| motor2 | 1013 | 100 | 830 | 2320 | 2.9% | 32% | 68% | 10.2% |
| regla | 1035 | 100 | 835 | 2350 | 3.0% | 34% | 66% | **14.9%** |
| no-miope | 848 | 80 | 505 | 2260 | 5.0% | 44% | 56% | 9.2% |

### 🚨 El agregado MIENTE — año por año contra el motor (Δ$ ± error)
| vs motor | 2021 | 2022 | 2023 | 2025 |
|---|--:|--:|--:|--:|
| motor2 | −306±48 | +402±50 | −57±40 | +147±47 |
| regla | **+454±67** | +44±60 | −136±41 | −91±51 |
| no-miope | −538±65 | +406±64 | −208±47 | −134±51 |

`regla` sale +$68 en el agregado **solo por 2021**; pierde en 2023 y 2025.
`motor2` gana 2 años y pierde 2. Es la regla IV.14 en acción: el promedio
escondía al caso que mata.

**El motor tiene además el mejor PISO**: su peor año es $610 (regla $475,
motor2 $553, no-miope $403). Con dinero real, el piso pesa.

### Qué roster construye cada una (media)
| | QB | RB | WR | TE | DT | DE | LB | CB | S |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| motor | 3.0 | 3.5 | 3.1 | 1.4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| regla | 3.0 | 3.2 | 3.5 | 1.4 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| motor2 | 3.0 | 2.7 | 2.7 | 1.3 | 1.2 | 1.3 | 1.4 | 1.4 | 1.1 |
| greedy | 2.9 | 1.0 | 2.0 | 1.0 | 1.7 | 1.6 | 2.0 | 1.8 | 1.9 |

Las que ganan toman **el mínimo de cada IDP** y meten la profundidad en
RB/WR. La que se llena de IDP es la peor por lejos.

### ❌ "Mirar hasta el final" (no-miope) HACE DAÑO
Pierde $118 contra el motor (t = −3.9) y en 3 de 4 temporadas. Construye
rosters de QB 1.9 / RB 1.2 llenos de IDP: sobreajusta al ruido del tablero.
Ya nos había pasado en la fase anterior; ahora está medido con dinero.

### ❌ El BOSQUE ALEATORIO no sirve — y la razón importa
Validación cruzada dejando una temporada fuera: **acierto 19% con 4 clases**,
por DEBAJO del azar (25%), y −$375 contra la mejor política fija.

Causa raíz medida: qué política gana es una propiedad de la TEMPORADA, no del
estado del tablero.

| año | motor | motor2 | regla | no-miope |
|---|--:|--:|--:|--:|
| 2021 | 25% | 13% | **51%** | 11% |
| 2022 | 14% | 34% | 15% | **37%** |
| 2023 | **32%** | 24% | 24% | 20% |
| 2025 | 25% | **35%** | 19% | 21% |

Entrenar en tres años y probar en el cuarto falla porque la distribución del
ganador se mueve entre años. **Respuesta a la pregunta de Andrés: no, no hay
forma de recomendar condicionado a lo que quede. Basta con una política fija.**

### ⚠️ Lo que este backtest NO prueba (declarado)
1. El tablero de IDP es "puntos del año anterior" (rho 0.50). Sesga EN CONTRA
   de tomar IDP temprano. El 7-sep tendremos la proyección ESPN 2026 de IDP,
   que sí incorpora noticias: hay que rehacer esta medición ese día.
2. No hay waivers, cambios ni streaming: las diferencias entre políticas se
   ven más chicas de lo que serían de verdad.
3. Sólo 4 temporadas. Los intervalos por año son de ±$40-70 sobre medias de
   ~$1.000: alcanzan para descartar a greedy y a no-miope, no para separar a
   motor / motor2 / regla.

### Verificación del verificador: la meta-política RIGUROSA también pierde
El primer test evaluaba un voto de mayoría por temporada — que mide "elegir
UNA política por año", no lo que Andrés preguntó. Se rehizo metiendo el bosque
DENTRO del draft, decidiendo en cada uno de mis 18 turnos:

| año | meta | motor | Δ | mejor fija de ese año |
|---|--:|--:|--:|---|
| 2021 | 1043 | 1190 | −147 ± 89 | regla $1749 |
| 2022 | 1424 | 1434 | −10 ± 79 | no-miope $1793 |
| 2023 | 458 | 575 | −117 ± 53 | motor $575 |
| 2025 | 597 | 710 | −113 ± 77 | motor2 $836 |

**−$97 de media y pierde en las 4 temporadas.** Mismo veredicto que el test
grueso, con el diseño correcto. ✅ Cerrado: política fija = **motor**.

---

## 28-ago (10): 🔒 REGLA DE ANDRÉS — un IDP por posición, cero IDP en banca

> *"Regla: un idp por posicion. No quiero idp en mi banca nunca."*

Es una restricción DURA sobre mi equipo, no una preferencia del motor. Los
rivales siguen con sus topes de siempre (hasta 2 por posición IDP): la regla
es mía, no de la sala.

**No va contra los datos, va con ellos.** El backtest de 4 temporadas × 300
simulaciones ya había mostrado que las políticas ganadoras toman exactamente
1.0 de cada IDP y meten la profundidad en RB/WR, y que la que se llena de IDP
es la peor de todas por lejos:

| política | DT | DE | LB | CB | S | E[$] |
|---|--:|--:|--:|--:|--:|--:|
| motor | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 967 |
| regla | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1035 |
| motor2 | 1.2 | 1.3 | 1.4 | 1.4 | 1.1 | 1013 |
| greedy | 1.7 | 1.6 | 2.0 | 1.8 | 1.9 | **498** |

### Dónde quedó escrita (en código, no en intención)
- `optimize/sala.py` → `MAX_UTIL_MIO` (lo usan las herramientas de producción)
- `optimize/plan_draft.py` → mis topes sólo para mi asiento
- `optimize/live_draft.py` → el asistente del 7-sep
- `optimize/liga.py` → `MAX_POS_MIO` y `Config.topes(t)` en el simulador
- `optimize/politicas.py` → también dentro de los rollouts de no-miope, que
  simulan MIS picks futuros

### Candado
`rosters míos que violan la regla: 0/50` (5 políticas × 10 semillas).

### Consecuencia lateral que hay que vigilar
Con el tope en 1, `motor2` pierde su única palanca (tomaba 1.2-1.4 IDP). Es
decir: **la regla de Andrés vuelve a motor2 idéntico al motor en la práctica**.
Queda medido en la corrida siguiente.

---

## 28-ago (11): ✅ FICHAS CERRADAS (Brian, Santi Gut, S-IDP) + 🚨🎯 T1 SONÓ

### Fichas cerradas por Andrés
- Asiento 9 ("el l.ai.on", cuenta de Heejin Lee) **ES Brian** → su
  personalidad medida (−4, 15) aplica. Asiento 16 ("The Nest") = **Santi
  Gut**, manager nuevo sin historia → personalidad global. `managers.py`
  documentado.
- El "1400" de puntos: era solo temporada regular; sin contradicción.

### ✅ S-IDP CERRADO — el ECR de IDP SÍ existía (Andrés: "busca, en algún
lado encontrarás"). Estaba en NUESTRO propio parquet de DynastyProcess:
páginas `idp/dl/lb/db/k/dst-cheatsheets` con snapshots de pretemporada
2021-2026 (IDP: 186-268 jugadores/año con cruce a gsis; K: 29-48; DST: 32).
`universo()` ya no usa "puntos del año anterior" (rho 0.5) sino el consenso
de expertos de ESE año. El año anterior queda solo de relleno.

### 🚨🎯 EL TRIPWIRE T1 SONÓ — el mismo día en que montamos el candado HTML
El candado de arranque de `tablero_vivo.py` detectó el descuadre y
`check_settings.py` lo confirmó (`scoring_hash e487…→c529…`). El commish:
- **ELIMINÓ** el ítem "tacleada total" (statId 109, 1.0)
- **BAJÓ** la solitaria (statId 108) de 1.5 a **1.0**

Solitaria efectiva 2.5→**1.0** (−60%) · asistida 1.5→**0.5** (−67%) · sack
~4.5→~3.0. **"Solo 1 punto" era literal — Andrés lo leyó bien desde el
principio y el análisis inicial lo subestimó.**

Protocolo ejecutado completo:
1. Settings vivos archivados con hash (`data/archivo/2026-08-28/espn_settings_post_t1.json`).
2. Config actualizado; el pre-T1 queda congelado en
   `config/espn_settings_2026_v3_pre_t1.json` (es la vara contra la que se
   validó el corpus 2025 — los tests de fixtures apuntan ahí, 16/16 verdes,
   y hay tests nuevos de las reglas vivas).
3. Impacto medido (2025 re-puntuado, titular medio top-16):
   **LB −59% · S −58% · DT −55% · CB −53% · DE −48% · ofensiva −1%.**
   VBD del #1: RB 213 · QB 211 · TE 196 · WR 175 · **LB 42 · DT 39 · DE 33 ·
   CB 21 · S 20.**
4. Tableros 2026 regenerados (proyeccion_v2 → distribuciones → vbd → notas).
   Candado: top IDP nuevo = Cashman vbd 30 (era ~208). Ofensiva intacta.
5. REGLAMENTO y PLAN_DRAFT actualizados; backtest de políticas y candado de
   liga re-lanzados bajo reglas vivas.

### Consecuencias estratégicas (las grandes)
- **Muere el IDP como ventaja**: el mejor IDP de la liga vale lo que un WR
  del montón. La idea del DT temprano queda enterrada con datos.
- La regla de Andrés (1 IDP por posición, 0 en banca) pasa de correcta a
  trivialmente obvia.
- El draft es ahora ~90% ofensiva: WR R1 / QB R2 condicional siguen; los
  picks 3-11 son ofensiva casi pura; IDP+K+DST = rondas 12-18.
- El peso de reglas locales de LB/DT/S/CB/DE se desploma → el consenso
  público se equivoca MENOS en IDP ahora; nuestra ventaja se concentra en
  QB (TD de pase a 6, completos, primeros downs) y el pateador de pierna
  larga (FG 50-59 = 10 pts sigue intacto).
