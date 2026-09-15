"""CANDADOS del marcador semanal.

El marcador solo va a producir su veredicto dentro de varias semanas, así que
su maquinaria hay que probarla HOY con datos sintéticos: si la correlación o
el filtro de semanas completas están mal, no queremos enterarnos en octubre
mirando un número que parece razonable.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from optimize.marcador_semanal import completa, rangos, spearman


def test_semana_completa():
    llena = {f'e{i}': 100.0 + i for i in range(16)}
    assert completa(llena), '16 equipos con puntos = semana completa'
    # jueves jugado, domingo no: la mitad en cero -> NO cuenta
    media = dict(llena)
    for i in range(8):
        media[f'e{i}'] = 0.0
    assert not completa(media), 'una semana a medias no puede entrar'
    faltante = {f'e{i}': 100.0 for i in range(15)}
    assert not completa(faltante), 'con 15 equipos no se cierra la semana'
    nulos = dict(llena, e0=None)
    assert not completa(nulos), 'un None no puede pasar por jugado'


def test_rangos():
    assert rangos({'a': 10, 'b': 30, 'c': 20}) == {'b': 1, 'c': 2, 'a': 3}


def test_spearman_casos_conocidos():
    real = {'a': 100, 'b': 90, 'c': 80, 'd': 70}
    igual = {'a': 4, 'b': 3, 'c': 2, 'd': 1}          # mismo orden
    rho, n = spearman(real, igual)
    assert n == 4 and abs(rho - 1.0) < 1e-9, 'orden idéntico debe dar +1'
    inverso = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    rho, _ = spearman(real, inverso)
    assert abs(rho + 1.0) < 1e-9, 'orden invertido debe dar -1'


def test_spearman_solo_interseccion():
    """Los snapshots de FantasyPros no cubren los 16 equipos: la correlación
    se calcula sobre los comunes y REPORTA cuántos son. Nunca se rellena."""
    real = {'a': 100, 'b': 90, 'c': 80, 'd': 70, 'e': 60}
    parcial = {'a': 9, 'c': 5, 'e': 1}
    rho, n = spearman(real, parcial)
    assert n == 3, 'debe usar solo la intersección'
    assert abs(rho - 1.0) < 1e-9
    rho, n = spearman(real, {'a': 1, 'b': 2})
    assert rho is None and n == 2, 'con menos de 3 comunes no se opina'
