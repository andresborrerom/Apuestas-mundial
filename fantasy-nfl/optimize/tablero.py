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
