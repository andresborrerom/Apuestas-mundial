# PLAN DE DRAFT — Peace and Love 2026
**7-sep 19:00 COL · snake 16 equipos · 18 rondas · 45s por pick · Pocho = pick 5**

Mis picks globales: **5, 28, 37, 60, 69, 92, 101, 124, 133, 156, 165, 188,
197, 220, 229, 252, 261, 284**.

---

## ✅ BLOQUEO LEVANTADO (28-ago) — pick 5 verificado en la app

El commish cargó el sorteo. `pickOrder` = [13, 7, 1, 17, 10, 2, 15, 4, 16,
3, 11, 8, 14, 12, 9, 5] → **teamId 10 ('No Team for Old Men' = Pocho) en la
posición 5** ✅. `draftDetail` confirma mis picks globales exactamente como
los tenía el plan: 5, 28, 37, 60, 69, 92, 101, 124, 133, 156, 165, 188, 197,
220, 229, 252, 261, 284 — validación cruzada de mi implementación del snake
contra la fuente. Tripwire re-aceptado; sigue vigilando por si lo cambian.

### Asientos verificados contra los nombres de equipo de la app
14 de 16 cuadran solos (WTrash=Jaime/JHJ, ComNich=Nich, Ayayay=Diego,
Bolivia=Sergio, el l.ai.on=Brian, Raw Dawg=Rodrigo, Victorious Secret=
Santi A, Back 2 Back=SteveO, EZWAR=Esguerra, KeepMyTeam...=Kike,
Panamanian P!mps=James B, Ferchos=Ferchos, Injury Report=Gabriel).
⚠️ **Dos por confirmar con Andrés**: el asiento 4 es *"Amanecera y veremos"*
(yo esperaba a Luis Carlos, cuyo equipo 2025 se llamaba "The Nest") y el
asiento 16 es *"The Nest"*. Importa: el asiento 4 pica JUSTO antes que yo y
Luis Carlos es el más ávido de QB de la sala (w=1.39).

---

## LA REGLA (validada, 4 escenarios de sala, pareado)

> **Pick 5 → el mejor WR del tablero.**
> **Pick 28 → si sobrevive un QB con VBD ≥ 110, tómalo. Si no, WR otra vez.**
> De ahí en adelante: mejor valor sobre la línea base, respetando los tiers.

Rendimiento (E[VBD del titular], 100 drafts simulados por escenario):

| estrategia | A conserv. (16 QB) | **B MEDIDO (20)** | C alto (26) | D medido+IDP | media | peor |
|---|--:|--:|--:|--:|--:|--:|
| **WR + condicional 110** | **717** | **668** | **741** | **704** | **708** | **668** |
| WR-WR fijo | 666 | 668 | 741 | 704 | 695 | 666 |
| WR-QB fijo | 717 | 624 | 622 | 673 | 659 | 622 |

Grilla **calibrada contra la conducta real de ESTA sala** con slot OP
(ver abajo). En el escenario medido la condicional no se dispara (ningún QB
con VBD≥110 sobrevive al pick 28) y equivale a WR-WR; en el conservador
gana +50. Es una opción gratis: nunca peor, a veces mucho mejor.

La condicional **nunca pierde** contra WR-WR y gana el 92% de los drafts
cuando la corrida de QBs no ocurre. QB temprano es la PEOR opción salvo en
ese mundo.

### Por qué (los tres hallazgos que la sostienen)

1. **El OP no es un superflex de QB.** ✅ Verificado en `eligibleSlots`: el
   slot 7 admite QB/RB/WR/TE — Nacua es elegible. **No estás obligado a un
   2º QB**: puedes poner un WR élite ahí. Refuta la premisa de H1.
2. **La sala sobrepaga QBs — medido con el slot OP ya presente.** ✅ En los
   settings rescatados: 2023 y 2025 YA tenían el slot QB/RB/WR/TE; 2024 no.
   QBs en R1-R3: **2023 = 21/16 eq (1.31)** · **2025 = 17/14 eq (1.21)** ·
   2024 sin OP = 5/16 (0.31). El "año anómalo" no era anomalía: era el año
   sin OP — la sala responde a la regla. Centro 2026 (16 eq) ≈ **20 QBs en
   R1-R3**; la grilla cubre 16-26. Que ellos gasten picks tempranos en QBs
   nos deja los WR élite.
3. **El roster v3 volvió la WR profunda**: 2 slots dedicados × 16 equipos =
   32 titulares + flex → baseline WR38. El WR élite tiene ahora la mayor
   ventaja sobre su reemplazo de todo el tablero.

---

## DISPONIBILIDAD EN MIS DOS PRIMEROS PICKS (escenario C, 60 drafts)

| jugador | pos | VBD | vivo en el 5 | vivo en el 28 |
|---|---|--:|--:|--:|
| Josh Allen | QB | 196 | 0% | 0% |
| **Puka Nacua** | WR | 164 | **100%** | 0% |
| Drake Maye | QB | 153 | 5% | 0% |
| Jahmyr Gibbs | RB | 148 | 100% | 57% |
| **Ja'Marr Chase** | WR | 145 | **100%** | 70% |
| Jalen Hurts | QB | 145 | 13% | 0% |
| Bijan Robinson | RB | 139 | 100% | 63% |
| **Jaxon Smith-Njigba** | WR | 138 | **100%** | 73% |
| Amon-Ra St. Brown | WR | 133 | 100% | 83% |
| Christian McCaffrey | RB | 128 | 100% | 83% |
| CeeDee Lamb | WR | 106 | 100% | 88% |

**Lectura:** los QB élite ya volaron cuando llegas al 5 (Allen 0%, Maye 5%,
Hurts 13%) — perseguirlos es imposible, no una opción. En cambio **Nacua
llega vivo el 100% de las veces** y es el #2 del tablero. Y en el 28 todavía
sobrevive un WR top-4 (Chase 70%, JSN 73%, St. Brown 83%).

---

## GUÍA POR RONDA (moda de la política ganadora)

| ronda | pick | posición | candidatos típicos |
|--:|--:|---|---|
| 1 | 5 | **WR** | Nacua |
| 2 | 28 | **WR** (o QB si VBD≥110) | Chase · JSN · St. Brown · Lamb |
| 3 | 37 | RB (61%) / WR | J. Taylor · McCaffrey · St. Brown |
| 4 | 60 | **TE** (70-83%) | Brock Bowers |
| 5 | 69 | **LB** | Blake Cashman |
| 6 | 92 | LB / WR | Jordyn Brooks · Travis Hunter |
| 7 | 101 | **DT** | **Jeffery Simmons** (el cuello de botella) |
| 8 | 124 | QB | el mejor que quede |
| 9 | 133 | RB / DT | profundidad |
| 10 | 156 | **DE** | Maxx Crosby |
| 11 | 165 | **D/ST** | Steelers · Seahawks · Ravens |
| 12 | 188 | **CB** | Nick Emmanwori |
| 13 | 197 | RB / WR | profundidad |
| 14 | 220 | QB2 / S | Penix · Chinn |
| 15-18 | — | S · DT2 · **K** · relleno | Nick Folk · Buckner |

Notas de timing medidas en la historia de la sala: el primer IDP de la liga
cae en ronda 10-11 y los K en la 13 — por eso Cashman (R5) y Simmons (R7)
son *reaches* solo en apariencia: nadie más los está mirando todavía.

---

## SUPUESTOS VIVOS

- ⚠️ **Apetito de QB de la sala**: los 4 escenarios cubren de 16 a 30 QBs en
  R1-R3. La regla es robusta a todo el rango (por eso es condicional).
- ⚠️ **Split del flex RB/WR 60/40** (baselines RB26/WR38). Sensibilidad
  corrida: Nacua es #2 del tablero en las 4 variantes (hasta con flex 100% RB
  sigue #4). La recomendación no depende del split.
- ⚠️ **Conciencia IDP de la sala**: escenarios con primer IDP en R10 (medido)
  y en R5 (si notan la proyección de tackles). La regla gana en ambos.
- ❓ **Cambio de tackles del commish** (ficha T1): si toca la regla, el
  tripwire truena y hay que regenerar el tablero antes del draft.
