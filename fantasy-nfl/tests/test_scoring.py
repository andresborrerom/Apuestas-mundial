"""Tests del motor. Fixtures = casos VALIDADOS al decimal contra ESPN (10-ago)."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model.scoring import cargar_reglas, puntos

ITEMS = cargar_reglas()

def _e(raw, pos, esperado):
    assert abs(puntos(raw, pos, ITEMS) - esperado) < 0.01, \
        f"esperado {esperado}, dio {puntos(raw, pos, ITEMS)}"

def test_garrett_2025():   # DE (posId 10) — validado contra ESPN
    _e({'99':23,'109':60,'107':17,'112':15,'106':3,'113':1}, 10, 136.5)

def test_crosby_2025():
    _e({'99':10,'109':73,'107':28,'112':23.5,'106':2,'113':6,'95':1}, 10, 143.5)

def test_sack_efectivo_4pts():
    # un sack "puro" llega en los crudos como sack+tackle+stuff
    _e({'99':1,'109':1,'112':1}, 10, 4.0)

def test_tackle_asistido_1_5():
    _e({'109':1,'107':1}, 11, 1.5)

def test_borde_umbral_99_vs_100():
    # 99 yd: 9 dieces, sin bono. 100 yd: 10 dieces + bono 2. Salto = 3 pts
    sin  = puntos({'28':9}, 2, ITEMS)
    con  = puntos({'28':10,'37':1}, 2, ITEMS)
    assert con - sin == 3.0

def test_td_50_apila_con_40():
    # TD de 50+: raw trae 35 y 36 a la vez (validado en crudos de Gibbs)
    _e({'25':1,'35':1,'36':1}, 2, 9.0)   # 6 + 1 + 2

def test_dst_shutout():
    _e({'89':1}, 16, 20.0)

def test_dst_sack_es_1_no_2():
    _e({'99':1}, 16, 1.0)

def test_qb_pasa_por_25():
    _e({'8':12}, 1, 12.0)   # 300 yardas = 12 unidades de 25 = 12 pts

def test_int_lanzada_menos3():
    _e({'20':2}, 1, -6.0)

if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__,'-q']))
