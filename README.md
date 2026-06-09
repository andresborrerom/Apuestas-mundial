# Apuestas Mundial — motor de probabilidades para pollas

Herramienta para rellenar pollas del Mundial maximizando los **puntos
esperados** según las reglas de cada polla, a partir de las cuotas de las
casas de apuestas.

## La idea

Las cuotas de las casas son el mejor predictor barato que existe: incorporan
muchísima información y son difíciles de batir. Pero hay tres claves que casi
nadie aplica bien y que son donde se ganan las pollas:

1. **Las cuotas no son probabilidades.** Sus inversos suman >100%; ese exceso
   es el margen de la casa. Hay que quitarlo (`motor/cuotas.py`).
2. **No se rellena con lo más probable, sino con lo que maximiza puntos
   esperados** según las reglas de TU polla (`motor/puntuacion.py`). Con
   marcador exacto el óptimo suele ser 1-0 / 1-1 aunque esperes goleada.
3. **Los goles salen de la distribución completa** de marcadores (Poisson /
   Dixon-Coles), despejada del 1X2 + Over/Under (`motor/marcadores.py`).

Para campeón / subcampeón se simula el torneo entero miles de veces
(`motor/simulacion.py`).

## Estructura

```
motor/            # común a todas las pollas (no depende de reglas)
  cuotas.py       # cuotas -> probabilidades (quita el margen)
  marcadores.py   # distribución de marcadores (Poisson/Dixon-Coles)
  puntuacion.py   # relleno que maximiza puntos esperados
  simulacion.py   # Monte Carlo del torneo (campeón, subcampeón, ...)
pollas/
  _plantilla/     # ejemplo de cómo definir las reglas de una polla
  CSC/            # cada polla: su presentación + sus reglas
  COLFONDOS/
  INGENIERO/
tests/            # verificación de la matemática
```

## Uso rápido

```python
from motor import analizar_partido
from motor.puntuacion import regla_personalizada

regla = regla_personalizada(pts_exacto=5, pts_diferencia=3, pts_resultado=2)

r = analizar_partido(
    cuotas_1x2=[1.80, 3.60, 4.50],   # [local, empate, visita]
    cuotas_ou=[2.00, 1.80],          # [under, over] 2.5
    regla=regla,
)
print(r["relleno_optimo"], r["puntos_esperados"])
```

## Instalar y probar

```bash
pip install -r requirements.txt
python tests/test_motor.py
```

## Estado / siguientes pasos

- [x] Motor de cuotas, marcadores, puntuación y simulación.
- [ ] Reglas concretas de cada polla (CSC, COLFONDOS, INGENIERO).
- [ ] Cargar cuotas reales de la casa.
- [ ] Estructura del Mundial 2026 (48 equipos) para la simulación.
- [ ] Ajuste *contrarian* para pollas grandes con premio único.
