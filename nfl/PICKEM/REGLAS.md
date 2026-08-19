# PICK'EM — LIGA EL FULBITOL · NFL 2026 (semanas 1-18)

Fuente: `Reglamento_EL_FULBITOL_2026.pdf` (reglamento oficial del comisionado).

## Inscripción

- App Yahoo Fantasy → **Pro Football Pick'em** → Join a group.
- **Group ID 498 · Password NICOPEPE** (no crear grupo nuevo).
- Usar un nombre reconocible y **el mismo username que en el Survival**.
- Si la app no acepta las credenciales: escribir al comisionado por WhatsApp
  antes del jueves de la Semana 1.

## Cómo se juega

- Cada semana se escoge el **ganador de todos los partidos** de la NFL.
- **1 punto por acierto.** No hay puntos por marcador ni diferencia.
- Entre 13 y 16 partidos por semana (equipos en bye no juegan).
- **Cierre por partido: 5 minutos antes de su kickoff.** No hay cierre único
  semanal — el pick del jueves se mete antes del jueves o se pierde ese partido.
- Sin picks: 0 puntos esa semana **y la apuesta se paga igual**.
- Reporte oficial: cuadro de puntos y saldos cada martes por WhatsApp.

## Las 4 apuestas (independientes entre sí, COP por jugador)

| Apuesta | Valor | Cómo se gana | Cuándo se paga |
|---|---|---|---|
| Batalla Semanal | $50.000/semana | Más aciertos en la semana | Corte 1 y Corte 2 |
| Small Pot 1 | $100.000 | Más puntos acumulados sem. 1-9 | Corte 1 |
| Small Pot 2 | $100.000 | Más puntos acumulados sem. 10-18 (contador se reinicia) | Corte 2 |
| Big Pot | $200.000 | Más puntos acumulados sem. 1-18 | Fin de temporada regular |

En todas, el ganador recibe el valor de la apuesta **de cada uno** de los demás
jugadores. Empate en Small Pots / Big Pot: el pozo se divide en partes iguales
entre los empatados del primer lugar.

### Batalla Semanal — acumulación

- $50.000 por jugador **todas** las semanas (el aporte nunca cambia).
- Empate en el primer lugar → no hay ganador, el pozo pasa a la semana
  siguiente (y se sigue poniendo los $50.000 nuevos).
- **Máximo 2 acumulaciones** (3 semanas):

| Situación | Pones esa semana | Pozo en juego | Ganador único recibe |
|---|---|---|---|
| Semana normal | $50.000 | $50.000 | $50.000 de cada rival |
| 1ª acumulación | $50.000 | $100.000 | $100.000 de cada rival |
| 2ª acumulación (tope) | $50.000 | $150.000 | $150.000 de cada rival |

- Empate en la semana del tope ($150.000): se acabó la acumulación, los
  $150.000 de cada jugador se reparten entre los empatados de esa semana.
- Tras cualquier liquidación, la semana siguiente arranca de cero ($50.000).
- **Una acumulación nunca cruza un corte**: si al terminar la semana 9 o la 18
  hay empate o acumulación en curso, se liquida obligatoriamente ahí (se
  reparte entre los empatados de esa semana).

## Cortes y pagos

No se paga semana a semana; todo es saldo (positivo o negativo) que se liquida
en dos momentos:

| | Corte 1 | Corte 2 |
|---|---|---|
| Cubre | Semanas 1-9 | Semanas 10-18 |
| Fecha | Martes tras el Monday Night de la sem. 9 | Martes tras el Monday Night de la sem. 18 |
| Liquida | Batalla Semanal (1-9) + Small Pot 1 | Batalla Semanal (10-18) + Small Pot 2 + Big Pot |

Mecánica: (1) el comisionado consolida y publica un único número por persona;
(2) los saldos en contra consignan primero al **Nequi de Nico Villaveces
3183377514 (llave @3183377514)** dentro de los 3 días siguientes al corte, con
comprobante al grupo; (3) el comisionado paga a los saldos a favor.

## Reglas generales

- Quien no pague su saldo en el plazo del corte **no participa en el corte
  siguiente y sus puntos no cuentan para el Big Pot**.
- Retiro a mitad de temporada: paga los saldos acumulados; sus apuestas
  acumuladas (Small Pot y Big Pot) se pierden a favor del pozo.
- El resultado válido es el que registre Yahoo; reclamos por fallas técnicas se
  resuelven con el comisionado antes del martes.
- Alcance: temporada regular (sem. 1-18). Survival y playoffs son aparte, con
  reglamento propio.
- Situaciones no contempladas: las resuelve el comisionado. Modificaciones se
  comunican por WhatsApp y aplican desde la semana siguiente.

## Notas para el modelo

- Puntuación plana (1 pt/acierto) → el pick individual EV-máx es siempre el
  favorito del moneyline (sin margen, `motor/cuotas.py`).
- El juego real está en la **Batalla Semanal** (winner-take-all semanal, con
  acumulación): contra un field que también toma favoritos, diferenciarse en
  los partidos ~50/50 es donde se compra P(1º) barata — la misma lógica de
  perturbación mínima del PLAYBOOK, pero por semana.
- Small Pots y Big Pot son maratones de consistencia: ahí la varianza extra
  cuesta; los picks contrarios convienen solo si vas detrás en la tabla cerca
  del corte (comportamiento tipo opción: al perdedor le pagan la varianza).
