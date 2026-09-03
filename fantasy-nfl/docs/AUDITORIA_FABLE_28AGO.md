# AUDITORÍA ADVERSARIAL (Fable) — 28-ago-2026

Mandato: **cuestionar todo lo avanzado**. Cada afirmación del sistema se
re-verificó contra su fuente (API viva, planilla real, código, re-cómputo),
no contra la memoria de la conversación. Formato: hallazgo → evidencia →
severidad → estado.

---

## A. LO QUE LA AUDITORÍA INTENTÓ TUMBAR Y NO PUDO

| afirmación | cómo se atacó | resultado |
|---|---|---|
| `MI_TEAM_ID = 10` del asistente en vivo | leer `mTeam` de la API HOY | ✅ teamId 10 = "No Team for Old Men", owner **Andres Borrero** |
| Pick 5 en el snake | leer `pickOrder` real de `mSettings` | ✅ `[13,7,1,17,**10**,...]` → asiento 5 = teamId 10. 45s/pick, SNAKE |
| 14 semanas + 8 a playoffs + desempate por PF | `scheduleSettings` de la API | ✅ coincide con la simulación (incluye `TOTAL_POINTS_SCORED`) |
| Candado 1 (nivel −1.2%) "podría ser cancelación de dos errores" (rosters flacos pero picks perfectos) | contar ofensivos/equipo tras el fix de rivales | ✅ descartado: real 12.5-14.0 vs sim 12.7-13.7 (el 8.0 que asusté era de ANTES del fix) |
| "Los rivales toman IDP al azar en el sim" (habría inflado mi ventaja) | rho(orden de toma, tablero) por posición | ✅ falso: rho 0.84-0.93 — la sala simulada toma IDP en orden sensato. Mi ventaja IDP medida: +82 pts reales, modesta |
| Scoring ofensivo/K/IDP | ya validado contra appliedTotal (1801/1801; K MAE 0.35) | ✅ se sostiene |

## B. LO QUE LA AUDITORÍA ENCONTRÓ ROTO (y se arregló en el acto)

### B1. 🚨 `calibrar_liga.py` estaba ROTO — el candado no podía ejecutarse
El refactor de `estado_sala` cambió la firma con que `draftear` llama a la
política; el `pol_greedy` local del candado no aceptaba `estado=` →
`TypeError`. **El candado de liga llevaba horas sin poder correr y nadie lo
sabía porque nadie lo re-corrió tras el refactor.** Un candado que no corre
no existe. FIX: `**kw` + re-corrida completa. REGLA NUEVA: después de tocar
`liga.py`, correr el candado — está en el checklist del día del draft.

### B2. 🚨 El modelo de premios repartía $10,100 de un pozo de $10,950
Se leyó la planilla REAL (`Fantasy_Payouts_2026.xlsx`) celda por celda. El
simulador no modelaba **$1,400 en flujos**:
- Highest Scorer Reg Season **+$250** (premia el PF crudo — favorece justo el
  perfil de equipo que arma el motor)
- Losers bracket **+$250** · Points against +$50 · Racha invicta +$50 ·
  Máximo de 1 semana +$50
- Multas: 2º DFL **−$150**, 3º **−$100**, 4º **−$75**, lowest margin −$25
  (solo el DFL −$200 estaba)
FIX: todo implementado. Candado nuevo: el neto repartido por temporada
simulada = **$10,400 exactos** = 16 buy-ins de $650 (los $550 de multas
financian el gap hasta $10,950 de premios brutos). Re-corrida en curso.

### B3. 🚨 El ECR histórico vivía en un directorio EFÍMERO
`ecr.parquet` (38 MB, insumo de TODO el backtest) estaba hardcodeado al
scratchpad de esta sesión en 3 archivos. Al morir el contenedor, el backtest
completo quedaba irreproducible sin que ningún error lo dijera. FIX: movido a
`data/ecr_fpecr.parquet` + URL de regeneración documentada en los 3 archivos.

### B4. ⚠️ Docstring que mentía
`elegibles()` decía que la anticipación de la sala estaba "medida por
asiento". Es constante (1). Un supuesto disfrazado de medición es exactamente
el bug invisible de la constitución. FIX: docstring honesto; la mejora real
(usar `managers.pesos()`) queda anotada como pendiente, no como hecha.

## C. LO QUE QUEDA CUESTIONADO (decisiones/estado — no código)

### C1. Asiento 9: ¿quién es? — NECESITA A ANDRÉS
La app dice asiento 9 = teamId 16 **"el l.ai.on"**, owner **Heejin Lee**.
Nuestro modelo tiene ahí a **Brian** (sesgo −4, ruido 15). Si es un manager
nuevo, le corresponde la personalidad global (0, 20). Impacto bajo (1 de 15
rivales), pero el mapeo manda sobre la personalidad. También: teamId 5 "The
Nest" (asiento 16, "Santi Gut") aún **sin owner** en la app.

### C2. La dispersión del sim ahora es MAYOR que la real (138%)
El candado pedía "al menos 60%" y pasa, pero pasó por ARRIBA: sim 1º/3º
1.084 vs real 1.061. La nota vieja del libro ("las diferencias entre
políticas se ven MÁS CHICAS — lado conservador") quedó **invertida**: con
dispersión 1.4×, los Δ$ entre políticas pueden verse algo MÁS GRANDES de lo
real. No cambia el veredicto (motor ganó por robustez año-a-año, no por Δ$
agregado), pero el sesgo declarado ahora apunta al otro lado.

### C3. Los intervalos pareados agrupan 4 temporadas como si fueran iid
El `t=2.4` de "regla vs motor" trata 1.200 diferencias como independientes;
están agrupadas por año (4 clusters). Con clustering honesto, motor/motor2/
regla son **estadísticamente indistinguibles** — que es justo lo que la tabla
año-por-año ya mostraba. El veredicto "motor por robustez y piso" sobrevive;
cualquier lectura de "regla +$68 es real" NO sobrevive.

### C4. PLAN_DRAFT.md está en tensión con el backtest — resolver el 7-sep
El plan pre-backtest tiene LB en R5 (Cashman) y DT en R7 (Simmons). El
backtest dice que el IDP temprano no pagó (motor2 ≈ motor) — PERO con
tablero de IDP = año anterior (rho 0.5), que sesga EN CONTRA del IDP
temprano. Ninguno de los dos gana el argumento todavía. Se resuelve el
día del draft re-midiendo con la proyección ESPN 2026 de IDP (que sí trae
noticias). Además la ficha **T1 sigue viva**: si el commish quita el ítem
"total" (statId 109), el LB pierde ~40% y el plan de IDP cambia entero —
el tripwire de settings corre ANTES de armar el tablero final.

### C5. Aproximaciones del simulador que siguen declaradas (aceptadas)
- 3º/4º de playoffs pagados como promedio (no se simula el partido por el 3º).
- `_surv` del motor usa el número de pick GLOBAL contra un rank solo-ofensivo:
  a mitad de draft sobreestima el consumo de ofensiva (el motor se adelanta
  un poco). Impacto acotado; anotado, no corregido.
- Banca con δ=0 en los rollouts de no-miope (δ nunca se pudo calibrar).
- Sin waivers/streaming en temporada.

## D. VEREDICTO DEL AUDITOR

1. **La cadena de scoring es sólida** — validada contra la fuente que paga,
   con candados que ya cazaron 6+ errores reales. Se sostiene.
2. **El simulador de liga es utilizable para COMPARAR políticas**, no para
   pronosticar E[$] absolutos (los $967 del motor tienen ±: premios ahora
   completos, dispersión 1.4×, 4 temporadas).
3. **El veredicto "motor, política fija, bosque no aporta" sobrevive la
   auditoría** — se apoya en la robustez año-a-año y en dos resultados
   negativos fuertes (greedy t=−16.8, no-miope t=−3.9), no en los Δ frágiles.
4. **Los tres hallazgos rotos (B1-B3) eran exactamente del tipo que la
   constitución predice**: el candado que nadie corre, la planilla que nadie
   leyó entera, la ruta efímera que nadie declaró. Arreglados y con regla.
5. Pendientes para Andrés: **C1** (¿quién es "el l.ai.on"/Heejin Lee?) y
   confirmar hora del draft (la app dice **7-sep 7:00pm Bogotá**).
