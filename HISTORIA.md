# Cómo construimos un modelo ganador de pollas con Claude — la historia

> Material de enseñanza. Esta es la crónica real de cómo, conversando con Claude,
> pasamos de "se me ocurre usar las cuotas" a un modelo validado con datos
> reales y una decisión final fundamentada. Está escrito para que **otro Claude
> pueda convertirlo en un curso** sobre *cómo usar Claude para ciencia de datos*.
>
> Si ganamos la polla, esta es la prueba de que el método funciona. Si no, sigue
> siendo un caso de estudio honesto de buen proceso.

---

## El arco de la historia (de un vistazo)

Empezamos con una idea simple y, a través de **~15 interacciones**, la fuimos
endureciendo. Lo notable: **casi todas las mejoras grandes nacieron de ideas del
usuario**, y Claude las **convirtió en experimentos medibles** — confirmando
unas y **refutando otras con honestidad**. Ese baile (humano propone intuición →
Claude la vuelve falsable → los datos deciden) es la lección central.

---

## Acto 1 — La idea germinal y el motor base

**El usuario dijo:** "Quiero usar estadísticas para crear una función de
puntuación basada en la probabilidad de que un equipo gane, sacada de casas de
apuestas."

**Claude hizo:** explicó que las cuotas son el mejor predictor barato, pero
señaló tres cosas que casi nadie aplica:
1. las cuotas **no son probabilidades** (hay que quitar el margen de la casa);
2. no se rellena con lo más probable sino con lo que **maximiza puntos
   esperados** según las reglas;
3. los goles salen de una **distribución completa** (Poisson/Dixon-Coles).

Montó un motor en Python (`motor/`) con tests y lo dejó funcionando.

**Lección de uso de Claude:** dale el objetivo, no la implementación. Claude
aporta el marco técnico (de-vig, Poisson, EV) que tú quizá no sabías que
necesitabas. Pídele que **deje tests** desde el día 1.

---

## Acto 2 — Las reglas reales lo cambian todo

**El usuario subió el PDF** del reglamento de la polla (CSC, "Super Polla de los
Pollos").

**Claude hizo:** leyó el PDF y descubrió que el sistema de puntos **no era** el
que había asumido por defecto. Acá se premia por separado: (1) acertar
ganador/empate, (2) goles exactos del local, (3) goles exactos del visitante; y
**más goles acertados = más puntos**, con los puntos **subiendo por ronda**.
Codificó esa regla y escribió tests que **replican los 6 ejemplos del PDF** (y
coincidieron exactos).

**Lección:** **dale a Claude la fuente primaria (el PDF/las reglas), no tu
resumen.** Un detalle de las reglas (el castigo al "0") cambió toda la
estrategia. Y pídele que **valide contra los ejemplos oficiales**.

---

## Acto 3 — Automatizar la entrada de datos

**El usuario pidió:** "Un comando que se conecte a una API, baje todo y llene
los marcadores del día siguiente."

**Claude hizo:** evaluó fuentes con honestidad (Rushbet no tiene API pública;
scrapear es frágil), eligió **The Odds API** (consenso de muchas casas, más
robusto que una sola), y construyó el comando `llenar.py`. Lo probó con datos de
ejemplo antes de gastar la API key.

**Lección:** Claude **investiga y compara fuentes** y te dice los trade-offs
(robustez vs. fidelidad a una casa). Deja que pruebe con *mocks* antes de gastar
recursos reales.

---

## Acto 4 — "¿Cuántos cupos compro?" y la suma cero

**El usuario preguntó** cómo optimizar la **utilidad = premio − costo de cupos**.

**Claude hizo:** explicó que la polla es **suma cero** (los premios = 100% del
recaudo) → solo hay ganancia si superas al participante promedio. Montó un
**simulador Monte Carlo** de la polla con rivales sintéticos, y mostró que la
respuesta **depende del supuesto sobre los rivales** (por eso hizo análisis de
sensibilidad).

**Lección:** Claude no te da un número falsamente preciso; **expone el supuesto
clave** (qué tan buenos son los rivales) y te muestra cómo cambia la respuesta.

---

## Acto 5 — Validación con ground truth (lo que separa ciencia de cuento)

**El usuario dijo:** "Vamos de ciencia. Validemos con datos reales sin sesgo."

**Claude hizo:** como no hay histórico gratis de Mundiales, usó
**football-data.co.uk** (~12.000 partidos reales con cuotas de cierre y
resultados). Hizo un **backtest con walk-forward** (entrenar en temporadas
viejas, medir en nuevas): el relleno EV-máximo **gana +0.285 a +0.97 puntos por
partido** vs métodos a mano, las probabilidades están **bien calibradas**, y el
edge **persiste fuera de muestra**.

**Lección — la más importante:** exige **walk-forward y ground truth**. Pídele a
Claude que **separe dos niveles de evidencia**: lo validado con datos reales vs.
lo que sale solo de simulación con supuestos. Claude lo hizo explícito en una
tabla.

---

## Acto 6 — Una idea del usuario que SÍ funcionó (sesgo a gol=1)

**El usuario notó:** "El modelo predice '0 goles' de más y '1' de menos. ¿No
deberíamos sesgar hacia 1?"

**Claude hizo:** lo volvió un experimento honesto: tuneó la magnitud del sesgo
**en train** y midió **en test**. Resultado: **calibrar puro NO ayuda** (porque
la regla es asimétrica), pero un sesgo a "1" sí (**+0.03 pts/partido fuera de
muestra**). Lo integró (α=0.05) solo para *elegir* el relleno.

**Lección:** tus intuiciones de dominio son oro, pero **pídele a Claude que las
falsee con walk-forward** antes de creerlas.

---

## Acto 7 — Dos ideas del usuario que NO funcionaron (y eso es bueno)

**El usuario propuso:** (a) sesgar más al favorito (condicionar por 1X2); (b)
que el sesgo dependa del total de goles esperado (λ).

**Claude hizo:** ambos como experimentos walk-forward. **Ambos refutados:** el
1X2 ya está dentro del modelo, y el sesgo del "0" es parejo entre partidos. El α
constante basta.

**Lección — la prueba de honestidad:** un asistente que confirma *todo* lo que
propones es peligroso. Que Claude **refute** ideas (con datos) es señal de que el
proceso es insesgado. Celébralo.

---

## Acto 8 — ¿El modelo transfiere a Mundiales?

**El usuario dudó:** "La relación cuotas↔resultados puede cambiar por
competición."

**Claude hizo:** mandó un sub-agente a buscar datos, encontró el paquete
**`oddor`** (gratis, 1X2 + goles de 4 Mundiales), y validó: el Mundial es **más
defensivo** (más ceros) pero el modelo **sigue prediciendo el 0 de más** → el
sesgo transfiere, y el **edge es incluso mayor** (+0.48). Recomendó **no gastar
en datos**.

**Lección:** Claude puede **delegar investigación a sub-agentes** y traerte una
recomendación de compra/no-compra fundamentada.

---

## Acto 9 — La idea estrella del usuario: perturbación mínima

**El usuario intuyó:** "Con premio top-heavy, importa la **probabilidad de que
UNA entrada quede 1ª**, no el promedio. Si mis cupos son idénticos, suben y bajan
juntos. ¿Qué aleatoriedad mínima los descorrelaciona sin alejarnos del modelo?"

**Claude hizo:** implementó **perturbar solo los partidos casi-empatados en EV**
(cambiar al 2º mejor relleno, que cuesta casi nada). Simuló rankings: la
perturbación mínima **multiplica P(1º)** (de ~5% a ~47% contra rivales buenos)
sin bajar la media. "Demasiado azar" la mata; el punto dulce es chico.

**Lección:** una intuición de teoría de juego, **traducida por Claude a un
mecanismo medible**, fue la mejora más potente. El usuario aportó el *qué*;
Claude, el *cómo medirlo*.

---

## Acto 10 — Otra idea del usuario: dispersión creciente por ronda

**El usuario intuyó:** "En grupos (muchos partidos) la ley de grandes números me
protege; en eliminatorias (pocos partidos, mucho valor) necesito más dispersión
para ganar."

**Claude hizo:** construyó un **simulador de torneo completo** y testeó con
**presupuesto fijo de dispersión**: concentrarla en eliminatorias da **P(1º) 30%
vs 17.7%** en grupos (6 semillas). Confirmado. Lo automatizó en `llenar.py`
(poca dispersión en grupos, mucha en eliminatorias). Honesto: corrigió su propia
corrida inicial (una sola semilla) que daba un falso empate.

**Lección:** Claude **vuelve a medir cuando el resultado es ruidoso** y corrige
sus propias conclusiones. Pídele estabilidad (varias semillas).

---

## Acto 11 — Entender de dónde sale el E[util] (deciles y libro mayor)

**El usuario pidió ver** las simulaciones por dentro: en cada Mundial simulado,
en qué puesto quedó cada cupo.

**Claude hizo:** un "libro mayor" (puesto de cada cupo → premio → utilidad) y
rompió la utilidad **por deciles**. Se ve claro: **pierdes el costo ~1 de cada 4
veces**, y el E[util] lo cargan los **deciles altos** (cuando capturas varios
premios a la vez). Top-heavy puro.

**Lección:** no te quedes con un número. Pídele a Claude que te muestre la
**distribución** (deciles, casos individuales). Entender la forma > confiar en la
media.

---

## Acto 12 — La decisión final

Con todo medido, compararon **3, 4, 5, 6 cupos** (24.000 sims c/u). El E[util]
sube siempre, pero el ROI cae; **5 cupos** maximiza P(premio) y **minimiza el
riesgo de perder** (25%) con ROI sólido. **Decisión: 5 cupos.** Claude generó la
planilla (`grupos_CSC.csv`).

**Lección:** la decisión no fue "el máximo E[util]" (eso era seguir comprando)
sino un **balance riesgo/eficiencia** que el usuario eligió, con Claude
poniendo los números.

---

## Las 10 lecciones de "cómo usar Claude" (para el curso)

1. **Da el objetivo, no la implementación.** Claude aporta el marco técnico.
2. **Entrega la fuente primaria** (PDF, reglas, datos), no tu resumen.
3. **Exige tests** y validación contra ejemplos oficiales desde el inicio.
4. **Pide ground truth y walk-forward.** Sin eso, es opinión.
5. **Haz que separe evidencia validada de simulación con supuestos.**
6. **Trae tus intuiciones de dominio** — son oro — pero deja que Claude las
   falsee.
7. **Celebra cuando Claude REFUTA tu idea.** Es la prueba de no-sesgo.
8. **Pide sensibilidad y varias semillas;** desconfía de un solo número.
9. **Delega investigación a sub-agentes** (buscar datos, comparar precios).
10. **Mira la distribución, no solo la media.** Deciles, casos, colas.

---

## Para el Claude que arme el curso

Tienes todo el material reproducible en este repo:
- **La narrativa:** este archivo (`HISTORIA.md`).
- **Las decisiones técnicas:** `pollas/CSC/DECISIONES.md` (bitácora completa con
  números, fórmulas y comandos).
- **La metodología transferible:** `PLAYBOOK.md` (la receta para una polla nueva).
- **El código vivo:** `motor/` (motor general) y `pollas/CSC/*.py` (cada
  experimento es un script ejecutable y autoexplicado).

Sugerencia de estructura de curso: un módulo por Acto, cada uno con (a) la
intuición humana, (b) cómo Claude la volvió experimento, (c) el resultado, (d)
la lección de proceso. Los scripts `pollas/CSC/demo_*.py` y `experimento_*.py`
son demos en vivo listas para clase. Para cada concepto, el patrón pedagógico es
el mismo: **intuición → experimento falsable → dato → decisión.**
