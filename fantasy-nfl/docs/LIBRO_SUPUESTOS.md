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
