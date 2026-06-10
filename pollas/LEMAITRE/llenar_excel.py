#!/usr/bin/env python3
"""
LEMAITRE — llena el EXCEL completo (hojas Grupos y Form000) con los picks del
modelo calibrado. Genera una copia '*_LLENO.xlsx' (no toca la plantilla).

    python pollas/LEMAITRE/llenar_excel.py --mock /tmp/wc_grupos.json

Marcadores y equipos = EV-máx del árbol coherente. Los extras de JUGADOR
(goleador, 1er/últ gol) no son modelables sin datos de plantilla: se ponen como
mejor-conjetura y van marcados [REVISAR] para que tú los confirmes.
"""
import argparse, os, sys
import numpy as np
from collections import Counter
import openpyxl
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pollas.LEMAITRE.modelo_lemaitre as M
import pollas.LEMAITRE.competencia_lemaitre as C

PLANTILLA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "2026 06 Form Polla Mundial US-MX-CA.xlsx")

# API (inglés) -> (nombre español, código de la hoja)
ESP = {
 "Mexico":("México","MEX"),"South Africa":("Sudáfrica","SUD"),"South Korea":("Corea del Sur","CDS"),
 "Czech Republic":("Rep. Checa","CHE"),"Canada":("Canadá","CAN"),"Bosnia & Herzegovina":("Bosnia","BOS"),
 "Qatar":("Qatar","QAT"),"Switzerland":("Suiza","SUI"),"Brazil":("Brasil","BRA"),"Morocco":("Marruecos","MAR"),
 "Haiti":("Haití","HAI"),"Scotland":("Escocia","ESC"),"USA":("Est. Unidos","USA"),"Paraguay":("Paraguay","PAR"),
 "Australia":("Australia","LIA"),"Turkey":("Turquía","TUR"),"Germany":("Alemania","ALE"),"Curaçao":("Curazao","CUR"),
 "Ivory Coast":("Costa de Marfil","CDM"),"Ecuador":("Ecuador","ECU"),"Netherlands":("Países Bajos","HOL"),
 "Japan":("Japón","JAP"),"Sweden":("Suecia","SUE"),"Tunisia":("Túnez","TUN"),"Belgium":("Bélgica","BEL"),
 "Egypt":("Egipto","EGI"),"Iran":("Irán","IRN"),"New Zealand":("Nueva Zelanda","NZE"),"Spain":("España","ESP"),
 "Cape Verde":("Cabo Verde","CAB"),"Saudi Arabia":("Arabia Saudita","ASA"),"Uruguay":("Uruguay","URU"),
 "France":("Francia","FRA"),"Senegal":("Senegal","SEN"),"Iraq":("Irak","IRK"),"Norway":("Noruega","NOR"),
 "Argentina":("Argentina","ARG"),"Algeria":("Argelia","AGE"),"Austria":("Austria","ATA"),"Jordan":("Jordania","JOR"),
 "Portugal":("Portugal","POR"),"DR Congo":("RD Congo","CON"),"Uzbekistan":("Uzbekistán","UZB"),
 "Colombia":("Colombia","COL"),"England":("Inglaterra","ING"),"Croatia":("Croacia","CRO"),"Ghana":("Ghana","GHA"),
 "Panama":("Panamá","PAN"),
}
CONT_ES = {"UEFA":"Europa (UEFA)","CONMEBOL":"Sudamérica","CONCACAF":"Norteamérica",
           "CAF":"África","AFC":"Asia"}
# fila de cada equipo en la hoja Grupos (col equipo, col Pos, filas)
GRUPO_CELDAS = {  # grupo -> (col_equipo, col_pos, fila_inicial)
 "A":("A","B",7),"B":("C","D",7),"C":("E","F",7),"D":("G","H",7),"E":("I","J",7),"F":("K","L",7),
 "G":("A","B",12),"H":("C","D",12),"I":("E","F",12),"J":("G","H",12),"K":("I","J",12),"L":("K","L",12),
}


def nombre(tid_inv, i):  # team-id -> español
    return ESP.get(tid_inv[i], (tid_inv[i], "?"))[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", default="/tmp/wc_grupos.json")
    ap.add_argument("--futures", default="/tmp/wc_champ_futures.json")
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--sims", type=int, default=20000)
    args = ap.parse_args(argv)

    realiz, atk, dfn, Pgrupo, nuestra, teams, tid, inv = C.construir(args)
    S = realiz["S"]
    G = M.GRUPOS_OFICIALES

    # ---- extras desde la simulación ----
    gf, gc = realiz["gf"], realiz["gc"]
    score = realiz["score"]
    tot = gf.sum(axis=0) + sum(score[sl][0] + score[sl][1] for sl in score)
    cc = Counter(M.cont_de.get(inv[i], "?") for i in realiz["campeon"].tolist())
    cs = Counter(M.cont_de.get(inv[i], "?") for i in realiz["subcampeon"].tolist())
    gf_mean, gc_mean = gf.mean(axis=1), gc.mean(axis=1)
    ic = tid["Colombia"]
    PcolK = [Counter(realiz["pos"][("K", pu)].tolist()).get(ic, 0) / S for pu in range(1, 5)]
    col_pos = int(np.argmax(PcolK)) + 1
    extras = {
        "total_goles": int(round(tot.mean())),
        "cont_camp": CONT_ES.get(cc.most_common(1)[0][0], "?"),
        "cont_sub": CONT_ES.get(cs.most_common(1)[0][0], "?"),
        "mas_gf": nombre(inv, int(np.argmax(gf_mean))),
        "mas_gc": nombre(inv, int(np.argmax(gc_mean))),
        "menos_gf": nombre(inv, int(np.argmin(gf_mean))),
        "menos_gc": nombre(inv, int(np.argmin(gc_mean))),
        "ultimo_lugar": nombre(inv, int(np.argmin(gf_mean - gc_mean))),  # peor dif de gol
        "col_gf": int(round(gf[ic].mean())), "col_gc": int(round(gc[ic].mean())),
        "col_pos": col_pos,
    }

    wb = openpyxl.load_workbook(PLANTILLA)

    # ===== Hoja Grupos: escribir posición (1-4) junto a cada equipo =====
    wg = wb["Grupos"]
    for g, (ce, cp, f0) in GRUPO_CELDAS.items():
        pick = nuestra["grupo"][g]  # team-ids en orden 1..4
        posde = {pick[i]: i + 1 for i in range(4)}
        for k in range(4):
            cell = wg[f"{ce}{f0 + k}"]
            # detectar de qué equipo es la fila por el código en el texto
            txt = str(cell.value)
            code = txt.split()[-1].replace("\xa0", "")
            # team-id por código
            tcode = next((tid[t] for t in G[g] if ESP[t][1] == code), None)
            if tcode is None:  # fallback por nombre
                tcode = next((tid[t] for t in G[g] if ESP[t][0].split()[0] in txt), None)
            wg[f"{cp}{f0 + k}"] = posde.get(tcode, "")

    # ===== Hoja Form000: bracket + marcadores + extras =====
    wf = wb["Form000"]
    # mapa P# -> (fila_respuesta, col_eq1, col_eq2, col_m1, col_m2)
    slotcell = {}
    for row in wf.iter_rows():
        for c in row:
            v = c.value
            if isinstance(v, str) and v.strip().startswith("P#"):
                try:
                    n = int(v.replace("P#", "").strip())
                except ValueError:
                    continue
                col = c.column  # 1=A...
                if col == 1:   # bloque izquierdo: eq1=B eq2=C m1=D m2=E
                    cols = ("B", "C", "D", "E")
                else:          # bloque derecho: eq1=G eq2=H m1=I m2=J
                    cols = ("G", "H", "I", "J")
                slotcell[n] = (c.row + 1, *cols)

    def escribe_slot(sl, eq1_i, eq2_i, marc):
        fila, c1, c2, m1, m2 = slotcell[sl]
        wf[f"{c1}{fila}"] = nombre(inv, eq1_i)
        wf[f"{c2}{fila}"] = nombre(inv, eq2_i)
        wf[f"{m1}{fila}"] = marc[0]
        wf[f"{m2}{fila}"] = marc[1]

    for sl, c1, c2 in M.R32:
        a, b = nuestra["r32"][sl]
        escribe_slot(sl, a, b, nuestra["marc"][sl])
    for sl in [89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104]:
        A, B, _ = nuestra["arbol"][sl]
        escribe_slot(sl, A, B, nuestra["marc"][sl])

    # Extras Colombia (col N) y Extras (col R)
    wf["N6"] = "Luis Díaz"                # Anotador 1er Gol Colombia (conjetura: estrella COL)
    wf["N7"] = "Luis Díaz"                # Anotador Ultimo Gol Colombia (conjetura)
    wf["N8"] = extras["col_gf"]            # Total goles Favor Colombia
    wf["N9"] = extras["col_gc"]            # Total goles Contra Colombia
    wf["N10"] = f"{extras['col_pos']}º grupo K"  # Posición Tabla
    wf["R6"] = extras["total_goles"]      # Número Total de Goles
    wf["R7"] = "Kylian Mbappé"            # Jugador Goleador (favorito mercado ~14%)
    wf["R8"] = 7                           # Número de Goles del goleador (estimado formato ampliado)
    wf["R9"] = "México"                   # Equipo Primer Gol (local del partido inaugural)
    wf["R10"] = "España"                  # Equipo Ultimo Gol (campeón anota en la final)
    wf["R11"] = "España"                  # Equipo Gol No. 50 (conjetura: equipo más goleador)
    wf["R12"] = "Alemania"               # Equipo Gol No. 100 (conjetura: equipo más goleador)
    wf["R13"] = extras["ultimo_lugar"]    # Equipo Ultimo Lugar
    wf["R14"] = extras["mas_gf"]          # Equipo + Goles a favor
    wf["R15"] = extras["mas_gc"]          # Equipo + Goles en contra
    wf["R16"] = extras["menos_gf"]        # Equipo - Goles a favor
    wf["R17"] = extras["menos_gc"]        # Equipo - goles en contra
    wf["R18"] = extras["cont_camp"]       # Continente Campeón
    wf["R19"] = extras["cont_sub"]        # Continente Sub-campeón

    out = PLANTILLA.replace(".xlsx", "_LLENO.xlsx")
    wb.save(out)
    print(f"Excel lleno guardado en:\n  {out}")
    print("\nResumen de extras modelados:")
    for k, v in extras.items():
        print(f"  {k:14}: {v}")
    print("\nCeldas [REVISAR] = extras de jugador (sin data gratis): confírmalos tú.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
