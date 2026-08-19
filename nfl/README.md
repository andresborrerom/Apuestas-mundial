# NFL 2026 — LIGA EL FULBITOL (Pick'em + Survival)

Proyecto NFL aparte de las pollas del Mundial (`pollas/`) y aparte del fantasy.
Dos juegos independientes en la app de Yahoo Fantasy, con reglamentos, pozos y
responsables distintos. Los PDF oficiales están en cada carpeta.

| | 🔵 PICK'EM | 🟠 SURVIVAL |
|---|---|---|
| Participación | Todos los de la liga | Voluntario (solo apuntados) |
| App (Yahoo Fantasy) | Pro Football Pick'em | Survival Football |
| Group ID | **498** | **9724** |
| Password | **NICOPEPE** | **NICOVD** |
| Aporte | Saldos por corte (ver reglas) | **$300.000 único, por adelantado** |
| Pago a | Nequi Nico Villaveces 3183377514 | Nequi Pepe Cely 3108687756 (@3108687756) |
| Administra | Comisionado (Nico) | Pepe Cely |
| Reglas | [`PICKEM/REGLAS.md`](PICKEM/REGLAS.md) | [`SURVIVAL/REGLAS.md`](SURVIVAL/REGLAS.md) |

⚠️ Son grupos y contraseñas **distintas**. Usar el **mismo username** en los dos
juegos (si no, no se pueden cruzar las tablas).

Descarga: [sports.yahoo.com/fantasy/mobile](https://sports.yahoo.com/fantasy/mobile)

## Fechas clave

| Fecha | Qué pasa |
|---|---|
| **Antes del kickoff Semana 1** (~9-sep-2026, confirmar en la app) | Deadline duro del Survival: inscrito en Yahoo **y** pagado. Yahoo cierra el grupo solo; no hay entrada tardía. |
| Cada martes | El comisionado publica cuadro de puntos y saldos en WhatsApp. |
| Martes tras Monday Night Semana 9 | **Corte 1** Pick'em: Batalla Semanal (sem. 1-9) + Small Pot 1. |
| Martes tras Monday Night Semana 18 | **Corte 2** Pick'em: Batalla Semanal (sem. 10-18) + Small Pot 2 + Big Pot. |

## Qué se puede modelar (reúso del motor)

Es NFL, no fútbol: acá no hay marcadores exactos ni Poisson de goles. Lo que sí
transfiere del `motor/` es la idea central: **cuotas → probabilidades sin margen**
(`motor/cuotas.py` es agnóstico al deporte) y **suma cero: solo ganas si le ganas
al participante promedio**.

| Bloque | Cómo | Estado |
|---|---|---|
| P(gana) por partido | Moneylines NFL de The Odds API (sport key `americanfootball_nfl`), consenso de casas, quitar margen | listo para montar |
| Pick'em: picks base | 1 pt por acierto plano → el EV-máx individual es **el favorito en todo** | trivial |
| Pick'em: Batalla Semanal (winner-take-all) | Con N jugadores todos en favoritos, empatas y el pozo acumula. Valor esperado de **diferenciarse** en los partidos más parejos (P≈50%) — misma lógica de decorrelación del PLAYBOOK | por modelar |
| Survival: qué equipo quemar cada semana | Problema clásico de optimización: no repetir equipo + 2 vidas + cierre único el jueves. Greedy (mejor favorito de la semana) vs. planeación (guardar súper-favoritos para semanas flacas), DP/ILP sobre el calendario | por modelar |
| Survival: valor de las 2 vidas | Simulación del pozo: cuándo conviene arriesgar sabiendo que la 1ª vida es amortiguador | por modelar |

## Preguntas abiertas (operativas)

1. ¿Cuántos jugadores quedan inscritos en cada juego? (define pozos y el field
   contra el que se compite).
2. ¿The Odds API da moneylines NFL con la key actual? (sí en el plan gratis,
   verificar cupo de requests para 18 semanas).
3. Pick'em: ¿se ven los picks de los rivales antes del cierre? (cambia la
   estrategia de la Batalla Semanal las últimas semanas de cada corte).
