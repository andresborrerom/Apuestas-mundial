# COLFONDOS — picks recomendados (foto de cuotas ~10-jun-2026)

> Outrights del modelo calibrado (`modelo_colfondos.py`); marcadores diarios con
> `marcadores_colfondos.py`; jugadores del consenso de mercado (agente web, The
> Odds API NO tiene mercados de jugador — solo campeón).

## Apuestas de torneo (una vez, al inicio)

**Orden COHERENTE (recomendado).** España y Francia caen en la **misma semifinal**
(1H y 1I) → si España es campeón, Francia **no puede** ser subcampeón. El sub debe
salir del **otro lado** del cuadro:

| Premio | Pts | Pick (coherente) | Nota |
|---|---:|---|---|
| Campeón | 20 | **España** | 15.8% marginal |
| Subcampeón | 15 | **Inglaterra** | otro lado del cuadro; puede perder la final vs España |
| Tercer puesto | 10 | **Francia** | perdió la semi contra España |
| Malla menos vencida | 7 | **España** | 0.63 GC/partido, P(semi) 40% |

Por qué Inglaterra y no Francia de sub (aunque Francia tenga P marginal un pelo
mayor, 8.9 vs 8.5): el **E[pts] es casi idéntico** (linealidad), pero el orden
coherente hace que **en el escenario bueno peguen los 3 juntos** (España gana la
final a Inglaterra, Francia 3ª) → +35 pts de golpe, que es lo que gana pollas.
Ver §2 de la nota al usuario.

**Clasificados 2da ronda — los 32 (todos los que clasifican, 4 pts c/u):**
España 99, Alemania 98, Brasil 98, Francia 97, Argentina 97, Bélgica 96,
Inglaterra 96, Portugal 95, Suiza 94, México 91, P. Bajos 91, Uruguay 88,
Noruega 88, Ecuador 88, Canadá 88, Colombia 87, Austria 84, Marruecos 83,
Croacia 83, C. Marfil 82, USA 81, Turquía 79, Japón 79, Egipto 75, Senegal 72,
**Argelia 68, Chequia 68, Corea Sur 67, Bosnia 65, Escocia 64, Suecia 63,
Paraguay 61** (estos 7 son burbuja <70% — los puntos 26-32, donde conviene
diferenciar entre entradas). Justo afuera: Irán 61, Ghana 45.

## Premios individuales (consenso de mercado, jun-2026)

The Odds API **no** los expone → data de Oddschecker/Goal/FOX/Covers (agente).

| Premio | Pts | Pick recomendado | Por qué |
|---|---:|---|---|
| Goleador (Bota) | 15 | **Mbappé (Francia)** ~14% | favorito del mercado; Francia llega lejos en el modelo |
| — alt. diferenciar | | **Kane (Inglaterra)** ~12% | Inglaterra es FINALISTA en nuestro bracket y enfrenta grupo débil (Panamá/Ghana) → tu intuición del partido desbalanceado |
| Balón de Oro (MVP) | 10 | **Lamine Yamal (España)** ~11% | mercado alto + España campeón (el Balón suele ser del campeón/finalista) |
| Guante de Oro (portero) | 10 | **Unai Simón (España)** ~18% | co-favorito + España campeón (4 de 5 últimos del país campeón) |
| Mejor joven | 7 | **Lamine Yamal (España)** ~39% | favoritísimo absoluto |

**Tesis España:** campeón + Yamal (MVP y Joven) + Unai Simón (guante) + malla =
~47 pts muy correlacionados. Es EV-máx (España es campeón del modelo Y del
mercado), pero si España cae, caen juntos. Para varias entradas, **decorrelar**:
una entrada España-céntrica, otra Francia/Mbappé o Inglaterra/Kane.

Riesgo de jugador: Yamal arrastraba molestia muscular (abr) — vigilar minutos.

## Marcadores (día a día — loop)
`marcadores_colfondos.py` da el marcador EV-máx por partido bajo los pesos de
COLFONDOS (exacto 4 / ganador 3 / dif 1 / goles-equipo 1). Estos pesos premian el
MARGEN, así que en partidos desbalanceados el óptimo es mayor que en CSC
(p.ej. Brasil 3-0 Haití, Curazao 0-2 C. Marfil). El `--riesgo` desvía hacia
upside cuando vamos atrás en el field.

## Pendiente del usuario
- ¿Cuántos "clasificados 2da ronda" pide Pollaya (¿16? ¿24? ¿32?)?
- Confirmar puntos reales si el creador los editó.
- Refrescar cuotas de jugador cerca del cierre (se mueven a diario).
