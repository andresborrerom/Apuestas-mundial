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

**Decisión 2026 (criterio del usuario: máximo esperado neto PROPIO → se
juega SOLO).** La alianza con banca reparte mejor el EV pero no lo sube; el
esperado neto individual manda en ambos juegos:

*Survival — tu neto individual según qué haga el amigo (θ=25):*

| escenario | E[neto] tuyo |
|---|---|
| **solo (amigo juega como field)** | **+$0.67M** |
| amigo COPIA tus picks (sin banca) | +$0.24M ← el peligro |
| pacto sin banca: tú 1ª opción, él 2ª | +$0.66M |
| alianza con banca coordinada | +$0.47M/cabeza |

*Pick'em — tu neto individual:* Batalla con flips=2 solo: +$37k/semana (vs
+$34k/cabeza aliado). Pots solo con flips=1: Big +$1.67M, Smalls +$0.31M
(vs ~$0.95M/cabeza aliado — la planilla del socio te canibaliza, porque tu
P(1º) ya es alta). **Solo gana en los dos juegos.**

**La condición para que "solo" sea óptimo: que el amigo NO copie tus
picks.** Si copia (probable si compartes el modelo), tu Survival cae de
+$0.67M a +$0.24M. El seguro barato: pacto SIN banca donde tú tomas la 1ª
opción y él la 2ª — tu EV queda intacto (+$0.66M) y él mejora vs copiarte.
Regla práctica: los picks no se comparten antes del cierre, o se comparte
el modelo CON el pacto de rutas.

## 9. Perfeccionamiento del juego en solitario (refinamientos probados)

Cuatro ideas de mejora, cada una vuelta experimento. **Dos refutadas, una
confirmada, una operativa** — se documentan todas (regla de honestidad):

1. **Params del marrano por nested walk-forward** (elegidos por temporada
   solo con el pasado) — `experimento_afinar_marrano.py`: **REFUTADO**
   (11.1 sem. vs 11.9 del fijo; +$0.37M vs +$0.62M). El nested converge
   solo a (0.70, bottom-5) desde 2015 → el default a priori no estaba
   sobreajustado. El marrano se queda como está.
2. **Consciente de vidas** (con 1 vida → cambiar a máxima p): **REFUTADO y
   fuerte** (9.5 sem., E[neto] ≈ 0). Perder una vida y volver a la manada
   es exactamente el error: el descuento estructural del marrano vale
   también con la última vida.
3. **Política de flips con la plata completa** — `PICKEM/temporada.py`
   simula la temporada entera con las reglas reales de la Batalla
   (acumulación tope 2, liquidación forzada en cortes) + Smalls + Big,
   N=14, 300 sims × 15 temporadas × 3 semillas:

   | política | E[batalla] | E[pots] | E[TOTAL]/temp. | P(total>0) |
   |---|---|---|---|---|
   | m0 (favoritos puros) | −$0.52M | +$2.69M | +$2.17M | 80% |
   | m1 | +$0.80M | +$2.51M | +$3.32M | 84% |
   | **m3** | **+$1.60M** | **+$2.14M** | **+$3.75M** | **87%** |
   | m5 | +$1.76M | +$1.43M | +$3.20M | 84% |
   | dinámica (según standing) | +$1.10M | +$2.18M | +$3.28M | 84% |

   **Decisión: 3 flips fijos** (meseta m1-m3, pico estable en m3 con 3
   semillas; desde m4 los pots sangran más de lo que la Batalla paga). La
   política dinámica según standing **no mejora** las estáticas: refutada
   (al menos esta versión; con datos reales de standing se puede revisar).
4. **Operatividad** — Action `.github/workflows/nfl-semana.yml`: cada
   miércoles 8am Colombia (sep-ene) refresca líneas y publica los picks en
   un issue. Los equipos quemados del Survival viven en
   `nfl/SURVIVAL/usados_2026.txt` (anotar ahí el pick real de cada semana;
   `semana.py` lo lee solo).

## 10. ESPN NFL Pick'em nacional — vía hermano/sobrino en Seattle

**Actualización:** el usuario tiene hermano y sobrino en Seattle
(residentes elegibles; el sobrino debe ser 18+). Con eso el concurso pasa
de descartado a jugable con 20 entradas (10 por persona). Análisis en
`nfl/ESPN/backtest_espn.py`, entradas semanales en `nfl/ESPN/entradas.py`:

- **Confidence es el modo a entrenar** (edge por rival +24.2 pts sobre 50%
  vs +18.8 de Standard, 260 semanas): rankear los 16 partidos por P
  calibrada es el óptimo teórico y el público ordena "a ojo" (nuestro
  score 72.2% del máximo vs 64.0% del público). Score casi continuo →
  menos empates → la habilidad se ve. Una entrada pura por persona.
- **Standard**: sin habilidad de ordenar, solo colas. Con 20 entradas
  descorrelacionadas (favoritos + 1-3 flips escalonados en los más
  parejos), alguna entrada pega semana 15+/16 en **15.4%** de las semanas
  (vs 2.3% con una) — la máquina de tiquetes para premios semanales.
- Spread y Pick 5: sin edge (el spread ES el mercado); se llenan con el
  pick de Vegas tal cual solo para habilitar el bono de $5K por completar
  los 4 modos.
- Pendiente (lo ven ellos en la app): la tabla exacta de premios por modo
  (semanal vs temporada) y el tiebreaker del semanal.

Notas del análisis original (siguen vigentes):

Concurso gratis de ESPN (58 premios, US$102K, modos Standard/Spread/Pick 5/
Confidence, hasta 10 entradas). Verificado 2026-08-22:

- **Elegibilidad para premios: solo residentes legales de los 50 estados de
  EE.UU. + DC y Canadá (sin Quebec), 18+.** Es el texto estándar de toda la
  familia de sweepstakes de ESPN (confirmado en las reglas oficiales de
  Pigskin Win Totals; el juego se puede *jugar* desde afuera, pero al
  verificar al ganador piden residencia). **Desde Colombia no se puede
  cobrar → EV = $0.**
- Aun siendo elegible: pool nacional de cientos de miles de entradas. Con
  nuestro edge (66.6% vs ~62-64% del público), P(1º) es de lotería —
  E[premio] de centavos. La plata real está en pools chicos (N=14) donde
  el edge por rival es grande. Confirma la regla de suma cero del PLAYBOOK.
- Si algún día se juega por diversión: los modos donde el modelo aporta son
  **Standard** (favoritos directo) y **Confidence** (rankear los 16 picks
  por P calibrada — ventaja directa nuestra). **Spread y Pick 5 NO**: el
  spread ES el mercado, cada pick es ~50/50 por diseño y no hay edge barato.

## 11. La caza de edge REAL contra la línea de cierre (sprint completo)

Mandato del usuario: dejar de asumir eficiencia y buscar edge con datos de
verdad (clima, estilos, QB vs DL, viajes...). Se corrieron 3 baterías con
protocolo anti-multiplicidad (hipótesis declaradas antes de mirar, K
explícito, split-half 2002-13 vs 2014-25, walk-forward para candidatos).

**Batería 1 — situacionales** (`nfl/EDGE/buscar_edge.py`, K=15, n=6.208
partidos 2002-2025): home dogs, dogs divisionales, bye, semana corta,
jueves, viento 15/20mph, frío vs equipos de domo/ciudad cálida, viajes de
2+ husos horarios (mapa de 32 equipos), primetime, diciembre outdoor.
**Resultado: CERO candidatos** (todo |z|<1.5).

**Batería 2-3 — QBs y matchups de estilo** (`nfl/EDGE/matchups.py`, K=7,
con EPA por pase/carrera de nflverse stats_team_week 2003-2025, perfiles
walk-forward con shrinkage a la temporada previa): QB titular nuevo, aire
vs muro aéreo, tierra élite vs colador, cazadores de sacks vs O-line
comilona, shootouts. **Resultado: CERO candidatos.**

**G5, la prueba reina:** logística walk-forward logit(p) ~ mercado + 4
features de matchup EPA + QB nuevo, entrenada en temporadas previas,
testeada 2011-2025: **mejora media −0.0006 de log-loss — agregar EPA
EMPEORA fuera de muestra. La línea de cierre ya digirió el EPA público.**

Migajas consistentes en ambas mitades pero NO significativas (se anotan,
no se usan): dog divisional sobre-preciado (−0.024), viento castiga
favoritos (−0.021), QB nuevo sobre-preciado (−0.019), y favoritos grandes
p≥0.80 infra-preciados (+0.011) — esta última **respalda al marrano** (los
picks ~0.80 valen si acaso más de lo que dice el de-vig).

**Conclusión (documentada, no maquillada):** con datos públicos no hay
edge explotable contra el cierre de Vegas. El edge real de este proyecto
es ESTRUCTURAL y ya está montado: (1) ganarle al field, no a Vegas
(marrano, flips, ranking calibrado); (2) cobertura de colas con volumen.

## 12. El ejército (≈50 personas elegibles en USA, 10 entradas c/u)

`nfl/ESPN/ejercito.py` — entradas = favoritos + combos de flips sobre los
12 partidos más parejos, ordenadas por P(patrón), ground truth 2011-2025:

| entradas | P(alguna semana 15+/16) | P(alguna PERFECTA 16/16) |
|---|---|---|
| 20 | 12.6% | 3.9% |
| 100 | 30.3% | 10.0% |
| **500** | **55.4%** | **27.7%** |

Con 500 entradas, una semana perfecta cae más de 1 de cada 4 semanas: eso
es cobertura sistemática de caminos de upsets que el público no cubre —
el "camino aleatorio donde no vemos edge" del usuario, pero guiado por
P(patrón). Confidence no necesita ejército (1 entrada óptima por persona
es el tope; el resto del cupo va a Standard). Operativa: cada persona real
maneja SU cuenta (límite de ESPN: 10 entradas/persona) y nosotros
mandamos la hoja semanal por correo. Pendiente: tiebreaker del premio
semanal y tabla de premios por modo (verlos en la app).

## 13. Apuestas reales (investigación E1-E3) — los primeros candidatos VIVOS

Contexto: el usuario (vive en Panamá) explora apostar vía su hermano en
Seattle. **Regla de cumplimiento primero:** las casas de EE.UU. exigen que
quien apuesta esté en el estado licenciado; el *proxy betting* (operar la
cuenta de otro) viola términos y arriesga confiscación. El camino limpio:
el hermano apuesta su cuenta con su decisión; la investigación se comparte.

**E1 — VIENTO vs TOTALES (`nfl/EDGE/viento_totales.py`)** — primer
candidato real de toda la cacería. Con cuotas de CIERRE 2010-2025 (n=977
partidos outdoor, viento >=10 mph): el under pega 56.2% con viento 10-15
(z=+3.18), el efecto muere en 20+ (las casas sí castigan el viento
extremo, descuentan de menos el moderado). **ROI under viento>=10: +7.7%
tras vig, 2.51σ sobre cero, 12/16 temporadas positivas.** Implementable:
los totales se apuestan hasta minutos antes del kickoff, cuando el viento
del estadio ya es ~conocido (nuestro dato es viento observado ≈ apostable
tarde). Estado: **candidato a paper trading 2026** — registrar cada
apuesta hipotética antes del kickoff y medir un año antes de plata real.

**E2 — APERTURA vs CIERRE (`nfl/EDGE/apertura_cierre.py`)**, SBRO
2013-2020 (n=2.129, mirror en `nfl/datos/sbro/`; aussportsbetting y el
sitio original bloqueados por proxy/reestructura):
  - El cierre predice mejor que la apertura (MAE 10.02 vs 10.11) — la
    información fluye toda la semana. Contra el CIERRE no hay nada (§11);
    contra la APERTURA sí hay juego.
  - **Seguir el vapor cubre la apertura 56.9% (mov>=1) a 59.2% (mov>=2,
    n=645)** — muy sobre el break-even 52.4%. El edge vive en saber ANTES
    hacia dónde se mueve la línea.
  - Viento: el mercado lo mete casi todo desde la apertura (el total solo
    baja 0.5-0.8 más en semana); el under ventoso rinde ~igual contra
    apertura (59.1% a 10-15) que contra cierre.

**E3 — ¿PRONOSTICAMOS el vapor? (`nfl/EDGE/predecir_vapor.py`)**: nuestro
Elo (puro resultados, walk-forward, pendiente ajustada solo con
2002-2012) vs la apertura 2013-2020: la línea se mueve hacia el lado del
Elo 55-59% de las veces, y ese lado cubre la apertura **54.3%** (gap>=0.2,
n=1115, ROI≈+3.7% a -110). Fino pero positivo — con el modelo MÁS tosco
posible. El programa de investigación: mejorar el pronosticador de vapor
(cierres de la semana pasada + lesiones con timestamps + QB) y re-testear.

**Tablero honesto:** cierre = muro (22 hipótesis muertas, §11). Apertura =
blanda (vapor 57-59%, Elo-vs-apertura 54.3%). Viento-under = candidato
+7.7% ROI en paper trading. Nada de plata real hasta que el paper trading
de una temporada confirme — y aún así, las casas limitan ganadores.

## 14. E4 — Anatomía del vapor (`nfl/EDGE/vapor_profundo.py`, K=8)

Qué más hay en el movimiento apertura→cierre (SBRO 2013-2020, split-half
estable 56.7%/57.2%):

- **V1 dosis-respuesta:** movimientos de medio punto son RUIDO (cubren
  46.6% — ni seguirlos); el vapor real arranca en 1+ punto y satura:
  1.5-2.5 → 57.9%, 2.5+ → 59.5%.
- **V3 números clave (la joya):** cuando el movimiento CRUZA el 3 o el 7
  cubre **62.6%** (n=190, ±3.6) vs 55.9% si no cruza. Pagar el costo de
  cruzar un número clave = el mercado está seguro.
- **V2 asimetría:** vapor hacia el underdog 58.1% vs hacia el favorito
  55.8% (dirección esperada — el sharp va al dog — pero no concluyente).
- **V4 totales:** el vapor también funciona en totales (mov ≥2 → 58.3%,
  n=714).
- **V5 (la conclusión operativa):** contra el CIERRE el vapor cubre
  **50.4%** — el cierre absorbe TODO. No existe "seguir el vapor tarde":
  el juego entero es ser temprano.
- **V6 overshoot:** 48.4% vs cierre en movimientos grandes — insinúa
  contra-valor pero dentro del ruido. No accionable.
- **V7 estación: REFUTADA** — el vapor de semanas 1-4 cubre MENOS (54.7%
  vs 57.6%); las aperturas tempranas no son más blandas.
- **V8 vapor×Elo (el hallazgo):** cuando el Elo y el movimiento COINCIDEN
  el lado cubre la apertura **60.4%** (n=384, ±2.6). Cuando chocan: 50/50
  — el dinero informado neutraliza al modelo. Ojo: 60.4% condiciona en
  observar el movimiento (futuro al momento de apostar la apertura); la
  versión implementable necesita líneas INTRA-semana.

**Infraestructura nueva:** `nfl/EDGE/snapshot_odds.py` + Action
`nfl-snapshot-lineas.yml` — 2 snapshots diarios de spread/total/ML de
todas las casas (The Odds API, ~60 req/mes del free tier), apilados en
`nfl/datos/snapshots/`. Desde la semana 1 de 2026 construimos NUESTRO
dataset intra-semana: el insumo del pronosticador de vapor v2 (¿a qué
hora del día se mueve?, ¿qué casa mueve primero?, reverse line movement).

## 15. Preguntas abiertas / siguientes pasos

1. ¿Yahoo muestra la **distribución de picks** del grupo antes del cierre?
   Si sí, el field model deja de ser supuesto y se puede esquivar el pick
   masivo con datos (anticrowd informado, no ciego).
2. Semanas 15-18 del Survival: si la banca sigue viva contra 1-2 rivales,
   cambia a juego head-to-head (bloquear/espejar picks) — no modelado aún.
3. Falta de líneas en semanas futuras de 2026: hoy solo la semana 1 tiene
   moneyline; el plan élite/marrano usa Elo hasta que se publiquen.
4. Si el N real cambia (retiros antes del kickoff), re-correr `alianza.py`:
   la sensibilidad al tamaño ya está en `backtest_survival.py`.
