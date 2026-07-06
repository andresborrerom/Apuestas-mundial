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

## 2. Clasificación de equipos (por SLOT — acertar qué equipos llegan a cada llave)

`calcClasifScore` compara equipos predichos vs reales (`real_equipos`) por slot.
El app puntúa en TRAMOS que se van activando a medida que se define cada bracket:

| Tramo (slots) | Ambos en orden | Invertidos | Uno en su puesto | Uno cambiado |
|---------------|:---:|:---:|:---:|:---:|
| **Fase 32 (73–88)** | 40 | 25 | 20 | 15 |
| **Octavos (89–96)** | 35 | 25 | 18 | 12 |

> ⚠️ **Esta columna crece por ronda.** Cuando se armó el bracket de octavos, el
> app agregó el tramo 89–96 (nuestra Clasif saltó de 420 a 597, +177). **El
> scorer debe incluir cada tramo nuevo o subestima el total.** (Bug detectado y
> corregido el 6-jul: faltaba el tramo de octavos.)

> 🔜 **Pendiente:** cuando llegue CUARTOS, el app agregará el tramo **97–100**.
> El código actual del app (`calcClasifScore`) solo tiene 73–96. Apenas active
> cuartos, revisar los valores reales y agregarlos a `calc_clasif`
> (probablemente 30/20/15/10, pero CONFIRMAR contra el app, no asumir).

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

---

## 6. Estado y ENDGAME (6-jul-2026, marcadores hasta P#91)

### Tabla oficial validada 7/7 (con clasificación de octavos)

| # | Participante | Marc | Clasif | Extras | TOTAL |
|---|--------------|------|--------|--------|-------|
| 1 | Dionisio E Araújo | 454 | 595 | 60 | **1109** |
| 2 | **Pocho (NOSOTROS)** | 404 | 597 | 60 | **1061** (−48) |
| 3 | Fabian Camacho | 412 | 557 | 60 | 1029 |
| 4 | Andres Harker | 436 | 558 | 20 | 1014 |
| 5 | Hdo Luque | 398 | 514 | 100 | 1012 |

En **Clasif somos #1 del torneo (597)**; Dionisio nos saca ventaja en marcadores.
(P#92 México-Inglaterra aún sin cargar por el admin; suma +18 a Pocho y +18 a
Dionisio → no cambia la brecha.)

### Probabilidad de ganar (Monte Carlo del torneo restante)

`endgame_lemaitre.py` simula el bracket restante (goles ~ Poisson de la fuerza de
cada equipo según las cuotas) con las 27 planillas locked. Resultado (15k sims):

| | P(1º = ganar) | P(top-3 = plata) | E[premio] |
|---|:---:|:---:|:---:|
| Dionisio (líder) | **75%** | ~95% | $2.91M |
| **Pocho (nosotros)** | **12%** | **48%** | **$848k** |
| Hdo Luque | 4% | | |
| Fabian / Andres | 1–2% | | |

Pozo $6.318.000; premios 1º $3.41M / 2º $1.71M / 3º $569k.

> **SUPUESTOS del modelo** (declarados): fuerzas de las cuotas de octavos como
> proxy de ataque; clasificación de cuartos/semis y standings final con valores
> ASUMIDOS (el app aún no los codifica). Los números se refinan a medida que se
> resuelven rondas y se confirman los puntajes reales.

### Techos "vivos" y colisiones de bracket (techos_lemaitre.py)

El Monte Carlo ya respeta que un equipo predicho y ya eliminado no puntúa (nunca
aparece en el bracket simulado). ADEMÁS hay que ver COLISIONES: dos picks de un
mismo participante que se enfrentan antes de semis no pueden coexistir en el top-4.
Los 4 semifinalistas salen uno de cada "grupo de cuarto":
- P97: Francia/Marruecos · P98: Portugal/España/EEUU/Bélgica ·
  P99: Noruega/Inglaterra · P100: Argentina/Egipto/Suiza/Colombia.

Diagnóstico 6-jul: **Dionisio tiene los 4 picks de final en grupos distintos
(techo pleno 210)**; nosotros tenemos España(campeón) y Portugal(4to) en el MISMO
grupo P98 → colisión −30 y hueco en P100. Por eso **hoy nos conviene que gane
España** (mantiene vivo el pick de campeón, 80 pts, vs 4to de Portugal, 30).
