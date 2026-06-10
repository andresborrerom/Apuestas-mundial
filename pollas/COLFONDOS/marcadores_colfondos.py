#!/usr/bin/env python3
"""
COLFONDOS (Pollaya) — filler DIARIO de marcadores EV-máx.

Puntaje por partido (tablero Pollaya):
  marcador exacto 4 · ganador/empate 3 · diferencia de gol 1 · goles de un equipo 1
Es CUMULATIVO (cada sub-acierto suma). Supuesto: "goles de un equipo" = +1 si
aciertas los goles de AL MENOS un equipo (redacción en singular). Ajustable.

Pensado para correr DÍA A DÍA (loop): baja cuotas, filtra los partidos del día y
escupe el marcador EV-máx de cada uno. El 'dial de riesgo' (--riesgo) desvía del
EV-máx hacia marcadores de más varianza cuando vamos ATRÁS en el field.

    ODDS_API_KEY=... python pollas/COLFONDOS/marcadores_colfondos.py
    python pollas/COLFONDOS/marcadores_colfondos.py --mock /tmp/wc_grupos.json
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from motor import odds_api
from pollas.CSC.cupos import matriz_de_evento

# pesos COLFONDOS
W_EXACTO, W_GANADOR, W_DIF, W_GOLES = 4, 3, 1, 1


def matriz_puntos(nA, nB, modo_goles="uno"):
    """pts[a,b,x,y] -> matriz de puntos COLFONDOS de predecir (a,b) si sale (x,y).
    Devuelve P[a,b] (EV por celda) tras multiplicar por probabilidades aparte."""
    A = np.arange(nA)[:, None, None, None]
    B = np.arange(nB)[None, :, None, None]
    X = np.arange(nA)[None, None, :, None]
    Y = np.arange(nB)[None, None, None, :]
    s = np.zeros((nA, nB, nA, nB), dtype=float)
    s += W_GANADOR * (np.sign(A - B) == np.sign(X - Y))
    s += W_DIF * ((A - B) == (X - Y))
    if modo_goles == "uno":
        s += W_GOLES * ((A == X) | (B == Y))
    else:  # "cada": +1 por equipo acertado
        s += W_GOLES * ((A == X).astype(float) + (B == Y))
    s += W_EXACTO * ((A == X) & (B == Y))
    return s  # (a,b,x,y)


def evmax(M, riesgo=0.0, modo_goles="uno"):
    """Marcador EV-máx bajo COLFONDOS. M = matriz de prob de marcador (x,y).
    riesgo in [0,1]: 0 = EV-máx puro; >0 penaliza la prob del marcador elegido
    (busca upside, para remontar en el field)."""
    nA, nB = M.shape
    S = matriz_puntos(nA, nB, modo_goles)         # (a,b,x,y)
    EV = np.einsum("abxy,xy->ab", S, M)           # EV de cada (a,b)
    if riesgo > 0:
        # premia varianza: resta una fracción de la prob de acertar exacto el
        # propio marcador (favorece marcadores menos obvios con EV parecido)
        EV = EV - riesgo * M * (S.max() )         # heurística suave
    a, b = np.unravel_index(np.argmax(EV), EV.shape)
    return (int(a), int(b)), float(EV[a, b])


def evmax_riesgo(M, r=0.0, modo_goles="uno"):
    """Elige el marcador que maximiza EV + r·desviación (busca-varianza).
    r=0 -> EV-máx; r alto -> marcadores de más upside (para remontar al field).
    Devuelve (a,b), EV, std."""
    nA, nB = M.shape
    S = matriz_puntos(nA, nB, modo_goles)            # (a,b,x,y) puntos
    EV = np.einsum("abxy,xy->ab", S, M)
    E2 = np.einsum("abxy,xy->ab", S * S, M)
    std = np.sqrt(np.clip(E2 - EV * EV, 0, None))
    obj = EV + r * std
    a, b = np.unravel_index(np.argmax(obj), obj.shape)
    return (int(a), int(b)), float(EV[a, b]), float(std[a, b])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--riesgo", type=float, default=0.0, help="0=EV-máx, >0 busca upside")
    ap.add_argument("--modo-goles", default="uno", choices=["uno", "cada"])
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8"))
               if args.mock and os.path.exists(args.mock) else odds_api.bajar_eventos(args.api_key))
    print(f"{'PARTIDO':42} {'MARC':>5} {'EV':>6}  (riesgo={args.riesgo})")
    filas = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if not c["cuotas_1x2"]:
            continue
        M = matriz_de_evento(c, "proporcional", 2.5)
        (a, b), ev = evmax(M, args.riesgo, args.modo_goles)
        filas.append((c.get("commence_time", ""), c["home"], c["away"], a, b, ev))
    for ct, h, a_, ga, gb, ev in sorted(filas):
        dia = str(ct)[:10]
        print(f"{dia} {h[:18]:18} vs {a_[:16]:16} {ga}-{gb:<3} {ev:5.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
