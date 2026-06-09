# CSC — Bitácora: enseñanzas, decisiones y cómo correr

Registro vivo de qué construimos, qué aprendimos y por qué. Polla:
**La Super Polla de los Pollos 2026** (reglas en el PDF de esta carpeta).

---

## 1. Reglas que mandan en todo (validado contra el PDF)

Puntaje por partido = suma de tres componentes independientes:
- **Ganador/empate** (tendencia 1X2).
- **Goles exactos del local.**
- **Goles exactos del visitante.**

Goles premian a cada equipo por separado; **más goles acertados = más puntos**
(`# goles + base`), salvo el 0 (puntaje fijo `cero`, menor). Los puntos **suben
por ronda**:

| Ronda | ganador | goles=0 | goles≠0 |
|---|---|---|---|
| primera | 1 | 2 | #goles + 3 |
| dieciseisavos | 2 | 3 | #goles + 5 |
| octavos | 3 | 4 | #goles + 7 |
| cuartos | 4 | 6 | #goles + 10 |
| semis | 5 | 8 | #goles + 12 |
| tercer_puesto | 6 | 10 | #goles + 14 |
| final | 8 | 12 | #goles + 16 |

Los 6 ejemplos del PDF están replicados como tests (`tests/test_motor.py`).

---

## 2. Decisiones del modelo (y por qué)

1. **Fuente de cuotas: consenso de muchas casas** (The Odds API, mediana), no
   Rushbet (sin API pública y se mueve con el consenso). Más robusto.
2. **Quitar el margen** de la casa → probabilidades reales. Default
   `proporcional` (validado: el método casi no cambia el resultado).
3. **Goles con Poisson + Dixon-Coles**, ajustando λ al 1X2 + Over/Under.
4. **No se rellena con el marcador más probable**, sino con el que **maximiza
   puntos esperados** según las reglas de la ronda. Esto es el corazón.
5. **Optimización POR RONDA**: el relleno óptimo cambia con la tabla de puntos
   (ej. México 2-1 en grupos → 1-0 en la final: en rondas altas la `base` crece
   y conviene el conteo más probable, no arriesgar goles).
6. **Sesgo hacia gol=1** (`sesgo_goles`, default 0.05): el modelo predice "0"
   de más y "1" de menos, y la regla premia más el "1". Validado **walk-forward**
   (+~0.03 pts/partido fuera de muestra). Se aplica **solo para elegir el
   relleno**; las probabilidades reportadas son las reales.
   - Variantes probadas y **REFUTADAS** (ground truth, no mejoran el constante):
     sesgo asimétrico al favorito (`experimento_sesgo_favorito.py`) — el 1X2 ya
     está en el modelo; y sesgo λ-dependiente (`experimento_sesgo_lambda.py`) —
     el "0 de más" es parejo entre partidos. **El α constante basta.**

---

## 3. Validación empírica (ver RESULTADOS_BACKTEST.md)

- ~12k partidos reales (football-data.co.uk) con cuotas de cierre y resultado.
- **Edge real:** EV-máximo +0.285 pts/partido vs "modal" y +0.967 vs
  "favorito 1-0". Calibración 1X2/Over-Under/goles: muy buena.
- **Walk-forward:** el edge y el sesgo **persisten fuera de muestra** (sin
  sobreajuste).

---

## 4. ¿Cuántos cupos? (suma cero)

La polla reparte el 100% del recaudo (premios 50/20/15/10/5%). Solo hay utilidad
positiva si superamos al participante promedio. El edge medido sitúa al rival
realista en **field-skill ≈ 0.4–0.6**. Bajo ese supuesto, el óptimo son **pocos
cupos (≈2–4)** con la estrategia adecuada (ver §5). Comando:

```bash
python pollas/CSC/cupos.py --participantes <N> --field-skill 0.5
```

---

## 5. Colas y aleatoriedad mínima (RESUELTO)

Hipótesis (correcta): con premio top-heavy importa **P(que UNA entrada quede de
primera)**, no el promedio. Cupos idénticos están 100% correlacionados → suben y
bajan juntos. Una **perturbación mínima** (cambiar al 2º mejor relleno solo en
partidos donde 1º y 2º están casi empatados en EV) descorrelaciona casi sin
perder media. Experimento: `pollas/CSC/experimento_colas.py`.

Resultado (k=3, N=120, field-skill 0.5, simulando ranking):

| Estrategia | E[util] | P(1º) | P(premio) |
|---|---|---|---|
| evmax (idénticas) | $243k | 2.0% | 15% |
| **perturbada n=15** | **$823k** | **8.9%** | **36%** |
| diversificada (mucho azar) | ~$0 | 1.9% | 15% |
| mano: siempre 2-1 | −$181k | 0.7% | 2% |
| mano: modal | −$65k | 1.4% | 5% |

Hallazgos:
- **La perturbación mínima domina** a las copias idénticas en TODO nivel de
  field (incluso 0.9, donde evmax ya pierde). Sube P(1º) ~4x y la media.
- **"Demasiado azar" (diversificada) mata el edge.** El punto dulce es chico:
  **n_swaps ≈ 15** (gana ~78% del máximo sin alejarse del modelo).
- **El downside está acotado** a lo que compras (peor caso = perder los cupos);
  por eso se optimiza la **cola de arriba** (P(1º)/P(premio)), no la de abajo.
- Con perturbación, **cada cupo extra sigue sumando** (a diferencia de las
  copias idénticas, que se estancan), porque están descorrelacionados.

**Robustez al modelo de rivales** (`experimento_rivales.py`): rivales como
MEZCLA de arquetipos (motor.generar_field_mix): "cal" (muestrea de M, idea del
usuario), "hum" (cerca del modal, humano), "opt" (EV-máximo). Resultado: la
**perturbación le gana a las copias idénticas en TODAS las mezclas** (k=4,
N=100), y el efecto crece cuando los rivales son buenos (evmax colapsa a ~5% de
P(1º), perturbada ~47%). Matiz: el "calibrado puro" es el field más FÁCIL (los
rivales que muestrean dispersan y puntúan poco); los humanos reales se
concentran en el modal y son más duros. Los valores absolutos varían mucho con
el supuesto → confiar en lo RELATIVO (perturbar > idénticas; diferenciarse).

**Dispersión CRECIENTE por ronda** (`experimento_dispersion_rondas.py`,
`motor/torneo.py`): la polla paga por el TOTAL acumulado; en grupos (72
partidos) la ley de grandes números ya protege nuestra ventaja → perturbar ahí
es casi desperdicio; en eliminatorias (pocos partidos, cada uno vale ×5 a ×16)
cada swap descorrelaciona mucho más. Test con MISMO presupuesto (24 swaps, 6
semillas, simulación de torneo completo):

| dónde se pone la dispersión | P(1º) |
|---|---|
| todo en grupos | 17.7% |
| uniforme | 25.7% |
| **knockout-pesado** | **30.0%** |

→ El modelo NO es único por ronda en DOS ejes: (a) el relleno EV-máximo cambia
con los puntos de la ronda (ground truth), y (b) la **dispersión óptima sube por
ronda** (simulación). Operacionalizado en `llenar.py` (`DISPERSION_POR_RONDA`):
grupos 12 · 16avos 8 · octavos 5 · cuartos 3 · semis 2 · 3º/final 1. Honesto:
(a) es medible en ground truth; (b) depende del modelo de rivales (simulación).
Pendiente: en rondas de 1-2 partidos conviene cubrir el top-k de rellenos
distintos (no swaps aleatorios) — afinar al llegar.

**Estrategia adoptada:** comprar K cupos con perturbación CRECIENTE por ronda
(cupo 1 = EV-máximo; cupos 2..K = 2º mejor en los casi-empatados, pocos en
grupos y muchos en eliminatorias). Generarlos:

```bash
python pollas/CSC/llenar.py --all --cupos 4 --csv grupos.csv
```

**Recomendación de K:** 4 cupos es el balance (captura P(premio)~43%, robusto si
el field es más sharp, costo $400k). Si crees que el field es muy casual y el
presupuesto lo permite, 5–6 siguen siendo +EV en el modelo; si conservador, 3.

---

## 6. ¿Cambia la relación cuotas↔resultados en Mundiales? (validado)

Datos: paquete R `oddor` (gratis) — 1X2 de cierre + goles reales de los 4
Mundiales 2010–2022 (256 partidos). Script `backtest_mundial.py`.

- **1X2:** razonablemente calibrado también en Mundial (más ruidoso, n chico).
- **Goles:** el Mundial es **más defensivo** (marca 0 más seguido que en clubes:
  0.291 vs 0.251). Pero el **modelo sigue prediciendo "0" de más** (0.341 vs
  0.291) → **el sesgo a gol=1 sigue siendo correcto en Mundiales** (+0.035 pts).
- **Edge EV-máximo vs modal: +0.48 pts/partido** (mayor que el +0.285 de clubes;
  el Mundial tiene más mismatches de grupo donde optimizar goles rinde más).

**Conclusión:** el modelo transfiere bien al Mundial; no hace falta comprar
datos ahora. Confound: solo hay 1X2 de Mundial (sin Over/Under); parte del "0 de
más" podría ser el O/U faltante. Mejora futura **gratis**: scrapear OddsPortal
(OddsHarvester) para O/U y marcador exacto de Mundiales y recalibrar.

Fuentes de histórico de Mundial (del agente): `oddor` (gratis, 1X2 de 4
Mundiales) ✅ usado; OddsPortal+scraper (gratis, +O/U +marcador exacto, zona
gris ToS); The Odds API histórico (solo 2022, $30/mes).

---

## 6. Runbook — correr por ronda

`llenar.py` infiere la ronda por fecha, pero puedes forzarla con `--round`.
Necesitas `export ODDS_API_KEY=tu_key`.

```bash
# FASE DE GRUPOS (primera) — toda de una (deadline: antes del 1er partido)
python pollas/CSC/llenar.py --all --csv grupos.csv

# Una ronda eliminatoria concreta (cuando se sorteen los cruces):
python pollas/CSC/llenar.py --round dieciseisavos --csv 16avos.csv
python pollas/CSC/llenar.py --round octavos       --csv octavos.csv
python pollas/CSC/llenar.py --round cuartos        --csv cuartos.csv
python pollas/CSC/llenar.py --round semis          --csv semis.csv
python pollas/CSC/llenar.py --round tercer_puesto  --csv tercero.csv
python pollas/CSC/llenar.py --round final           --csv final.csv

# Día específico (la ronda se infiere de la fecha):
python pollas/CSC/llenar.py --date 2026-06-15
```

Notas por ronda:
- El relleno se recalcula con la tabla de puntos de esa ronda (automático).
- En eliminatorias cuenta el resultado **tras 120 min** (penales no) y se puede
  apostar al empate. Si la casa publica cuotas "tras alargue", úsalas.
- **Pendiente eliminatorias:** re-tunear `--sesgo-goles` por ronda (el 0.05 se
  validó con puntos de *primera*). Mientras tanto 0.05 es razonable.

Deadlines de envío (hora Colombia): primera 11/06 1:59pm · dieciseisavos 28/06
1:59pm · octavos 04/07 11:59am · cuartos 09/07 2:59pm · semis 14/07 1:59pm ·
3º/4º 18/07 3:59pm · final 19/07 1:59pm.
