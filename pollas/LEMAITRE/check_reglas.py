#!/usr/bin/env python3
"""TRIPWIRE de reglas LEMAITRE (post-mortem 17-jul: el app activó tramos de
clasif con valores distintos a los asumidos y lo detectamos DÍAS tarde por no
re-bajar el código).

Baja index.html oficial, extrae los bloques de scoring (PTS, calcMarcador,
calcClasifScore, calcExtrasScore, calcColombiaScore, FINAL_KEYS) y compara su
hash contra el snapshot guardado. Si algo cambió: EXIT 1 y muestra qué bloque.

USO OBLIGATORIO antes de cualquier proyección/endgame:
    python pollas/LEMAITRE/check_reglas.py            # verifica
    python pollas/LEMAITRE/check_reglas.py --accept   # re-valida y guarda hash nuevo
"""
import hashlib, json, os, re, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
URL = "https://raw.githubusercontent.com/TempleColombia/polla-mundial-2026/main/index.html"
SNAP = os.path.join(AQUI, "reglas_hash.json")

BLOQUES = {
    "PTS": r"const PTS\s*=\s*\{.*?\};",
    "calcMarcador": r"function calcMarcador\(.*?\n\}",
    "calcClasifScore": r"function calcClasifScore\(.*?\n\}",
    "calcExtrasScore": r"function calcExtrasScore\(.*?\n\}",
    "calcColombiaScore": r"function calcColombiaScore\(.*?\n\}",
    "FINAL_KEYS": r"const FINAL_KEYS\s*=\s*\[.*?\];",
}

def extraer(html):
    out = {}
    for k, pat in BLOQUES.items():
        m = re.search(pat, html, re.S)
        out[k] = hashlib.sha256(m.group(0).encode()).hexdigest()[:16] if m else "AUSENTE"
    return out

def main():
    html = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
    ahora = extraer(html)
    if "--accept" in sys.argv or not os.path.exists(SNAP):
        json.dump(ahora, open(SNAP, "w"), indent=2)
        print("✅ hash de reglas guardado:", json.dumps(ahora, indent=2))
        return 0
    antes = json.load(open(SNAP))
    diff = [k for k in BLOQUES if antes.get(k) != ahora.get(k)]
    if diff:
        print("🚨 CAMBIÓ EL CÓDIGO DE SCORING DEL APP en:", ", ".join(diff))
        print("   NO proyectes con el modelo actual. Leer el código nuevo, actualizar")
        print("   puntos_lemaitre/endgame, RE-VALIDAR 7/7 vs la tabla y luego --accept.")
        return 1
    print("✅ reglas sin cambios (6 bloques verificados contra el app oficial)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
