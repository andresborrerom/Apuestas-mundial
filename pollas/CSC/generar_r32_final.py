#!/usr/bin/env python3
"""
Genera los 5 cupos FINALES de R32 (esquema MIXTO + ajuste 120') y el snippet de
consola para llenar el formulario. Decidido en ESTUDIO_R32.md.

Esquema (asignado a las entradas por su puntaje actual, PDF 27/06):
  - ANDRES BORRERO 4 (276) = ANCLA: EV-máximo puro (protege el mejor cupo).
  - ANDRES BORRERO 1 (262) = perturbada n_swaps=3 (semilla A).
  - ANDRES BORRERO 2 (256) = perturbada n_swaps=3 (semilla B).
  - ANDRES BORRERO 3 (250) = ESCALÓN 2º fill en todo (lotería).
  - ANDRES BORRERO 5 (243) = ESCALÓN 3º fill en todo (lotería).
Ajuste 120' (delta=0.45): los empates a 90' se resuelven parcialmente en el
alargue, así el ancla no sobre-apuesta penales y los empates quedan repartidos.

Uso:
    ODDS_API_KEY=... python pollas/CSC/generar_r32_final.py            # cuotas en vivo
    python pollas/CSC/generar_r32_final.py --snapshot pollas/CSC/r32_odds_snapshot.json
"""
import argparse, csv, json, os, sys, unicodedata, re
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from motor import analizar_partido, marcadores, simulacion_polla as sp, odds_api
from pollas.CSC.reglas import regla_de_ronda, RONDAS
from pollas.CSC import llenar as L
from pollas.CSC.experimento_r32 import ajuste_120, ranking_fills

AQUI = os.path.dirname(os.path.abspath(__file__))
PARAMS = RONDAS["dieciseisavos"]; G = 7

ALIAS = {
 "Sudáfrica": ["sudafrica", "southafrica"], "Canadá": ["canada"],
 "Brasil": ["brasil", "brazil"], "Japón": ["japon", "japan"],
 "Alemania": ["alemania", "germany"], "Paraguay": ["paraguay"],
 "Países Bajos": ["paisesbajos", "netherlands", "holanda"], "Marruecos": ["marruecos", "morocco"],
 "Costa de Marfil": ["costademarfil", "ivorycoast"], "Norway": ["noruega", "norway"],
 "Francia": ["francia", "france"], "Sweden": ["suecia", "sweden"],
 "México": ["mexico"], "Ecuador": ["ecuador"],
 "Inglaterra": ["inglaterra", "england"], "DR Congo": ["congo", "drcongo", "rdcongo"],
 "Bélgica": ["belgica", "belgium"], "Senegal": ["senegal"],
 "USA": ["usa", "estadosunidos", "unitedstates", "eeuu"], "Bosnia & Herzegovina": ["bosnia", "bosniaherzegovina"],
 "España": ["espana", "spain"], "Austria": ["austria"],
 "Portugal": ["portugal"], "Croacia": ["croacia", "croatia"],
 "Suiza": ["suiza", "switzerland"], "Algeria": ["argelia", "algeria"],
 "Australia": ["australia"], "Egipto": ["egipto", "egypt"],
 "Argentina": ["argentina"], "Cape Verde": ["caboverde", "capeverde"],
 "Colombia": ["colombia"], "Ghana": ["ghana"],
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-key", default=os.environ.get("ODDS_API_KEY"))
    ap.add_argument("--snapshot", default=None, help="usar JSON de eventos en vez de la API")
    ap.add_argument("--delta", type=float, default=0.45)
    ap.add_argument("--csv", default=os.path.join(AQUI, "r32_CSC.csv"))
    ap.add_argument("--snippet", default=os.path.join(AQUI, "snippet_r32.js"))
    args = ap.parse_args(argv)

    if args.snapshot:
        ev = json.load(open(args.snapshot, encoding="utf-8"))
    else:
        if not args.api_key:
            ap.error("se requiere ODDS_API_KEY o --snapshot")
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Bogota")
        todos = odds_api.bajar_eventos(args.api_key, sport=odds_api.SPORT_MUNDIAL,
                                       regions="us,uk,eu", markets="h2h,totals")
        ev = [e for e in todos if e.get("commence_time") and L.inferir_ronda(
              datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(tz).date()) == "dieciseisavos"]

    filas, M90, lam = [], [], []
    for e in ev:
        c = odds_api.consenso_evento(e, linea_pref=2.5)
        if not c["cuotas_1x2"]:
            continue
        r = analizar_partido(cuotas_1x2=c["cuotas_1x2"], regla=regla_de_ronda("dieciseisavos"),
                             cuotas_ou=c["cuotas_ou"], linea_ou=c["linea"] or 2.5,
                             sesgo_goles=0.0, max_goles_relleno=7)
        M90.append(r["matriz"]); lam.append((r["modelo"]["lambda_local"], r["modelo"]["lambda_visita"]))
        from datetime import datetime
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Bogota"))
        filas.append({"fecha": dt.strftime("%Y-%m-%d"), "hora": dt.strftime("%H:%M"),
                      "local": L.es(c["home"]), "visita": L.es(c["away"])})

    # ajuste 120' + construir esquema MIXTO
    M120 = [ajuste_120(M, lL, lV, args.delta) for M, (lL, lV) in zip(M90, lam)]
    Ms = [marcadores.aplicar_sesgo_goles(M, 0.05) for M in M120]
    rk = ranking_fills(Ms)
    ph, pa = sp.generar_nuestras(Ms, 5, PARAMS, estrategia="perturbada",
                                 rng=np.random.default_rng(7), n_swaps=3, pool=40, gap_max=0.30, G=G)
    anc_h, anc_a = ph[0], pa[0]
    p1h, p1a = ph[1], pa[1]
    p2h, p2a = ph[2], pa[2]
    l2h = np.array([r[1][0] for r in rk]); l2a = np.array([r[1][1] for r in rk])  # 2º fill
    l3h = np.array([r[2][0] for r in rk]); l3a = np.array([r[2][1] for r in rk])  # 3º fill

    # mapeo a entradas: cupo_N = ANDRES BORRERO N
    cupos = {1: (p1h, p1a),       # B1 (262) perturbado A
             2: (p2h, p2a),       # B2 (256) perturbado B
             3: (l2h, l2a),       # B3 (250) escalón 2º
             4: (anc_h, anc_a),   # B4 (276) ancla EV-máx
             5: (l3h, l3a)}       # B5 (243) escalón 3º

    for i, f in enumerate(filas):
        for n in range(1, 6):
            f[f"cupo_{n}"] = f"{cupos[n][0][i]}-{cupos[n][1][i]}"
        f["marcador"] = f["cupo_4"]  # ancla como referencia

    cols = ["fecha", "hora", "local", "visita", "marcador"] + [f"cupo_{n}" for n in range(1, 6)]
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
        for f in filas:
            w.writerow({k: f[k] for k in cols})
    print(f"💾 CSV -> {args.csv}")

    # snippet de consola (un cupo por formulario; CUPO=N -> ANDRES BORRERO N)
    PART = [{"L": f["local"], "V": f["visita"], "aL": ALIAS[f["local"]], "aV": ALIAS[f["visita"]],
             "s": [[int(f[f"cupo_{n}"].split("-")[0]), int(f[f"cupo_{n}"].split("-")[1])] for n in range(1, 6)]}
            for f in filas]
    snip = ('(function(){\n'
            '  /* CSC 16avos MIXTO+120\'. CUPO = nº de ANDRES BORRERO (1..5). Cambia y re-pega. NO envía. */\n'
            '  var CUPO = 4;  // <<<<<< 4=ancla(B4) · 1,2=perturbados · 3,5=lotería\n'
            '  var PART = ' + json.dumps(PART, ensure_ascii=False) + ';\n'
            '  function k(s){return (s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^a-z]/g,"");}\n'
            '  function has(t,al){for(var i=0;i<al.length;i++){if(t.indexOf(al[i])>=0)return t.indexOf(al[i]);}return -1;}\n'
            '  function setVal(el,v){el.value=v;["input","change","blur"].forEach(function(ev){el.dispatchEvent(new Event(ev,{bubbles:true}));});}\n'
            '  var inputs=[].slice.call(document.querySelectorAll("input[type=number],input[type=text],input:not([type])"));\n'
            '  var conts=[],seen=[];\n'
            '  inputs.forEach(function(inp){var n=inp;for(var u=0;u<7&&n;u++){n=n.parentElement;if(!n)break;\n'
            '    if(n.querySelectorAll("input[type=number],input[type=text],input:not([type])").length>=2){if(seen.indexOf(n)<0){seen.push(n);conts.push(n);}break;}}});\n'
            '  var ok=0,miss=[];\n'
            '  PART.forEach(function(p){var done=false;\n'
            '    for(var c=0;c<conts.length;c++){var t=k(conts[c].textContent);var iL=has(t,p.aL),iV=has(t,p.aV);\n'
            '      if(iL>=0&&iV>=0){var ins=conts[c].querySelectorAll("input[type=number],input[type=text],input:not([type])");if(ins.length<2)continue;\n'
            '        var rev=iV<iL,gl=p.s[CUPO-1][0],gv=p.s[CUPO-1][1];setVal(ins[0],rev?gv:gl);setVal(ins[1],rev?gl:gv);ok++;done=true;break;}}\n'
            '    if(!done)miss.push(p.L+" vs "+p.V);});\n'
            '  console.log("%cCSC ANDRES BORRERO "+CUPO+": llené "+ok+"/"+PART.length,"font-size:14px;color:"+(ok==PART.length?"green":"orange"));\n'
            '  if(miss.length)console.warn("FALTAN (a mano):",miss);\n'
            '  console.log("Revisa y dale ENVIAR tú. Cambia CUPO y re-pega para el siguiente.");\n'
            '})();')
    open(args.snippet, "w", encoding="utf-8").write(snip)
    print(f"💾 snippet -> {args.snippet}")

    # imprimir tabla
    print("\n  Partido                       B1     B2     B3     B4*    B5")
    for f in filas:
        print(f"  {f['local']+' vs '+f['visita']:28}" + " ".join(f"{f['cupo_'+str(n)]:>6}" for n in range(1, 6)))
    print("  (* B4 = ancla. Cupo_N llena ANDRES BORRERO N.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
