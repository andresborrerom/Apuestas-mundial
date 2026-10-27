# Dossier de evidencia — "El modelo fue perfecto; el resultado, casi"

> Material de respaldo para la publicación de LinkedIn. Todo lo listado aquí
> es **verificable por terceros**: los commits de git son sellos de tiempo
> criptográficos (un hash SHA no se puede fabricar retroactivamente sin
> romper todo el historial del repositorio), y las tablas oficiales de las
> dos pollas son públicas o auditables por sus organizadores.

---

## 1. La prueba central: la final se predijo EXACTA, dos días antes

**Commit `de4498a` — 17 de julio de 2026, 13:37 UTC** (la final se jugó el
19 de julio, 19:00 UTC). Contenido del archivo `pollas/CSC/finales_CSC.csv`
en ese commit, verificable por cualquiera con acceso al repo:

```
$ git show de4498a:pollas/CSC/finales_CSC.csv
fecha,hora,local,visita,marcador,cupo_1,cupo_2,cupo_3,cupo_4,cupo_5
2026-07-18,16:00,Francia,Inglaterra,3-1,1-2,1-2,1-2,3-1,2-1
2026-07-19,14:00,España,Argentina,2-1,1-0,2-1,1-2,2-1,1-2
```

- **Cupo 1, final: España 1-0 Argentina.** Resultado real: **España 1-0**
  (gol en el alargue). Predicho 54 horas antes, congelado en git.
- El mismo archivo predijo ganador Inglaterra en el 3er puesto (cupos 1-3)
  — Inglaterra ganó.

Ese 1-0 exacto valía el campeonato de la polla (posición #1 de 114). No se
cobró por un bug de **entrega** (sección 4), no de modelo.

## 2. Timeline completa: cada predicción committeada ANTES de cada evento

| Commit | Fecha (UTC) | Qué quedó escrito | Qué pasó después |
|---|---|---|---|
| `7065107` | 28-jun 13:27 | Cupos de Fase 32 (motor EV-máximo + dispersión) | El pack tomó el liderato de la polla en octavos |
| `869355e`→`dfdaada` | 13-jul 00:09-01:16 | Config de semis G3 elegida por **auditoría de 3 agentes adversariales** (uno derrotó la config original) | Semi 1 (Fra 0-2 Esp): el 71% del field puntuó CERO; nuestro cupo 4 pasó al #1 general |
| `de4498a` | 17-jul 13:37 | Planilla de finales, incl. **España 1-0** | La final terminó España 1-0 |
| `a9870fb`, `a80fda1`, `9c2ed95`, `67deb00` | 14-19 jul | Cada resultado real registrado el día del partido, con recálculo público de probabilidades | — |

## 3. Resultados finales verificables

- **Polla CSC (114 planillas, ~$11.4M de pozo):** terminamos **2º y 3º**
  (ANDRES BORRERO 4 = 546 y ANDRES BORRERO 5 = 529) → **≈$3.99M en premios**
  con una inversión de 5 cupos. Fuente: PDF oficial de resultados del
  organizador, 19-jul-2026.
- **Polla LEMAITRE (27 participantes):** **3º** (Pocho, 2004 puntos), tabla
  pública en https://templecolombia.github.io/polla-mundial-2026/ — nuestro
  scorer replica esa tabla **celda por celda, 7/7 validaciones** a lo largo
  del torneo (el código de scoring del app es público en el repo de GitHub
  del organizador).

## 4. La honestidad de la historia: el error que costó el título

La transparencia es lo que hace creíble el resto. El cupo 1 tenía el 1-0
exacto y quedó 6º: el formulario de envío listaba los equipos en orden
inverso ("Argentina vs España") y el script de llenado escribió los goles
sin verificar el orden → los 5 cupos se enviaron con el marcador invertido.

**Prueba de la causa (auditoría post-mortem, commit `7c31376`):** los puntos
que ganó cada cupo en los últimos 2 partidos cuadran EXACTOS con los picks
invertidos — los cinco: +0, +17, +8, +23, +14. Los recibos oficiales del
formulario ("Pronósticos_N.pdf") muestran la inversión. Costo calculado:
**$4.56M y el título** (con el llenado correcto: #1 + #3 + #4 = ~$8.55M).

De ese error salió la regla que cierra la historia: *el candado debe cubrir
hasta donde el artefacto es ACEPTADO por el receptor, no hasta donde sale de
tus manos.* (Documentada en `CLAUDE.md` Parte III.10 y `HISTORIA.md` Acto 19.)

## 5. El método, en números verificables

- **Backtest walk-forward con ~12.000 partidos reales** (football-data.co.uk):
  el relleno EV-máximo gana +0.285 a +0.97 pts/partido vs métodos manuales,
  fuera de muestra (`pollas/CSC/RESULTADOS_BACKTEST.md`, scripts incluidos).
- **Auditorías multi-agente adversariales** (agentes independientes con el
  mandato "derrota esta configuración"): una atrapó un error de etiqueta de
  ~$500k antes de enviar; otra encontró una config superior (+$545k de EV
  medido en validación pareada) que fue la que finalmente se jugó — y la que
  quedó #2 y #3.
- **Tripwire de reglas:** script que hashea el código de scoring del
  organizador y bloquea toda proyección si cambió. Disparó el 20-jul al
  detectar el bloque nuevo de puntuación final — el mismo día en que cambió.
- **Predicción bajo incertidumbre declarada:** cada proyección publicada en
  los commits separa VALIDADO / CALCULADO / SUPUESTO / INCOGNOSCIBLE, con
  sensibilidad. (Protocolo completo: `PROTOCOLO_SUPUESTOS.md`.)

## 6. Cómo puede verificarlo un tercero escéptico

1. Clonar el repositorio y correr `git log --format='%h %ad %s'` — la
   cadena de hashes hace imposible insertar predicciones después del hecho.
2. `git show de4498a:pollas/CSC/finales_CSC.csv` — la planilla de la final,
   sellada el 17-jul.
3. Comparar la tabla LEMAITRE del app público contra
   `pollas/LEMAITRE/puntos_lemaitre.py` (réplica exacta del scoring).
4. Pedir al organizador de CSC los PDFs oficiales de posiciones (28-jun a
   19-jul) y los recibos de los formularios.

---

*Resumen para el post: el sistema predijo el marcador exacto de la final del
Mundial 54 horas antes (sellado en git), terminó 2º y 3º entre 114 con dinero
real, y perdió el #1 por un bug de un centímetro en la entrega — que quedó
documentado, probado y convertido en regla. La historia completa, acto por
acto, está en HISTORIA.md.*
