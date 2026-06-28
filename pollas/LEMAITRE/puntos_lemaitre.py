#!/usr/bin/env python3
"""
TABLERO LEMAITRE — puntúa nuestra planilla ronda por ronda contra resultados reales.

Lee:
  - FORMULARIO_lemaitre.csv   (nuestras predicciones)
  - resultados_lemaitre.csv   (resultados reales; crece cada ronda)
y reporta puntos por bloque + total acumulado + qué falta.

    python pollas/LEMAITRE/puntos_lemaitre.py
    python pollas/LEMAITRE/puntos_lemaitre.py --detalle

Reglas de puntaje: hoja "Puntajes" del Excel del reglamento. La CLASIFICACIÓN
(bloques A y B) usa tramos por grupo:
  A.- Clasif. a Fase 32 (640):   ambos 1º+2º en orden=40 · invertidos=25 · solo 1º=20 · solo 2º=15
  B.- Clasif. a Octavos  (280):  ambos en orden=35 · invertidos=25 · solo 1º=18 · solo 2º=12
NOTA: la aplicación por-grupo de los tramos es nuestra interpretación del
reglamento; los VALORES son los oficiales. Las cuentas de aciertos (1º/2º/3º
correctos) son exactas y no dependen de esa interpretación. Verificar contra un
puntaje oficial si el organizador lo publica.
"""
import argparse, csv, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))

# Tramos de clasificación (valores oficiales de la hoja "Puntajes")
A = {"ambos": 40, "inv": 25, "primero": 20, "segundo": 15}   # Fase 32
B = {"ambos": 35, "inv": 25, "primero": 18, "segundo": 12}   # Octavos


def cargar_form():
    pred = {}
    for r in csv.DictReader(open(os.path.join(AQUI, "FORMULARIO_lemaitre.csv"), encoding="utf-8")):
        if r["seccion"].startswith("GRUPO_"):
            g = r["seccion"].split("_")[1]
            pred.setdefault(g, {})[r["casilla"]] = r["pick"].strip()
    return pred


def cargar_resultados():
    real = {}
    for r in csv.DictReader(open(os.path.join(AQUI, "resultados_lemaitre.csv"), encoding="utf-8")):
        sec = r["seccion"].strip()
        if sec.startswith("#") or not sec:
            continue
        if sec.startswith("GRUPO_"):
            g = sec.split("_")[1]
            real.setdefault(g, {})[r["clave"]] = r["valor"].strip()
    return real


def tramo(pred1, pred2, real1, real2, tabla):
    """Puntos de un grupo según 1º/2º predichos vs reales."""
    if real1 in ("", "?") or real2 in ("", "?"):
        return 0, "pend"
    ok1, ok2 = pred1 == real1, pred2 == real2
    if ok1 and ok2:
        return tabla["ambos"], "1º+2º ✓✓"
    if pred1 == real2 and pred2 == real1:
        return tabla["inv"], "invertidos"
    if ok1:
        return tabla["primero"], "solo 1º ✓"
    if ok2:
        return tabla["segundo"], "solo 2º ✓"
    return 0, "—"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--detalle", action="store_true")
    args = ap.parse_args(argv)
    pred, real = cargar_form(), cargar_resultados()
    GR = "ABCDEFGHIJKL"

    ptsA = ptsB = 0
    h1 = h2 = h3 = t3 = 0
    filas = []
    for g in GR:
        p, r = pred.get(g, {}), real.get(g, {})
        p1, p2, p3 = p.get("pos1", ""), p.get("pos2", ""), p.get("pos3", "")
        r1, r2, r3 = r.get("pos1", ""), r.get("pos2", ""), r.get("pos3", "")
        pa, na = tramo(p1, p2, r1, r2, A)
        pb, _ = tramo(p1, p2, r1, r2, B)
        ptsA += pa; ptsB += pb
        if r1 not in ("", "?"):
            if p1 == r1: h1 += 1
            if p2 == r2: h2 += 1
        if r3 not in ("", "?"):
            t3 += 1
            if p3 == r3: h3 += 1
        filas.append((g, p1, p2, r1, r2, pa + pb, na))

    if args.detalle:
        print(f"{'Gr':3}{'pred 1º/2º':28}{'real 1º/2º':28}{'pts':>5}  detalle")
        for g, p1, p2, r1, r2, pts, na in filas:
            print(f"{g:3}{(p1+' / '+p2)[:27]:28}{((r1 or '?')+' / '+(r2 or '?'))[:27]:28}{pts:>5}  {na}")
        print()

    print("=== LEMAITRE — clasificación (grupos cerrados) ===")
    print(f"Ganadores de grupo (1º):  {h1}/12   correctos")
    print(f"Segundos de grupo (2º):   {h2}/12")
    print(f"Terceros que avanzaron:   {h3}/{t3}")
    print(f"\nPuntos estimados:")
    print(f"  A.- Clasificación a Fase 32:   {ptsA}  (de 640 presupuestado)")
    print(f"  B.- Clasificación a Octavos:   {ptsB}  (de 280)")
    print(f"  TOTAL clasificación hasta hoy: {ptsA + ptsB}")
    print(f"\nPENDIENTE (arranca con R32 hoy): marcadores de eliminatoria (1430),")
    print(f"  clasif. cuartos/semis, cuadro de honor, extras Colombia, otros extras.")
    print(f"  Máximo total de la polla: 3900.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
