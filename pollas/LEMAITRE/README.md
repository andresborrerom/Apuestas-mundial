# Polla LEMAITRE

Nueva polla a la que también entramos. **Punto de partida: el método ya
construido para CSC** (ver `../../PLAYBOOK.md` y `../../HISTORIA.md`), ajustado a
las **reglas de pago de LEMAITRE**.

## Pasos

1. Sube aquí el archivo con las **reglas/presentación** de LEMAITRE (PDF/imagen).
2. Claude codifica su puntuación en `reglas.py` y la **valida contra los
   ejemplos del reglamento** con tests.
3. Re-tunea el sesgo a gol=1 y modela los premios para decidir cuántos cupos.
4. Aplica los mecanismos validados (EV-máximo, perturbación mínima, dispersión
   creciente por ronda), ajustados a sus reglas.
5. Genera la planilla con cuotas en vivo antes del deadline.

> No reinventes nada: el motor (`motor/`) es común. Aquí solo va lo que depende
> de las reglas de LEMAITRE. Sigue la receta de `PLAYBOOK.md`.
