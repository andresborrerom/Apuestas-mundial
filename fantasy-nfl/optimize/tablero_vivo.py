"""TABLERO HTML EN VIVO para el draft (7-sep, 7:00pm, 45 s/pick).

Pedido de Andrés (28-ago): *"herramienta html que se conecte en vivo y que yo
le dé ctrl+shift+R para que se refresque en cada elección y me muestre lo que
va quedando, EN ORDEN DE TU RECOMENDACIÓN PARA MI EQUIPO teniendo TODO en
cuenta (si los equipos que van a escoger ya tienen RB, la probabilidad de que
se lleven uno es más baja, etc.)"*.

Eso último es exactamente lo que hace el motor de `live_draft.Estado`: simula
los picks REALES entre mi turno y el siguiente, con cada rival conservando el
roster que ya lleva (sus necesidades posicionales suben o bajan la
probabilidad de cada posición). Este módulo solo le pone la cara HTML.

    python optimize/tablero_vivo.py            # en vivo → http://localhost:8787
    python optimize/tablero_vivo.py --demo     # ensayo HOY con sala simulada
    python optimize/tablero_vivo.py --sleeper <draft_id> --mi-slot 5
        # mock REAL en Sleeper (crea el mock en sleeper.com, copia el id del
        # URL). API pública sin login; cruce sleeper_id→espn_id por el
        # crosswalk (93% del pool 2026 cubierto).
        # ⚠️ NO probado extremo a extremo hasta el primer mock: los candados
        # de mapeo gritan si un pick no cruza, pero la primera corrida es
        # ensayo, no confianza.

La página se refresca sola cada 10 s y con ctrl+shift+R al instante.

CANDADOS al arrancar (si alguno truena, banner ROJO y no se recomienda):
  1. TRIPWIRE T1: el scoring de la API se compara ítem por ítem contra
     config/espn_settings_2026.json (si el commish quitó el "total" de las
     tacleadas, el tablero viejo MIENTE y hay que regenerarlo).
  2. pickOrder real de la app == asiento 5 para teamId 10 (mi equipo).
  3. teamId 10 pertenece a Andres Borrero (mTeam).
"""
import argparse
import html as H
import json
import sys
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import requests
from ingest.espn_auth import credenciales
from optimize.sala import EQUIPOS, RONDAS, MI_PICK, OFE
from optimize.plan_draft import calibrar, preparar
from optimize.live_draft import MI_TEAM_ID, Estado, api_picks

RAIZ = Path(__file__).resolve().parent.parent
PUERTO = 8787
ORDEN_POS = ('QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'DST', 'K')

PAGINA_HTML = None          # la última página renderizada (bytes)
CANDADOS = []               # [(nombre, ok, detalle)]
NOMBRES_EQUIPO = {}         # teamId -> nombre en la app


def candados_arranque():
    """Los tres candados. Devuelve lista de (nombre, ok, detalle)."""
    out = []
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    r = requests.get(u, params={'view': ['mSettings', 'mTeam']},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=30)
    r.raise_for_status()
    d = r.json()
    # 1. TRIPWIRE de scoring (la ficha T1 vive aquí)
    local = json.load(open(RAIZ / 'config' / 'espn_settings_2026.json'))
    canon = lambda items: sorted(
        (it['statId'], it.get('points'), tuple(sorted((it.get('pointsOverrides')
                                                       or {}).items())))
        for it in items)
    ahora = canon(d['settings']['scoringSettings']['scoringItems'])
    guardado = canon(local['settings']['scoringSettings']['scoringItems'])
    dif = [a for a in ahora if a not in guardado] + \
          [g for g in guardado if g not in ahora]
    out.append(('scoring vs config local (T1)', not dif,
                'idéntico' if not dif else f'🚨 {len(dif)} ítems cambiaron: '
                f'{sorted({x[0] for x in dif})} — REGENERAR TABLERO'))
    # 2. pickOrder
    orden = d['settings'].get('draftSettings', {}).get('pickOrder') or []
    ok2 = len(orden) == EQUIPOS and orden[MI_PICK - 1] == MI_TEAM_ID
    out.append((f'pick {MI_PICK} = mi equipo (teamId {MI_TEAM_ID})', ok2,
                f'pickOrder={orden}'))
    # 3. dueño del equipo
    dueños = {m['id']: f"{m.get('firstName','')} {m.get('lastName','')}".strip()
              for m in d.get('members', [])}
    quien = ''
    for t in d.get('teams', []):
        NOMBRES_EQUIPO[t['id']] = t.get('name', f"team {t['id']}")
        if t['id'] == MI_TEAM_ID:
            quien = ', '.join(dueños.get(o, o) for o in t.get('owners', []))
    out.append((f'teamId {MI_TEAM_ID} es mío', 'Andres' in quien,
                f'owner: {quien or "?"}'))
    # 4. la GRILLA real del snake (ESPN la pre-publica con playerId=-1) debe
    #    coincidir con la secuencia que calcula la herramienta — así el orden
    #    de turnos queda verificado contra la fuente, no contra nuestra cuenta.
    try:
        from optimize.live_draft import api_picks
        from optimize.sala import orden_snake
        _, _, grilla = api_picks()
        pickorder = d['settings'].get('draftSettings', {}).get('pickOrder') or []
        esp = {gp: pickorder[t] if t < len(pickorder) else None
               for gp, t in enumerate(orden_snake(), 1)}
        malos = [gp for gp, tid in grilla if esp.get(gp) != tid]
        out.append(('grilla snake de ESPN == mi secuencia', not malos,
                    f'{len(grilla)} slots comparados'
                    + ('' if not malos else f' · difieren {len(malos)}: {malos[:5]}')))
    except Exception as e:
        out.append(('grilla snake de ESPN == mi secuencia', False,
                    f'{type(e).__name__}: {e}'))
    return out


def notas():
    try:
        return json.load(open(RAIZ / 'data' / 'notas.json'))
    except Exception:
        return {}


# ------------------------------------------------------------------ RENDER
CSS = """
:root{--bg:#0e1116;--panel:#161b24;--line:#232b38;--tx:#dbe2ee;--dim:#7d8aa0;
--acc:#58a6ff;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--top:#1f6feb22}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:14px/1.45 -apple-system,'Segoe UI',
Roboto,sans-serif;padding:14px 18px;max-width:1240px;margin:auto}
h1{font-size:17px;margin-bottom:2px} .dim{color:var(--dim)} .ok{color:var(--ok)}
.bad{color:var(--bad)} .warn{color:var(--warn)} .acc{color:var(--acc)}
.fila{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:8px;
padding:10px 14px}
.reco{border-color:var(--acc);flex:1 1 100%}
.reco .nom{font-size:26px;font-weight:700}
table{border-collapse:collapse;width:100%} td,th{padding:3px 8px;text-align:right;
white-space:nowrap} th{color:var(--dim);font-weight:600;border-bottom:1px solid
var(--line);position:sticky;top:0;background:var(--panel)}
td:nth-child(2),th:nth-child(2){text-align:left}
tr:nth-child(-n+3) td{background:var(--top)}
.nota{color:var(--dim);font-size:12px;max-width:430px;overflow:hidden;
text-overflow:ellipsis;white-space:nowrap;text-align:left}
.pos{display:inline-block;min-width:30px;text-align:center;border-radius:4px;
padding:0 4px;font-weight:700;font-size:12px}
.candado{font-size:12px;margin-right:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:6px}
.mini{background:var(--bg);border:1px solid var(--line);border-radius:6px;
padding:5px 8px;font-size:12px}
"""
COLPOS = {'QB': '#d2a8ff', 'RB': '#7ee787', 'WR': '#79c0ff', 'TE': '#ffa657',
          'DT': '#f0883e', 'DE': '#f0883e', 'LB': '#ff7b72', 'CB': '#e3b341',
          'S': '#e3b341', 'DST': '#8b949e', 'K': '#8b949e'}


def pos_chip(p):
    return f'<span class="pos" style="color:{COLPOS.get(p,"#ccc")}">{p}</span>'


def render(est, hechos, idx, info, N, demo=False):
    P = est.pool
    n = len(hechos)
    prox = est.proximo_mio(hechos)
    ronda = n // EQUIPOS + 1
    quien = est.secuencia[n] if n < len(est.secuencia) else None
    turno = NOMBRES_EQUIPO.get(quien + 1, f'asiento {quien + 1}') if quien is not None else '—'
    ahora = time.strftime('%H:%M:%S')
    top = []
    if info.get('tabla'):
        surv = info['surv']
        luego_pos = {p: luego for g, p, i, a, luego, sv in info['tabla']}
        vivos_el = [i for i in range(len(P)) if i not in est.tomados]
        cnt = defaultdict(int)
        for i in est.mis:
            cnt[P[i]['pos']] += 1
        from optimize.sala import MAX_UTIL_MIO
        for i in vivos_el:
            p = P[i]['pos']
            if cnt[p] >= MAX_UTIL_MIO.get(p, 3):
                continue                      # regla: 1 IDP por posición, etc.
            g = P[i]['vbd'] - luego_pos.get(p, 0.0)
            top.append((g, i, surv[i]))
        top.sort(reverse=True)

    filas = []
    for k, (g, i, sv) in enumerate(top[:N]):
        j = P[i]
        nt = NOTAS.get(j['nombre'], {})
        nota = nt.get('hechos', '')
        if nt.get('espn'):
            nota = (nota + ' · ' if nota else '') + '“' + nt['espn'][:90] + '”'
        filas.append(
            f"<tr><td class=dim>{k+1}</td><td><b>{H.escape(j['nombre'])}</b></td>"
            f"<td>{pos_chip(j['pos'])}</td><td>{j['vbd']:.0f}</td>"
            f"<td class=dim>{j['vbd']-g:.0f}</td>"
            f"<td><b class={'ok' if g>15 else 'dim'}>{g:+.0f}</b></td>"
            f"<td>{sv*100:.0f}%</td>"
            f"<td class=nota>{H.escape(nota)}</td></tr>")

    reco = ''
    if idx is not None:
        j = P[idx]
        razon = info.get('regla') or (
            f"mayor ganancia marginal: ahora {j['vbd']:.0f} · si espero "
            f"{j['vbd'] - top[0][0]:.0f} · P(vive a mi turno) "
            f"{info['surv'][idx]*100:.0f}%") if info.get('surv') is not None else ''
        nt = NOTAS.get(j['nombre'], {})
        reco = (f'<div class="panel reco">'
                f'<span class=dim>MI RECOMENDACIÓN — pick {info.get("mi_pick","?")} '
                f'(ronda {(info.get("mi_pick",1)-1)//EQUIPOS+1})</span><br>'
                f'<span class=nom>{H.escape(j["nombre"])}</span> {pos_chip(j["pos"])} '
                f'<span class=dim>piso {j["p10"]:.0f} · mediana {j["p50"]:.0f} · '
                f'techo {j["p90"]:.0f}</span><br>'
                f'<span class=acc>{H.escape(razon or "")}</span><br>'
                f'<span class=dim>{H.escape(nt.get("hechos",""))}'
                f'{("  ·  “"+H.escape(nt["espn"][:160])+"”") if nt.get("espn") else ""}'
                f'</span></div>')

    # mejor vivo por posición
    mejor_pos = []
    porpos = defaultdict(list)
    for i in range(len(P)):
        if i not in est.tomados:
            porpos[P[i]['pos']].append(i)
    for p in ORDEN_POS:
        l = sorted(porpos.get(p, []), key=lambda i: -P[i]['vbd'])[:2]
        if l:
            t = ' · '.join(f"{H.escape(P[i]['nombre'].split()[-1])} {P[i]['vbd']:.0f}"
                           for i in l)
            mejor_pos.append(f'<div class=mini>{pos_chip(p)} {t}</div>')

    # mi roster y huecos
    mio = ''.join(f'<div class=mini>{pos_chip(P[i]["pos"])} '
                  f'{H.escape(P[i]["nombre"])}</div>' for i in est.mis) or \
          '<span class=dim>aún nada</span>'
    gaps = {k: v for k, v in info.get('gaps', {}).items() if v}

    ults = []
    for gp, team, pid in hechos[-8:][::-1]:
        i = est.por_id.get(pid)
        nm = P[i]['nombre'] if i is not None else f'id {pid}'
        eq = NOMBRES_EQUIPO.get(team, f'team {team}')
        mark = ' class=acc' if team == MI_TEAM_ID else ''
        ults.append(f'<div class=mini{mark}>{gp}. {H.escape(nm)} '
                    f'<span class=dim>— {H.escape(str(eq))[:18]}</span></div>')

    cand = ' '.join(
        f'<span class="candado {"ok" if ok else "bad"}">'
        f'{"✅" if ok else "🚨"} {H.escape(nom)}</span>'
        for nom, ok, det in CANDADOS)
    alerta = ''.join(f'<div class="panel bad" style="border-color:var(--bad)">'
                     f'🚨 {H.escape(nom)}: {H.escape(det)}</div>'
                     for nom, ok, det in CANDADOS if not ok)

    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta http-equiv=refresh content=10><title>Draft en vivo — Peace and Love</title>
<style>{CSS}</style></head><body>
<h1>Peace and Love 2026 — tablero en vivo {'· <span class=warn>DEMO</span>' if demo else ''}</h1>
<div class=dim>pick {n + 1} · ronda {ronda} · pica: <b>{H.escape(str(turno))}</b>
 · mi próximo turno: <b class=acc>{prox or '—'}</b>
 (faltan {prox - n - 1 if prox else '—'} picks) · {ahora} · {cand}</div>
{alerta}
<div class=fila>{reco}</div>
<div class=fila>
<div class=panel style="flex:2 1 640px">
<table><tr><th></th><th>jugador</th><th>pos</th><th>VBD</th><th>si espero</th>
<th>ganancia</th><th>P(vive)</th><th style="text-align:left">nota</th></tr>
{''.join(filas)}</table></div>
<div style="flex:1 1 260px;display:flex;flex-direction:column;gap:12px">
<div class=panel><b>mejor vivo por posición</b><div class=grid>{''.join(mejor_pos)}</div></div>
<div class=panel><b>mi roster</b> <span class=dim>{('faltan: ' + H.escape(str(gaps))) if gaps else ''}</span>
<div class=grid>{mio}</div></div>
<div class=panel><b>últimos picks</b><div class=grid>{''.join(ults)}</div></div>
</div></div>
<div class=dim style="margin-top:10px">orden = ganancia marginal del motor
(VBD ahora − lo que espero que quede en esa posición en mi próximo turno,
simulando a CADA rival con el roster que ya lleva) · la página se refresca
sola cada 10 s · ctrl+shift+R fuerza</div>
</body></html>"""


# ------------------------------------------------------------------ SERVIDOR
# ---- PUENTE DEL NAVEGADOR (1-sep): la pestaña del draft room POSTea aquí
# el Pick History que ve en el DOM. Es la fuente EN VIVO del 7-sep (medido
# 28-ago: la API de ESPN no publica picks hasta el cierre).
PUENTE = {'picks': [], 'ts': 0.0, 'sin_resolver': []}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/puente':
            self.send_response(404); self.end_headers(); return
        try:
            n = int(self.headers.get('Content-Length') or 0)
            datos = json.loads(self.rfile.read(n).decode('utf-8', 'replace'))
            PUENTE['picks'] = datos.get('picks', [])
            PUENTE['ts'] = time.time()
        except Exception as e:
            print('puente: cuerpo inválido:', type(e).__name__, e)
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_GET(self):
        cuerpo = PAGINA_HTML or b'<meta http-equiv=refresh content=2>arrancando...'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def bucle(est, args, fuente_picks):
    global PAGINA_HTML
    ultimo, idx, info = -1, None, {}
    while True:
        try:
            hechos = fuente_picks()
        except Exception as e:
            print('API:', type(e).__name__, e)
            time.sleep(args.intervalo)
            continue
        for gp, team, pid in hechos:
            est.marcar(est.por_id.get(pid), team, gp)
        if len(hechos) != ultimo:
            ultimo = len(hechos)
            t0 = time.time()
            idx, info = est.recomendar(hechos, sims=args.sims)
            print(f'  pick {ultimo}: recomputado en {time.time()-t0:.1f}s → '
                  f'{est.pool[idx]["nombre"] if idx is not None else "—"}')
        PAGINA_HTML = render(est, hechos, idx, info, args.filas,
                             demo=args.demo).encode()
        time.sleep(args.intervalo)


def main():
    global CANDADOS, NOTAS
    ap = argparse.ArgumentParser()
    ap.add_argument('--demo', action='store_true')
    ap.add_argument('--sleeper', help='draft_id de un mock de Sleeper')
    ap.add_argument('--puente', action='store_true',
                    help='fuente = POST /puente desde optimize/puente.js en la pestaña del draft')
    ap.add_argument('--mi-slot', type=int, default=MI_PICK,
                    help='mi asiento en el mock de Sleeper (default: 5)')
    ap.add_argument('--puerto', type=int, default=PUERTO)
    ap.add_argument('--intervalo', type=float, default=4.0)
    ap.add_argument('--sims', type=int, default=200)
    ap.add_argument('--filas', type=int, default=25)
    ap.add_argument('--qbs-r13', type=int, default=20)
    args = ap.parse_args()
    NOTAS.update(notas())
    print('candados de arranque...', flush=True)
    try:
        CANDADOS[:] = candados_arranque()
    except Exception as e:
        CANDADOS[:] = [('conexión a la API', False, f'{type(e).__name__}: {e}')]
    for nom, ok, det in CANDADOS:
        print(f'  {"✅" if ok else "🚨"} {nom}: {det}')
    if not all(ok for _, ok, _ in CANDADOS) and not args.demo:
        print('\n🚨 HAY CANDADOS EN ROJO — el tablero los muestra en banner.')
    print('preparando tablero y calibrando sala...', flush=True)
    pool = preparar()
    qb_b, pen = calibrar(pool, args.qbs_r13, 10)
    est = Estado(pool, qb_b, pen)
    print(f'mis picks: {est.mis_picks}')

    if args.demo:
        demo_estado = {'hechos': []}
        secuencia = est.secuencia

        def avanzar():
            rng = np.random.default_rng(99)
            d = est.cargar_estado(rng)
            while len(demo_estado['hechos']) < EQUIPOS * RONDAS:
                gp = len(demo_estado['hechos']) + 1
                t = secuencia[gp - 1]
                if t == MI_PICK - 1:
                    i, _ = est.recomendar(demo_estado['hechos'], sims=60)
                    team = MI_TEAM_ID
                else:
                    i = d.pick_rival(t, (gp - 1) // EQUIPOS + 1)
                    team = t + 1
                if i is None:
                    break
                d.tomar(t, i)
                demo_estado['hechos'].append((gp, team, pool[i].get('espn_id')))
                time.sleep(2.0 if t != MI_PICK - 1 else 6.0)
        threading.Thread(target=avanzar, daemon=True).start()
        fuente = lambda: list(demo_estado['hechos'])
    elif args.sleeper:
        import duckdb
        con = duckdb.connect(str(RAIZ / 'db' / 'fantasy.duckdb'), read_only=True)
        s2e = {str(int(sl)): int(e) for e, sl in con.execute(
            "select espn_id, sleeper_id from xwalk_ids_nflverse "
            "where espn_id is not null and sleeper_id is not null").fetchall()}
        con.close()
        sin_cruce = set()

        def fuente_sleeper():
            r = requests.get(f'https://api.sleeper.app/v1/draft/{args.sleeper}/picks',
                             timeout=15)
            r.raise_for_status()
            out = []
            for pk in r.json():
                eid = s2e.get(str(pk.get('player_id')))
                if eid is None and pk.get('player_id') not in sin_cruce:
                    sin_cruce.add(pk.get('player_id'))
                    m = pk.get('metadata') or {}
                    print(f"  ⚠️ sin cruce sleeper→espn: {m.get('first_name','')} "
                          f"{m.get('last_name','')} (sleeper {pk.get('player_id')})")
                team = (MI_TEAM_ID if pk.get('draft_slot') == args.mi_slot else
                        -int(pk.get('draft_slot') or 0))
                out.append((pk['pick_no'], team, eid))
            return sorted(out)
        fuente = fuente_sleeper
        # en Sleeper mi asiento puede NO ser el 5: reindexar mis turnos
        if args.mi_slot != MI_PICK:
            est.mis_picks = [gp for gp, t in enumerate(est.secuencia, 1)
                             if t == args.mi_slot - 1]
            print(f'⚠️ asiento Sleeper {args.mi_slot}: mis picks {est.mis_picks}')
    elif args.puente:
        import unicodedata

        def norm(s):
            s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode()
            return ' '.join(s.lower().replace('.', ' ').replace("'", '').split())

        SUF = {'jr', 'sr', 'ii', 'iii', 'iv', 'v'}
        por_nombre = {}
        for i, j in enumerate(pool):
            por_nombre.setdefault((norm(j['nombre']), j['pos']), i)
            base = ' '.join(w for w in norm(j['nombre']).split() if w not in SUF)
            por_nombre.setdefault((base, j['pos']), i)
        por_apellido = {}
        for i, j in enumerate(pool):
            ap_ = [w for w in norm(j['nombre']).split() if w not in SUF]
            if ap_:
                por_apellido.setdefault((ap_[-1], j['pos']), []).append(i)

        avisados = set()

        def resolver(nombre, pos):
            pos = {'D/ST': 'DST', 'DST': 'DST'}.get(pos, pos)
            n = norm(nombre)
            base = ' '.join(w for w in n.split() if w not in SUF)
            i = por_nombre.get((n, pos)) or por_nombre.get((base, pos))
            if i is not None:
                return i
            if pos == 'DST':      # el DOM dice "Steelers D/ST" o "Pittsburgh"
                c = [k for k, j in enumerate(pool) if j['pos'] == 'DST'
                     and (norm(j['nombre']).split()[0] in n or n.split()[0] in norm(j['nombre']))]
                return c[0] if len(c) == 1 else None
            c = por_apellido.get((base.split()[-1] if base else '', pos), [])
            return c[0] if len(c) == 1 else None

        def fuente_puente():
            out, sin = [], []
            for p in sorted(PUENTE['picks'], key=lambda x: x.get('n', 0)):
                gp = int(p.get('n') or 0)
                if not gp:
                    continue
                i = resolver(p.get('nombre', ''), p.get('pos', ''))
                asiento = est.secuencia[gp - 1] if gp <= len(est.secuencia) else -1
                team = MI_TEAM_ID if asiento == MI_PICK - 1 else -(asiento + 1)
                if i is None:
                    sin.append(f"pick {gp}: {p.get('nombre')} ({p.get('pos')})")
                    if (gp, p.get('nombre')) not in avisados:
                        avisados.add((gp, p.get('nombre')))
                        print(f"  🚨 puente SIN RESOLVER pick {gp}: "
                              f"{p.get('nombre')!r} ({p.get('pos')}) — corrígelo o dime")
                    continue
                out.append((gp, team, pool[i].get('espn_id')))
            PUENTE['sin_resolver'] = sin
            edad = time.time() - PUENTE['ts'] if PUENTE['ts'] else None
            if edad is not None and edad > 20:
                print(f"  ⚠️ puente sin señal hace {edad:.0f}s — ¿la pestaña sigue viva?")
            return sorted(out)
        fuente = fuente_puente
    else:
        fuente = lambda: api_picks()[0]

    threading.Thread(target=bucle, args=(est, args, fuente), daemon=True).start()
    print(f'\n▶ abre  http://localhost:{args.puerto}   (ctrl+shift+R para forzar)')
    ThreadingHTTPServer(('0.0.0.0', args.puerto), Handler).serve_forever()


NOTAS = {}

if __name__ == '__main__':
    main()
