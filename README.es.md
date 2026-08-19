# Apuestas Mundial — motor de probabilidades para pollas

Herramienta para rellenar pollas del Mundial maximizando los **puntos
esperados** según las reglas de cada polla, a partir de las cuotas de las
casas de apuestas.

## 📚 Documentos clave (empieza aquí)

- **[`HISTORIA.md`](HISTORIA.md)** — la crónica de cómo llegamos al modelo
  (material de enseñanza: "cómo usar Claude para ciencia de datos").
- **[`PLAYBOOK.md`](PLAYBOOK.md)** — la receta reutilizable para atacar una
  polla nueva. **Punto de partida para COLFONDOS, INGENIERO, LEMAITRE.**
- **[`pollas/CSC/DECISIONES.md`](pollas/CSC/DECISIONES.md)** — la bitácora
  técnica completa (números, fórmulas, comandos, hallazgos y refutaciones).

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
motor/                # común a todas las pollas (no depende de reglas)
  cuotas.py           # cuotas -> probabilidades (quita el margen)
  marcadores.py       # distribución de marcadores (Poisson/DC) + sesgo gol=1
  puntuacion.py       # relleno que maximiza puntos esperados
  odds_api.py         # bajar cuotas (consenso de casas, The Odds API)
  simulacion_polla.py # simulador de la polla (utilidad, P(1º), perturbación)
  torneo.py           # simulador del torneo completo (dispersión por ronda)
  backtest.py         # validación con partidos reales (football-data.co.uk)
  simulacion.py       # Monte Carlo del torneo (campeón, subcampeón, ...)
pollas/
  _plantilla/         # ejemplo de cómo definir las reglas de una polla
  CSC/                # CERRADA: reglas + experimentos + DECISIONES.md + planilla
  COLFONDOS/          # por montar (incluye campeón/goleador)
  INGENIERO/          # por montar (incluye campeón/goleador)
  LEMAITRE/           # por montar
nfl/                  # NFL 2026 — LIGA EL FULBITOL (Yahoo Pick'em + Survival), proyecto aparte
tests/                # verificación de la matemática
```

Cada `pollas/<X>/` tiene scripts ejecutables y autoexplicados: `reglas.py`
(puntuación), `llenar.py` (genera planilla), `cupos.py` (cuántos comprar),
`experimento_*.py` (cada teoría probada) y `demo_*.py` (demos pedagógicas).

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
- [x] **CSC cerrada:** reglas validadas, modelo validado con ground truth
  (backtest + walk-forward), decisión de **5 cupos**, planilla generada.
- [x] Mecanismos validados: EV-máximo, sesgo a gol=1, perturbación mínima entre
  cupos, dispersión creciente por ronda.
- [ ] COLFONDOS / INGENIERO / LEMAITRE: aplicar el `PLAYBOOK.md` a sus reglas.
- [ ] Modelo de campeón/goleador (Monte Carlo + `soccer_fifa_world_cup_winner`).
- [ ] Eliminatorias: top-k de rellenos en rondas de 1-2 partidos.
- [ ] Opcional: scrapear OddsPortal (gratis) para Over/Under de Mundiales.
