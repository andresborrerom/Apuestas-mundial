#!/usr/bin/env python3
"""
Genera los 5 cupos de OCTAVOS (esquema MIXTO position-aware + ajuste 120') y el
snippet de consola. Plug-and-play: apenas se cierre el bracket de octavos y haya
cuotas, corre esto y llena el formulario.

Regla octavos = (3,4,7) — ganador 3 / gol=0 vale 4 / gol!=0 vale (#+7).
Deadline octavos: 04/07/2026 11:59 AM (hora Colombia).

ESQUEMA position-aware (PDF 2-jul: vamos #1 B4=383, #2 B1=371, #5 B2=362,
B3/B5 ~#16 fuera de premio). Como LIDERAMOS, defendemos los cupos de arriba y
solo apostamos con los que ya están fuera de premio:
  - B4 (ancla, #1)  = EV-máximo puro            -> DEFENDER el liderato
  - B1 (#2)         = perturbada n_swaps=2      -> defender, casi-EV, decorrela
  - B2 (#5 burbuja) = perturbada n_swaps=3      -> defender la casilla de premio
  - B3 (fuera)      = 2º fill (lotería)         -> moonshot, nada que perder
  - B5 (fuera)      = 3º fill (lotería)         -> moonshot
Con --modo atacar se sube la dispersión (si en el próximo PDF caemos del podio).

Uso:
    ODDS_API_KEY=... python pollas/CSC/generar_octavos.py                 # cuotas en vivo (octavos)
    python pollas/CSC/generar_octavos.py --snapshot pollas/CSC/oct_odds_snapshot.json
"""
import argparse, csv, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from motor import analizar_partido, marcadores, simulacion_polla as sp, odds_api
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC import llenar as L
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills
from pollas.CSC.generar_r32_final import ALIAS  # 32 equipos R32 ⊇ equipos octavos

AQUI = os.path.dirname(os.path.abspath(__file__))
RONDA = "octavos"
PARAMS = RONDAS[RONDA]; G = 7


def alias_de(nombre_es):
    """Alias para el snippet; cae a nombre normalizado si el equipo no está mapeado."""
    if nombre_es in ALIAS:
        return ALIAS[nombre_es]
    import unicodedata, re
    k = re.sub(r"[^a-z]", "", unicodedata.normalize("NFD", nombre_es).encode("ascii", "ignore").decode().lower())
    return [k]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--snapshot", default=None, help="JSON de eventos de octavos")
    ap.add_argument("--delta", type=float, default=0.45)
    ap.add_argument("--modo", choices=["defender", "equilibrado", "atacar"], default="defender")
    ap.add_argument("--csv", default=os.path.join(AQUI, "oct_CSC.csv"))
    ap.add_argument("--snippet", default=os.path.join(AQUI, "snippet_oct.js"))
    args = ap.parse_args(argv)

    # dispersión por modo (n_swaps de las perturbadas B1/B2)
    swaps = {"defender": (2, 3), "equilibrado": (3, 4), "atacar": (5, 6)}[args.modo]

    if args.snapshot:
        ev = json.load(open(args.snapshot, encoding="utf-8"))
    else:
        if not args.api_key:
            ap.error("se requiere ODDS_API_KEY o --snapshot (aún sin cuotas de octavos)")
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Bogota")
        todos = odds_api.bajar_eventos(args.api_key, sport=odds_api.SPORT_MUNDIAL,
                                       regions="us,uk,eu", markets="h2h,totals")
        ev = [e for e in todos if e.get("commence_time") and L.inferir_ronda(
              datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(tz).date()) == RONDA]

    if not ev:
        ap.error("no hay eventos de octavos en la fuente (¿bracket aún sin cerrar o snapshot vacío?)")

    filas, M90, lam = [], [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]:
            continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda(RONDA),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
        from datetime import datetime
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Bogota"))
        filas.append({"fecha": dt.strftime("%Y-%m-%d"), "hora": dt.strftime("%H:%M"),
                      "local": L.es(c["home"]), "visita": L.es(c["away"])})

    M120 = [ajuste_120(M, lL, lV, args.delta) for M, (lL, lV) in zip(M90, lam)]
    Ms = [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]
    rk = ranking_fills(Ms)
    # B4 ancla + B1/B2 perturbadas (una semilla por cada n_swaps)
    phA, paA = sp.generar_nuestras(Ms, 2, PARAMS, estrategia="perturbada",
                                   rng=np.random.default_rng(7), n_swaps=swaps[0], pool=40, gap_max=0.30, G=G)
    phB, paB = sp.generar_nuestras(Ms, 2, PARAMS, estrategia="perturbada",
                                   rng=np.random.default_rng(11), n_swaps=swaps[1], pool=40, gap_max=0.30, G=G)
    anc_h, anc_a = phA[0], paA[0]           # EV-máx (ancla)
    p1h, p1a = phA[1], paA[1]               # perturbada suave (B1, defiende #2)
    p2h, p2a = phB[1], paB[1]               # perturbada media (B2, defiende #5)
    l2h = np.array([r[1][0] for r in rk]); l2a = np.array([r[1][1] for r in rk])  # 2º fill
    l3h = np.array([r[2][0] for r in rk]); l3a = np.array([r[2][1] for r in rk])  # 3º fill

    cupos = {1: (p1h, p1a), 2: (p2h, p2a), 3: (l2h, l2a), 4: (anc_h, anc_a), 5: (l3h, l3a)}
    for i, f in enumerate(filas):
        for n in range(1, 6):
            f[f"cupo_{n}"] = f"{cupos[n][0][i]}-{cupos[n][1][i]}"
        f["marcador"] = f["cupo_4"]

    cols = ["fecha", "hora", "local", "visita", "marcador"] + [f"cupo_{n}" for n in range(1, 6)]
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for f in filas:
            w.writerow({k: f[k] for k in cols})
    print(f"💾 CSV -> {args.csv}   (modo={args.modo}, n_swaps={swaps})")

    PART = [{"L": f["local"], "V": f["visita"], "aL": alias_de(f["local"]), "aV": alias_de(f["visita"]),
             "s": [[int(f[f"cupo_{n}"].split("-")[0]), int(f[f"cupo_{n}"].split("-")[1])] for n in range(1, 6)]}
            for f in filas]
    # snippet con la lógica CORREGIDA (validada en R32): ancla en el ELEMENTO
    # de título más corto que contiene ambos equipos y llena los 2 inputs que
    # están DENTRO o que le SIGUEN, marcando inputs ya usados (used) para no
    # reescribir las mismas casillas. NO usar la lógica de "contenedor por texto"
    # (reescribía las mismas 2 celdas). Ver POST-MORTEM en OCTAVOS_CHECKLIST.md.
    snip = ('(function(){\n'
            '  /* CSC MIXTO+120\'. CUPO = nº de ANDRES BORRERO (1..5). Cambia y re-pega. NO envía. */\n'
            '  var CUPO = 4;  // <<<<<< 4=ancla(B4) · 1,2=defensivas · 3,5=lotería\n'
            '  var PART = ' + json.dumps(PART, ensure_ascii=False) + ';\n'
            '  function k(s){return (s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}\n'
            '  function hasA(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return true;}return false;}\n'
            '  function setVal(el,v){el.value=v;["input","change","blur","keyup"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}\n'
            '  var inputs=[].slice.call(document.querySelectorAll("input")).filter(function(i){return i.type!=="email"&&i.type!=="hidden";});\n'
            '  if(inputs.length<PART.length){console.log("%c⚠️ CONTEXTO EQUIVOCADO: en el dropdown arriba-izq de la consola elige userHtmlFrame (userCodeAppPanel) y re-pega.","font-size:16px;font-weight:bold;color:red");return;}\n'
            '  var els=[].slice.call(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,span,p,label,td,li,b,strong"));\n'
            '  var used=[],ok=0,miss=[],log=[];\n'
            '  PART.forEach(function(p){\n'
            '    var lab=null,len=1e9;\n'
            '    for(var i=0;i<els.length;i++){var t=k(els[i].textContent||"");\n'
            '      if(hasA(t,p.aL)&&hasA(t,p.aV)){var L=(els[i].textContent||"").length;if(L<len){len=L;lab=els[i];}}}\n'
            '    if(!lab){miss.push(p.L+" vs "+p.V);return;}\n'
            '    var inside=inputs.filter(function(x){return lab.contains(x)&&used.indexOf(x)<0;});\n'
            '    var foll=inputs.filter(function(x){return (lab.compareDocumentPosition(x)&Node.DOCUMENT_POSITION_FOLLOWING)&&used.indexOf(x)<0;});\n'
            '    var cand=(inside.length===2)?inside:foll;\n'
            '    if(cand.length<2){miss.push(p.L+" vs "+p.V);return;}\n'
            '    var gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];\n'
            '    setVal(cand[0],gl);setVal(cand[1],gv);used.push(cand[0],cand[1]);ok++;\n'
            '    log.push(p.L+" "+gl+"-"+gv+" "+p.V);\n'
            '  });\n'
            '  console.log("%cCSC BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:15px;font-weight:bold;color:"+(ok==PART.length?"green":"orange"));\n'
            '  console.log(log.join("\\n"));\n'
            '  if(miss.length)console.warn("FALTAN (a mano):",miss);\n'
            '})();')
    open(args.snippet, "w", encoding="utf-8").write(snip)
    print(f"💾 snippet -> {args.snippet}")

    print(f"\n  Partido                       B1     B2     B3     B4*    B5")
    for f in filas:
        print(f"  {f['local']+' vs '+f['visita']:28}" + " ".join(f"{f['cupo_'+str(n)]:>6}" for n in range(1, 6)))
    print("  (* B4 = ancla EV-máx. Cupo_N llena ANDRES BORRERO N.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
