#!/usr/bin/env python3
"""
TABLAS DEL MUNDIAL (ground truth) — grupos, general de equipos y extras.

Replica EXACTO la lógica del app oficial (index.html de templecolombia):
- Grupos: 3/1/0; desempate pts -> dif de gol (GF-GC) -> GF. Top-2 clasifica.
  (visto en la función renderGrupos del app).
- Los EXTRAS (último lugar, más/menos goles, etc.) los entra el ADMIN a mano;
  el app NO los calcula. Aquí SÍ los calculamos desde grupos_results + resultados
  de knockout para saber cuál será su valor real y cuáles ya son concluibles.

Fuente de datos: lemaitre_data.json (snapshot de BASE_DATA; refrescar con
puntos_lemaitre.py --refresh). Los goles cuentan grupos (1-72) + knockout jugado.

    python pollas/LEMAITRE/tablas_mundial.py            # grupos + general + extras
"""
import json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(AQUI, "lemaitre_data.json")


def cargar(bd=None):
    return bd or json.load(open(SNAP, encoding="utf-8"))


def tallies_equipos(BD, incluir_knockout=True):
    """GF/GC/pts por equipo. Grupos (grupos_results) + knockout jugado (real_scores)."""
    T = {}

    def add(eq, gf, gc, contexto):
        s = T.setdefault(eq, dict(eq=eq, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0,
                                  grupo=None, pj_grp=0, gf_grp=0, gc_grp=0, pts_grp=0))
        s["pj"] += 1; s["gf"] += gf; s["gc"] += gc
        if gf > gc: s["g"] += 1; s["pts"] += 3
        elif gf < gc: s["p"] += 1
        else: s["e"] += 1; s["pts"] += 1
        if contexto == "grupo":
            s["pj_grp"] += 1; s["gf_grp"] += gf; s["gc_grp"] += gc
            s["pts_grp"] += 3 if gf > gc else (1 if gf == gc else 0)

    for p in BD["grupos_results"]:
        if p.get("e1") is None or p.get("e2") is None:
            continue
        e1, e2 = p["eq1"], p["eq2"]
        add(e1, p["e1"], p["e2"], "grupo"); add(e2, p["e2"], p["e1"], "grupo")
        T[e1]["grupo"] = p["grupo"]; T[e2]["grupo"] = p["grupo"]

    if incluir_knockout:
        for k, r in BD["real_scores"].items():
            if r.get("g1") is None or r.get("g2") is None:
                continue
            add(r["e1"], r["g1"], r["g2"], "ko"); add(r["e2"], r["g2"], r["g1"], "ko")

    return T


def tablas_grupos(BD):
    """Devuelve {grupo: [filas ordenadas]} replicando renderGrupos."""
    grupos = {}
    for p in BD["grupos_results"]:
        if p.get("e1") is None:
            continue
        g = p["grupo"]
        st = grupos.setdefault(g, {})
        for eq in (p["eq1"], p["eq2"]):
            st.setdefault(eq, dict(eq=eq, pj=0, g=0, e=0, p=0, gf=0, gc=0, pts=0))
        s1, s2 = st[p["eq1"]], st[p["eq2"]]
        s1["pj"] += 1; s2["pj"] += 1
        s1["gf"] += p["e1"]; s1["gc"] += p["e2"]; s2["gf"] += p["e2"]; s2["gc"] += p["e1"]
        if p["e1"] > p["e2"]: s1["g"] += 1; s1["pts"] += 3; s2["p"] += 1
        elif p["e1"] < p["e2"]: s2["g"] += 1; s2["pts"] += 3; s1["p"] += 1
        else: s1["e"] += 1; s1["pts"] += 1; s2["e"] += 1; s2["pts"] += 1
    out = {}
    for g, st in grupos.items():
        out[g] = sorted(st.values(),
                        key=lambda a: (-a["pts"], -(a["gf"] - a["gc"]), -a["gf"]))
    return out


def general_equipos(BD, solo_grupos=True):
    """Ranking global de los 48 equipos (por defecto SOLO fase de grupos, que es
    la base para 'último lugar del Mundial'). Orden: pts -> difgol -> GF."""
    T = tallies_equipos(BD, incluir_knockout=not solo_grupos)
    if solo_grupos:
        filas = [dict(eq=s["eq"], grupo=s["grupo"], pj=s["pj_grp"], gf=s["gf_grp"],
                      gc=s["gc_grp"], dif=s["gf_grp"] - s["gc_grp"], pts=s["pts_grp"])
                 for s in T.values()]
    else:
        filas = [dict(eq=s["eq"], grupo=s["grupo"], pj=s["pj"], gf=s["gf"],
                      gc=s["gc"], dif=s["gf"] - s["gc"], pts=s["pts"]) for s in T.values()]
    filas.sort(key=lambda a: (-a["pts"], -a["dif"], -a["gf"], a["gc"]))
    return filas


def ultimo_lugar(BD):
    """Último del Mundial: peor por pts -> dif de gol -> (más) goles en contra."""
    filas = general_equipos(BD, solo_grupos=True)
    # peor: menos pts, peor dif, más GC, menos GF
    peor = sorted(filas, key=lambda a: (a["pts"], a["dif"], -a["gc"], a["gf"]))
    return peor


def extras_candidatos(BD):
    """Valores reales (a hoy) de los extras basados en goles, con concluibilidad."""
    T = tallies_equipos(BD, incluir_knockout=True)  # todo el torneo a la fecha
    vivos = equipos_vivos(BD)
    filas = list(T.values())
    mas_fav = sorted(filas, key=lambda s: (-s["gf"], -(s["gf"] - s["gc"])))
    men_fav = sorted(filas, key=lambda s: (s["gf"], s["gf"] - s["gc"]))
    mas_con = sorted(filas, key=lambda s: (-s["gc"],))
    men_con = sorted(filas, key=lambda s: (s["gc"],))
    return dict(mas_goles_fav=mas_fav, menos_goles_fav=men_fav,
                mas_goles_contra=mas_con, menos_goles_contra=men_con, vivos=vivos)


def equipos_vivos(BD):
    """Equipos aún en competencia (aparecen en un partido de knockout SIN jugar)."""
    vivos = set()
    for k, teams in BD.get("partido_teams", {}).items():
        pass  # partido_teams son etiquetas (2° Gpo A), no equipos reales
    # Equipos reales en slots R32 (real_equipos 73-88) que NO han sido eliminados:
    real_eq = BD.get("real_equipos", {})
    rs = BD["real_scores"]
    en_ko = set()
    for pid in range(73, 89):
        e = real_eq.get(str(pid))
        if e and e.get("e1") and e.get("e2"):
            en_ko.add(e["e1"]); en_ko.add(e["e2"])
    # eliminados en R32 jugado
    elim = set()
    for pid in range(73, 89):
        r = rs.get(str(pid))
        if r and r.get("g1") is not None:
            if r["g1"] > r["g2"]: elim.add(r["e2"])
            elif r["g2"] > r["g1"]: elim.add(r["e1"])
    return en_ko - elim


def _fmt(s):
    return f"{s['eq']:18}{s.get('grupo') or '-':>3}  PJ{s['pj']:>2}  {s['gf']:>2}-{s['gc']:<2} dif{s.get('dif', s['gf']-s['gc']):>+3}  pts{s['pts']:>2}"


def main():
    BD = cargar()
    print("=" * 60, "\nTABLAS DE GRUPOS (top-2 clasifica)\n" + "=" * 60)
    for g, filas in sorted(tablas_grupos(BD).items()):
        print(f"\n Grupo {g}:")
        for i, s in enumerate(filas, 1):
            mark = "✓" if i <= 2 else ("·" if i == 3 else "✗")
            print(f"   {mark}{i} {_fmt(s)}")

    print("\n" + "=" * 60, "\nGENERAL (48 equipos, solo grupos) — cola de la tabla\n" + "=" * 60)
    filas = general_equipos(BD, solo_grupos=True)
    for i, s in enumerate(filas, 1):
        if i > len(filas) - 8:
            print(f"   {i:>2}. {_fmt(s)}")

    print("\n" + "=" * 60, "\nÚLTIMO LUGAR (peor: pts -> dif -> +GC)\n" + "=" * 60)
    for i, s in enumerate(ultimo_lugar(BD)[:6], 1):
        print(f"   {i}. {_fmt(s)}")

    print("\n" + "=" * 60, "\nEXTRAS DE GOLES (todo el torneo a la fecha)\n" + "=" * 60)
    ex = extras_candidatos(BD)
    vivos = ex["vivos"]
    for key, titulo, peor_es_menos in [
        ("mas_goles_fav", "MÁS goles a favor", False),
        ("menos_goles_fav", "MENOS goles a favor", True),
        ("mas_goles_contra", "MÁS goles en contra", False),
        ("menos_goles_contra", "MENOS goles en contra", True)]:
        top = ex[key][:4]
        lider = top[0]
        # ¿concluible? Si el líder ya está eliminado y ningún vivo puede superarlo.
        print(f"\n {titulo}:  líder actual = {lider['eq']} "
              f"(GF {lider['gf']}, GC {lider['gc']})  {'[vivo]' if lider['eq'] in vivos else '[eliminado]'}")
        for s in top:
            print(f"     {s['eq']:16} GF{s['gf']:>2} GC{s['gc']:>2}  {'vivo' if s['eq'] in vivos else 'elim'}")


if __name__ == "__main__":
    main()
