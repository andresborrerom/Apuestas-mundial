#!/usr/bin/env python3
"""
TABLERO LEMAITRE — réplica EXACTA del scoring del organizador (templecolombia).

Validado: reproduce los totales publicados (Pocho/nosotros = 534, etc.). La data
sale del app público (index.html embebe todo): planillas de los 27 participantes,
resultados reales y la lógica de puntos. Snapshot en `lemaitre_data.json`.

    python pollas/LEMAITRE/puntos_lemaitre.py            # tabla + nuestro desglose
    python pollas/LEMAITRE/puntos_lemaitre.py --refresh  # baja la data en vivo del repo

Lógica replicada de la app (no inventada):
- Marcadores por partido (73-104): exacto/ganador/parcial, puntos por fase
  (F32/OCT 40/18/12 · CUAR 50/30/14 · SEMI 60/40/15 · 3º 70/48/20 · FINAL 80/48/24).
- Clasificación: por slot R32 (73-88), equipos predichos vs reales:
  40 ambos en orden · 25 invertidos · 20 uno en su puesto · 15 uno cambiado.
- Extras / Colombia: total_goles 120, goleador 50, hitos 40, stats 30, etc.
"""
import argparse, json, os, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(AQUI, "lemaitre_data.json")
URL = "https://raw.githubusercontent.com/TempleColombia/polla-mundial-2026/main/index.html"

PTS = {"F32": {"e": 40, "g": 18, "p": 12}, "OCT": {"e": 40, "g": 18, "p": 12},
       "CUAR": {"e": 50, "g": 30, "p": 14}, "SEMI": {"e": 60, "g": 40, "p": 15},
       "TERC": {"e": 70, "g": 48, "p": 20}, "FINAL": {"e": 80, "g": 48, "p": 24}}
ALIAS = {'países bajos': 'Holanda', 'paises bajos': 'Holanda', 'estados unidos': 'EEUU',
         'rd congo': 'RD Congo', 'r.d. congo': 'RD Congo',
         'república democrática del congo': 'RD Congo',
         'arabia saudí': 'Arabia Saudí', 'arabia saudi': 'Arabia Saudí',
         'bosnia': 'Bosnia', 'bosnia herzegovina': 'Bosnia', 'cabo verde': 'Cabo Verde'}


def refrescar():
    html = urllib.request.urlopen(URL, timeout=40).read().decode("utf-8")
    i = html.find('const BASE_DATA = ') + len('const BASE_DATA = ')
    depth = 0
    for j in range(i, len(html)):
        if html[j] == '{': depth += 1
        elif html[j] == '}':
            depth -= 1
            if depth == 0: break
    BD = json.loads(html[i:j + 1])
    json.dump(BD, open(SNAP, "w"), ensure_ascii=False)
    return BD


def norm(name):
    if not name: return ''
    return ALIAS.get(str(name).strip().lower(), str(name).strip())


def calc_marcador(pred, real, fase):
    # Regla ADITIVA (validada contra el oficial 2/7/2026): exacto=e; si no,
    # ganador (g) y parcial (p) SUMAN por separado. Un 1-0 sobre un 2-0 da
    # 18 (ganador) + 12 (acertó el 0 de la visita) = 30 — NO se degrada.
    if not real or real.get('g1') is None or real.get('g2') is None: return 0
    if not pred or pred.get('e1') is None or pred.get('e2') is None: return 0
    pp = PTS[fase]; r1, r2 = real['g1'], real['g2']; e1, e2 = pred['e1'], pred['e2']
    if e1 == r1 and e2 == r2: return pp['e']
    rw = 1 if r1 > r2 else (2 if r1 < r2 else 0)
    pw = 1 if e1 > e2 else (2 if e1 < e2 else 0)
    pts = 0
    if rw == pw: pts += pp['g']
    if e1 == r1 or e2 == r2: pts += pp['p']
    return pts


def calc_clasif(predE, realEq):
    pts = 0
    for pid in range(73, 89):
        s = str(pid); real = realEq.get(s); pred = predE.get(s)
        if not real or not real.get('e1') or not real.get('e2') or not pred: continue
        p1, p2 = norm(pred['e1']), norm(pred['e2']); r1, r2 = norm(real['e1']), norm(real['e2'])
        if p1 == r1 and p2 == r2: pts += 40
        elif p1 == r2 and p2 == r1: pts += 25
        elif p1 == r1 or p2 == r2: pts += 20
        elif p1 == r2 or p2 == r1: pts += 15
    return pts


def _mv(p, r): return p is not None and r is not None and str(p).strip().lower() == str(r).strip().lower()
def _mn(p, r):
    try: return p is not None and r is not None and int(p) == int(r)
    except (ValueError, TypeError): return False


def calc_extras(px, rx):
    pts = 0
    if _mn(px.get('total_goles'), rx.get('real_total_goles')): pts += 120
    if _mv(px.get('goleador'), rx.get('real_goleador')): pts += 50
    if _mn(px.get('goles_goleador'), rx.get('real_goles_goleador')): pts += 50
    for h in ['25', '50', '75', '100', '125', '150']:
        if _mv(px.get('gol_' + h), rx.get('real_gol_' + h)): pts += 40
    for k in ['ultimo_lugar', 'mas_goles_fav', 'mas_goles_contra', 'menos_goles_fav', 'menos_goles_contra']:
        if _mv(px.get(k), rx.get('real_' + k)): pts += 30
    for k in ['primer_gol_equipo', 'ultimo_gol_equipo', 'continente_camp', 'continente_subcamp']:
        if _mv(px.get(k), rx.get('real_' + k)): pts += 20
    return pts


def calc_colombia(px, rx):
    pts = 0
    if _mv(px.get('col_1er_gol'), rx.get('real_col_1er_gol')): pts += 40
    if _mv(px.get('col_ultimo_gol'), rx.get('real_col_ultimo_gol')): pts += 40
    if _mn(px.get('col_goles_fav'), rx.get('real_col_goles_fav')): pts += 50
    if _mn(px.get('col_goles_contra'), rx.get('real_col_goles_contra')): pts += 50
    if _mn(px.get('col_posicion'), rx.get('real_col_posicion')): pts += 70
    return pts


def calc_todo(BD):
    rs, req, rx = BD['real_scores'], BD['real_equipos'], BD.get('real_extras', {})
    ph, pm, pe, pxs = BD['partido_phases'], BD['predictions_m'], BD['predictions_e'], BD['predictions_x']
    out = {}
    for p in BD['participants']:
        n = str(p['num'])
        mar = sum(calc_marcador((pm.get(n) or {}).get(k), rs.get(k), ph[k]) for k in ph)
        cl = calc_clasif(pe.get(n) or {}, req)
        ext = calc_extras(pxs.get(n) or {}, rx)
        col = calc_colombia(pxs.get(n) or {}, rx)
        out[n] = dict(name=p['name'], id=p['id'], mar=mar, cl=cl, ext=ext, col=col,
                      total=mar + cl + ext + col)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="baja la data en vivo del repo")
    args = ap.parse_args(argv)
    BD = refrescar() if args.refresh else json.load(open(SNAP, encoding="utf-8"))
    sc = calc_todo(BD)
    rank = sorted(sc.values(), key=lambda x: -x['total'])
    jug = sum(1 for v in BD['real_scores'].values() if v.get('g1') is not None)
    print(f"=== LEMAITRE — tabla ({jug} partidos puntuados) ===")
    print(f"  {'#':>2} {'Participante':22}{'Marc':>5}{'Clasif':>7}{'ExtCol':>7}{'Extras':>7}{'TOTAL':>7}")
    for i, v in enumerate(rank, 1):
        flag = '  <<< NOSOTROS' if v['name'] == 'Pocho' else ''
        if i <= 6 or flag:
            print(f"  {i:>2} {v['name'][:22]:22}{v['mar']:>5}{v['cl']:>7}{v['col']:>7}{v['ext']:>7}{v['total']:>7}{flag}")
    yo = next(v for v in sc.values() if v['name'] == 'Pocho')
    seg = rank[1]['total'] if rank[0]['name'] == 'Pocho' else rank[0]['total']
    print(f"\n  POCHO (nosotros): {yo['total']} pts  ·  marcadores {yo['mar']} · clasif {yo['cl']} · extras {yo['ext']}")
    print(f"  Ventaja sobre el 2º: {yo['total']-seg:+d}" if rank[0]['name'] == 'Pocho'
          else f"  A {rank[0]['total']-yo['total']} del líder")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
