"""Verificación de la matemática del motor. Ejecutar con: python -m pytest -q
o simplemente: python tests/test_motor.py"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from motor import cuotas, marcadores, puntuacion, analizar_partido


def test_probabilidades_suman_uno():
    for metodo in ["proporcional", "aditivo", "potencia", "shin"]:
        p = cuotas.a_probabilidades([1.80, 3.60, 4.50], metodo=metodo)
        assert abs(p.sum() - 1.0) < 1e-9, metodo
        assert np.all(p > 0), metodo


def test_margen_positivo():
    m = cuotas.margen([1.80, 3.60, 4.50])
    assert m > 0  # la casa siempre cobra margen


def test_favorito_mas_probable():
    # cuota más baja => mayor probabilidad
    p = cuotas.a_probabilidades([1.50, 4.0, 6.0])
    assert p[0] > p[1] > p[2]


def test_matriz_es_distribucion():
    M = marcadores.matriz_marcadores(1.6, 1.1, rho=-0.05)
    assert abs(M.sum() - 1.0) < 1e-9
    assert np.all(M >= 0)


def test_ajuste_reproduce_mercado():
    # partimos de probabilidades conocidas y comprobamos que el ajuste las recupera
    p_local, p_empate, p_visita = 0.50, 0.28, 0.22
    aj = marcadores.ajustar_lambdas(p_local, p_empate, p_visita)
    h, d, a = marcadores.prob_1x2(aj["matriz"])
    assert abs(h - p_local) < 0.02
    assert abs(d - p_empate) < 0.02
    assert abs(a - p_visita) < 0.02


def test_relleno_exacto_es_bajo():
    # con regla de marcador exacto, el óptimo debe ser un marcador bajo y realista
    regla = puntuacion.regla_personalizada(pts_exacto=3, pts_resultado=1)
    r = analizar_partido([1.80, 3.60, 4.50], regla, cuotas_ou=[2.0, 1.8])
    gh, ga = r["relleno_optimo"]
    assert gh <= 3 and ga <= 3
    assert gh >= ga  # local favorito => no predecir que pierde


def test_solo_resultado_predice_favorito():
    regla = puntuacion.regla_solo_resultado(pts=1)
    r = analizar_partido([1.40, 4.5, 7.0], regla)
    gh, ga = r["relleno_optimo"]
    assert gh > ga  # debe apostar a que gana el favorito local


def test_bonus_argmax():
    probs = {"Brasil": 0.22, "Francia": 0.18, "España": 0.15}
    r = puntuacion.mejor_apuesta_bonus(probs, puntos=10)
    assert r["opcion"] == "Brasil"
    assert abs(r["puntos_esperados"] - 2.2) < 1e-9


def test_csc_ejemplos_del_reglamento():
    # Replica EXACTAMENTE los ejemplos del PDF de CSC (fase de grupos:
    # ganador/empate=1, goles 0 acertado=2, goles!=0 acertado = #goles+3).
    regla = puntuacion.regla_goles_por_equipo(1, 2, 3)
    # (prediccion_local, prediccion_visita), (real_local, real_visita) -> pts
    assert regla((0, 0), (2, 0)) == 2   # acierta el 0 de visita
    assert regla((1, 2), (3, 2)) == 5   # acierta 2 goles visita (2+3)
    assert regla((2, 0), (2, 0)) == 8   # pleno: 1 + (2+3) + 2
    assert regla((2, 0), (2, 1)) == 6   # ganador + goles local (1 + 5)
    assert regla((2, 2), (2, 1)) == 5   # solo goles local (2+3), pierde tendencia
    assert regla((0, 0), (2, 2)) == 1   # solo acierta empate


def test_csc_relleno_sensato():
    from pollas.CSC import reglas as csc
    r = csc.rellenar("primera", cuotas_1x2=[1.50, 4.20, 6.50],
                     cuotas_ou=[2.10, 1.75])
    gh, ga = r["relleno_optimo"]
    assert gh > ga          # favorito local: predecir que gana
    assert 1 <= gh <= 4     # número de goles razonable
    assert r["puntos_esperados"] > 0


def test_consenso_evento():
    from motor import odds_api
    import json, os
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "pollas", "CSC", "ejemplo_odds.json")
    with open(ruta, encoding="utf-8") as f:
        eventos = json.load(f)
    c = odds_api.consenso_evento(eventos[0])
    assert c["home"] == "Mexico" and c["away"] == "South Africa"
    # mediana de [1.50, 1.53] = 1.515 para el local
    assert abs(c["cuotas_1x2"][0] - 1.515) < 1e-9
    assert c["linea"] == 2.5
    assert c["cuotas_ou"] is not None  # [under, over]
    assert c["n_casas"] == 2


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if nombre.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  OK   {nombre}")
            except AssertionError as e:
                fallos += 1
                print(f"  FALLA {nombre}: {e}")
    print("\nTodo correcto" if not fallos else f"\n{fallos} fallo(s)")
    sys.exit(1 if fallos else 0)
