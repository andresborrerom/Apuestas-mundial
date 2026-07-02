# LEMAITRE — Reglas oficiales y ground truth

> **Fuente de verdad (en orden de autoridad):**
> 1. **El app publicado** (JavaScript que calcula la tabla que reparte la plata):
>    - Tabla en vivo: https://templecolombia.github.io/polla-mundial-2026/
>    - Código + data: https://raw.githubusercontent.com/TempleColombia/polla-mundial-2026/main/index.html
>    - `BASE_DATA` embebido = planillas de los 27, resultados, grupos, extras.
> 2. **El Excel oficial de reglas**: `2026 06 Form Polla Mundial US-MX-CA.xlsx`, hojas
>    `Descripcion` y `Puntajes`.
>
> **Regla de oro:** NUNCA inferir la regla de scoring a partir de los totales.
> Leer el código `calcMarcador`/`calcClasifScore`/`calcExtrasScore` del app y
> validar celda por celda contra la tabla publicada. (El flip-flop
> aditivo/degradado de julio 2026 vino de inferir de totales con un `real_score`
> contaminado — no repetir.)

Nosotros somos **Pocho — D024 — participante #24**.

---

## 1. Marcadores (solo knockout; los de grupos NO puntúan)

> Del Excel: *"no vamos a considerar los marcadores de la fase de grupo"*.
> Solo se puntúan los marcadores de **Fase 32 en adelante** (partidos 73–104).
> El marcador es **al minuto 90** (se permite empate en todas las fases).

**La regla es ADITIVA** (confirmado en el código `calcMarcador` del app):

```js
if (pred == exacto)            -> pp.e                      // Marcador Total
const partial = e1==r1 || e2==r2;
if (ganador_correcto)          -> pp.g + (partial ? pp.p : 0)   // SUMAN
else if (partial)              -> pp.p
else                           -> 0
```

Es decir: **ganador (`g`) y parcial (`p`) SE SUMAN**, no se degradan.
Un **1-0 sobre un 2-0** = 18 (ganador) + 12 (acertó el 0) = **30 pts**.

> ⚠️ El Excel dice *"Ganador o Empate SIN marcador = 18"* / *"Marcador Parcial = 12"*,
> que **se lee como excluyente** (degradado). PERO el app los suma, y la tabla
> publicada confirma el aditivo (validado 7/7 el 2-jul-2026). **El app manda.**

Puntos por fase `(exacto e / ganador g / parcial p)`:

| Fase | e | g | p |
|------|---|---|---|
| Fase 32 (73–88) `F32` | 40 | 18 | 12 |
| Octavos (89–96) `OCT` | 40 | 18 | 12 |
| Cuartos (97–100) `CUAR` | 50 | 30 | 14 |
| Semifinal (101–102) `SEMI` | 60 | 40 | 15 |
| 3er/4to puesto (103) `TERC` | 70 | 48 | 20 |
| Final (104) `FINAL` | 80 | 48 | 24 |

---

## 2. Clasificación de equipos (por slot R32, partidos 73–88)

`calcClasifScore` compara equipos predichos vs reales (`real_equipos`) en cada
uno de los 16 slots de Fase 32:

| Caso | Pts |
|------|-----|
| Ambos equipos en orden | 40 |
| Ambos invertidos | 25 |
| Uno en su puesto | 20 |
| Uno cambiado de puesto | 15 |

Máximo 640 (16 × 40). (Octavos+ tienen sus propias tablas de clasificación:
OCT 35/25/18/12, CUAR 30/20, SEMI 40/30, Final 210/120/80/60/40/30/25.)

---

## 3. Extras — puntos y **quién los pone**

> **Los extras los entra el ADMIN a mano** (`real_extras` en BASE_DATA +
> localStorage). El app **NO** los calcula. Un extra solo suma cuando el admin
> registra su valor. Nosotros SÍ podemos calcular el valor real desde
> `grupos_results` para saber qué va a pasar y qué ya es concluible.

**Otros Extras (500 pts):**

| Extra | Pts (app) | Pts (Excel) | Notas |
|-------|-----------|-------------|-------|
| Número total de goles | **120** | 100 | ⚠️ discrepancia; app paga 120 |
| Jugador goleador | 50 | 50 | |
| Nº de goles del goleador | 50 | 50 | |
| Equipo del gol Nº 25/50/75/100/125/150 | 40 c/u | (Excel: solo 50 y 100) | ⚠️ app tiene 6 hitos |
| **Equipo Último Lugar** | **30** | 30 | ver definición ↓ |
| Equipo + goles a favor | 30 | 30 | |
| Equipo + goles en contra | 30 | 30 | |
| Equipo − goles a favor | 30 | 30 | |
| Equipo − goles en contra | 30 | 30 | |
| Equipo primer gol del torneo | 20 | 15 | ⚠️ |
| Equipo último gol del torneo | 20 | 15 | ⚠️ |
| Continente campeón / subcampeón | 20 c/u | 20 | |

**Extras Colombia (250 pts):** 1er gol 40 · último gol 40 · goles a favor 50 ·
goles en contra 50 · posición final 70.

**Definición "Último Lugar":** el peor equipo de TODO el Mundial.
Orden: **menos puntos → peor diferencia de gol → más goles en contra**.
(No es "último de un grupo".)

**Máximo posible total = 3900** = Marcadores 1430 + Equipos 1720 + Extras Col 250 + Otros Extras 500.

**Premio:** 90% del pozo → **1º 60% · 2º 30% · 3º 10%**. Empates suman y reparten.
→ La diferencia 1º vs 2º es enorme; cada punto arriba pesa.

---

## 4. Estado ground truth (2-jul-2026, 82/104 = 72 grupos + 10 de Fase 32)

### Tabla oficial (validada 7/7 vs screenshot 2-jul 11:45am)

| # | Participante | Marc | Clasif | Extras | TOTAL |
|---|--------------|------|--------|--------|-------|
| 1 | Dionisio E Araújo | 202 | 400 | 60 | **662** |
| 2 | **Pocho (NOSOTROS)** | 180 | 420 | 60 | **660** |
| 3 | Viviana Araújo | 216 | 420 | 20 | 656 |
| 4 | Andres Harker | 246 | 380 | 20 | 646 |
| 5 | Hdo Luque | 184 | 360 | 100 | 644 |
| 6 | Papo Luque | 216 | 360 | 60 | 636 |
| 7 | Fabian Camacho | 188 | 380 | 60 | 628 |

Vamos **2º, a −2 de Dionisio**.

### Extras concluibles HOY (aún sin puntuar por el admin)

| Extra | Valor real (ground truth) | Quién le pega (del top) | Efecto |
|-------|---------------------------|--------------------------|--------|
| **Último lugar** | **Irak** (0 pts, dif −11, GC 12) | solo Paula Fonseca (#21) | no mueve la cima |
| **Menos goles a favor** | **Panamá** (0 goles, fijo) | Fabian Camacho → +30 (a 658) | Fabian sube a 3º |

> ❌ Curazao NO es último (1 pto, 43º). Ni Pocho ni Harker(#14) le pegan al último lugar.

### Extras NO concluibles aún (torneo en curso)
- Más goles a favor (Francia 13, **vivo** y subiendo).
- Más/menos goles en contra (equipos vivos aún pueden variar).
- Total de goles, goleador, hitos, continentes, Colombia: pendientes.

### Anomalía de data conocida
En `grupos_results` el Grupo K trae "RD Congo" y "R.D. Congo" como equipos
separados (falta normalizar). No afecta el último lugar ni el top; `normEquipo`
del app los unifica para la clasificación.

---

## 5. Cómo recalcular (scripts en esta carpeta)

```bash
python pollas/LEMAITRE/puntos_lemaitre.py --refresh   # baja BASE_DATA oficial + tabla
python pollas/LEMAITRE/tablas_mundial.py              # grupos, general 48, último lugar, extras
python pollas/LEMAITRE/que_marcador.py --match 83     # qué resultado nos conviene (locked)
```

`puntos_lemaitre.py` reproduce la tabla oficial EXACTA. Siempre validar los
totales contra el screenshot/link antes de concluir nada.
