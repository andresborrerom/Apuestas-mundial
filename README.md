# World Cup Pool Engine — can math beat your office betting pool?

A probabilistic engine that fills out World Cup prediction pools ("pollas")
by maximizing **expected points** under each pool's specific scoring rules,
starting from bookmaker odds.

*Documentación en español: [`README.es.md`](README.es.md). The modeling
chronicle ([`HISTORIA.md`](HISTORIA.md)) and the reusable recipe
([`PLAYBOOK.md`](PLAYBOOK.md)) are currently in Spanish.*

## The idea

Bookmaker odds are the best cheap predictor available: they aggregate
enormous amounts of information and are notoriously hard to beat. But there
are three keys almost nobody applies correctly — and that's where pools are
won:

1. **Odds are not probabilities.** Their inverses sum to more than 100%;
   the excess is the bookmaker's margin, and it must be removed
   (`motor/cuotas.py`).
2. **You don't fill in the most likely outcome — you fill in the one that
   maximizes expected points** under YOUR pool's rules
   (`motor/puntuacion.py`). With exact-score points, the optimum is usually
   1-0 / 1-1 even when you expect a blowout.
3. **Scorelines come from the full probability distribution** of results
   (Poisson / Dixon-Coles), backed out from 1X2 + Over/Under markets
   (`motor/marcadores.py`).

For champion / runner-up picks, the entire tournament is simulated thousands
of times (`motor/simulacion.py`).

## Structure

```
motor/                # pool-agnostic engine (independent of scoring rules)
  cuotas.py           # odds -> probabilities (removes bookmaker margin)
  marcadores.py       # scoreline distribution (Poisson/DC) + goal=1 bias
  puntuacion.py       # fill-in that maximizes expected points
  odds_api.py         # fetch odds (bookmaker consensus, The Odds API)
  simulacion_polla.py # pool simulator (utility, P(1st), perturbation)
  torneo.py           # full-tournament simulator (dispersion by round)
  backtest.py         # validation against real matches (football-data.co.uk)
  simulacion.py       # tournament Monte Carlo (champion, runner-up, ...)
pollas/
  _plantilla/         # template showing how to define a pool's rules
  CSC/                # CLOSED: rules + experiments + decision log + entry sheet
  ...                 # other private pools built from the playbook
nfl/                  # NFL 2026 league (Yahoo Pick'em + Survival) — separate project
tests/                # verification of the math
```

Each `pollas/<X>/` contains self-explanatory executable scripts: `reglas.py`
(scoring), `llenar.py` (generates the entry sheet), `cupos.py` (how many
entries to buy), `experimento_*.py` (each theory tested) and `demo_*.py`
(teaching demos).

## Quick use

```python
from motor import analizar_partido
from motor.puntuacion import regla_personalizada

regla = regla_personalizada(pts_exacto=5, pts_diferencia=3, pts_resultado=2)

r = analizar_partido(
    cuotas_1x2=[1.80, 3.60, 4.50],   # [home, draw, away]
    cuotas_ou=[2.00, 1.80],          # [under, over] 2.5
    regla=regla,
)
print(r["relleno_optimo"], r["puntos_esperados"])
```

## Install and test

```bash
pip install -r requirements.txt
python tests/test_motor.py
```

## Status / next steps

- [x] Odds, scoreline, scoring and simulation engine.
- [x] **First pool closed:** rules validated, model validated against ground
  truth (backtest + walk-forward), entry count decided, sheet generated.
- [x] Validated mechanisms: max-EV fill-in, goal=1 bias, minimal perturbation
  across entries, increasing dispersion by round.
- [ ] Apply the playbook to the remaining pools.
- [ ] Champion / top-scorer model (Monte Carlo + `soccer_fifa_world_cup_winner`).
- [ ] Knockout rounds: top-k fill-ins for 1-2 match rounds.
- [ ] Optional: scrape OddsPortal (free) for World Cup Over/Unders.

---

*Built end-to-end (data → model → backtesting → tool) with AI coding agents,
by a mathematician who takes betting pools far too seriously.*
