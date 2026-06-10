# LEMAITRE — modelo final, por qué y con qué evidencia

Polla LEMAITRE (Mundial 2026). Inscripción **$234.000**, máximo **3.900 puntos**.
Premios: 90% de lo recaudado → **60% / 30% / 10%** (1º/2º/3º).
A diferencia de CSC, **no se puntúan los marcadores de fase de grupos**: aquí
casi todo el puntaje es **clasificación** (quién avanza y a qué puesto) +
marcadores de eliminatorias + extras.

## 1. De dónde sale cada puntaje (presupuesto del reglamento)

| Bloque | Puntos | % | Cómo lo modelamos |
|---|---:|---:|---|
| Clasificación a Fase 32 (A) | 640 | 16.4 | sim de grupos (cuotas de cada partido) |
| Marcadores Fase 32 | 640 | 16.4 | EV-máx por llave |
| Octavos: marcadores | 320 | 8.2 | EV-máx por llave |
| Clasif. Octavos / orden de grupo (B) | 280 | 7.2 | sim de grupos |
| Clasif. Cuartos (C) | 240 | 6.2 | bracket calibrado |
| Extras Colombia (H) | 250 | 6.4 | sim (posición, GF/GC) + jugadores (no) |
| **Otros extras (I)** | **500** | **12.8** | parcialmente modelable (ver §5) |
| Clasif. Semis (D) | 160 | 4.1 | bracket calibrado |
| Cuadro de honor (G) | 210 | 5.4 | bracket calibrado |
| Semis gan/perd (E) | 190 | 4.9 | bracket calibrado |
| Marcadores cuartos/semis/3º/final | 200+120+70+80 | | EV-máx por llave |

**Hallazgo clave:** el 44% del puntaje es *clasificación* (poco que ver con
goles). El bloque "Otros extras" (500 pts, 12.8%) lo estábamos ignorando y es
casi un quinto de la polla — buena parte es modelable.

## 2. Dos fuentes de verdad, combinadas con honestidad

1. **Cuotas de cada PARTIDO de grupos** (mercado directo, gratis del API).
   → sim Monte Carlo de los 12 grupos → quién clasifica, posiciones, mejores
   terceros, y la distribución de marcadores de cada llave de Fase 32.
   *Validado con ground truth* (`backtest_clasificacion.py`, 4 Mundiales reales):
   P(clasificar) bien calibrada (0.66→0.65, 0.88→0.85); ganador de grupo 69%;
   top-2 exacto 38% (los grupos son genuinamente impredecibles — ese 38% es
   piso de incertidumbre, no error del modelo).

2. **Cuotas de CAMPEÓN** (futures, 5 casas, gratis: `soccer_fifa_world_cup_winner`).
   → **calibran la fuerza de eliminatorias**.

### Por qué hacía falta la calibración (sesgo medido, no supuesto)
Los ratings de ataque/defensa salían **solo** de partidos de grupo. Eso
sobre-estima a equipos de grupos débiles e infra-estima a escuadras élite en
grupos medios. Medido contra el mercado:

| Equipo | sim crudo | mercado | corrección |
|---|---:|---:|---:|
| France | 8.2% | 14.7% | sim muy **bajo** |
| England | 6.8% | 10.4% | bajo |
| Portugal | 6.0% | 9.8% | bajo |
| Germany | 10.3% | 5.5% | sim muy **alto** (grupo E débil) |
| Belgium | 7.3% | 2.1% | altísimo (grupo G débil) |

Mecanismo: ganarle fácil a Egipto/Irán/N.Zelanda (Bélgica) **no** es lo mismo
que ganarle a España/Francia, pero el rating de grupo no lo distingue. El
futures sí lo precia (escuadra + dificultad del camino).

### Cómo se calibra (estable, 1 parámetro)
La teoría de torneos da `log P(campeón) ≈ k·fuerza_eliminatoria + cte`. Por eso
**reemplazamos** la fuerza de cada contendiente por la implícita en el mercado
(δ ∝ log p_campeón, centrado), preservando su estilo ataque/defensa y el nivel
global de goles. Una sola **temperatura τ** controla la dispersión; se busca en
1-D para minimizar la divergencia KL contra el mercado. Resultado tras calibrar:

```
Spain 15.8% (mkt 15.4) · France 14.2 (14.7) · England 10.9 (10.4)
Portugal 11.0 (9.8) · Argentina 8.7 (8.3) · Brazil 8.6 (8.3) · Germany 5.9 (5.5)
```
Cuadra con el consenso de 5 casas — la mejor verdad disponible para fuerza de
ronda final. (Intentos previos —regresión + IPF, gradiente en el loop— eran
inestables y los descartamos; quedó documentado.)

**Separación limpia:** los grupos NO se tocan (sus cuotas de partido ya son el
mercado correcto). Solo se recalibra la fuerza cruzada de eliminatorias.

## 3. Cómo se llena (EV-máx, no "lo más probable" cuando difieren)
- **Orden de grupo / Fase 32 / terceros:** equipo de mayor probabilidad marginal
  por casilla (la recompensa por "equipo en su puesto exacto" domina).
- **Bracket:** árbol **coherente** (forward pass) — en cada llave avanza el de
  mayor P(ganar) cabeza a cabeza entre los dos ocupantes elegidos. El formulario
  exige un árbol consistente (el ganador del #X fluye al siguiente).
- **Marcadores:** EV-máx sobre la distribución de marcador de **esa llave**
  (independiente de quién juegue — así lo dice el reglamento), bajo los tramos
  exacto/resultado/parcial de cada ronda. Da casi siempre 1-0/1-1 porque en
  eliminatoria a sede neutral el favorito gana por mínima y el bono por marcador
  exacto jala al marcador modal.

## 4. Cuadro de honor proyectado (con esta foto de cuotas)
**1º España · 2º Inglaterra · 3º Francia · 4º Portugal** (España campeón ~16%).
Es la proyección coherente del árbol; España y Francia caen en la **misma mitad**
(1H y 1I → se cruzan en semis), por eso solo uno llega a la final.

## 5. Extras modelables (los que sí salen de la simulación)
- Número total de goles: **~275** (p10 254 – p90 296).
- Continente campeón / subcampeón: **UEFA** (72% / 63%).
- Equipo +/− goles a favor/contra: España (+GF, −GC) / Curaçao (−GF, +GC).
- Colombia: posición de grupo (2º más probable, 44%), GF~5, GC~3.
- **No modelables sin datos de jugadores (~360 pts):** goleador, jugador 1er/últ
  gol, equipo del gol 50/100. Requieren mercado de goleador (no gratis aquí) o
  datos de plantillas. Marcados como pendientes — no inventamos.

## 6. Valor esperado en puntos (Monte Carlo contra el torneo simulado)
| Bloque | E[pts] | máx |
|---|---:|---:|
| Marcadores (exacto) | 528 | 1430 |
| Clasificación (aprox. lineal) | 474 | 1320 |
| Cuadro de honor (exacto) | 49 | 210 |
| Semis gan/perd (exacto) | 36 | 190 |
| Extras modelables | 44 | 140 |
| **TOTAL estimado** | **~1130** | 3900 |

p10–p90: **909–1364** (varianza alta: una polla se gana o pierde en los aciertos
raros de eliminatoria). Honestidad: este E[pts] se puntúa contra **nuestro
propio** modelo (es "lo que esperamos si la realidad se parece a nuestras
creencias"), no un número validado contra resultados reales. Marcadores y honor
usan reglas exactas; clasificación usa aproximación lineal por presupuesto de
sección (los sub-tramos "en orden / invertido" del reglamento no cambian el
*pick* EV-máx, solo el reporte de puntos).

## 7. Lo que falta para E[GANANCIAS] (pendiente de tus datos)
E[ganancia] = Σ P(quedar 1º/2º/3º)·premio − inscripción. Necesita:
- **N inscritos** y valor (para el pozo: 0.90·N·$234.000, repartido 60/30/10).
- **Modelo de campo** (como en CSC): simular las planillas rivales (arquetipos:
  sigue-mercado, favoritos, casual) puntuando el MISMO torneo, y medir dónde cae
  nuestra planilla. Con varianza p10–p90 de ~450 pts, ganar depende de pegar los
  aciertos raros — igual que en CSC, conviene **diferenciar** si se compran
  varias planillas. Listo para correr en cuanto pases N.

### Sensibilidad CRÍTICA: qué tan afilado es el campo (N=80, 1 planilla)
Nuestra ventaja en E[pts] es real (1083 vs ~879 del pool), pero que se convierta
en +E[dinero] depende **enteramente** de la habilidad de los rivales — un dato
del mundo real que solo tú conoces (¿son familiares casuales o apostadores
afilados?):

| Campo (fracción afilados) | P(1º) | E[utilidad] |
|---|---:|---:|
| Mayormente casual (10%) | 7.2% | **+$1.13M** |
| Mixto (25%) | 1.6% | +$196k |
| Afilado (50%) | 0.4% | −$97k |
| Muy afilado (80%) | 0.1% | −$203k |

→ La decisión de comprar (y cuántas planillas) depende de **N** y de esta mezcla.
Necesito tu lectura del campo. (`--p-afilado` ajusta el supuesto.)

```
python pollas/LEMAITRE/competencia_lemaitre.py --inscritos N --planillas K --p-afilado X
```

## Reproducir
```
ODDS_API_KEY=... python pollas/LEMAITRE/modelo_lemaitre.py            # live
python pollas/LEMAITRE/modelo_lemaitre.py --mock /tmp/wc_grupos.json  # cache
python pollas/LEMAITRE/backtest_clasificacion.py                      # ground truth
```
Salida del formulario completo: `pollas/LEMAITRE/FORMULARIO_lemaitre.csv`.
