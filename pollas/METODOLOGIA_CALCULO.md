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

## Principio #5 — Honestidad sobre incertidumbre

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
