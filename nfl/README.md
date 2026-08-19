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

## El modelo (montado y validado walk-forward 2011-2025)

**Bitácora completa con números: [`MODELO.md`](MODELO.md).** Resumen:

| Bloque | Resultado | Estado |
|---|---|---|
| P(gana) por partido | Moneyline de cierre de-vig (nflverse `games.csv`, 2010-2025) — Brier 0.2104, bien calibrado; Elo solo para proyectar futuro | ✅ validado |
| Pick'em: pots | Favorito en todo (66.6% de acierto). P(1º Big Pot) 53-84% según field | ✅ validado |
| Pick'em: Batalla Semanal | Favoritos puros: P(1º único) ~0%. **Voltear 1-2 coin-flips**: 3.5-15%, costo ~1 pt/temporada | ✅ validado |
| Survival: estrategia | **Heurística marrano** (no-élite vs bottom-5, élites guardadas): 11.9 semanas medias vs 8.5 greedy; única E[ganancia]>0 bajo todo supuesto de field | ✅ validado |
| Survival: el marrano | Pick "contra marrano" disponible el 100% de las semanas con p≈0.81; bien calibrado (82% real) | ✅ medido |

## Uso cada semana (2026)

```bash
# refrescar líneas y pedir picks de la próxima semana
curl -sSL -o nfl/datos/games.csv \
    https://github.com/nflverse/nfldata/raw/master/data/games.csv
python nfl/semana.py --usados KC,PHI   # equipos ya quemados en Survival
```

## El pool real: N=14 + alianza de 2

Somos 14 en ambos juegos, con alianza de banca compartida con un amigo
(análisis en `MODELO.md` §8; scripts `nfl/SURVIVAL/alianza.py` y
`nfl/PICKEM/alianza.py`). El plan 2026:

- **Survival**: A juega marrano; B juega marrano excluyendo el pick de A
  cada semana (rutas distintas). Coordinarse duplica el E[neto] por cabeza
  y sube P(cobrar) de 32% a 51-62%.
- **Pick'em**: A = favoritos + flip del coin-flip #1; B = favoritos + flips
  de los coin-flips #2 y #3. La banca pasa de −$46k a +$68k esperados por
  semana en la Batalla, sin costo en los pots.

## Preguntas abiertas (operativas)

1. ¿Yahoo muestra la **distribución de picks del grupo** antes del cierre?
   (volvería el anticrowd informado en vez de supuesto).
2. Semanas finales del Survival mano a mano: juego head-to-head no modelado.
3. Si el N cambia antes del kickoff, re-correr `alianza.py`.
