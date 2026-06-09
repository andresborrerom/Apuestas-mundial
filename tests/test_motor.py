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
