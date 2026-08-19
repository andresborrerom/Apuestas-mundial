# SURVIVAL — EL FULBITOL · NFL 2026 (voluntario, aparte del Pick'em)

Fuente: `Reglamento_SURVIVAL_EL_FULBITOL_2026.pdf`. Administra **Pepe Cely**.
Juego independiente: no toca la Batalla Semanal, los Small Pots ni el Big Pot
del Pick'em.

## Inscripción (las DOS cosas antes del kickoff de la Semana 1)

1. Estar inscrito en Yahoo → **Survival Football** → Join a group →
   **Group ID 9724 · Password NICOVD** (⚠️ NO es el grupo 498/NICOPEPE del
   Pick'em).
2. **Pagar $300.000** (aporte único, COP) al **Nequi de Pepe Cely 3108687756
   (llave @3108687756)** y reportar el comprobante en el grupo de WhatsApp,
   escribiendo "SURVIVAL" en el mensaje del Nequi. Sin pago reportado no
   cuentas como inscrito, aunque aparezcas en Yahoo.

Deadline duro: **kickoff del primer partido de la Semana 1** (Yahoo indica
9-sep-2026; confirmar en la app). Yahoo cierra el grupo automáticamente: quien
no cumpla las dos cosas queda por fuera y el pozo queda fijo ($300.000 × cada
inscrito pagado).

Usar **el mismo username del Pick'em**.

## Cómo se juega

- Cada semana se escoge **UN equipo** que creas que gana su partido.
- Si gana, sobrevives. **No se puede repetir equipo**: cada equipo usado queda
  bloqueado el resto de la temporada (Yahoo lo controla).
- Equipos en bye no aparecen como opción esa semana.
- Semanas 1 a 18; no hay playoffs.

### Las 2 vidas (strikes en Yahoo)

Cuestan una vida, y valen exactamente lo mismo:

| Situación | Qué pasa |
|---|---|
| Tu equipo pierde | Pierdes una vida |
| Tu equipo empata | Pierdes una vida |
| No metes pick esa semana | Pierdes una vida |

- Segunda vida perdida → **eliminado, sin reingreso** (ni pagando otra vez).
- Nadie avisa personalmente los picks pendientes; responsabilidad de cada uno.
- El dinero del eliminado se queda en el pozo; no se devuelve nada. El
  eliminado puede seguir viendo el juego en la app.

### Cierre de picks — distinto al Pick'em

**Un solo cierre semanal: 5 minutos antes del primer partido de la semana**
(normalmente el jueves). Aunque tu equipo juegue el domingo, el pick va antes
del jueves o pierdes una vida.

No hay cobros durante la temporada: todo se pagó por adelantado, el pozo está
completo desde la Semana 1.

## Cómo se gana

- Gana el **último jugador vivo**: se lleva todo el pozo.
- Varios vivos al terminar la semana 18 → el pozo se divide en partes iguales
  entre todos ellos (sin importar cuántas vidas le queden a cada uno).
- Todos eliminados la misma semana → el pozo se divide entre los que cayeron
  de último.
- Pepe paga la semana siguiente a que se defina el ganador.

## Reglas generales

- Solo miembros de la liga EL FULBITOL; no entra gente de afuera.
- Lo que registre Yahoo es lo válido; reclamos por fallas técnicas se resuelven
  con Pepe antes del martes siguiente.
- Situaciones no contempladas: las resuelven Pepe y el comisionado.

## Notas para el modelo

Problema clásico de survivor pool, con dos particularidades de esta liga:

- **2 vidas** en vez de 1: la primera vida es un amortiguador que abarata el
  riesgo temprano; su valor se estima simulando el pool (¿cuándo conviene un
  pick más flojo hoy para guardar un súper-favorito?).
- **Empate cuesta vida** (raro en NFL pero existe, ~2-3 por temporada): usar
  P(gana) estricta del moneyline, no P(no pierde).
- Greedy (mejor favorito disponible cada semana) es el baseline, pero quema
  temprano los equipos élite; contra un field que hace greedy, la planeación
  sobre el calendario completo (DP/ILP con moneylines proyectados y
  restricción de no-repetir) y la **decorrelación del field** (evitar el pick
  masivo en semanas trampa) son donde se gana — otra vez suma cero.
- Ganar no exige sobrevivir 18 semanas: exige durar más que los demás. El
  objetivo es maximizar P(último vivo), no P(sobrevivir).
