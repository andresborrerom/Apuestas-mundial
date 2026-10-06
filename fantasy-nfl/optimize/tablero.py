"""TABLERO de decisión — el que se usa en vivo y en los mocks.

Ordena por lo que decide el motor (GANANCIA marginal = VBD ahora − VBD
esperado de esa posición en mi próximo turno), no por VBD bruto, y explica
cada fila:

  RAZÓN  — por qué está donde está (se va / no se mueve / cubre slot /
           último de su tier).
  NOTICIA— hechos nuestros calculados (cuota de backfield, targets,
           tacleadas, juegos perdidos) + cita corta de ESPN.

La regla validada (R1 mejor WR · R2 QB si VBD≥110 si no WR) sigue mandando
en los dos primeros picks; si el motor discrepa se muestra.
"""
import csv, json
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_NOTAS = None


def notas():
    global _NOTAS
    if _NOTAS is None:
        f = RAIZ / 'data' / 'notas.json'
        _NOTAS = json.load(open(f)) if f.exists() else {}
    return _NOTAS


def tiers_por_pos(pool, tomados):
    """Tier de cada disponible dentro de su posición (barranco > max(8,10%))."""
    porpos = defaultdict(list)
    for i, j in enumerate(pool):
        if i not in tomados:
            porpos[j['pos']].append(i)
    tier, ultimo = {}, {}
    for p, idxs in porpos.items():
        idxs.sort(key=lambda i: -pool[i]['vbd'])
        t, prev = 1, None
        for k, i in enumerate(idxs):
            v = pool[i]['vbd']
            if prev is not None and (prev - v) > max(8, 0.10 * max(prev, 1)):
                t += 1
            tier[i] = t
            prev = v
        # ¿es el último de su tier?
        for k, i in enumerate(idxs):
            sig = idxs[k + 1] if k + 1 < len(idxs) else None
            ultimo[i] = sig is None or tier[sig] != tier[i]
    return tier, ultimo


def razon(pool, i, surv, gap, gan, tier, ultimo, sig_pick):
    j = pool[i]
    s = surv[i]
    partes = []
    if gap.get(j['pos'], 0) > 0:
        partes.append(f"cubre {j['pos']} vacío")
    if s < 0.35:
        partes.append(f"SE VA: {s*100:.0f}% llega al {sig_pick}")
    elif s > 0.85:
        partes.append(f"no se mueve ({s*100:.0f}%): puedes esperar")
    else:
        partes.append(f"{s*100:.0f}% de llegar al {sig_pick}")
    if ultimo.get(i) and tier.get(i, 9) <= 3:
        partes.append(f"ÚLTIMO del tier {tier[i]} en {j['pos']}")
    partes.append(f"ganancia {gan:+.0f}")
    return ' · '.join(partes)


def render(pool, est, info, idx_reco, n=10, ancho_noticia=96):
    """Imprime el tablero completo. `info` viene de Estado.recomendar()."""
    surv = info['surv']
    gap = {k: v for k, v in info.get('gaps', {}).items()}
    sig = info.get('sig', '—')
    tier, ultimo = tiers_por_pos(pool, est.tomados)
    N = notas()
    filas = sorted(info['tabla'], reverse=True)[:n]
    print(f"\n{'='*100}")
    print(f" PICK {info['mi_pick']} (ronda {(info['mi_pick']-1)//16+1})"
          f"  ·  siguiente turno tuyo: {sig}"
          f"  ·  te faltan: { {k:v for k,v in gap.items() if v} }")
    print('=' * 100)
    for k, (g, p, i, ahora, luego, sv) in enumerate(filas, 1):
        j = pool[i]
        marca = '➡️ ' if i == idx_reco else f'{k:>2}.'
        print(f"{marca} {j['nombre'][:22]:22} {p:>3}  vbd {j['vbd']:>4.0f} "
              f"piso {j['p10']:>3.0f}/techo {j['p90']:>3.0f}")
        print(f"     ↳ {razon(pool, i, surv, gap, g, tier, ultimo, sig)}")
        nt = N.get(j['nombre'])
        if nt:
            if nt['hechos']:
                print(f"     · {nt['hechos']}")
            if nt['espn']:
                print(f"     · ESPN: {nt['espn'][:ancho_noticia]}")
    if info.get('regla'):
        print(f"\n REGLA VALIDADA: {info['regla']}")
        m = info.get('motor')
        if m is not None and m != idx_reco:
            print(f" (el motor miope preferiría {pool[m]['nombre']})")
    print('=' * 100)


def menu_futuro(est, pool, hechos, sims=200, seed=3):
    """Lo que Andrés pidió: no 'jugador vs reemplazo gratis', sino QUÉ TENGO
    EN CADA POSICIÓN EN MIS PRÓXIMOS TURNOS.

    Simula la sala hacia adelante (yo tomando greedy en mis turnos, para que
    el pool se agote de forma realista) y devuelve, por posición, el MEJOR VBD
    esperado en el turno actual y en los dos siguientes.
    """
    import numpy as np
    from optimize.sala import EQUIPOS, RONDAS
    n = len(hechos)
    mios = [p for p in est.mis_picks if p > n]
    if not mios:
        return {}, []
    horizontes = mios[:3]
    acc = {h: defaultdict(list) for h in horizontes}
    for s in range(sims):
        rng = np.random.default_rng(seed + s)
        d = est.cargar_estado(rng)
        for gp in range(n + 1, min(horizontes[-1] + 1, EQUIPOS * RONDAS + 1)):
            t = est.secuencia[gp - 1]
            ronda = (gp - 1) // EQUIPOS + 1
            if gp in acc:                       # es turno mío: fotografía
                mejor = defaultdict(float)
                for i in range(len(pool)):
                    if d.alive[i]:
                        p = d.pos[i]
                        if d.vbd[i] > mejor[p]:
                            mejor[p] = d.vbd[i]
                for p, v in mejor.items():
                    acc[gp][p].append(v)
            if t == est.mis_picks[0] - 1 or gp in acc:
                cand = d.candidatos(est.secuencia[gp - 1], ronda,
                                    d.forzado(est.secuencia[gp - 1]), limite=200)
                i = int(max(cand, key=lambda i: d.vbd[i])) if cand else None
            else:
                i = d.pick_rival(t, ronda)
            if i is not None:
                d.tomar(t, i)
    salida = {}
    for p in ('QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'DST', 'K'):
        fila = []
        for h in horizontes:
            v = acc[h].get(p)
            fila.append(sum(v) / len(v) if v else 0.0)
        if any(fila):
            salida[p] = fila
    return salida, horizontes


def render_menu(salida, horizontes):
    print(f"\n QUÉ TENGO EN CADA POSICIÓN, TURNO POR TURNO (mejor VBD esperado)")
    print(f" {'pos':>4}" + ''.join(f"{'pick '+str(h):>12}" for h in horizontes)
          + f"{'caída 1º→2º':>14}{'lectura':>0}")
    orden = sorted(salida.items(), key=lambda kv: -(kv[1][0] - (kv[1][1] if len(kv[1]) > 1 else 0)))
    for p, fila in orden:
        caida = fila[0] - fila[1] if len(fila) > 1 else 0
        if caida > 40:
            lec = '  ⬅️ AQUÍ SE DECIDE: se desploma'
        elif caida > 15:
            lec = '  cae fuerte'
        elif caida < 5:
            lec = '  intacta: puedes esperar'
        else:
            lec = ''
        print(f" {p:>4}" + ''.join(f"{v:>12.0f}" for v in fila)
              + f"{caida:>14.0f}{lec}")
