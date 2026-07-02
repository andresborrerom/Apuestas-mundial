# CSC — "La Super Polla de los Pollos 2026" — Reglas y ground truth

> **Fuente de verdad:**
> - **Reglamento oficial**: `Reglamento Polla Super Polla 2026.pdf` (esta carpeta) —
>   slides con la mecánica y la tabla "LOS PUNTOS AUMENTAN POR RONDA".
> - Formulario de inscripción: Google Form `https://forms.gle/Fxjw4D9badtutdKf9`.
> - Tabla de posiciones: **PDF diario** que envía el organizador (no hay app
>   abierta como LEMAITRE). El más reciente que tenemos: `1.7.26.pdf` (1-jul-2026).
> - Organizan: Santiago Schlesinger y Carlos Pinto (sin ánimo de lucro).
>
> Somos **ANDRES BORRERO** con **5 cupos** (ANDRES BORRERO 1..5). Cada cupo es
> independiente y suma puntos por separado (estrategia de dispersión MIXTA:
> B4 = ancla EV-máx, B1/B2 perturbaciones suaves, B3/B5 lotería/escalón).

---

## 1. Regla de puntuación (VALIDADA 1:1 contra el reglamento oficial)

Por **cada partido**, el puntaje del cupo = **suma** de:
1. **Ganador o empate** acertado (tendencia 1X2) → `pts_res`.
2. **Goles del equipo local** exactos → si el número es **0**: `pts_cero`;
   si es **≠0**: `(#goles + base)`.
3. **Goles del equipo visitante** exactos → misma regla (0 → `pts_cero`, ≠0 → `#+base`).

> Es decir: **premia acertar el número de goles de CADA equipo por separado, y
> entre más goles aciertas más puntos** (un gol alto vale más). Acertar un 0 paga
> plano. NO hay campeón/goleador/extras: solo marcadores, ronda por ronda.

**Tabla oficial "LOS PUNTOS AUMENTAN POR RONDA"** (= `pollas/CSC/reglas.py` `RONDAS`):

| Ronda | Ganador/Empate | Goles = 0 | Goles ≠ 0 | Código `(res,cero,base)` |
|-------|:---:|:---:|:---:|:---:|
| primera (grupos)* | 1 | 2 | #+3 | `(1, 2, 3)` |
| **dieciseisavos** | 2 | 3 | #+5 | `(2, 3, 5)` |
| octavos | 3 | 4 | #+7 | `(3, 4, 7)` |
| cuartos | 4 | 6 | #+10 | `(4, 6, 10)` |
| semis | 5 | 8 | #+12 | `(5, 8, 12)` |
| 3º y 4º puesto | 6 | 10 | #+14 | `(6, 10, 14)` |
| final | 8 | 12 | #+16 | `(8, 12, 16)` |

\* En CSC la fase de grupos SÍ puntúa marcadores (a diferencia de LEMAITRE).

**Ejemplos del reglamento (todos reproducidos por `motor/backtest.puntos`):**
- Grupos, México 2-0, cupo 2-0 → ganador 1 + (2+3) + (0→2) = **8** ✓
- Grupos, real 3-2, cupo 1-2 → acertó visita (2) → 2+3 = **5** ✓
- Grupos, real 2-1, cupo 2-0 → ganador 1 + (2+3) = **6** ✓
- Grupos, real 2-2, cupo 0-0 → acertó empate = **1** ✓

**Consecuencia estratégica:** el sistema premia marcadores con goles (2-1, 3-1),
no el 1-0. El ancla EV-máx va con 2-1/3-1, no 1-0 (opuesto a LEMAITRE).

---

## 2. Eliminatorias — regla de los 120 minutos

Desde dieciseisavos, el resultado válido es el del **partido finalizado**:
- Si terminó a los 90' → ese marcador.
- Si fue a alargue → el de los **120 minutos**.
- **Penales NO cuentan.** Se puede apostar al **empate** en cualquier ronda; si
  a los 120' hay empate, el que apostó empate suma aunque haya definición por penales.

→ Por eso el motor aplica el ajuste de descuento de empate (delta≈0.45) en knockout.

---

## 3. Premios (90% del recaudo, 5 puestos)

| Puesto | Premio |
|--------|--------|
| 1º | 50% |
| 2º | 20% |
| 3º | 15% |
| 4º | 10% |
| 5º | 5% |

Empate en un puesto → rifa (desempate por sorteo), NO se reparte el %. Solo 5
ganadores. → Estar en el top-5 con varios cupos multiplica la chance de premio.

---

## 4. Estado ground truth (PDF 1-jul-2026)

**Vamos LÍDERES.** Top del PDF:

| Pos | Cupo / Participante | Puntaje |
|-----|---------------------|---------|
| 1 | **ANDRES BORRERO 4 (ancla, NOSOTROS)** | **357** |
| 2 | Alejandro Carvajal 1 | 344 |
| 3 | **ANDRES BORRERO 1** | 342 |
| 4 | **ANDRES BORRERO 2** | 336 |
| 5 | Robert Muñoz 1 | 336 |

Ventaja del ancla sobre el mejor rival (Carvajal): **+13**. Tenemos **3 cupos en
el top-4**. La dispersión funciona.

### Cosecha en dieciseisavos (10/16 partidos jugados, validada con `reglas.py`)

| Cupo | Pts R32 |
|------|---------|
| **ANDRES BORRERO 4 (ancla EV-máx)** | **86** |
| ANDRES BORRERO 1 | 85 |
| ANDRES BORRERO 2 | 85 |
| ANDRES BORRERO 3 | 59 |
| ANDRES BORRERO 5 | 55 |

El orden de la cosecha R32 coincide con el orden del PDF (ancla mejor, lotería
abajo) — internamente consistente.

> ⚠️ **Límite de validación (honesto):** a diferencia de LEMAITRE (app abierto,
> validado celda por celda), CSC es un Google Form cerrado: NO tenemos las
> planillas de los rivales ni nuestras propias apuestas de fase de grupos
> guardadas. Por eso **no** podemos reconstruir el acumulado 357 desde cero; sí
> validamos (a) la **regla** 1:1 con el reglamento y (b) la **cosecha R32** de
> nuestros cupos. La posición sale del PDF oficial del organizador.

---

## 5. Cómo recalcular / operar

```bash
python pollas/CSC/reglas.py                    # regla por ronda (params oficiales)
# marcador a mandar por partido = EV-máx bajo la regla de la ronda:
python pollas/CSC/generar_r32_final.py         # genera los 5 cupos MIXTOS de una ronda
```
Datos: cupos enviados en `r32_CSC.csv`; cuotas en `r32_odds_snapshot.json`.
Para el gap real vs líderes, usar SIEMPRE el PDF más reciente del organizador.
