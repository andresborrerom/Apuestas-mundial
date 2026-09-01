"""ASISTENTE EN VIVO del draft (7-sep, 45 s por pick).

Lee el draft REAL de la API de ESPN (view mDraftDetail) cada pocos segundos,
mantiene el pool disponible y, cuando se acerca mi turno, calcula en ~2 s:

  - top recomendaciones = VBD(ahora) − E[VBD(mejor de esa posición en mi
    PRÓXIMO turno)], con supervivencia simulada DESDE EL ESTADO REAL
    (no de una tabla precalculada: la sala ya se desvió del guion).
  - qué slots me faltan y cuántos picks quedan para llenarlos.
  - alertas de barranco: "último de su tier", "si no lo tomas ya, no vuelve".

Modo manual (`--manual`) por si la API no refresca en vivo: se escriben los
nombres tomados y el motor sigue igual.

CANDADO DE ÚLTIMA MILLA: tras cada pick mío verifica contra la API que el
jugador quedó EN MI ROSTER (teamId 10). Si no aparece, GRITA.

    python optimize/live_draft.py                 # auto (poll cada 5 s)
    python optimize/live_draft.py --manual        # entrada por teclado
    python optimize/live_draft.py --simulacro     # mock contra la sala
"""
import argparse, json, sys, time
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import requests
from ingest.espn_auth import credenciales
from optimize.sala import (EQUIPOS, RONDAS, MI_PICK, MAX_UTIL, MAX_UTIL_MIO, OBLIG, OBLIG_MIO, OFE,
                           OFE_MIN, cargar, score_sala, orden_snake)
from optimize.plan_draft import Draft, UMBRAL_BYE, calibrar, e_mejor, preparar

MI_TEAM_ID = 10                      # 'No Team for Old Men' — verificado
QB_BONUS_DEF, IDP_PEN_DEF = None, None   # se calibran al arrancar


def api_picks():
    lid, s2, swid = credenciales()
    u = (f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026"
         f"/segments/0/leagues/{lid}")
    r = requests.get(u, params={'view': ['mDraftDetail', 'mTeam']},
                     cookies={'espn_s2': s2, 'SWID': swid}, timeout=20)
    r.raise_for_status()
    d = r.json()
    # 🚨 FIX 28-ago (lo cazó la pregunta de Andrés "¿puedes conectarte al
    # draft real?"): ESPN pre-publica la grilla completa del snake con
    # playerId = -1 ANTES del draft. El filtro viejo `if playerId` dejaba
    # pasar los -1 (truthy) → la herramienta habría visto "288 picks hechos"
    # y dado el draft por terminado antes de empezar. Solo playerId > 0 es
    # un pick real.
    hechos = [(p['overallPickNumber'], p['teamId'], p.get('playerId'))
              for p in d['draftDetail']['picks']
              if (p.get('playerId') or 0) > 0]
    # la grilla (con o sin jugador) sirve de candado: el snake REAL de ESPN
    grilla = [(p['overallPickNumber'], p['teamId'])
              for p in d['draftDetail']['picks']]
    orden = [t['id'] for t in sorted(d.get('teams', []), key=lambda t: t['id'])]
    return sorted(hechos), d['draftDetail'].get('drafted'), sorted(grilla)


class Estado:
    def __init__(self, pool, qb_bonus, idp_pen):
        self.pool = pool
        self.por_id = {j['espn_id']: i for i, j in enumerate(pool) if j.get('espn_id')}
        self.por_nombre = {j['nombre'].lower(): i for i, j in enumerate(pool)}
        self.qb_bonus, self.idp_pen = qb_bonus, idp_pen
        self.tomados = {}                    # idx -> teamId
        self.por_pick = {}                   # pick global -> idx
        self.mis = []                        # idx que tomé yo
        self.secuencia = orden_snake()       # índice de equipo por pick global
        self.mis_picks = [gp for gp, t in enumerate(self.secuencia, 1)
                          if t == MI_PICK - 1]

    def marcar(self, idx, team, pick=None):
        if idx is not None and idx not in self.tomados:
            self.tomados[idx] = team
            if pick:
                self.por_pick[pick] = idx
            if team == MI_TEAM_ID:
                self.mis.append(idx)

    def buscar(self, texto):
        t = texto.strip().lower()
        if t in self.por_nombre:
            return self.por_nombre[t]
        cands = [i for n, i in self.por_nombre.items() if t in n and i not in self.tomados]
        return cands[0] if len(cands) == 1 else (cands if cands else None)

    def proximo_mio(self, hechos):
        n = len(hechos)
        return next((p for p in self.mis_picks if p > n), None)

    def cargar_estado(self, rng):
        """Draft con el estado REAL: cada pick global va al slot del snake que
        le toca, así los rivales conservan sus necesidades posicionales."""
        d = Draft(self.pool, rng, 12.0, self.qb_bonus, self.idp_pen)
        for gp, idx in sorted(self.por_pick.items()):
            if idx is None:
                continue
            d.tomar(self.secuencia[gp - 1], idx)
        return d

    def recomendar(self, hechos, sims=250, seed=7):
        """Simula desde el estado real hasta mi próximo turno y decide."""
        hechos_n = len(hechos)
        mi_pick = next((p for p in self.mis_picks if p > hechos_n), None)
        if mi_pick is None:
            return None, {}
        sig = next((p for p in self.mis_picks if p > mi_pick), None)
        vivos = np.ones(len(self.pool), bool)
        for i in self.tomados:
            vivos[i] = False
        # cuenta de MI roster
        cnt = defaultdict(int)
        for i in self.mis:
            cnt[self.pool[i]['pos']] += 1
        # 🔒 guardarraíl QB>=2 (1-sep): mi segundo QB es obligatorio
        gaps = {p: max(0, k - cnt[p]) for p, k in OBLIG_MIO.items()}
        ofe = sum(cnt[p] for p in OFE) + sum(gaps[p] for p in OFE)
        extra_ofe = max(0, OFE_MIN - ofe)
        quedan = RONDAS - len(self.mis)
        forzado = sum(gaps.values()) + extra_ofe >= quedan
        elegibles = [i for i in range(len(self.pool)) if vivos[i]
                     # 🔒 mis topes, no los de la sala: un IDP por posición
                     and cnt[self.pool[i]['pos']] < MAX_UTIL_MIO.get(self.pool[i]['pos'], 3)
                     and (not forzado or gaps.get(self.pool[i]['pos'], 0) > 0
                          or (extra_ofe > 0 and self.pool[i]['pos'] in OFE))]
        if sig is None:
            mejor = max(elegibles, key=lambda i: self.pool[i]['vbd'])
            return mejor, {'motivo': 'último turno: mejor VBD disponible'}
        # supervivencia: simular los picks REALES entre mi turno y el siguiente,
        # con cada rival conservando el roster que ya lleva
        cont = np.zeros(len(self.pool))
        rng = np.random.default_rng(seed)
        for _ in range(sims):
            d = self.cargar_estado(rng)
            for gp in range(mi_pick + 1, sig):
                t = self.secuencia[gp - 1]
                i = d.pick_rival(t, (gp - 1) // EQUIPOS + 1)
                if i is not None:
                    d.tomar(t, i)
            cont += d.alive
        surv = cont / sims
        porpos = defaultdict(list)
        for i in elegibles:
            porpos[self.pool[i]['pos']].append(i)
        filas = []
        opciones = []            # (g, i) — incluye al 2º de cada posición si empata
        for p, idxs in porpos.items():
            idxs.sort(key=lambda i: -self.pool[i]['vbd'])
            ahora_i = idxs[0]
            ahora = self.pool[ahora_i]['vbd']
            arr = np.array([self.pool[i]['vbd'] for i in idxs])
            luego = e_mejor(arr, surv[np.array(idxs)])
            filas.append((ahora - luego, p, ahora_i, ahora, luego,
                          surv[ahora_i]))
            opciones.append((ahora - luego, ahora_i))
            if len(idxs) > 1 and ahora - self.pool[idxs[1]]['vbd'] <= UMBRAL_BYE:
                opciones.append((ahora - luego - (ahora - self.pool[idxs[1]]['vbd']),
                                 idxs[1]))
        filas.sort(reverse=True)
        elegido, regla, desempate = filas[0][2], None, None
        # 🔄 DESEMPATE POR BYES (1-sep, validado pareado en 20 salas: −VBD 0,
        # menos semanas con 3+ titulares ofensivos en bye): entre opciones a
        # ≤5 pts de la mejor ganancia, evitar apilar un TERCER bye ofensivo.
        g_max = max(g for g, i in opciones)
        finalistas = [(g, i) for g, i in opciones if g >= g_max - UMBRAL_BYE]
        if len(finalistas) > 1:
            mis_byes = defaultdict(int)
            for i in self.mis:
                j = self.pool[i]
                if j['pos'] in OFE and j.get('bye'):
                    mis_byes[j['bye']] += 1

            def llave(gi):
                g, i = gi
                b = self.pool[i].get('bye') if self.pool[i]['pos'] in OFE else 0
                return (max(0, mis_byes.get(b, 0) - 1) if b else 0, -g)
            alt = min(finalistas, key=llave)[1]
            if alt != elegido:
                desempate = (f"desempate por byes: {self.pool[alt]['nombre']} "
                             f"sobre {self.pool[elegido]['nombre']} (evita 3er "
                             f"bye sem {self.pool[elegido].get('bye')}, "
                             f"cuesta ≤{UMBRAL_BYE:.0f} pts)")
                elegido = alt
        # REGLA VALIDADA (pareada, 4 escenarios) para mis DOS primeros picks:
        # el motor de ganancia marginal es MIOPE (mira un turno adelante) y en
        # la comparación perdió contra la apertura fija. Del pick 3 en adelante
        # no hay regla fija validada y manda el motor.
        n_mios = len(self.mis)
        if n_mios == 0:
            elegido = max(porpos.get('WR', elegibles), key=lambda i: self.pool[i]['vbd'])
            regla = 'R1: mejor WR (regla validada)'
        elif n_mios == 1:
            qbs = porpos.get('QB', [])
            mejor_qb = max((self.pool[i]['vbd'] for i in qbs), default=-1e9)
            if mejor_qb >= 110:
                elegido = max(qbs, key=lambda i: self.pool[i]['vbd'])
                regla = f'R2: QB con VBD {mejor_qb:.0f} ≥ 110 (regla validada)'
            else:
                elegido = max(porpos.get('WR', elegibles), key=lambda i: self.pool[i]['vbd'])
                regla = 'R2: ningún QB ≥ 110 vivo → mejor WR (regla validada)'
        return elegido, {'tabla': filas, 'surv': surv, 'mi_pick': mi_pick,
                         'sig': sig, 'gaps': gaps, 'extra_ofe': extra_ofe,
                         'regla': regla, 'motor': filas[0][2],
                         'desempate': desempate}


def pinta(est, idx, info, hechos):
    P = est.pool
    print('\n' + '=' * 74)
    print(f" PICK {info.get('mi_pick','?')} (ronda {(info.get('mi_pick',1)-1)//EQUIPOS+1})"
          f"   ·   siguiente turno mío: {info.get('sig','—')}"
          f"   ·   tomados: {len(hechos)}")
    faltan = {k: v for k, v in info.get('gaps', {}).items() if v}
    print(f" me faltan: {faltan or 'nada obligatorio'}"
          f"  · ofensivos extra por llenar: {info.get('extra_ofe', 0)}")
    print('-' * 74)
    print(f" {'':2}{'jugador':22}{'pos':>4}{'VBD':>7}{'si espero':>11}{'ganancia':>10}{'P(vive)':>9}")
    for k, (g, p, i, ahora, luego, sv) in enumerate(info.get('tabla', [])[:7]):
        marca = '>>' if k == 0 else '  '
        print(f" {marca}{P[i]['nombre'][:22]:22}{p:>4}{ahora:>7.0f}{luego:>11.0f}"
              f"{g:>10.0f}{sv*100:>8.0f}%")
    if idx is not None:
        j = P[idx]
        print('-' * 74)
        print(f" ➡️  TOMA: {j['nombre']} ({j['pos']})   piso {j['p10']:.0f} · techo {j['p90']:.0f}")
        if info.get('regla'):
            print(f"     [{info['regla']}]")
            m = info.get('motor')
            if m is not None and m != idx:
                print(f"     (el motor miope preferiría {P[m]['nombre']} — la regla"
                      f" validada manda en los 2 primeros picks)")
    print('=' * 74)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manual', action='store_true')
    ap.add_argument('--intervalo', type=float, default=5.0)
    ap.add_argument('--qbs-r13', type=int, default=20,
                    help='QBs esperados en R1-R3 (medido: ~20)')
    args = ap.parse_args()
    pool = preparar()
    print('calibrando modelo de sala...', flush=True)
    qb_b, pen = calibrar(pool, args.qbs_r13, 10)
    est = Estado(pool, qb_b, pen)
    print(f'listo (qb_bonus={qb_b:.0f}, idp_pen={pen:.0f}) · mis picks: {est.mis_picks}')
    if args.manual:
        hechos = []
        while len(hechos) < EQUIPOS * RONDAS:
            prox = est.proximo_mio(hechos)
            if prox == len(hechos) + 1:
                idx, info = est.recomendar(hechos)
                pinta(est, idx, info, hechos)
            txt = input(f"[{len(hechos)+1}] tomado > ").strip()
            if not txt:
                continue
            if txt.lower() in ('q', 'salir'):
                break
            i = est.buscar(txt)
            if isinstance(i, list) or i is None:
                print('   ambiguo/no encontrado:', i if i else 'sin match')
                continue
            equipo = MI_TEAM_ID if est.secuencia[len(hechos)] == MI_PICK - 1 else -1
            est.marcar(i, equipo, len(hechos) + 1)
            hechos.append((len(hechos) + 1, equipo, pool[i].get('espn_id')))
            print(f"   ✓ {pool[i]['nombre']} ({pool[i]['pos']})"
                  f"{'  <<< MÍO' if equipo == MI_TEAM_ID else ''}")
        return 0
    ultimo = 0
    while True:
        try:
            hechos, listo, _ = api_picks()
        except Exception as e:
            print('API:', type(e).__name__, e); time.sleep(args.intervalo); continue
        for gp, team, pid in hechos:
            i = est.por_id.get(pid)
            # 🚨 FIX auditoría 28-ago: sin `pick=gp`, por_pick quedaba vacío y
            # la simulación de supervivencia arrancaba con la sala SIN los
            # picks ya hechos (los tomados "resucitaban" y absorbían picks de
            # los rivales → supervivencia inflada).
            est.marcar(i, team, gp)
        if len(hechos) != ultimo:
            ultimo = len(hechos)
            nuevos = hechos[-3:]
            for gp, team, pid in nuevos:
                i = est.por_id.get(pid)
                nm = pool[i]['nombre'] if i is not None else f'id {pid}'
                print(f"  {gp:>3}. {nm}{'   <<< MÍO' if team == MI_TEAM_ID else ''}")
            prox = est.proximo_mio(hechos)
            if prox and prox - len(hechos) <= 3:
                idx, info = est.recomendar(hechos)
                pinta(est, idx, info, hechos)
            # CANDADO: ¿mi último pick quedó en MI roster?
            mios = [gp for gp, t, _ in hechos if t == MI_TEAM_ID]
            if mios and len(mios) != len(est.mis):
                print('🚨 DESCUADRE: la API no refleja mis picks como esperaba.')
        if listo:
            print('draft cerrado.'); return 0
        time.sleep(args.intervalo)


if __name__ == '__main__':
    raise SystemExit(main())
