# Playbook — cómo atacar una polla NUEVA (punto de partida)

Receta reutilizable para cualquier polla, derivada de lo que construimos para
CSC. **El motor (`motor/`) y los mecanismos son los mismos; lo que cambia son
las REGLAS DE PAGO de cada polla.** Para una polla nueva, copia la carpeta de
CSC como plantilla y ajusta los puntos 1-2.

> Lectura previa recomendada: `HISTORIA.md` (cómo llegamos) y
> `pollas/CSC/DECISIONES.md` (todos los números y comandos).

---

## Lo que es COMÚN a todas las pollas (no se toca)

`motor/`:
- `cuotas.py` — cuotas → probabilidades (quita el margen de la casa).
- `marcadores.py` — distribución de marcadores (Poisson/Dixon-Coles) + sesgo a
  gol=1.
- `puntuacion.py` — relleno que maximiza puntos esperados.
- `odds_api.py` — bajar cuotas (consenso de casas, The Odds API).
- `simulacion_polla.py` — simulador de la polla (utilidad, P(1º), perturbación).
- `torneo.py` — simulador del torneo completo (dispersión por ronda).
- `backtest.py` — validación con partidos reales (football-data.co.uk).

Mecanismos validados (transferibles, re-tunear magnitudes por polla):
- **EV-máximo** (rellenar maximizando puntos esperados, no el más probable).
- **Sesgo a gol=1** (si la regla premia goles exactos asimétricamente).
- **Perturbación mínima** entre cupos (descorrelacionar para subir P(1º)).
- **Dispersión creciente por ronda** (poca donde hay muchos partidos, mucha
  donde hay pocos y valen más).

---

## Lo que CAMBIA por polla (lo único que hay que ajustar)

1. **La función de puntuación** (`reglas.py` de la polla): cómo reparte puntos.
   Familias ya disponibles en `motor/puntuacion.py`:
   - `regla_goles_por_equipo(...)` — goles de cada equipo por separado (CSC).
   - `regla_personalizada(pts_exacto, pts_diferencia, pts_resultado)` — marcador
     exacto / diferencia / resultado.
   - `regla_solo_resultado(pts)` — solo 1X2.
   Si la polla pide **campeón / goleador / etc.**, se modela con Monte Carlo
   (`motor/simulacion.py` + mercado `soccer_fifa_world_cup_winner`).

2. **La estructura de premios** (para decidir cuántos cupos): % por puesto,
   cuántos pagan. Va en el simulador (`PREMIOS` y `N`, `precio`).

---

## Receta paso a paso para una polla nueva

1. **Consigue las reglas** (PDF/imagen) y ponlas en `pollas/<NOMBRE>/`. Dáselas
   a Claude **completas** (no un resumen).
2. **Codifica la puntuación** en `pollas/<NOMBRE>/reglas.py` y **valida contra
   los ejemplos oficiales** del reglamento con tests.
3. **Verifica el relleno EV-máximo** en unos partidos (¿tiene sentido para esas
   reglas?). Recuerda: el óptimo NO suele ser el marcador más probable.
4. **Re-tunea el sesgo a gol=1** para los puntos de ESA polla (walk-forward con
   `backtest.py`; el α de CSC no necesariamente aplica).
5. **Modela los premios** y corre el simulador de cupos
   (`simulacion_polla.py` / `torneo.py`): decide K con análisis de sensibilidad
   al field y a N.
6. **Aplica perturbación + dispersión por ronda** según la estructura de la
   polla (muchos partidos → poca; pocos y valiosos → mucha).
7. **Genera la planilla** con cuotas en vivo, justo antes del deadline.

---

## Reglas de oro (heredadas de CSC)

- **Ground truth manda.** Toda mejora se mide walk-forward antes de creerla.
- **Separa evidencia real de simulación.** Los pesos en $ de las simulaciones
  son ilustrativos (dependen del modelo de rivales); lo robusto es lo relativo y
  lo validado con datos.
- **Suma cero:** solo ganas si le ganas al participante promedio.
- **Cuotas en vivo:** regenera la planilla cerca del deadline; las cuotas se
  mueven.
- **Honestidad:** documenta también lo que NO funcionó.

---

## Estado de las pollas

| Polla | Reglas | Modelo | Estado |
|---|---|---|---|
| CSC | ✅ (PDF) | EV-máx + sesgo + perturbación + dispersión/ronda | **Cerrada: 5 cupos** |
| COLFONDOS | imagen subida | pendiente (incluye campeón/goleador) | por montar |
| INGENIERO | PDF + xlsx subidos | pendiente (incluye campeón/goleador) | por montar |
| LEMAITRE | por subir | parte del playbook | por montar |
