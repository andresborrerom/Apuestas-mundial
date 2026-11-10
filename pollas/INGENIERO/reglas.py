"""
Reglas de la "Polla Mundial 2026" (INGENIERO, organiza Pato Rodríguez).

Puntaje por partido = SUMA de (todos se califican):
  - marcador exacto (completo) ............ 3
  - ganador o empate (1X2) ................ 2
  - marcador de un equipo ................. 1   (al menos un equipo; ver `un_equipo`)
  - total de goles del partido ............ 1
  - goles de un equipo ≥3, exacto ......... 5   (por equipo)
  - goles de Colombia, exacto ............. 5   (solo el partido de Colombia)
  - cada equipo clasificado en cada ronda . 3
  - equipo campeón ........................ 7
  - ser el ÚNICO que acierta un marcador .. 8   (depende del campo; no optimizable a priori)

Marcadores: a 90 MINUTOS (el reglamento de 16avos lo dice: "ni suplementarios
ni penales"). No se aplica el ajuste 120' de CSC/LEMAITRE.

VALIDADO contra ground truth (`backtest_ingeniero.py`, miles de partidos reales):
  - El relleno EV-máximo bajo ESTAS reglas gana puntos reales (+~0.63/partido vs
    modal). El bono de +5 por ≥3 goles hace que **3-0 a favoritos** sea óptimo de
    verdad (no espejismo): para favoritos fuertes, 3-0 ≈ EV-máx y le saca >0.5
    (hasta +1.6 en aplastantes) por partido a "favorito 2-1". Confirmado.

A diferencia de CSC, NO se decorrelaciona: aquí (y sobre todo en consolación, que
es donde está Jose Yesid Torres) se maximiza el total esperado con EV-máximo.
"""
import numpy as np


def puntos_partido(pred, real, colombia_side=None, un_equipo="or"):
    """Puntaje INGENIERO de un marcador `pred=(gl,gv)` vs `real=(gl,gv)`.

    colombia_side: 'H' si Colombia es local, 'A' si visitante, None si no juega.
    un_equipo: 'or' = 1 pt si aciertas al menos un equipo (lectura conservadora
               del reglamento); 'cada' = 1 pt por equipo acertado.
    No incluye: clasificado (3), campeón (7), único acertante (8) — se cuentan aparte.
    """
    pa, pv = pred
    ra, rv = real
    s = 0
    if pa == ra and pv == rv:
        s += 3
    if np.sign(pa - pv) == np.sign(ra - rv):
        s += 2
    if un_equipo == "cada":
        s += int(pa == ra) + int(pv == rv)
    else:
        s += 1 if (pa == ra or pv == rv) else 0
    if pa + pv == ra + rv:
        s += 1
    if pa >= 3 and pa == ra:
        s += 5
    if pv >= 3 and pv == rv:
        s += 5
    if colombia_side == "H" and pa == ra:
        s += 5
    if colombia_side == "A" and pv == rv:
        s += 5
    return s


def relleno_optimo(M, colombia_side=None, un_equipo="or", G=6):
    """Marcador que MAXIMIZA el puntaje INGENIERO esperado sobre la matriz M
    (distribución de marcadores del partido). Devuelve (gl, gv)."""
    n, m = M.shape
    best, bev = (0, 0), -1.0
    for h in range(G + 1):
        for a in range(G + 1):
            ev = 0.0
            for gh in range(n):
                row = M[gh]
                for ga in range(m):
                    p = row[ga]
                    if p > 1e-12:
                        ev += p * puntos_partido((h, a), (gh, ga), colombia_side, un_equipo)
            if ev > bev:
                bev, best = ev, (h, a)
    return best, bev


# Auto-test mínimo de la lógica (suma de conceptos)
if __name__ == "__main__":
    # favorito que mete 3, débil 0, acertado exacto:
    assert puntos_partido((3, 0), (3, 0)) == 3 + 2 + 1 + 1 + 5, "3-0 exacto"
    # ganador acertado sin marcador:
    assert puntos_partido((2, 0), (1, 0)) == 2 + 1, "gana local, visita 0 ok"
    # Colombia local mete 1, acertado: +5 extra
    assert puntos_partido((1, 0), (1, 2), colombia_side="H") == 1 + 5, "Colombia local 1 ok"
    print("reglas INGENIERO: tests OK")
