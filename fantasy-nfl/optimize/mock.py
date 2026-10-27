"""MOCK DRAFT interactivo (entrenamiento para el 7-sep).

La sala juega con el modelo calibrado; en cada turno mío muestra el tablero
y ESPERA la decisión (a ciegas). Al registrarla, revela qué habría hecho el
motor y cuánto costó la diferencia — así se entrena el ojo, no la obediencia.

    python optimize/mock.py --nuevo [--seed 42] [--qbs 20]
    python optimize/mock.py --pick "Puka Nacua"
    python optimize/mock.py --auto            # el motor completa el resto
    python optimize/mock.py --resultado       # mi draft vs el motor (pareado)

El estado vive en data/mock_estado.json.
"""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.live_draft import Estado, MI_TEAM_ID
from optimize.plan_draft import preparar, calibrar
from optimize.sala import EQUIPOS, RONDAS, MI_PICK, orden_snake, valor_roster

RAIZ = Path(__file__).resolve().parent.parent
EST = RAIZ / 'data' / 'mock_estado.json'
SEC = orden_snake()


def nuevo(seed, qbs):
    pool = preparar()
    qb_b, pen = calibrar(pool, qbs, 10)
    return {'seed': seed, 'qb_bonus': qb_b, 'idp_pen': pen, 'qbs': qbs,
            'picks': [], 'mios': [], 'costos': []}


def montar(st):
    pool = preparar()
    est = Estado(pool, st['qb_bonus'], st['idp_pen'])
    for gp, idx in st['picks']:
        est.marcar(idx, MI_TEAM_ID if SEC[gp - 1] == MI_PICK - 1 else -1, gp)
    return pool, est


def avanzar(st, pool, est):
    """La sala juega hasta que sea mi turno (o se acabe el draft)."""
    rng = np.random.default_rng(st['seed'] + len(st['picks']))
    d = est.cargar_estado(rng)
    gp = len(st['picks']) + 1
    while gp <= EQUIPOS * RONDAS and SEC[gp - 1] != MI_PICK - 1:
        t = SEC[gp - 1]
        i = d.pick_rival(t, (gp - 1) // EQUIPOS + 1)
        if i is None:
            break
        d.tomar(t, i)
        est.marcar(i, -1, gp)
        st['picks'].append([gp, int(i)])
        gp += 1
    return gp


def tablero(pool, est, st, gp, n=10):
    from optimize.tablero import render, menu_futuro, render_menu
    hechos = [(g, 0, None) for g, _ in st['picks']]
    idx_motor, info = est.recomendar(hechos, sims=250)
    render(pool, est, info, idx_motor, n=n)
    sal, hor = menu_futuro(est, pool, hechos, sims=150)
    render_menu(sal, hor)
    return idx_motor, info


def tablero_viejo(pool, est, st, gp, n=12):
    hechos = [(g, 0, None) for g, _ in st['picks']]
    idx_motor, info = est.recomendar(hechos, sims=250)
    ronda = (gp - 1) // EQUIPOS + 1
    sig = info.get('sig')
    print(f"\n{'='*72}\n TU TURNO — pick {gp} (ronda {ronda}) · siguiente tuyo: {sig}"
          f" · faltan {sig - gp - 1 if sig else 0} picks de por medio")
    cnt = defaultdict(int)
    for i in est.mis:
        cnt[pool[i]['pos']] += 1
    print(f" tu roster: {dict(cnt) or 'vacío'}")
    faltan = {k: v for k, v in info.get('gaps', {}).items() if v}
    print(f" te faltan: {faltan} · ofensivos extra: {info.get('extra_ofe',0)}")
    print('-' * 72)
    print(f" {'jugador':24}{'pos':>4}{'VBD':>7}{'piso':>7}{'techo':>7}{'P(vive próximo)':>17}")
    surv = info.get('surv')
    vistos = defaultdict(int)
    mostrados = 0
    for g, p, i, ahora, luego, sv in sorted(
            [(pool[i]['vbd'], pool[i]['pos'], i, 0, 0, surv[i] if surv is not None else 0)
             for i in range(len(pool)) if i not in est.tomados], reverse=True):
        if vistos[p] >= 3 or mostrados >= n:
            continue
        vistos[p] += 1; mostrados += 1
        j = pool[i]
        print(f" {j['nombre'][:24]:24}{p:>4}{j['vbd']:>7.0f}{j['p10']:>7.0f}"
              f"{j['p90']:>7.0f}{sv*100:>16.0f}%")
    print('=' * 72)
    print(" ⏱️  45 segundos. Decide y registra con: --pick \"Nombre\"")
    return idx_motor, info


def registrar(st, pool, est, nombre, gp):
    i = est.buscar(nombre)
    if isinstance(i, list):
        print('ambiguo:', [pool[k]['nombre'] for k in i[:6]]); return None
    if i is None:
        print('no encontrado:', nombre); return None
    idx_motor, info = est.recomendar([(g, 0, None) for g, _ in st['picks']], sims=250)
    est.marcar(i, MI_TEAM_ID, gp)
    st['picks'].append([gp, int(i)])
    st['mios'].append(int(i))
    tuyo, motor = pool[i], pool[idx_motor]
    print(f"\n ✓ tomaste: {tuyo['nombre']} ({tuyo['pos']}) · VBD {tuyo['vbd']:.0f}"
          f" · piso {tuyo['p10']:.0f} / techo {tuyo['p90']:.0f}")
    if idx_motor == i:
        print(" 🎯 coincide con el motor.")
        st['costos'].append(0.0)
    else:
        d = motor['vbd'] - tuyo['vbd']
        print(f" 🤖 el motor tomaba: {motor['nombre']} ({motor['pos']}) ·"
              f" VBD {motor['vbd']:.0f}  → diferencia {d:+.0f} VBD")
        if info.get('regla'):
            print(f"    razón: {info['regla']}")
        st['costos'].append(float(d))
    return i


def resultado(st, pool, est):
    mio = {pool[i]['nombre']: pool[i] for i in st['mios']}
    v = valor_roster(mio)
    print(f"\n{'='*72}\n RESULTADO DEL MOCK")
    porpos = defaultdict(list)
    for i in st['mios']:
        porpos[pool[i]['pos']].append(pool[i])
    for p in ['QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'DST', 'K']:
        if porpos[p]:
            print(f"  {p:>4}: " + ' · '.join(f"{j['nombre']} ({j['vbd']:.0f})"
                                             for j in porpos[p]))
    print(f"\n  VALOR DEL TITULAR: {v:.0f} VBD")
    print(f"  referencia: la política validada promedia ~708 (peor caso 668)")
    if st['costos']:
        c = [x for x in st['costos'] if x]
        print(f"  picks distintos al motor: {len(c)}/{len(st['costos'])}"
              f" · costo acumulado {sum(st['costos']):.0f} VBD")
    print('=' * 72)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nuevo', action='store_true')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--qbs', type=int, default=20)
    ap.add_argument('--pick')
    ap.add_argument('--auto', action='store_true')
    ap.add_argument('--resultado', action='store_true')
    a = ap.parse_args()
    if a.nuevo:
        st = nuevo(a.seed, a.qbs)
    else:
        st = json.loads(EST.read_text())
    pool, est = montar(st)
    if a.resultado:
        resultado(st, pool, est); return 0
    if a.pick:
        gp = len(st['picks']) + 1
        if SEC[gp - 1] != MI_PICK - 1:
            print('no es tu turno'); return 1
        if registrar(st, pool, est, a.pick, gp) is None:
            return 1
    if a.auto:
        while len(st['picks']) < EQUIPOS * RONDAS:
            gp = avanzar(st, pool, est)
            if gp > EQUIPOS * RONDAS:
                break
            idx, info = est.recomendar([(g, 0, None) for g, _ in st['picks']], sims=200)
            est.marcar(idx, MI_TEAM_ID, gp)
            st['picks'].append([gp, int(idx)]); st['mios'].append(int(idx))
            st['costos'].append(0.0)
            print(f"  R{(gp-1)//EQUIPOS+1:>2} pick {gp:>3}: {pool[idx]['nombre']}"
                  f" ({pool[idx]['pos']})")
        EST.write_text(json.dumps(st))
        resultado(st, pool, est); return 0
    gp = avanzar(st, pool, est)
    EST.write_text(json.dumps(st))
    if gp > EQUIPOS * RONDAS:
        resultado(st, pool, est); return 0
    # qué pasó desde mi último turno
    ult = st['picks'][-6:]
    print('\n últimos picks de la sala:')
    for g, i in ult:
        quien = 'TÚ' if SEC[g - 1] == MI_PICK - 1 else f'eq{SEC[g-1]+1}'
        print(f"   {g:>3}. {pool[i]['nombre'][:24]:24} {pool[i]['pos']:>4}  [{quien}]")
    tablero(pool, est, st, gp)
    EST.write_text(json.dumps(st))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
