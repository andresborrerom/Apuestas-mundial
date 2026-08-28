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
