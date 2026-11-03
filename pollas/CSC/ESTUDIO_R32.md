# Estudio R32 (16avos) — dispersión de cupos y dinámica de knockout

Análisis hecho el **28/06/2026** para decidir cómo enviar los 5 cupos de R32.
Reproducible: `python pollas/CSC/experimento_r32.py` (lee `r32_odds_snapshot.json`,
no necesita API key). Estado al cierre de grupos (PDF 27/06): vamos **#2 a −1**
del líder (B4=276 vs 277), los 5 cupos en el top 14 de 114.

## 1. ¿Cómo repartir los 5 cupos? (dispersión)

Comparamos 4 formas de construir los 5 cupos, midiendo P(quedar 1º), P(podio),
nº de cupos al premio y **E[% del pozo]** (premio 50/20/15/10/5%), con 30k
torneos y campo rival real, bajo 3 supuestos de dureza del campo:

- **idénticos**: los 5 = EV-máximo (correlación total).
- **perturbada n3**: ancla + 2º mejor en ≤3 partidos *empatados* (gap_max=0.30).
- **MIXTO**: ancla + 2 perturbados (protegen podio) + 2 "lotería" (2º y 3º fill
  en todo, en los cupos de atrás).
- **ESCALÓN**: cupo k = k-ésimo mejor fill en *todos* los partidos (dispersión máxima).

**Hallazgos (robustos al supuesto de campo; lo absoluto no, lo relativo sí):**

- **Más dispersión sube P(1º) pero baja E[$].** Para *ganar* (premio top-heavy)
  conviene separarse; para *recaudar* (premios secundarios) conviene agruparse.
- **El MIXTO Pareto-domina a la perturbada simple**: misma (o más) E[$] y más
  P(1º). Mete 3 cupos cerca del podio y 2 billetes de lotería al #1, casi gratis
  (esos 2 ya iban rezagados a 250/243).
- **El ESCALÓN maximiza P(1º)** (~81% campo blando) pero **sacrifica pozo**
  (~59% vs ~64%) y casi nunca cobra premios múltiples (#top5 ~2.1 vs ~2.7).
- **Cuanto más afilado el campo, más paga decorrelacionar**: con rivales sharp
  los idénticos caen a P(1º)=0% (empatan y la rifa reparte); separarse es la
  única vía al #1.

## 2. Dinámica de knockout (ajuste 120')

Las cuotas son de **90'** (tiempo reglamentario) pero CSC puntúa el resultado a
**120'** (tras alargue). Un empate a 90' suele **resolverse en el alargue**, así
que predecir `1-1` sobreestima que *siga* empatado. El ajuste mueve una fracción
`delta` de cada empate a marcador decidido, sesgado al favorito (gol en el alargue).

Con `delta=0.45` (45% de los empates a 90' se deciden en el alargue):

- **Empates esperados: 3.81/16 → 2.10/16.** Mucho más realista (≈2 a penales, no ≈4).
- **4 picks cambian** de `1-1` a decidido: Países Bajos, México, Bélgica → `2-1`;
  Australia → `1-2`. Son los partidos cerrados que ya decorrelacionábamos.
- **Bajo la realidad 120', las P(1º) caen y el ESCALÓN pierde ventaja**: gran
  parte de su brillo venía de escenarios con muchos empates (poco realistas). El
  MIXTO sigue siendo el mejor balance.

**Implicación operativa:** aplicar un ajuste 120' suave (no concentrar empates),
y repartir los `1-1` restantes entre cupos (que ~2 partidos sí empatan, pero no
sabemos cuáles → unos cupos los cubren y otros no). Eso ataca las dos cosas:
realismo (menos penales predichos) y cartera (empates no concentrados en el ancla).

## 3. Decisión

- **Esquema: MIXTO** (mejor balance P(1º)/E[$]; Pareto-mejor que la perturbada).
  El ESCALÓN queda como opción "todo al #1" si se prioriza ganar sobre recaudar.
- **Marcadores: ajuste 120' suave** para no predecir tantos penales y repartir
  los empates entre cupos.

> Caveat honesto (heredado del proyecto): los valores absolutos (p. ej. "64% del
> pozo") dependen del modelo de rivales y están inflados por la ventaja supuesta.
> Lo robusto es lo **relativo** (MIXTO > perturbada en ambos ejes; el escalón
> cambia P(1º) por E[$]; el ajuste 120' encoge la ventaja de la dispersión máxima).
