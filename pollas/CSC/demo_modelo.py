#!/usr/bin/env python3
"""
Demo pedagógico: el modelo GENERANDO marcadores.

Cada partido es una distribución de probabilidad sobre todos los marcadores
posibles (matriz M, derivada de las cuotas). "Generar un resultado" = sortear
un marcador de esa distribución. Aquí mostramos 10 corridas (sorteos) para 5
partidos, e imprimimos el modelo de cada partido (λ, 1X2, marcadores más
probables) para poder explicar cómo salió cada casilla.

    python pollas/CSC/demo_modelo.py [--mock /tmp/wc_grupos.json]
"""

import argparse
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from motor import odds_api, cuotas, marcadores


def abr(nombre):
    return "".join(nombre.split()[0][:3]).upper()


def modelo_partido(c):
    p = cuotas.a_probabilidades(c["cuotas_1x2"], "proporcional")
    p_over = cuotas.a_probabilidades(c["cuotas_ou"], "proporcional")[1] if c["cuotas_ou"] else None
    aj = marcadores.ajustar_lambdas(p[0], p[1], p[2], p_over=p_over)
    M = aj["matriz"]
    return {
        "home": c["home"], "away": c["away"],
        "lh": aj["lambda_local"], "la": aj["lambda_visita"],
        "p1x2": marcadores.prob_1x2(M), "M": M,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    args = ap.parse_args(argv)
    eventos = (json.load(open(args.mock, encoding="utf-8")) if args.mock and os.path.exists(args.mock)
               else odds_api.bajar_eventos(args.api_key))

    # construir modelos y elegir 5 partidos que abarquen distintos perfiles
    modelos = []
    for e in eventos:
        c = odds_api.consenso_evento(e)
        if c["cuotas_1x2"]:
            modelos.append(modelo_partido(c))
    modelos.sort(key=lambda m: m["p1x2"][0])  # por prob. de que gane el local
    # extremos y centro: visita favorita, equilibrado, leve, claro, favoritísimo
    idx = [1, len(modelos)//4, len(modelos)//2, 3*len(modelos)//4, len(modelos)-2]
    sel = [modelos[i] for i in idx]

    print("=== MODELO DE CADA PARTIDO (de las cuotas) ===")
    for m in sel:
        h, a = abr(m["home"]), abr(m["away"])
        pL, pD, pV = m["p1x2"]
        M = m["M"]
        top = sorted(((M[i, j], i, j) for i in range(7) for j in range(7)),
                     reverse=True)[:4]
        tops = "  ".join(f"{i}-{j}:{p*100:.0f}%" for p, i, j in top)
        print(f"\n{h}-{a}  ({m['home']} vs {m['away']})")
        print(f"  goles esperados λ: {m['lh']:.2f} - {m['la']:.2f}   "
              f"P(gana {h}/empate/gana {a}) = {pL*100:.0f}%/{pD*100:.0f}%/{pV*100:.0f}%")
        print(f"  marcadores más probables: {tops}")

    # 10 corridas: sortear un marcador de cada distribución
    rng = np.random.default_rng(123)
    etiquetas = [f"{abr(m['home'])}-{abr(m['away'])}" for m in sel]
    print("\n\n=== 10 RESULTADOS GENERADOS (filas = corrida, columnas = partido) ===")
    print("corrida  " + "  ".join(f"{e:>9}" for e in etiquetas))
    muestras = []
    for r in range(10):
        fila = []
        for m in sel:
            M = m["M"]; flat = M.ravel() / M.sum()
            k = rng.choice(flat.size, p=flat)
            i, j = k // M.shape[1], k % M.shape[1]
            fila.append(f"{i}-{j}")
        muestras.append(fila)
        print(f"  #{r+1:<5}  " + "  ".join(f"{x:>9}" for x in fila))

    # tabla de frecuencias por partido (cómo se reparten las 10 corridas)
    print("\n=== Frecuencia de cada marcador en las 10 corridas ===")
    for ci, m in enumerate(sel):
        from collections import Counter
        cnt = Counter(fila[ci] for fila in muestras)
        repr_ = ", ".join(f"{s}×{n}" for s, n in cnt.most_common())
        print(f"  {etiquetas[ci]:>9}: {repr_}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
