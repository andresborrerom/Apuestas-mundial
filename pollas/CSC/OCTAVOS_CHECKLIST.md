# CSC Octavos — checklist plug-and-play

**Deadline de octavos: 04/07/2026 11:59 AM (hora Colombia).** LEMAITRE está locked
(no se manda nada); solo CSC (e INGENIERO si aplica) se llenan por ronda.

## Estado del motor (2-jul-2026) — LISTO

- ✅ Regla octavos validada contra el reglamento: **(3, 4, 7)** — ganador 3 /
  gol=0 vale 4 / gol≠0 vale (#+7).
- ✅ Generador `generar_octavos.py` probado end-to-end (position-aware, ajuste 120').
- ✅ `ALIAS` de equipos reutiliza los 32 de R32 (⊇ equipos de octavos) → el
  snippet casa nombres en el formulario.
- ⏳ **Único input que falta: las CUOTAS de octavos** (la API no las tiene hasta
  que el bracket esté oficial).

## Bracket de octavos (89-96)

| Octavo | Llave | Estado |
|--------|-------|--------|
| P#91 | **Brasil vs Noruega** | ✅ definido |
| P#92 | **México vs Inglaterra** | ✅ definido |
| P#93 | **España vs Portugal** | ✅ definido |
| P#89 | Francia vs G#74 (Ale/Par) | ½ (falta penales P74) |
| P#90 | Canadá vs G#75 (Hol/Mar) | ½ (falta penales P75) |
| P#94 | USA vs G#82 (Bél/Sen) | ½ (falta penales P82) |
| P#95 | G#86 (Arg/CV) vs G#88 (Aus/Egi) | falta R32 |
| P#96 | G#85 (Sui/Arg) vs G#87 (Col/Gha) | falta R32 |

Falta cerrar R32: **P85, P86, P87, P88**, y los penales de los empates **P74, P75, P82**.

## Estrategia position-aware (PDF 2-jul: vamos #1 y #2 → DEFENDER)

Cupos actuales: **B4 #1 (383)**, **B1 #2 (371)**, **B2 #5 (362)**, B3/B5 ~#16 (fuera de premio).
Como lideramos, `--modo defender` (default):

| Cupo | Rol | Esquema |
|------|-----|---------|
| B4 (#1) | defender liderato | EV-máx puro |
| B1 (#2) | defender, decorrelar | perturbada n_swaps=2 |
| B2 (#5, burbuja) | defender casilla premio | perturbada n_swaps=3 |
| B3 (fuera) | moonshot | 2º fill (lotería) |
| B5 (fuera) | moonshot | 3º fill (lotería) |

Justificación (perfil bajo regla octavos): perturbar suave cuesta ~0.5 pts de
esperanza pero decorrelaciona; la lotería sacrifica ~11-16 pts (solo vale para
cupos sin premio que perder). Si el próximo PDF nos saca del podio → `--modo atacar`.

## Pasos el día del cierre (cuando haya cuotas de octavos)

```bash
# opción A — cuotas en vivo (auto-filtra a octavos por fecha):
ODDS_API_KEY=321f10743af221df5d09c913d498295d python pollas/CSC/generar_octavos.py

# opción B — snapshot (si guardamos las cuotas antes):
python pollas/CSC/generar_octavos.py --snapshot pollas/CSC/oct_odds_snapshot.json
```

Genera `oct_CSC.csv` (los 5 cupos) y `snippet_oct.js`. Luego, en el formulario
(Google Form del blog CSC): pegar el snippet, cambiar `CUPO` de 1 a 5 y re-pegar
por cada cupo (ANDRES BORRERO 1..5), revisar el "llené 8/8" verde, y **dar ENVIAR
tú**. Repetir por cada uno de los 5 cupos. Todo antes del **4/07 11:59 AM**.
