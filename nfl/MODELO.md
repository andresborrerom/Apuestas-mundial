# MODELO NFL 2026 — datos, calibración y estrategias validadas

Bitácora técnica (estilo `pollas/CSC/DECISIONES.md`): qué datos usamos, qué
se validó con ground truth walk-forward, qué es simulación con supuestos, y
las decisiones que salen de ahí.

## 1. Datos

**Fuente:** `nflverse/nfldata` → `games.csv` (snapshot en `nfl/datos/`,
commit `99822d1` del 2026-08-19). Todo en un CSV:

- Resultados reales 1999–hoy (ground truth), con empates marcados.
- Spread de cierre desde 1999; **moneylines de cierre completos 2010–2025**.
- Las líneas de la temporada 2026 ya publicadas (semana 1 completa) → la
  misma fuente sirve para los picks en vivo. Refrescar:
  `curl -sSL -o nfl/datos/games.csv
  https://github.com/nflverse/nfldata/raw/master/data/games.csv`

Backup en vivo: The Odds API (`americanfootball_nfl`), mismo `motor/odds_api`.

## 2. Calibración de P(gana) — walk-forward 2011-2025

`python nfl/backtest_probabilidades.py` — test año a año; el spread se
ajusta solo con temporadas previas; el Elo corre cronológico prediciendo
antes de actualizar. 3.918 partidos de test.

| proxy | Brier | log-loss | % favorito |
|---|---|---|---|
| **moneyline (de-vig proporcional)** | **0.2104** | 0.6081 | 66.6% |
| moneyline (Shin) | 0.2103 | 0.6078 | 66.6% |
| spread (logística ajustada) | 0.2104 | 0.6080 | 66.5% |
| Elo (solo resultados) | 0.2201 | 0.6299 | 64.7% |

Calibración por bucket (moneyline): 0.5-0.6→55.2%, 0.6-0.7→63.4%,
0.7-0.8→76.9%, 0.8-0.9→85.8%, 0.9-1.0→96.8%. **El mercado está bien
calibrado** — igual que en el Mundial, es el predictor a batir y no lo
batimos: lo usamos.

**Decisiones:** moneyline = fuente oficial de P(gana) (proporcional; Shin no
paga la complejidad en mercados a 2 salidas). Spread = respaldo. **Elo = solo
para proyectar semanas futuras** (planeación Survival) y para rankear
equipos cuando aún no hay señal de mercado (semanas 1-3).

**Empates:** 0.33% de los partidos. En Survival cuestan vida → siempre
usamos P estricta: `p × (1 − 0.004)`.

## 3. El marrano — la intuición del usuario, medida

`python nfl/SURVIVAL/marrano.py` — marranos = bottom-5 por fuerza de mercado
(calculada solo con semanas jugadas, sin futuro), 2011-2025:

- **En 215/215 semanas (100%) hubo pick "contra marrano"** con p promedio
  **0.807**, vs 0.843 del mejor pick absoluto. El marrano regala ~80% de
  P(gana) TODAS las semanas sin tocar a los élite.
- Picks **no-élite** contra marrano con p≥72%: n=261, el mercado decía
  79.2%, **ganaron el 82.0%**. Bien calibrado (hasta mejor).
- La "fiesta" del marrano extremo está sobre-preciada: cuando el mercado le
  da <15%, gana el **7.7%** real (favorite-longshot bias, a nuestro favor).

**Conclusión:** el mercado ya precia bien al marrano — la ventaja **no es de
probabilidad, es estructural**: pegarle al marrano con medianos te deja la
élite guardada para las semanas flacas, y te descorrelaciona del field (que
se amontona en el favorito máximo).

## 4. Survival — backtest walk-forward 2011-2025

`python nfl/SURVIVAL/backtest_survival.py` — reglas oficiales (2 vidas,
empate cuesta vida, sin repetir, cierre semanal). Nuestras estrategias
corren deterministas contra resultados reales, con información walk-forward.
Solo el field es simulado.

**Estrategias:** `greedy` (favorito máximo), `marrano` (heurística: no-élite
vs bottom-5 si p≥0.70; tiers por mercado, o por Elo en semanas 1-3),
`planeada` (asignación húngara semanas×equipos max Σlog p̂, futuros por Elo),
`anticrowd` (planeada + bajarse del pick masivo si hay alternativa a <0.03).

**Supervivencia real (determinista, 15 temporadas):**

| | greedy | marrano | planeada | anticrowd |
|---|---|---|---|---|
| semanas medias | 8.5 | **11.9** | 9.3 | 8.5 |
| vivo a la sem. 18 | 1/15 | **4/15** | 2/15 | 1/15 |

**E[ganancia] en aportes ($300k = 1) — depende del field model (supuesto):**
field = N rivales que pickean softmax(θ·p) sobre sus equipos disponibles.

| field θ=25 ("normal") | N=10 | N=20 | N=40 |
|---|---|---|---|
| greedy | −0.60 | −0.67 | −0.70 |
| **marrano** | **+1.46** | **+2.45** | **+4.29** |
| planeada | −0.11 | +0.05 | +0.17 |
| anticrowd | −0.42 | −0.55 | −0.71 |

Con field casual (θ=10) marrano sube a +2.9/+4.6/+6.7; con field afilado
(θ=50), +2.0/+2.9/+3.9. **Marrano es la única estrategia positiva bajo los
tres supuestos de field y los tres tamaños de pool.**

**Robustez** (`experimento_robustez_marrano.py`): malla umbral×bottom-K
(9 celdas) → **todas positivas** (+0.24 a +2.17 con θ=25, N=20). El signo es
estructural; la magnitud de la mejor celda no hay que tomarla literal (n=15
temporadas).

**Por qué pierde greedy:** muere CON la manada (todos toman el mismo
favorito máximo; cuando cae, caen todos y el pozo se reparte entre muchos).
Marrano sobrevive distinto: mismo ~80% de p, otra ruta.

**Por qué la planeada no gana:** el plan "óptimo" se sobreajusta a
proyecciones Elo ruidosas de semanas futuras. La heurística simple es más
robusta que la optimización sobre datos malos. (Documentado, no maquillado.)

**Honestidad:** 2024 fue masacre inevitable — TODAS las estrategias murieron
en semana 2 (CIN 75% y BAL 78% perdieron). El Survival tiene varianza
irreducible; la ventaja es sobre el field, no sobre la NFL.

## 5. Pick'em — backtest walk-forward 2011-2025

`python nfl/PICKEM/backtest_pickem.py` — field: N rivales que aciertan el
pick del favorito con prob q_j ~ U(0.75, 0.95) (supuesto explícito).

- **Pots acumulados (Small 1/2, Big):** favorito en todo = EV-máx. Rinde
  66.6% (~10 de 15 pts/semana). P(1º) contra ese field: Small ~50%/16%
  (N=10/20), **Big Pot 84%/53%**. La maratón premia la disciplina del
  favorito. [Sensible al field model: contra rivales q→1 la ventaja se
  encoge.]
- **Batalla Semanal (winner-take-all):** con favoritos puros
  **P(1º único) = 1.9% (N=10) / 0.0% (N=20)** — empatas con el mejor del
  field y el pozo rueda. **Volteando 1-3 coin-flips** (partidos más cercanos
  a 50%): P(1º único) sube a **11-15% / 3.5-9.7%**, costando 0.05-0.15
  pts/semana (~1-2.6 pts/temporada). La lección de perturbación mínima de
  CSC, tal cual.
- **Trade-off (una sola planilla juega las 4 apuestas):** 1 flip/semana casi
  no mueve los pots (84%→79% N=10; 53%→53% N=20) y multiplica la Batalla.
  **Decisión: favoritos + 1-2 flips en coin-flips.** Si cerca del corte vas
  detrás en un pot, sube flips (al perdedor le pagan la varianza); si vas
  adelante, flips=0.

## 6. Operatividad 2026

- **`python nfl/semana.py`** — el comando de cada semana: favoritos +
  coin-flips del Pick'em, y pick Survival de la heurística marrano
  (`--usados KC,PHI` para los equipos ya quemados). Verificado con las
  líneas reales de la semana 1 de 2026: pick LAC vs ARI (82.4%, contra
  marrano, élite intacta).
- Refrescar `games.csv` el día que se metan los picks (las líneas se mueven).
- El cierre del Survival es ÚNICO (jueves): meter el pick miércoles.

## 8. N=14 y la alianza de 2 (dato del usuario, 2026)

Somos **14 en ambos juegos** y hay opción de **aliarse con un amigo** (banca
compartida). Pozos reales: Survival $4.2M; Batalla Semanal $650k/semana al
ganador único; Small Pots $1.3M; Big Pot $2.6M.

**Survival** (`python nfl/SURVIVAL/alianza.py`): el punto fino es que dos
jugadores marrano SIN coordinar toman el MISMO pick todas las semanas
(rutas 100% correlacionadas — la "alianza" no diversifica nada). La
coordinación = cada semana B toma su mejor opción excluyendo el pick de A.
Resultado: rutas distintas en 14/15 temporadas, y por cabeza (field normal):

| config | E[neto]/cabeza | P(la banca cobra) |
|---|---|---|
| solo (los otros 13 son field) | +$0.63M | 32% |
| alianza descoordinada (mismos picks) | +$0.22M | 32% |
| **alianza coordinada (rutas distintas)** | **+$0.47M** | **51%** |

Lectura correcta: como el amigo juega de todas formas, la comparación real
es descoordinada vs coordinada — **coordinarse duplica el E[neto] por
cabeza y sube P(cobrar) de 32% a 51-62%**. La alianza es ante todo
reducción de varianza; no crea EV de la nada (jugar solo sigue teniendo el
mayor ROI individual: +$0.63M).

**Pick'em, Batalla Semanal** (`python nfl/PICKEM/alianza.py`): con las dos
planillas idénticas en favoritos la banca PIERDE (−$46k/semana esperados:
un rival gana solo el 51% de las semanas, la banca el 0.8%). Con flips
complementarios (A voltea el coin-flip #1; B los #2 y #3):

| (A,B) flips | P(banca 1º única) | E[neto banca]/semana |
|---|---|---|
| (0,0) idénticos | 0.8% | −$46k |
| (1,1) distintos | 11.6% | +$30k |
| **(1,2) disjuntos** | **17.4%** | **+$68k** |

**Pots acumulados:** la banca compara su MEJOR planilla contra el mejor
rival — dos planillas descorrelacionadas suben P(Big Pot) de 75% a 82% y
P(Small Pot) de 37% a 56% con (1,2). Los flips de la Batalla salen gratis
en la maratón. [Todo esto bajo el field model q~U(0.75,0.95); es supuesto,
no dato.]

**Decisión 2026:** alianza coordinada en ambos juegos. Survival: A marrano,
B marrano-excluyendo-a-A (el `--usados` de `semana.py` maneja los dos
inventarios). Pick'em: A favoritos + flip del coin-flip #1, B favoritos +
flips de los coin-flips #2 y #3. Reparto de banca: acordar por escrito
ANTES de la semana 1 (sugerido 50/50 sobre flujos netos de ambos juegos).

## 9. Preguntas abiertas / siguientes pasos

1. ¿Yahoo muestra la **distribución de picks** del grupo antes del cierre?
   Si sí, el field model deja de ser supuesto y se puede esquivar el pick
   masivo con datos (anticrowd informado, no ciego).
2. Semanas 15-18 del Survival: si la banca sigue viva contra 1-2 rivales,
   cambia a juego head-to-head (bloquear/espejar picks) — no modelado aún.
3. Falta de líneas en semanas futuras de 2026: hoy solo la semana 1 tiene
   moneyline; el plan élite/marrano usa Elo hasta que se publiquen.
4. Si el N real cambia (retiros antes del kickoff), re-correr `alianza.py`:
   la sensibilidad al tamaño ya está en `backtest_survival.py`.
