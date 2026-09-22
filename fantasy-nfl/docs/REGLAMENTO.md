# REGLAMENTO DE PUNTUACIÓN — Peace and Love 2026

Auditoría completa de los 75 ítems de la configuración real de la liga.
Cada ítem fue **identificado empíricamente** (cruzando los crudos de ESPN
contra nflverse y contra los valores extremos de 2025), no de memoria.
El motor reproduce el `appliedTotal` de ESPN **1,801 de 1,801 jugadores**.

> Regla de lectura: 🔴 = se aparta del estándar y pesa. Ahí está el edge.

---

## Lo que hace RARA a esta liga (y cuánto pesa)

Porcentaje de los puntos de 2025 que vino de reglas NO estándar:

| posición | pts medios | de reglas locales | % |
|---|--:|--:|--:|
| **LB** | 169 | 80 | **47%** |
| **DT** | 88 | 40 | **46%** |
| **S** | 154 | 68 | **44%** |
| **DE** | 96 | 39 | **40%** |
| **CB** | 124 | 50 | **40%** |
| **QB** | 248 | 82 | **33%** |
| **K** | 148 | 28 | **19%** |
| RB | 160 | 15 | 9% |
| WR | 139 | 11 | 8% |
| TE | 118 | 8 | 6% |

**Casi la mitad de lo que anota un defensivo y un tercio de lo que anota un
QB viene de reglas que no existen en una liga normal.** Ahí es donde el
consenso público se equivoca y nosotros no: nuestro tablero re-puntúa las
estadísticas crudas con ESTAS reglas.

---

## PASE 🔴

| regla | puntos | ¿estándar? |
|---|--:|---|
| **TD de pase** | **6** | 🔴 el estándar es **4** |
| Yardas de pase | 1 cada 25 | estándar |
| **Pase completo** | **+0.1** | 🔴 no existe en ligas normales |
| **Pase incompleto** | **−0.05** | 🔴 |
| **Primer down de pase** | **+0.2** | 🔴 |
| Intercepción lanzada | **−3** | 🔴 el estándar es −2 |
| **Sack recibido** | **−0.1** | 🔴 |
| Juego de 300-399 yardas | +3 | 🔴 bono |
| Juego de 400+ yardas | +4 | 🔴 bono (NO se suma al de 300: son tramos) |
| TD de pase de 40+ / 50+ yardas | +1 / +2 | 🔴 **APILAN**: uno de 50+ paga 3 |
| 2 puntos por pase | +1 | |

Ejemplo real — Stafford 2025 (519.8 pts): TD pase **276** · yardas 180 ·
primeros downs **+47.2** · completos **+38.8** · INT −24 · incompletos −10.5.
**Un QB de esta liga vale por volumen de TD y por primeros downs.**

## TIERRA Y AIRE

| regla | puntos | ¿estándar? |
|---|--:|---|
| TD | 6 | estándar |
| Yardas | 1 cada 10 | estándar |
| **Recepción** | **+1** | PPR completo |
| **Primer down (tierra/recepción)** | **+0.2** | 🔴 |
| Juego 100-199 yardas | +2 | 🔴 bono |
| Juego 200+ yardas | +3 | 🔴 (tramos disjuntos, no se suman) |
| TD de 40+ / 50+ yardas | +1 / +2 | 🔴 **APILAN** |
| Balón perdido | −2 | estándar |

## KICKER 🔴🔴 — la regla que faltaba descubrir

| FG | puntos | detalle |
|---|--:|---|
| 0-39 yardas | +3 | |
| 40-49 | +4 | |
| **50-59** | **+10** | 🔴🔴 paga DOS ítems: "50+" (5) **y** "50-59" (5) |
| **60+** | **+11** | 🔴🔴 paga "50+" (5) **y** "60+" (6) |
| Punto extra | +1 | |
| Fallos | −0.5 a −3 | el corto se castiga más que el largo |

**Un FG de 50-59 yardas vale 10 puntos — más que un TD de recepción.**
Aubrey 2025: **113 de sus 235 puntos** salieron solo de FG de 50+. Por eso
los pateadores de pierna larga valen mucho más aquí que en cualquier
ranking público. (Verificado: el motor reproduce su 235.2 exacto.)

## IDP — 🚨 REGLA CAMBIADA EL 28-AGO (tripwire T1)

**El 28-ago-2026 el candado de arranque detectó el cambio en la liga viva y
el tripwire lo confirmó** (`scoring_hash e487…→c529…`): el commish ELIMINÓ el
ítem "total" (statId 109) y bajó la solitaria (108) de 1.5 a 1.0. "Solo 1
punto" era literal — como lo leyó Andrés desde el principio.

| regla | ANTES (pre-T1) | **AHORA** |
|---|--:|--:|
| Tacleada solitaria | 2.5 | **1.0** (−60%) |
| Tacleada asistida | 1.5 | **0.5** (−67%) |
| Captura (sack) | ~4.5 | **~3.0** |

Impacto medido (temporada 2025 re-puntuada, titular medio top-16):
LB −59% · S −58% · DT −55% · CB −53% · DE −48% · ofensiva sin cambio.
**VBD del #1 de cada posición ahora**: RB 213 · QB 211 · TE 196 · WR 175 ·
**LB 42 · DT 39 · DE 33 · CB 21 · S 20**. El IDP dejó de ser fuente de
ventaja: se llena tarde (rondas 12-16), uno por posición y cero en banca.
La tabla de abajo queda como REGISTRO HISTÓRICO pre-T1.

| regla (pre-T1) | puntos efectivos |
|---|--:|
| Tacleada solitaria | 2.5 (pagaba "solitaria" 1.5 + "total" 1.0) |
| Tacleada asistida | 1.5 (pagaba "asistida" 0.5 + "total" 1.0) |
| Captura (sack) | +2 (y arrastra la tacleada → ~4.5) |
| Intercepción | +3 |
| Balón forzado / recuperado | +1 / +3 |
| Pase defendido | +1 |
| TD defensivo **o de retorno** | +6 |

✅ **Ficha T1 CERRADA (28-ago)**: el commish lo hizo — y más duro de lo
anunciado (también bajó la solitaria a 1.0). El tripwire lo cazó el día
exacto, antes de que contaminara un solo número del draft.

✅ **El TD de retorno se lo lleva EL JUGADOR** (no la defensa), contra lo que
se jugaba en la app de NFL.com. Verificado al decimal: el total real de
Shaheed (160.9) solo se reconstruye incluyéndolo.

## D/ST

Eventos (captura 1, INT 3, balón recuperado 3, safety 2, TD 6) **más**
escalones de puntos permitidos (blanqueada +20 … 46+ −6) **más** bono de
menos de 100 yardas permitidas (+5). Los ítems de margen de victoria
(161-166) están configurados pero **inertes**: nadie los acumula.

---

## Detalle técnico que cambia cuentas

**Las yardas se truncan POR PARTIDO, no por temporada.** ESPN entrega el
stat ya convertido a unidades: `Σ_juegos floor(yardas/25)` en pase y
`floor(yardas/10)` en tierra/aire. Stafford tuvo 4,707 yardas (=188.3
unidades) y cobró **180**: los restos de cada partido se pierden.
**Consecuencia:** con el mismo total de yardas, el jugador regular anota más
que el irregular. No es decisión nuestra — es la definición del stat.
