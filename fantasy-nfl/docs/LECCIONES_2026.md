# Lecciones del Fantasy 2026 — para el draft 2027

> Escrito el 22-sep-2026, con la temporada 1-1 y el simulador dando 20% de
> playoffs. No es una autopsia post-mortem: es a mitad de camino, con los
> números todavía verificables. Cada lección lleva la evidencia que la
> sostiene y la regla concreta que la reemplaza. Si una lección no tiene
> número al lado, no es una lección: es una opinión.

**El diagnóstico de Andrés, y es correcto: optimizamos por donde no era.**

El motor de draft maximizó **VBD del roster**. Lo que paga la temporada es
otra cosa: **puntos que de verdad se alinean, convertidos en victorias
semanales**. Todo lo que sigue sale de esa brecha.

---

## L1 — Se optimizó el ROSTER, se paga el LINEUP

**Evidencia (22-sep):** el lineup real proyecta **148.6 pg**; los mejores 14
del mismo roster proyectan **181.0**. Hay **45.5 pg atrapados en la banca**,
el 23% del valor del roster y **el más alto de los 16 equipos** (el segundo,
Panamanian, tiene 37.7).

Peor: el 10-sep reporté "2454 puntos, #1 de 16" usando `alinear()`, que
escoge los mejores 14. Nunca escribí que eso **asumía poder desplegarlos**.
Bowers estaba por lesionarse, Jacobs entró a la Commissioner's Exempt List y
Mendoza es suplente. El supuesto era invisible — el peor tipo según la
constitución (II.6).

**Regla 2027:** la función objetivo del draft es **E[puntos alineados]**, no
E[puntos del roster]. Un jugador que no se puede alinear vale cero esa
semana Y ocupa un cupo. La disponibilidad no es un descuento sobre los
puntos: es una restricción sobre el cupo.

**Candado:** antes de cerrar el draft, correr el simulador con el lineup que
de verdad se puede poner la semana 1, no con los mejores 14.

---

## L2 — Un supuesto que solo te beneficia a TI es sospechoso hasta validarlo

**Evidencia:** el escenario "central" fusionaba pares mutuamente excluyentes
del mismo equipo NFL. En la liga entera **solo había 4 pares y los 2
excluyentes eran míos** (Jacobs+Lloyd, Mendoza+Cousins). Ese supuesto me
sumaba **+141 puntos que ningún rival recibía**.

La semana 1 lo refutó: **Lloyd anotó 4.1 contra un pg de 8.54**.

**Regla 2027:** cualquier decisión de modelado cuyo beneficio sea
**asimétrico** — solo la recibe un equipo, y es el tuyo — se marca y se
valida contra datos ANTES de entrar a un ranking. Si no se puede validar,
se reporta el ranking con y sin ella.

---

## L3 — El handcuff NO hereda el rol

**Evidencia (box score GB@MIN, S1, con Jacobs completamente ausente):**

| | Acarreos | YPC | Targets | Rec | Pts |
|---|---:|---:|---:|---:|---:|
| MarShawn Lloyd | 13 (65%) | 2.8 | 1 | **0** | **4.1** |
| Chris Brooks | 7 (35%) | 4.1 | 1 | 0 | — |

El titular sale y el rol **se reparte**, no se traspasa. Y el trabajo por
aire — el que sostiene el piso en PPR — no se hereda casi nunca.

**Regla 2027:** el suplente se valora a su **share observado del comité**,
nunca a la tasa del titular. Tope por defecto del par fusionado: **65% del
pg del titular**, no 100%. Y si no hay dato del comité, no se fusiona.

---

## L4 — Los IDP se hacen STREAMING, no se draftean

**La lección más cara y la más fácil de aplicar.**

**Evidencia (22-sep):** mis 5 IDP drafteados suman **26.6 pg**. Los mejores
agentes libres de hoy, en las mismas 5 posiciones, suman **27.66 pg**.

| Slot | Drafteado | Mejor LIBRE hoy | |
|---|---:|---:|---|
| DT | 2.74 | **3.26** | el libre gana |
| DE | **4.52** | 4.34 | |
| LB | 7.54 | 7.54 | empate |
| CB | 6.00 | **6.10** | el libre gana |
| S | 5.84 | **6.42** | el libre gana |
| **Total** | **26.64** | **27.66** | **+1.02/semana gratis** |

**Todo el capital de draft gastado en IDP compró menos que el waiver wire.**
Y los 5 slots IDP son el **36% de la alineación titular** pero solo el
**18% de los puntos**.

**Regla 2027:** cero capital en IDP. Se llenan con cuerpos de última ronda o
directamente post-draft, y se hace streaming semanal con el motor validado:
**tasa propia de 17 jornadas + filtro de actividad (proyección de ESPN > 0)**.
Ver `optimize/idp_semanal.py`.

---

## L5 — En superflex, el slot OP es un titular, no un lujo

**Evidencia:** EZWAR anotó **290.2 en la semana 1** — el máximo de la liga
por 89 puntos — con **Bryce Young 47.4 (OP) + Caleb Williams 46.2 (QB) =
93.6 de dos slots**. Mi par QB/OP: **Maye 26.6 + Cousins 4.02 = 30.6**.

El error fino: sí draftié un segundo QB con techo (Mendoza, 15.69), pero es
un **activo condicional** — solo vale si Las Vegas sienta a Cousins. Un
activo condicional no llena un slot titular.

**Regla 2027:** en superflex, el segundo QB se paga como **titular de slot**,
y tiene que ser **titular HOY**, no un apostado a un cambio de rol. La
diferencia entre un QB2 real y un suplente es ~20 pg/semana — más que
cualquier decisión de RB o WR del draft.

---

## L6 — Puntos ≠ victorias, y la varianza semanal domina

**Evidencia:** σ semanal medido = **38.8 puntos** sobre 32 observaciones
equipo-semana. Con 14 jornadas, una ventaja en puntos se convierte
débilmente en récord: la semana 1 la ganó con 130.0 (8º de la jornada) y la
2 la perdió con 154.9 (8º también).

Y al revés: simular partidos **le favorece** cuando es inferior. Por puntos
sale 11º-14º; simulando standings sale 9.9-11.5. El ruido es amigo del que
va perdiendo.

**Regla 2027:** la métrica objetivo del draft es **P(playoffs) simulada**,
no E[puntos de temporada]. Se declara ANTES de empezar (Parte VII de la
constitución) y no se cambia a mitad.

---

## L7 — La recencia: en PUNTOS es ruido, en SNAPS es señal

**Evidencia (backtest 45.707 observaciones, 2021-2026, sin fuga):**

- Predecir con la última semana de **puntos**: MAE 2.403.
  Con las últimas 17: **1.923** — la última semana es **24% peor**.
- Pero el **snap share reciente** es la 2ª feature más fuerte del modelo
  (coef +0.316 contra +0.921 de la tasa propia), y añadir snaps mejora el
  MAE **+2.99%** — lo único de toda la investigación que le ganó al baseline.

Los puntos son **resultado** y son ruidosos. Los snaps son **rol** y son
estables. Meterlos en el mismo saco fue un error mío que duró tres días.

**Regla 2027:** para decisiones semanales, ordenar por tasa de 17 jornadas +
**tendencia de snaps**; ignorar la "forma" en puntos.

---

## L8 — Contra quién juega un IDP casi no importa

**Evidencia:** las 14 features de rival y contexto (jugadas, carreras,
sacks permitidos, EPA, puntos concedidos a la posición, spread, total, local,
descanso) empeoran la predicción **−1.10%** fuera de muestra. Los
coeficientes tienen todos el **signo correcto** — ser underdog ayuda, un
rival corredor ayuda — pero son **10 a 30 veces más pequeños** que la tasa
propia del jugador.

Y la ventana corta es peor, monótonamente: usar solo la semana anterior del
rival es **−10.6% a −12.4%**. Eso no es señal diluida, es ruido.

**Regla 2027:** no gastar tiempo en análisis de matchup para IDP. Decide
**quién es el jugador**, no contra quién juega.

---

## L9 — Los candados que sí cazaron algo (mantenerlos todos)

Cada uno atrapó un bug real esta temporada:

| Candado | Qué cazó |
|---|---|
| Reconstrucción == marcador oficial | valida los 16 lineups celda a celda cada semana |
| Unir por `team_id`, no por nombre | `'Injury Report '` con espacio y **2 equipos renombrados**, incluido el suyo, que se caían en silencio de TODA correlación |
| Cobertura de posiciones | `SAF` y `DL` sin mapear = **6.058 filas** de IDP fuera del modelo |
| Recibo del draft ≠ `playerId > 0` | los 16 D/ST tienen **id negativo**: 271 de 288 picks descartados |
| Partidos en FINAL (no "nadie en 0") | una semana con el Monday Night en curso pasa el chequeo ingenuo |
| Correcciones de estadística | 5 equipos se movieron en la semana 1 **después** del primer cierre |

**Regla 2027:** ningún candado se quita "porque nunca truena". El de
renombres tardó una semana en pagar y lo hizo con el equipo propio.

---

## L10 — Mis errores de proceso, para no repetirlos

No son de modelo, son de disciplina. Cada uno vale una regla:

1. **Reporté un ranking de puntos como si fuera un pronóstico de standings.**
   → Todo número se entrega con la pregunta que responde pegada.
2. **Dije "re-corro el jueves" y corrí el martes siguiente.** El candado de
   correcciones funcionó; el eslabón humano fui yo.
   → Lo que se promete con fecha, se agenda; no se recuerda.
3. **Construí una explicación de por qué FantasyPros se equivocaba** (37% de
   playoffs) en vez de tomarlo como dato adverso. Hoy mi motor da 20%.
   → Cuando una fuente externa discrepa, el primer sospechoso es el modelo
   propio, no la fuente.
4. **Recomendé DTs con tesis de matchup que nunca había validado.**
   → No se recomienda con un razonamiento que no ha pasado por backtest.
5. **Dos modelos míos se contradecían** (el marcador lo tenía #1 mientras el
   simulador lo tenía #15) y no lo detecté hasta que Andrés preguntó.
   → Cuando dos modelos propios dan órdenes distintos, eso es un incidente,
   no una curiosidad.

---

## Lista de arranque para el draft 2027

- [ ] Declarar la métrica objetivo: **P(playoffs) simulada**, no puntos.
- [ ] Correr el simulador con el **lineup desplegable de la semana 1**.
- [ ] Marcar y validar todo supuesto de **beneficio asimétrico**.
- [ ] Fusionar pares con tope del **65%**, o no fusionar.
- [ ] **Cero capital en IDP.** Plan de streaming escrito desde el día 1.
- [ ] Par **QB/OP con dos titulares reales**, no un condicional.
- [ ] Leer `scoringItems` **con sus `pointsOverrides` por slot** — el sack
      vale 3.0 en DT y 2.0 en DE/LB/CB/S, y eso no estaba en el motor 2026.
- [ ] Montar los 6 candados de L9 antes del primer cálculo.
- [ ] Escribir el Libro de Supuestos **aunque nazca vacío**, y meter ahí el
      de disponibilidad de cada jugador con bandera.
