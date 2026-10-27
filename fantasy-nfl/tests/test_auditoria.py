"""CANDADOS de la auditoría semanal.

`mejor_lineup` es el que separa "el modelo falló" de "el manager alineó mal".
Si se equivoca, le vamos a cobrar a alguien puntos que nunca dejó en la banca,
o peor, vamos a absolver un error de alineación. Se prueba con planteles
sintéticos donde la respuesta se conoce a mano, HOY, no en octubre.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from optimize.auditoria_semanal import mejor_lineup, resumen

# 14 titulares exactos: QBx2, RBx2, WRx2, TE, DT, DE, LB, CB, S, DST, K
EXACTO = [
    (1, 20.0, 'QB'), (2, 18.0, 'QB'), (3, 15.0, 'RB'), (4, 12.0, 'RB'),
    (5, 14.0, 'WR'), (6, 11.0, 'WR'), (7, 9.0, 'TE'), (8, 3.0, 'DT'),
    (9, 4.0, 'DE'), (10, 7.0, 'LB'), (11, 6.0, 'CB'), (12, 5.0, 'S'),
    (13, 8.0, 'DST'), (14, 10.0, 'K'),
]


def test_plantel_justo_usa_a_todos():
    """Con exactamente un jugador por slot, el óptimo es la suma de todos:
    QB->QB, QB->OP, RB->RB, RB->RB/WR y el resto a su slot dedicado."""
    assert abs(mejor_lineup(EXACTO) - sum(p for _, p, _ in EXACTO)) < 1e-9


def test_sube_al_mejor_de_la_banca():
    """Un WR de banca que anota más que el WR titular DEBE entrar al óptimo."""
    con_banca = EXACTO + [(15, 30.0, 'WR')]
    # entra el WR de 30 y sale el peor WR alineable (el de 11.0 salía por
    # RB/WR... el desplazado real es el de menor aporte entre los elegibles)
    assert mejor_lineup(con_banca) > mejor_lineup(EXACTO)
    assert abs(mejor_lineup(con_banca) - (sum(p for _, p, _ in EXACTO) + 30.0 - 11.0)) < 1e-9


def test_respeta_elegibilidad_de_posicion():
    """Un K monstruoso en la banca NO puede entrar al OP ni a ningún flex:
    solo hay un slot de K y ya está ocupado por uno mejor."""
    con_k = EXACTO + [(15, 99.0, 'K')]
    # el K de 99 sí desplaza al K de 10 (mismo slot), pero no aporta 99 extra
    assert abs(mejor_lineup(con_k) - (sum(p for _, p, _ in EXACTO) + 99.0 - 10.0)) < 1e-9
    con_dst = EXACTO + [(15, 99.0, 'DST')]
    assert abs(mejor_lineup(con_dst) - (sum(p for _, p, _ in EXACTO) + 99.0 - 8.0)) < 1e-9


def test_slot_vacio_no_rompe():
    """Un roster sin DT (el caso real de Andrés en la semana 1) debe calcular
    el óptimo igual, dejando ese slot en cero."""
    sin_dt = [x for x in EXACTO if x[2] != 'DT']
    assert abs(mejor_lineup(sin_dt) - (sum(p for _, p, _ in EXACTO) - 3.0)) < 1e-9


def test_resumen_sesgo_y_mae():
    filas = [{'ejecutado': 100.0, 'calc': 110.0},     # +10
             {'ejecutado': 100.0, 'calc': 80.0}]      # -20
    sesgo, mae = resumen(filas, 'calc')
    assert abs(sesgo - (-5.0)) < 1e-9, 'sesgo = media de los errores con signo'
    assert abs(mae - 15.0) < 1e-9, 'MAE = media de los valores absolutos'
