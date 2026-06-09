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

## Pendiente / afinar

- En eliminatorias cuenta el resultado tras **120 min** (no penales) y se
  puede apostar al empate. Si la casa publica cuotas "tras alargue"/"to
  advance", úsalas; si no, las 1X2 de tiempo reglamentario aproximan bien.
