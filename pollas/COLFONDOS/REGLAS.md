# COLFONDOS (plataforma Pollaya) — reglas y plan de modelado

Fuente: `IMG_9925.png` (tablero de puntos de la app Pollaya, game.pollaya.com).
⚠️ Nota de la propia app: *"Los puntos solo los puede editar el creador antes de
iniciar el torneo"* → **hay que confirmar que el creador no cambió estos puntos.**

## Puntos asignados (default Pollaya)

**Por PARTIDO (marcador):**
| Concepto | Puntos |
|---|---:|
| Marcador exacto | 4 |
| Selección del ganador (1X2) | 3 |
| Goles de un equipo (acertar goles de uno) | 1 |
| Diferencia de gol | 1 |

**Apuestas de TORNEO (outrights):**
| Concepto | Puntos |
|---|---:|
| Escoge campeón | 20 |
| Escoge subcampeón | 15 |
| Escoge tercer puesto | 10 |
| Clasificados 2da ronda (c/u) | 4 |
| Malla menos vencida (mejor defensa) | 7 |

**Premios individuales (jugadores):**
| Concepto | Puntos |
|---|---:|
| Goleador | 15 |
| Máximo asistente | 10 |
| Jugador más valioso (MVP) | 10 |
| Mejor portero | 10 |
| Mejor jugador joven | 7 |

**Otros:** Trivia acertada 1.

## Qué podemos modelar con lo que ya tenemos (reúso del motor)

| Bloque | Cómo | Estado |
|---|---|---|
| Marcadores por partido | **EV-máx con estos pesos** (exacto 4 / ganador 3 / goles-de-un-equipo 1 / dif 1). Es un *re-tuneo de pesos* del motor de CSC. | listo para correr |
| Campeón / sub / 3º | **futures de campeón** (ya bajados) + bracket calibrado (motor LEMAITRE) | listo |
| Clasificados 2da ronda | **P(avanzar)** de la sim de grupos (validada) | listo |
| Malla menos vencida | equipo con **menos goles en contra** en la sim | listo |
| Goleador / asistente / MVP / portero / joven (55 pts) | **necesitan mercados de jugador** (no gratis en The Odds API). Sin data, conjetura marcada `[REVISAR]`. | bloqueado por data |
| Trivia (1) | no modelable | n/a |

**Peso modelable:** ~todo menos los 55 pts de premios de jugador + 1 de trivia.
A diferencia de LEMAITRE, **no hay grilla de posiciones de grupo**; la
clasificación se premia plana (4 pts por equipo que avanza), así que el EV-máx de
clasificados ≈ los más probables de avanzar.

## Diferencia clave vs CSC/LEMAITRE (pesos → estrategia)
- "Goles de un equipo" + "Diferencia de gol" como ítems aparte (1+1) además de
  ganador (3) y exacto (4): premia acercarse. Hay que recalcular el EV-máx con
  esta tabla (puede mover el marcador óptimo respecto a CSC).
- Outrights pesan MUCHO (campeón 20, sub 15, 3º 10): aquí los futures de campeón
  valen aún más que en LEMAITRE.

## Preguntas abiertas (operativas — del usuario)
1. ¿Está **abierta**? ¿**deadline**?
2. ¿**Cuántos** participantes y **costo**? ¿Permite **varias** entradas?
3. ¿Cómo se **envía** (app Pollaya)? ¿Automatizamos con snippet de consola como CSC?
4. ¿El creador **editó** los puntos? (confirmar tabla real)
5. ¿Pide marcador de **todos** los partidos o por fases?
