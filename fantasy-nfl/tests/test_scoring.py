"""Tests del motor bajo scoring v2 (12-ago). Fixtures = casos VALIDADOS al
decimal contra el appliedTotal de ESPN en el corpus (candado 1801/1801).

Semántica de tackles v2 (verificada: 107+108=109 en Garrett/Crosby/Cashman):
  107 asistidas (+0.5) · 108 solitarias (+1.5) · 109 total (+1.0)
  -> solitaria efectiva 2.5 · asistida efectiva 1.5
Sack v2: ítem 99 (+2 DL/LB, +1 D/ST) + la solitaria que arrastra = ~4.5.
El "stuff" (97) solo lo acumulan los D/ST: el sack de jugador ya no lo lleva.
Ítems de margen de victoria (161-166): configurados pero INERTES — ningún
jugador/D/ST acumula esos statIds en todo el corpus 2025/2026.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from model.scoring import cargar_reglas, puntos

ITEMS = cargar_reglas()

def _e(raw, pos, esperado):
    assert abs(puntos(raw, pos, ITEMS) - esperado) < 0.01, \
        f"esperado {esperado}, dio {puntos(raw, pos, ITEMS)}"

def test_garrett_2025():   # DE (posId 10) — appliedTotal ESPN v2
    _e({'99': 23, '100': 46, '106': 3, '107': 17, '108': 43, '109': 60,
        '110': 13, '111': 7, '112': 15, '113': 1, '155': 5, '156': 12,
        '210': 17}, 10, 183.0)

def test_crosby_2025():    # DE — appliedTotal ESPN v2
    _e({'95': 1, '99': 10, '100': 20, '106': 2, '107': 28, '108': 45,
        '109': 73, '110': 19, '111': 8, '112': 23.5, '113': 6, '155': 2,
        '156': 13, '210': 15}, 10, 185.5)

def test_cashman_2025():   # LB (posId 11) — appliedTotal ESPN v2
    _e({'99': 2, '100': 4, '106': 1, '107': 83, '108': 61, '109': 144,
        '110': 43, '111': 24, '112': 7.5, '113': 2, '155': 7, '156': 6,
        '210': 13}, 11, 284.0)

def test_sack_efectivo_4_5():
    # sack v2 = ítem 99 (2) + solitaria que arrastra (108+109 = 2.5); sin stuff
    _e({'99': 1, '108': 1, '109': 1}, 10, 4.5)

def test_tackle_solitaria_2_5():
    _e({'108': 1, '109': 1}, 11, 2.5)

def test_tackle_asistida_1_5():
    _e({'107': 1, '109': 1}, 11, 1.5)

def test_borde_umbral_99_vs_100():
    # 99 yd: 9 dieces, sin bono. 100 yd: 10 dieces + bono 2. Salto = 3 pts
    sin = puntos({'28': 9}, 2, ITEMS)
    con = puntos({'28': 10, '37': 1}, 2, ITEMS)
    assert con - sin == 3.0

def test_td_50_apila_con_40():
    # TD de 50+: raw trae 35 y 36 a la vez (validado en crudos de Gibbs)
    _e({'25': 1, '35': 1, '36': 1}, 2, 9.0)   # 6 + 1 + 2

def test_dst_shutout_paga_20():
    # v2 re-activó los escalones de points-allowed (v1 los anulaba con override)
    _e({'89': 1}, 16, 20.0)

def test_dst_texans_2025():   # integración D/ST — appliedTotal ESPN v2
    _e({'89': 1, '91': 3, '92': 5, '94': 4, '95': 19, '96': 10, '97': 3,
        '99': 47, '100': 94, '103': 1, '104': 3, '105': 4, '106': 14,
        '107': 477, '108': 600, '109': 1077, '110': 353, '111': 208,
        '112': 66, '113': 90, '114': 1407, '115': 360, '116': 133,
        '117': 50, '118': 29, '119': 7, '120': 295, '121': 5, '122': 1,
        '123': 2, '127': 4713, '129': 1, '130': 10, '131': 4, '132': 2,
        '155': 12, '156': 5, '187': 295, '188': 1, '190': 3, '191': 5,
        '192': 5, '193': 1, '194': 2, '210': 17}, 16, 211.0)

def test_dst_sack_es_1_no_2():
    _e({'99': 1}, 16, 1.0)

def test_qb_pasa_por_25():
    _e({'8': 12}, 1, 12.0)   # 300 yardas = 12 unidades de 25 = 12 pts

def test_int_lanzada_menos3():
    _e({'20': 2}, 1, -6.0)

if __name__ == '__main__':
    import pytest
    raise SystemExit(pytest.main([__file__, '-q']))
