"""
Backtest / walk-forward del pipeline de predicción contra partidos reales.

Fuente: football-data.co.uk (gratis), que trae para miles de partidos de ligas
las cuotas de cierre (1X2 y Over/Under 2.5) y el resultado real (FTHG, FTAG).
Como no hay histórico de cuotas de Mundiales, validamos con fútbol de clubes:
el pipeline (cuotas → quitar margen → Poisson/Dixon-Coles → relleno óptimo) es
el mismo, así que la validación es transferible.

Qué responde:
  1. ¿El relleno EV-máximo (bajo las reglas CSC) gana puntos reales frente a
     baselines (marcador modal, favorito 1-0)? = nuestro EDGE.
  2. ¿Están bien calibradas las probabilidades (1X2, Over/Under, goles)?
  3. ¿Qué método para quitar margen y si Dixon-Coles ayuda? (walk-forward)
  4. Traduce el edge por partido a un `field_skill` realista para cupos.py.
"""

import csv
import io
import os
import urllib.request
import numpy as np

from . import cuotas, marcadores
from .simulacion_polla import ev_grid, _valor

CACHE = "/tmp/fd"
LIGAS = ["E0", "SP1", "I1", "D1", "F1"]
SEASONS = ["1819", "1920", "2021", "2122", "2223", "2324", "2425"]


# --------------------------------------------------------------------------
# Carga de datos
# --------------------------------------------------------------------------

def _descargar(season, div):
    os.makedirs(CACHE, exist_ok=True)
    f = f"{CACHE}/{season}_{div}.csv"
    if os.path.exists(f) and os.path.getsize(f) > 1000:
        return open(f, encoding="latin-1").read()
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        data = urllib.request.urlopen(req, timeout=30).read().decode("latin-1")
        open(f, "w", encoding="latin-1").write(data)
        return data
    except Exception:
        return None


def _num(row, *claves):
    """Primer valor numérico válido entre varias columnas alternativas."""
    for k in claves:
        v = row.get(k, "")
        if v not in ("", None):
            try:
                return float(v)
            except ValueError:
                pass
    return None


def cargar_partidos(seasons=SEASONS, ligas=LIGAS):
    """Lista de partidos con cuotas resueltas y resultado real."""
    out = []
    for s in seasons:
        for d in ligas:
            t = _descargar(s, d)
            if not t:
                continue
            for r in csv.DictReader(io.StringIO(t)):
                if r.get("FTHG", "") == "" or r.get("FTAG", "") == "":
                    continue
                H = _num(r, "AvgH", "B365H", "BbAvH", "PSH")
                D = _num(r, "AvgD", "B365D", "BbAvD", "PSD")
                A = _num(r, "AvgA", "B365A", "BbAvA", "PSA")
                if not (H and D and A):
                    continue
                over = _num(r, "Avg>2.5", "B365>2.5", "BbAv>2.5", "P>2.5")
                under = _num(r, "Avg<2.5", "B365<2.5", "BbAv<2.5", "P<2.5")
                out.append({
                    "season": s, "liga": d,
                    "home": r.get("HomeTeam"), "away": r.get("AwayTeam"),
                    "fthg": int(r["FTHG"]), "ftag": int(r["FTAG"]),
                    "cuotas_1x2": [H, D, A],
                    "cuotas_ou": ([under, over] if (over and under) else None),
                })
    return out


# --------------------------------------------------------------------------
# Modelo por partido y rellenos
# --------------------------------------------------------------------------

def matriz_de_partido(p, metodo="proporcional", dc=True, linea=2.5):
    prob = cuotas.a_probabilidades(p["cuotas_1x2"], metodo)
    p_over = None
    if p["cuotas_ou"]:
        p_over = cuotas.a_probabilidades(p["cuotas_ou"], metodo)[1]
    aj = marcadores.ajustar_lambdas(prob[0], prob[1], prob[2],
                                    p_over=p_over, linea=linea,
                                    usar_dixon_coles=dc)
    return aj["matriz"]


def fill_evmax(M, params, G=7):
    EV = ev_grid(M, params, G)
    i, j = np.unravel_index(np.argmax(EV), EV.shape)
    return int(i), int(j)


def fill_modal(M):
    i, j = np.unravel_index(np.argmax(M), M.shape)
    return int(i), int(j)


def fill_favorito1(M):
    pL = float(np.tril(M, -1).sum())
    pD = float(np.trace(M))
    pV = float(np.triu(M, 1).sum())
    if pL >= pD and pL >= pV:
        return 1, 0
    if pV >= pL and pV >= pD:
        return 0, 1
    return 1, 1


def puntos(pred, real, params):
    """Puntaje CSC de un relleno contra el resultado real."""
    res, cero, base = params
    pa, pv = pred
    ra, rv = real
    pts = 0
    if np.sign(pa - pv) == np.sign(ra - rv):
        pts += res
    if pa == ra:
        pts += cero if ra == 0 else ra + base
    if pv == rv:
        pts += cero if rv == 0 else rv + base
    return pts
