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
