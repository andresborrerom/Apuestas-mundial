# Backtest del pipeline CSC — resultados

Validación empírica con **football-data.co.uk** (cuotas de cierre 1X2 +
Over/Under 2.5 y goles reales). Sin histórico de Mundiales en plan free de The
Odds API, validamos con fútbol de clubes: el pipeline es idéntico, así que la
conclusión es transferible. Reproducir: `python pollas/CSC/backtest.py`.

Muestra del informe (4.000 partidos, 5 ligas × 7 temporadas):

## 1) Edge real (puntos CSC por partido, fase de grupos)

| Relleno | pts/partido | vs modal |
|---|---|---|
| **EV-máximo (nuestro)** | **3.439** | **+0.285** |
| Modal (marcador más probable) | 3.155 | — |
| Favorito 1-0 (humano típico) | 2.473 | −0.682 |

El relleno EV-máximo **gana puntos reales**: +0.285/partido vs un rival que
pone el marcador más probable, y **+0.967/partido** vs uno que pone "favorito
1-0". Sobre 72 partidos de grupos: **+20 a +70 puntos** de ventaja acumulada.

## 2) Calibración (predicho → observado)

- **1X2 P(gana local):** sigue la diagonal (0.14→0.12, 0.40→0.40, 0.65→0.69,
  0.77→0.75). Quitar el margen produce probabilidades **bien calibradas**.
- **Over 2.5:** 0.529 → 0.535. Casi perfecto.
- **Goles por equipo:** 0:0.273→0.251 · 1:0.329→0.346 · 2:0.220→0.230 ·
  3:0.109→0.112 · 4:0.045→0.042. El modelo Poisson/Dixon-Coles **acierta la
  distribución de goles**. (Leve sesgo: predice "0 goles" un pelín de más y "1"
  de menos → en la práctica **refuerza** la jugada de ponerle 1 al débil.)

## 3) Hiperparámetros + walk-forward

- Método de margen (proporcional/shin/potencia) y Dixon-Coles on/off: **todas
  las configs dentro de 0.02 pts** → el modelo es robusto, no frágil. Mejor:
  `proporcional + Dixon-Coles`.
- **Walk-forward:** se elige la config en temporadas viejas (2018–2021) y se
  mide **fuera de muestra** en 2021–2025: edge vs modal **+0.275** (vs +0.285
  in-sample). **No hay sobreajuste**: el edge persiste.

## 4) Implicación para cupos.py

El edge medido convierte el supuesto "a ojo" del field en algo medido: un rival
realista (modal/favorito) equivale a **field-skill ≈ 0.4–0.6**. Es decir, para
decidir cuántos cupos usar:

```bash
python pollas/CSC/cupos.py --participantes <N> --field-skill 0.5
```

no el optimista 0.1. Con eso la recomendación (≈2–3 cupos, copias EV-máximo)
queda anclada en datos reales, no en intuición.
