# Polla CSC — La Super Polla de los Pollos 2026

Reglamento completo en `Reglamento Polla Super Polla 2026.pdf`.

## Cómo puntúa (resumen)

Puntaje por partido = suma de **tres componentes**:
1. Acertar ganador/empate (tendencia 1X2).
2. Acertar los goles **exactos del equipo local**.
3. Acertar los goles **exactos del equipo visitante**.

Los goles premian a cada equipo por separado y **más goles acertados = más
puntos** (`# goles + base`), salvo el 0 (puntaje fijo menor). Los puntos
**suben por ronda** (la final vale ~5x la fase de grupos). Tabla en
`reglas.py` (`RONDAS`).

Solo se piden **marcadores**, ronda por ronda. No hay campeón ni goleador.

## Uso

```python
from pollas.CSC import reglas as csc

r = csc.rellenar(
    "primera",                       # ronda
    cuotas_1x2=[1.50, 4.20, 6.50],   # [local, empate, visita] de tu casa
    cuotas_ou=[2.10, 1.75],          # [under, over] 2.5 (opcional)
)
print(r["relleno_optimo"], r["puntos_esperados"])
```

Rondas válidas: `primera`, `dieciseisavos`, `octavos`, `cuartos`, `semis`,
`tercer_puesto`, `final`.

## Hallazgo estratégico clave

Como acertar **0 goles** vale menos que acertar **1** (`2` pts vs `1+3=4` en
grupos), al equipo débil conviene predecirle **1 gol aunque lo más probable
sea que no marque**. Ejemplo real del motor: con un favorito (goles esperados
2.0–0.86) el marcador más probable es **2-0**, pero el relleno **óptimo es
2-1**. Esto sale solo de las reglas y el motor lo explota automáticamente.

## Comando automático (bajar cuotas y rellenar)

`llenar.py` baja las cuotas del Mundial (consenso de varias casas vía
[The Odds API](https://the-odds-api.com)), calcula el relleno óptimo de cada
partido del día y lo imprime / exporta a CSV.

```bash
# 1) key gratis en the-odds-api.com
export ODDS_API_KEY=tu_key

# 2) rellenar los partidos de mañana (ronda inferida por fecha)
python pollas/CSC/llenar.py

# variantes
python pollas/CSC/llenar.py --date 2026-06-12 --round primera --csv marcadores.csv
python pollas/CSC/llenar.py --list-sports          # ver clave del torneo
python pollas/CSC/llenar.py --mock pollas/CSC/ejemplo_odds.json --date 2026-06-12
```

Notas:
- Usa el **consenso (mediana) de varias casas**, más robusto que una sola.
  Rushbet no tiene API pública y se mueve cerca de ese consenso.
- La ronda se infiere de la fecha (calendario 2026) o se fuerza con `--round`.
- El comando recuerda el **deadline de envío** de la ronda.
- Zona horaria por defecto `America/Bogota` (la de los deadlines).
- `--all` vuelca **toda la fase de grupos** (72 partidos) de una pasada — útil
  porque CSC exige enviar todos los marcadores de grupos antes del 11/06.

## ¿Cuántos cupos comprar? (optimizar utilidad)

`cupos.py` simula la polla (Monte Carlo) y recomienda cuántos cupos maximizan
la **utilidad esperada = premios − costo**.

```bash
python pollas/CSC/cupos.py --participantes 120 --sensibilidad
```

Claves del modelo:
- La polla es **suma cero** (premios = 100% del recaudo). Solo hay utilidad
  positiva si nuestro relleno **supera al participante promedio**.
- `--field-skill` (0=rivales casuales, 1=rivales óptimos) es el supuesto más
  importante y al que el resultado es más sensible. Usa `--sensibilidad`.
- `--participantes` = total de cupos en la polla (define el pot).
- Estrategia `evmax` (copias idénticas del relleno óptimo) suele ganarle a
  `diversificada`: cuando tu puntaje queda arriba, las copias empatan y la
  **rifa de desempate** las reparte en varios puestos del top-5.
- `--ruido-extra` añade incertidumbre tipo eliminatorias (la simulación base
  es solo fase de grupos; el ranking real incluye knockout, con más varianza).

**Hallazgos:** el nº óptimo de cupos es chico (≈1–5) y **cae rápido si el field
es bueno**. Contra un field sharp (≥60% óptimo) conviene 1 cupo; comprar muchos
es −EV. Los pesos absolutos son ilustrativos y dependen de tus supuestos.

## Pendiente / afinar

- En eliminatorias cuenta el resultado tras **120 min** (no penales) y se
  puede apostar al empate. Si la casa publica cuotas "tras alargue"/"to
  advance", úsalas; si no, las 1X2 de tiempo reglamentario aproximan bien.
