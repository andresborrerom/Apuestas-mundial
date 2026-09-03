# Historia de la liga 250007 (NFL.com, 2010-2025) — modelo de la sala

Fuente: 943 páginas rescatadas de fantasy.nfl.com (tarball en `data/`),
parseadas con `ingest/parse_historia.py` → `data/historia_drafts.csv`
(3,258 picks) y `data/historia_standings.csv` (202 filas).

**Validación** ✅: pick 1 del draft 2024 (McCaffrey → Stat Correctors /
Andres) cotejado celda a celda contra el HTML crudo; nº de equipos del
draft cuadra con standings los 16 años (8→10→12→14/18→16 equipos).

## Hallazgo 1 — la sala es QB-hambrienta (y desde 2021, voraz)

QBs drafteados en rondas 1-3, siendo liga de **1 solo QB** (sin OP):

| Año | Equipos | 1er QB (pick global) | QBs en R1-R3 |
|---|---|---|---|
| 2021 | 14 | #1 | 11 |
| 2022 | 14 | #1 | 16 |
| 2023 | 16 | #1 | 21 |
| 2024 | 16 | #16 | 5 (año anómalo) |
| 2025 | 14 | #1 | 17 — **7 QBs en la R1** |

2025 R1: Allen, Lamar, Daniels, Hurts, Burrow, Mahomes, Stroud entre los
primeros 14 picks. **Implicación 2026 (superflex OP):** la corrida de QBs
será violenta; el QB élite NO va a caer. Baseline QB30 confirmado por
Andrés (la liga alinea ~30) y coherente con esta historia.

## Hallazgo 2 — la sala IGNORA el IDP hasta la ronda 10+ (arbitraje)

IDP existe desde 2023 (DL/LB/DB genéricos, 3 slots). Primer pick IDP de
la sala: ronda 10-11; la masa cae en rondas 13-17. Nuestro VBD pone a
Cashman/Simmons con valor de ronda 3-5, pero **históricamente nadie los
pelea antes de la ronda 10** → no gastar picks tempranos en IDP; apuntar
a rondas 8-10 (justo antes del primer madrugador histórico: Renzo 10.0,
Brian 10.7, Kike 11.3, Big Daddy James 11.5). ⚠️ Caveat: en 2026 son 5
slots IDP específicos (DT/DE/LB/CB/S) y tackles a 2.5 — la sala puede
adaptarse parcialmente; el plan se re-testea en mocks.

## Hallazgo 3 — kickers: ronda ~13

Primer K por equipo (2021-25): media 13.3, moda 13-14. Con los bonos v2
nuestro board los sube; tomarlo ronda 11-13 ya es "temprano" para la sala.

## Perfiles por manager (2021-2025)

| Manager | QB1 (ronda prom.) | IDP1 | K1 | Palmarés 2010-25 |
|---|---|---|---|---|
| Andres (Pocho) | 1.4 | 14.3 | 13.6 | 🥇1 🥈2 |
| Nicholas | 1.8 | 14.0 | 12.4 | 🥇2 🥈3 🥉6 |
| Camilo | 2.2 | 14.7 | 13.8 | 🥇3 🥈1 (bicampeón 21-22... por confirmar mapeo) |
| Luis Carlos | 2.0 | 13.7 | 13.2 | 🥇1 🥈3 |
| Kike | 2.4 | 11.3 | 13.8 | 🥇2 🥉1 |
| Santiago E | 2.0 | 13.7 | 13.8 | 🥉2 |
| Diego | 2.8 | 14.7 | 11.2 | 🥉1 |
| Sergio | 3.2 | 14.0 | 14.4 | 🥉2 |
| Rodrigo (Raw) | 2.4 | 14.0 | 14.4 | 🥇1 🥉1 |
| Brian | 5.4 | 10.7 | 11.4 | 🥇1 🥈1 |
| Big Daddy James | 4.5 | 11.5 | 15.5 | — |
| JHJ | 2.2 | 14.0 | 11.8 | — |

Rivales a respetar por resultados recientes: **Nicholas** (2º-3º-2º en
2021-23), **Camilo**, **Luis Carlos**, **Kike**.

## Mapeo managers viejos ↔ liga 2026 — COMPLETO ✅ (Andrés, 19-ago)

| Equipo 2026 | Manager histórico | Data disponible |
|---|---|---|
| Pocho | Andres | 2013-2025 · 🥇1 🥈2 |
| NK | Nicholas (Kling) | 16 años · 🥇2 🥈3 🥉6 — **amenaza #1** |
| Ferchos | Camilo Fernández | 2018-2025 · 🥇3 🥈1 — **amenaza #2** |
| Kike | Kike | 2018-2025 · 🥇2 🥉1 |
| Luis Ca | Luis Carlos | 16 años · 🥇1 🥈3 |
| Raw | Rodrigo (Raw Dawg) | 2017-2025 · 🥇1 🥉1 |
| Brian | Brian (saga LEONS/LOKO) | 16 años · 🥇1 🥈1 |
| Sergio | Sergio (Bolivia) | 16 años · 🥉2 |
| Diego | Diego | 2017-2025 · 🥉1 |
| Santi E | Santiago E | 2019-2025 · 🥉2 |
| Jaime | JHJ = Jaime Hoyos | 2019-2025 · nunca top-3 |
| James B | Big Daddy James | 2024-2025 |
| Acero | ½ del dúo "Santiago, Steve" 2025 | 1 año · 🥇 2025 |
| Steve | ½ del dúo "Santiago, Steve" 2025 | 1 año · 🥇 2025 |
| Gabriel | Gabriel | 1 año (2025, último) |
| Amigo Steve | — nuevo | sin data → modelar como promedio |

Nota clave: "Victorious Secret" 2018-2024 era de Santiago "Tranny", que
NO juega en 2026; Acero+Steve heredaron el spot y el nombre en 2025.
Su historia pre-2025 NO se atribuye a Acero — Acero y Steve son
efectivamente rookies con 1 título compartido, y al separarse en 2026
sus tendencias individuales son incógnita (los picks 2025 del dúo son
la única señal, sin saber de quién fue cada decisión).

Cobertura del modelo de sala: 12/16 equipos con historial multi-año,
3/16 con un año, 1/16 sin data. Ventaja informacional que ningún rival
tiene.
