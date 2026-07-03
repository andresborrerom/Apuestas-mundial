# Metodología para calcular las pollas CORRECTAMENTE (con ground truth)

> Este documento fija el procedimiento obligatorio para responder "¿cómo vamos?"
> o "¿qué marcador nos conviene?" en cualquiera de las pollas. Nació de un error:
> haber inferido la regla de scoring de LEMAITRE a partir de los totales (y haber
> dado un flip-flop aditivo↔degradado). **No volver a hacer eso.**

## Principio #1 — La regla se LEE de la fuente, no se adivina de los totales

- Si existe **código** que puntúa (app/JS), esa es la máxima autoridad: leer la
  función de scoring literal.
- Si existe un **Excel/PDF de reglas oficial**, leerlo en detalle (hoja de
  puntajes, descripción). Si el código y el Excel discrepan, **manda el que
  reparte la plata** (normalmente el app), pero DOCUMENTAR la discrepancia.
- Nunca concluir "la regla es X" solo porque X reproduce un total. Un `real_score`
  contaminado hace que la regla equivocada "cuadre".

## Principio #2 — Validar celda por celda contra la tabla publicada

- Reproducir la tabla oficial con el scorer y comparar **cada columna de cada
  participante conocido** (marcadores, clasif, extras, total).
- Solo declarar "validado" con **cero discrepancias** en los renglones visibles.
- Guardar el snapshot de la tabla oficial (screenshot/valores) en el `.md` de
  ground truth de esa polla, con fecha y fuente.

## Principio #3 — Separar lo CONOCIDO de lo PENDIENTE

- Resultados de partidos: distinguir jugados vs por jugar.
- Extras: distinguir (a) ya puntuados por el organizador, (b) **concluibles**
  (matemáticamente fijos aunque el organizador no los haya cargado), (c)
  pendientes. Un extra es concluible solo si ningún equipo vivo puede cambiarlo.
- Al proyectar, marcar explícitamente qué es proyección y qué es oficial.

## Principio #4 — Ground truth de resultados y tablas derivadas

- Los marcadores reales salen del app (`real_scores`, `grupos_results`) y/o de
  una fuente verificable (FIFA / football-data). No inventar resultados.
- Grupos, general y "último lugar" se **calculan** de los resultados con la misma
  lógica de desempate del organizador (leerla del código: p.ej. LEMAITRE usa
  pts → dif de gol → GF para grupos; último lugar = peor por pts → dif → +GC).

## Principio #5 — El peligro es contra el RIVAL DIRECTO, no contra el promedio

> Aprendizaje del 3-jul-2026 (P#83 Portugal 2-1 Croacia). En el "qué nos
> conviene" reporté que nos golpeaban los empates y **no** marqué el 2-1 — que
> fue justo lo que salió y nos costó caer a 3º.

Dos errores a no repetir:

1. **No recortar a un top-3 arbitrario.** El 2-1 quedó de 4º peor (−9.0) a solo
   0.3 del 3º (1-1, −9.3): estaba empatado en peligro y lo escondí. Mostrar
   TODOS los resultados con neto negativo relevante, no solo los 3 peores.

2. **El neto-promedio ESCONDE el golpe posicional.** El neto se promedia sobre
   todos los perseguidores; si unos aciertan y otros fallan, se diluye. En el
   2-1: Dionisio, Papo y Fabian tenían 2-1 exacto (40) — contra los DOS líderes
   directos era **−22**, pero promediado con los que fallaban daba solo −9.
   Un empate que todos fallan baja poco en la tabla; un marcador que **clavan
   los punteros** te hunde aunque el promedio se vea moderado.

**Regla operativa:** en el análisis de marcadores, marcar explícitamente los
resultados que son el **pick de la(s) persona(s) que tenemos justo arriba y justo
abajo**, y reportar el **neto contra el rival directo** (el 1º si vamos 2º), no
solo el promedio. El `que_marcador.py` ya lo hace (columna "vs líder directo" +
🚨 si un rival directo lo clava).

## Principio #6 — Honestidad sobre incertidumbre

- Si un dato no está confirmado (p.ej. el organizador aún no cargó un extra, o un
  resultado difiere entre fuentes), decirlo. No presentar proyección como hecho.
- Si me equivoqué antes, corregir explícito y explicar la causa raíz.

---

## Checklist por polla

### LEMAITRE  (locked — planilla completa ya enviada)
- Fuente: `LEMAITRE/REGLAS_Y_GROUND_TRUTH.md` (link, reglas, scorer validado).
- Recalcular: `puntos_lemaitre.py --refresh` (baja BASE_DATA oficial y valida).
- Tablas del Mundial / extras: `tablas_mundial.py`.
- "¿Qué nos conviene?" (no elegimos, rooteamos): `que_marcador.py --match N`.
- Regla marcador: **ADITIVA** (ganador + parcial suman). Grupos NO puntúan marcador.

### CSC  (elegimos por ronda; 5 cupos con dispersión)
- Regla `motor/backtest.puntos`, params por ronda en `pollas/CSC/reglas.py`
  (dieciseisavos = `(res=2, cero=3, base=5)`: ganador +2, cada nº de gol +(goles+5),
  gol cero +3). Premia marcadores con más goles.
- "¿Qué marcador mandar?" = EV-máximo bajo esa regla (2-1/3-1 típico, no 1-0).
- Tabla oficial llega por PDF; validar el gap vs líderes con el PDF más reciente.

### INGENIERO  (elegimos por ronda)
- Reglas en `pollas/INGENIERO/reglas.py`, validadas con `backtest_ingeniero.py`
  contra ground truth (football-data). 3-0 a favoritos validado (+/match vs modal).

---

## Antes de dar una respuesta de "cómo vamos", confirmar:
1. ¿Leí la regla del código/Excel (no la inferí de totales)?  ✅/❌
2. ¿Mi scorer reproduce la tabla oficial 1:1 en los renglones conocidos?  ✅/❌
3. ¿Separé conocido / concluible / pendiente?  ✅/❌
4. ¿Marqué proyecciones como proyección?  ✅/❌
5. ¿Actualicé el `.md` de ground truth de la polla con la fecha/fuente?  ✅/❌
