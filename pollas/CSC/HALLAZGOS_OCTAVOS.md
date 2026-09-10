# CSC Octavos — hallazgos de las simulaciones (4-jul-2026)

Dos análisis con ground truth: (1) proyección competition-aware sembrando los
puntajes reales del PDF 3-jul, y (2) walk-forward sobre los 16 partidos de R32
ya jugados (resultados a 120', que es lo que CSC usa).

## Punto de partida (PDF 3-jul) — dominamos

- Field: 114 cupos (109 rivales + nuestros 5). Media 297, mediana 301, sd 46.
- Top-5 actual: **B4 393 (#1) · Rafael Muñoz 384 (#2) · B1 381 (#3) · Carvajal 378 (#4) · B2 372 (#5)**.
- Tenemos **3 de los 5 puestos de premio**. El nuevo es Rafael Muñoz (se metió a #2).

## Hallazgo 1 — octavos REORDENA fuerte (el liderato es frágil por partido)

La cosecha de octavos del ancla EV-máx es ~57 pts de media pero con **sd alta**:
la base de goles sube a 7, así que un 2-1 exacto vale 3+9+8 = **20 pts en un solo
partido**. Sobre 8 partidos, los reordenamientos de ±40-60 son normales. Nuestra
ventaja de 9 pts sobre el #2 es chica frente a esa varianza — PERO tenemos 5
entradas y lideramos en anchura, así que igual dominamos.

## Hallazgo 2 — la dispersión MIXTA defensiva es la óptima (robusta al field)

Premio esperado (pozo ~114 cupos × $100k) y prob. de podio, por estrategia y
según qué tan "sharp" sea el field (sensibilidad):

| Field | evmax | **mixto_def** | mixto_agr | todo_loteria |
|-------|------:|----------:|----------:|-------------:|
| casual | 6.95M | 7.07M | **7.15M** | 6.79M |
| mixto  | 7.68M | **7.71M** | 7.66M | 7.34M |
| sharp  | 7.56M | **7.60M** | 7.59M | 7.26M |

- **mixto_def gana o empata en los 3 escenarios** (mejor en mixto/sharp, casi en casual).
- **evmax (los 5 iguales) pierde**: 5 cupos idénticos están perfectamente
  correlacionados; descorrelacionar suave captura ~0.1 slot más de top-5.
- **todo_loteria** sube P(1º) pero baja E[slots] (2.2 vs 2.6) y el premio esperado:
  no vale la pena sacrificar plata cuando ya dominamos.
- En TODOS los casos: **P(algún premio) ~99-100%, E[slots en top-5] ~2.5-2.6,
  P(quedar 1º) ~85%**. Posición dominante.

**Decisión: modo `defender` (mixto_def).** Es lo que ya generó `generar_octavos.py`.

## Hallazgo 3 — walk-forward R32: el edge del EV-máx es REAL (+21 pts/ronda)

Sobre los 16 partidos de R32 con resultados reales (120'):

| Esquema | Cosecha R32 real |
|---------|-----------------:|
| **EV-máx (ancla)** | **117** |
| 3º fill (lotería) | 99 |
| 2º fill (lotería) | 93 |
| MODAL (lo que juega un humano) | 91 |
| Field humano (media simulada) | 96 |
| Field casual (media simulada) | 74 |

**El EV-máx sacó +21 pts sobre el humano promedio en datos reales.** Ese es
nuestro edge estructural: explotar la regla (premiar goles altos, no el 1-0).
Las loterías (2º/3º fill) rinden menos en media (93-99) — su valor no es la
media sino descorrelacionar para tapar más resultados posibles.

## Conclusión operativa

Los 5 cupos de `oct_CSC.csv` (modo defender) son los óptimos según la simulación.
Ancla EV-máx en los 8 partidos; B1/B2 perturbadas suaves (defienden #3/#5);
B3/B5 lotería (moonshot desde ~343, fuera del corte 372). Enviar antes del
deadline (4/07 11:59 AM).
