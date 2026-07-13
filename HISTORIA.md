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

## Acto 13 — Polla nueva (LEMAITRE): cuando el puntaje NO son los goles

**El usuario abrió otra polla** (LEMAITRE) y subió el Excel oficial. Al leer las
reglas, **el supuesto por defecto de CSC se cayó**: aquí **no se puntúan los
marcadores de fase de grupos**; el 44% del puntaje es **clasificación** (qué
equipos avanzan y a qué puesto), y hay 750 pts de **extras** (total goles,
continente campeón, Colombia, goleador…).

**Claude hizo:** leyó las 7 hojas del Excel, sacó el **presupuesto de puntos por
sección** (máx 3900) y reorientó el modelo: el motor de CSC optimizaba goles;
LEMAITRE exige optimizar **clasificación**. Construyó una sim Monte Carlo de los
12 grupos (de las cuotas de cada partido) → quién clasifica, posiciones, 8
mejores terceros — y la **validó con ground truth** (`backtest_clasificacion.py`,
4 Mundiales reales del paquete `oddor`): P(clasificar) **bien calibrada**;
ganador de grupo 69%; top-2 exacto **38%** (los grupos son genuinamente
impredecibles — ese 38% es **piso de incertidumbre**, no error del modelo).

**Lección:** **las reglas de pago redefinen el problema.** El usuario lo dijo
sin rodeos: *"calibramos para unos pagos que poco tienen que ver con goles"*. El
mismo motor, reapuntado a otra función objetivo.

---

## Acto 14 — El sesgo oculto de los ratings y la calibración al MERCADO de campeón

**El problema:** para las eliminatorias hay que cruzar equipos de grupos
distintos. Claude armó un modelo de **fuerzas (ataque/defensa)** sacado de los
partidos de grupo. Al simular el bracket, salía **Bélgica 7.6% campeón, Alemania
9.9%** — sospechosamente alto.

**Claude diagnosticó (medido, no supuesto):** derivar ratings **solo** de
partidos de grupo **sobre-estima a equipos de grupos débiles** (Bélgica le gana
fácil a Egipto/Irán/N.Zelanda → infla su ataque) e **infra-estima escuadras
élite en grupos medios** (Francia, Inglaterra). Lo confrontó con un **mercado
gratis que no estábamos usando**: las cuotas de **campeón** (`soccer_fifa_world_
cup_winner`, 5 casas). Brecha clara: Francia mercado 14.7% vs sim 8.2%; Bélgica
mercado 2.1% vs sim 7.3%.

**Claude hizo:** **calibró la fuerza de eliminatoria al futures de campeón.**
Primero intentó regresión + gradiente-en-el-loop — **inestable, lo descartó y lo
documentó**. La versión final: **una sola temperatura τ** que importa el ranking
del mercado (δ ∝ log p_campeón) **reemplazando** la fuerza sesgada de la sim,
buscada en 1-D por mínima divergencia KL. Resultado: la distribución de campeón
**cuadra con el consenso de 5 casas** (España 15.8 vs 15.4, Francia 14.2 vs
14.7…). Separación limpia: **los grupos no se tocan** (sus cuotas ya son el
mercado correcto); solo se recalibra la fuerza cruzada.

**Lección:** **usa TODOS los mercados gratis** — cada uno calibra una parte
distinta (partidos→grupos, futures→profundidad). Y cuando un método de
calibración es inestable, **se dice y se reemplaza**, no se maquilla.

---

## Acto 15 — Llenar el Excel completo (y un bug de coherencia)

**El usuario:** "Hay que llenar **todo** el Excel."

**Claude hizo:** mapeó las celdas exactas de las hojas *Grupos* y *Form000*,
construyó el **árbol del bracket coherente** (forward pass: en cada llave avanza
el de mayor P(ganar) cabeza a cabeza con los ratings calibrados; el ganador
fluye al siguiente partido) y escribió todo en una copia `*_LLENO.xlsx`. Al
verificar, **encontró su propio bug**: el marcador EV-máx (que es
team-independiente) decía "Brasil 1-0 Inglaterra" pero Claude hacía avanzar a
Inglaterra → la planilla se contradecía. Lo arregló **restringiendo el marcador
a ser coherente con el equipo que avanza** (costo de EV despreciable). Los
extras de **jugador** (goleador, 1er/últ gol) los dejó marcados `[REVISAR]`:
**sin data gratis, no se inventan.**

**Lección:** automatizar la **operatividad** (no pasarte un CSV para que copies)
y **verificar el artefacto final**, no solo el modelo. Los bugs aparecen al mirar
la salida real.

---

## Acto 16 — ¿Cuánto vale la aleatoriedad y DÓNDE meterla? (decorrelación, otra vez)

**El usuario:** "Me interesa cuánto vale algo de aleatoriedad y dónde meterla,
como hicimos en el pasado." (la idea estrella de CSC, ahora en LEMAITRE).

**Claude hizo:** un análisis que separa el valor de aleatorizar en tres lugares
y mide su **costo en E[pts]** vs su **ganancia en P(1º)** (`aleatoriedad_lemaitre
.py`), con reparto de premios real (60/30/10, con desempates). Hallazgos (N=50,
campo blando):
- **Planillas idénticas no sirven** (P(1º) 13→14% con K=5): todas empatan, no
  ensanchan la cola ganadora. Plata botada.
- **Marcadores = el lugar más barato** (30 con 2ª opción casi igual): cuesta ~6
  pts/planilla y **casi duplica P(1º)**.
- Luego **grupos cerrados** (D, B, K, F — el crédito "invertido" amortigua el
  swap) y por último un **cruce de bracket disputado** (caro pero alto impacto).
- Decorrelando en los tres, K=5 → **P(1º) 33%, E[util] +$2.25M** (vs +$1.11M con
  1 planilla). A N=100 el patrón se mantiene.

**Lección:** la mejor mejora de CSC **transfiere** a una polla de estructura
muy distinta, y Claude la volvió a **cuantificar por separado** (dónde, cuánto
cuesta, cuánto rinde) en vez de "echar azar a todo".

---

## Acto 17 — Field model honesto: el resultado vive de un supuesto

**Para E[ganancias]** Claude construyó un **modelo de campo** (rivales
sintéticos con habilidad θ: afilados que siguen el mercado vs casuales que
siguen nombres grandes) y midió P(1º/2º/3º) y E[util] según **N inscritos**.

**La bandera de honestidad:** el resultado es **extremadamente sensible** a qué
tan afilado es el campo — a N=80 va de **+$1.13M** (campo casual) a **−$203k**
(campo afilado). Nuestra ventaja en E[pts] es real (1086 vs 853), pero que se
vuelva +dinero depende de un dato del mundo real que **solo el usuario conoce**.
Claude lo dejó como **supuesto explícito y ajustable** (`--p-afilado`), nunca
escondido en un número.

**Lección:** cuando el resultado depende de algo que no se puede medir desde los
datos, **se nombra el supuesto, se da la sensibilidad, y se le pide al usuario su
lectura** — no se entrega un número falsamente preciso.

---

## Acto 18 — La auditoría multi-agente que se pagó sola (semis, 13-jul)

Con la estrategia de semis ya definida, commiteada y con el snippet listo para
llenar, **el usuario dijo:** *"Revisa lo que está hecho para rematar y mira si
puedes mejorarlo. Manda agentes para que la auditoría sea independiente."*

**Claude hizo:** lanzó **tres sub-agentes en paralelo, ciegos entre sí y con
mandatos adversariales** (no "revisa que esté bien", sino "encuentra lo que
está mal / derrota esta config"):

1. **Auditor de código** — reproducir el motor de premio línea por línea, con
   instrucción explícita de buscar el tipo de bug que ya nos mordió antes (un
   eje de broadcasting invertido en cuartos).
2. **Auditor de datos** — re-derivar TODO de las fuentes primarias con parser
   propio (PDF del field, cuotas crudas de 49 casas), sin mirar los scripts
   existentes.
3. **Estratega adversarial** — búsqueda más amplia que la del optimizador
   original + atacar la metodología misma: la miopía de horizonte (optimizar
   semis ignorando 3er puesto/final) y el herding real del field (la lección
   que el usuario había dado dos días antes: "no asumamos que todo el field
   estaba clavado").

**Lo que salió** (cada auditor encontró cosas de naturaleza distinta — por eso
se separan los mandatos):

- **Datos: 100% limpios.** Field re-parseado idéntico al peso; consenso de
  cuotas exacto. Valor: convierte "creo que los insumos están bien" en hecho.
- **Código: hallazgo GRAVE.** La planilla escrita en el CSV/snippet **no era la
  config que ganó la simulación**. El optimizador simuló anclas 2-1 (el EV-máx
  real bajo matrices a 120') pero Claude escribió 1-1 por una **etiqueta mal
  puesta** ("EV-máx" era 1-1 solo a 90 minutos). Costo del error: ~$500-700k de
  EV. La matemática estaba perfecta; la etiqueta no. Además: un bug latente
  (ranking de fills con la regla de otra ronda) que aún no dolía pero iba a
  doler en la final.
- **Estratega: encontró una config MEJOR** (G3, "cobertura de la grilla de
  ganadores": picks distintos POR PARTIDO cubriendo los 4 cuadrantes
  local/visita), que el menú estrecho del optimizador original — perfiles
  simétricos entre partidos — **nunca podía encontrar**. Dominante en TODOS los
  escenarios de sensibilidad, especialmente si el field se agolpa en el modal.

**Y el usuario remató con la pregunta clave:** *"En tus propios números, revisa
que esto de verdad mejore contra lo que tenías."* Es decir: **no le creas a tus
auditores tampoco.** Claude re-validó G3 con SU propio evaluador (no el del
agente), 10 semillas frescas y comparación PAREADA (misma realidad simulada por
semilla, solo cambian los picks): G3 ganó **10/10** contra la planilla vieja
(+$716k de media; +$286k incluso en la peor semilla) y 8/10 contra el óptimo
original del sweep.

**El cierre institucional:** el error de etiqueta se volvió **candado
automático** (`pollas/CSC/verificar_semis.py`): lee el CSV y el snippet **tal
como quedaron escritos**, verifica que coincidan entre sí, evalúa esos picks
exactos en el simulador y **truena si no rinden como la config auditada**. La
lección 13 ("verifica el artefacto final") dejó de ser consejo y pasó a ser un
gate ejecutable que corre antes de cada envío.

**Lección:** la auditoría multi-agente independiente no es lujo — aquí **pagó
~$1.2M de EV** (error evitado + config mejor) por unos minutos de cómputo. Las
claves: (a) mandatos **adversariales y separados** — código, datos y estrategia
fallan distinto y se auditan distinto; (b) **ciegos entre sí** para no
contaminarse; (c) el hallazgo se **re-verifica con números propios** antes de
adoptarlo (verificar al verificador); (d) todo error grave se convierte en un
**candado ejecutable**, no en un propósito de enmienda.

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
11. **Las reglas de pago redefinen el problema.** El mismo motor, reapuntado a
    otra función objetivo (CSC=goles, LEMAITRE=clasificación).
12. **Usa todos los mercados gratis** — cada uno calibra una parte distinta
    (cuotas de partido→grupos; futures de campeón→fuerza de eliminatoria).
13. **Verifica el artefacto final**, no solo el modelo: el bug de coherencia del
    marcador apareció al mirar el Excel lleno, no la simulación.
14. **Audita con agentes independientes y mandatos ADVERSARIALES.** No "revisa
    que esté bien" sino "encuentra el error / derrota esta config". Separa
    código / datos / estrategia (fallan distinto) y mantenlos ciegos entre sí.
    (Acto 18: un agente halló un error de ~$500k, otro una config mejor.)
15. **El error más caro puede ser de ETIQUETA, no de matemática.** Lo simulado
    y lo enviado divergieron por un nombre mal puesto ("EV-máx"). Antídoto:
    candados ejecutables que evalúan el artefacto ESCRITO contra la simulación
    (`verificar_semis.py`), corriendo antes de cada envío.
16. **Verifica al verificador.** Antes de adoptar el hallazgo de un sub-agente,
    reprodúcelo con tu propio evaluador, semillas frescas y comparación pareada.
    Si no sobrevive a eso, no era hallazgo.

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
