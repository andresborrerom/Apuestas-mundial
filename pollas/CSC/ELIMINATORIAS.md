# CSC — Runbook de ELIMINATORIAS

> Las eliminatorias deciden la polla. Los puntos suben fuerte por ronda
> (grupos: ganador=1; final: ganador=8, goles base 16 en vez de 3). Un solo
> marcador de cuartos/semis/final vale lo que varios de grupos. **No es momento
> de relajarse: es al revés.**

## El comando (un solo paso por ronda)

```bash
export ODDS_API_KEY=tu_key
python pollas/CSC/eliminatorias.py --csv ronda.csv
```

- Detecta **qué ronda viene** y su deadline; solo genera si faltan ≤ 4 días
  (cuando ya están los cruces y hay cuotas). Forzar: `--round octavos --force`.
- Genera los **5 cupos descorrelacionados** con los ajustes correctos de
  knockout: modelo enriquecido (`--rico`, curva O/U) y **más dispersión** que en
  grupos. Llena **un formulario por cupo**.

## Deadlines (hora Colombia) — enviar TODA la ronda antes del 1er partido

| Ronda | Partidos | Ventana | **Deadline de envío** |
|---|---|---|---|
| Dieciseisavos (R32) | 16 | 28 jun – 3 jul | **28/06/2026 1:59 PM** |
| Octavos (R16) | 8 | 4 – 7 jul | **04/07/2026 11:59 AM** |
| Cuartos | 4 | 9 – 11 jul | **09/07/2026 2:59 PM** |
| Semis | 2 | 14 – 15 jul | **14/07/2026 1:59 PM** |
| Tercer puesto | 1 | 18 jul | **18/07/2026 3:59 PM** |
| Final | 1 | 19 jul | **19/07/2026 1:59 PM** |

> ⏰ El más cercano es **R32: 28 de junio 1:59 PM**. Los cruces se conocen al
> terminar grupos (27 jun), así que la ventana real para generar y enviar es
> 27–28 jun. El GitHub Action `eliminatorias-aviso.yml` lo dispara y publica los
> cupos en un issue en esos días (requiere el secreto `ODDS_API_KEY`).

## Reglas que cambian la estrategia en knockout

1. **Resultado a 120 minutos, penales NO.** El marcador que cuenta es tras el
   alargue. Se **puede apostar al empate** (si quedó empatado a 120' y fue a
   penales, el marcador "empate" acierta). El modelo usa la cuota 1X2 de tiempo
   reglamentario como aproximación a 120' — buena, pero sesga un pelín a menos
   goles de los reales (el alargue agrega minutos). No corregimos: validado que
   la 1X2 reglamentaria es la mejor señal pública disponible.
2. **Más dispersión entre cupos.** Con pocos partidos de mucho valor, separar las
   5 planillas cubre más escenarios. `eliminatorias.py` ya sube `n_swaps` por
   ronda (R32=8, octavos=5, cuartos=3, semis=2, 3er/final=1).
3. **Modelo enriquecido por defecto** (`--rico`): 1 llamada API por partido para
   traer la curva O/U y O/U por equipo. Vale la pena donde cada acierto pesa.

## Flujo recomendado por ronda

1. Termina la ronda anterior → se definen los cruces (FIFA fija los partidos).
2. Corre `python pollas/CSC/eliminatorias.py --csv ronda.csv` (o espera el issue
   automático del Action).
3. Revisa los 5 cupos. Llena **un formulario por cupo** en la web de la polla.
4. Tras los partidos, `python pollas/puntos.py` puntúa con la regla de esa ronda.

## Por qué importa (recordatorio del modelo)

Con 48/72 de grupos jugados vamos 2º de ~110 planillas y con los 5 cupos en el
top 12. Pero **falta ~la mitad de los puntos del torneo**, casi todos en
knockouts de alto valor. La simulación da ~76% de meter ≥1 cupo al podio y ~27%
de ganar la polla — y ese número se mueve **mucho** según cómo acertemos las
eliminatorias. Aquí es donde se gana o se pierde.
