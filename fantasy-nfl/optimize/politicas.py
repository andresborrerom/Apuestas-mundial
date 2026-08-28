"""POLÍTICAS DE DRAFT y su comparación pareada sobre la liga completa.

Qué es una "política": la regla con la que YO decido en cada uno de mis 18
turnos. Todas ven el MISMO tablero; lo que cambia es cómo eligen.

  greedy    el de mayor VBD disponible. La referencia tonta.
  motor     ganancia marginal a UN turno: lo que vale tomarlo ahora menos lo
            que espero que quede en esa posición en mi próximo turno. Es la
            que usa el asistente en vivo.
  regla     la regla fija validada para 2026 (R1 el mejor WR; R2 un QB si el
            mejor QB vale al menos tanto como el mejor WR) y de ahí en
            adelante el motor.
  no-miope  para cada candidato simula TODO el resto del draft y se queda con
            el que termina con mejor roster. Mira hasta el final.
  meta      elige entre las anteriores según el estado del draft (lo entrena
            el bosque aleatorio de `meta_politica.py`).

Comparación PAREADA: la misma semilla genera el mismo comportamiento de los
15 rivales y el mismo calendario, así que la única diferencia entre dos
corridas es mi decisión. Sin esto el ruido de la sala se come cualquier señal.

Métrica principal: DINERO esperado, no puntos — como dijo Andrés, "no es al
que más puntos haga sino al que más partidos gane".

    python optimize/politicas.py --sims 200
"""
import argparse
import sys
from collections import defaultdict
from math import erf, sqrt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.liga import (CFG, cargar_todo, universo, draftear, temporada,
                           valor_roster, puntos_reales, OFE)
from optimize.managers import personalidades

SIGMA_SUP = 22.0        # dispersión efectiva de la sala para la supervivencia


def _surv(r, pick):
    """P(un jugador de rank de mercado r siga vivo en el pick global `pick`).

    Los no ofensivos tienen rank 10.000+: sobreviven con probabilidad 1, que
    es exactamente lo que se observa — la sala no los toca hasta el final."""
    return 0.5 * (1 + erf(((r - pick) / SIGMA_SUP) / sqrt(2)))


def _mejor_por_pos(el, vivos, val):
    d = defaultdict(list)
    for k in el:
        d[vivos[k][1]].append(k)
    for p in d:
        d[p].sort(key=lambda k: -val.get(k, 0))
    return d


def pol_greedy(el, vivos, val, cnt, roster, gp, mis, rank, **kw):
    return max(el, key=lambda k: val.get(k, 0))


def pol_motor(el, vivos, val, cnt, roster, gp, mis, rank, **kw):
    sig = next((p for p in mis if p > gp), None)
    if sig is None:
        return pol_greedy(el, vivos, val, cnt, roster, gp, mis, rank)
    mejor, mejor_g = None, -1e18
    for p, ks in _mejor_por_pos(el, vivos, val).items():
        ahora = val.get(ks[0], 0)
        luego, q = 0.0, 1.0
        for k in ks[:25]:
            s = _surv(rank[k], sig)
            luego += val.get(k, 0) * s * q
            q *= (1 - s)
            if q < 1e-3:
                break
        if ahora - luego > mejor_g:
            mejor, mejor_g = ks[0], ahora - luego
    return mejor


def pol_regla(el, vivos, val, cnt, roster, gp, mis, rank, **kw):
    k_turno = len([1 for p in mis if p < gp])
    d = _mejor_por_pos(el, vivos, val)
    if k_turno == 0 and d.get('WR'):
        return d['WR'][0]
    if k_turno == 1:
        qb, wr = d.get('QB'), d.get('WR')
        if qb and (not wr or val.get(qb[0], 0) >= val.get(wr[0], 0)):
            return qb[0]
        if wr:
            return wr[0]
    return pol_motor(el, vivos, val, cnt, roster, gp, mis, rank)


def pol_nomiope(el, vivos, val, cnt, roster, gp, mis, rank,
                rollouts=6, cand=4, cfg=CFG, **kw):
    """⚠️ La CONTINUACIÓN de cada simulación usa el MOTOR, no greedy: un
    rollout vale lo que valga su política de continuación."""
    if not [p for p in mis if p > gp]:
        return pol_greedy(el, vivos, val, cnt, roster, gp, mis, rank)
    cands = sorted(el, key=lambda k: -val.get(k, 0))[:cand]
    for p, ks in _mejor_por_pos(el, vivos, val).items():
        if ks and ks[0] not in cands:
            cands.append(ks[0])
    rng = np.random.default_rng(gp * 7919 + 13)
    # ⚡ El cuello de botella era simular a los rivales pick por pick con un
    # min() sobre ~400 jugadores: 288 picks × 400 = 115k comparaciones por
    # rollout (21.7s por draft, 500 veces más lento que las otras políticas).
    # Se sortea UNA vez el orden de preferencia de la sala por rollout y se
    # consume en orden. Mismo modelo, O(n log n) en vez de O(n²).
    claves = list(vivos)
    ranks = np.array([rank[k] for k in claves], dtype=float)
    ultimo = mis[-1] if mis else gp
    ordenes = []
    for _ in range(rollouts):
        ru = ranks + rng.normal(0, 20, size=len(claves))
        ordenes.append([claves[i] for i in np.argsort(ru)])
    mejor, mejor_v = None, -1e18
    for c in cands:
        tot = 0.0
        for it in range(rollouts):
            vv = dict(vivos); vv.pop(c, None)
            mi = list(roster) + [(c, vivos[c][1])]
            cc = defaultdict(int)
            for _k, _p in mi:
                cc[_p] += 1
            cola = ordenes[it]
            ptr = 0
            for pk in range(gp + 1, ultimo + 1):
                if not vv:
                    break
                if pk in mis:
                    faltan = sum(max(0, cfg.min_pos[p] - cc[p]) for p in cfg.min_pos)
                    quedan = cfg.rondas - len(mi)
                    ok = [k for k in vv
                          if cc[vv[k][1]] < cfg.max_pos.get(vv[k][1], 0)
                          and (faltan < quedan or cc[vv[k][1]] < cfg.min_pos.get(vv[k][1], 0))]
                    if not ok:
                        continue
                    k = pol_motor(ok, vv, val, cc, mi, pk, mis, rank)
                    mi.append((k, vv[k][1])); cc[vv[k][1]] += 1
                else:
                    while ptr < len(cola) and cola[ptr] not in vv:
                        ptr += 1
                    if ptr >= len(cola):
                        break
                    k = cola[ptr]; ptr += 1
                vv.pop(k, None)
            tot += valor_roster(mi, val, cfg=cfg)
        if tot / rollouts > mejor_v:
            mejor, mejor_v = c, tot / rollouts
    return mejor


def pol_motor2(el, vivos, val, cnt, roster, gp, mis, rank, cfg=CFG,
               estado=None, **kw):
    """MOTOR v2 — corrige el punto ciego del motor con los IDP/K/DST.

    El motor v1 estima la supervivencia sólo con el rank de mercado. Como los
    no ofensivos tienen rank 10.000+, les asigna supervivencia 1.0 SIEMPRE: es
    decir, cree que el mejor LB va a seguir ahí en la ronda 18. Falso. Con 5
    slots IDP × 16 equipos hay 80 picks defensivos obligatorios; cuando la sala
    entra en modo forzado, los buenos IDP vuelan en dos rondas.

    Aquí la supervivencia del no ofensivo se estima de la ARITMÉTICA de la
    sala: cuántos rivales pican antes de mi próximo turno y cuántos de ellos ya
    están obligados a cubrir casilla. Es la misma cuenta que hace que la sala
    los tome tarde — pero usada para saber CUÁNDO dejan de estar disponibles.
    """
    sig = next((p for p in mis if p > gp), None)
    if sig is None or estado is None:
        return pol_motor(el, vivos, val, cnt, roster, gp, mis, rank)
    forzados, huecos = estado          # picks forzados antes de mi turno y
    #                                    cuántos de esos van a cada posición
    d = _mejor_por_pos(el, vivos, val)
    mejor, mejor_g = None, -1e18
    for p, ks in d.items():
        ahora = val.get(ks[0], 0)
        if p in OFE:
            luego, q = 0.0, 1.0
            for k in ks[:25]:
                s = _surv(rank[k], sig)
                luego += val.get(k, 0) * s * q
                q *= (1 - s)
                if q < 1e-3:
                    break
        else:
            # se van los `n` mejores de esa posición antes de mi turno
            n = int(round(huecos.get(p, 0.0)))
            luego = val.get(ks[n], 0) if n < len(ks) else 0.0
        if ahora - luego > mejor_g:
            mejor, mejor_g = ks[0], ahora - luego
    return mejor


POLITICAS = {'greedy': pol_greedy, 'motor': pol_motor, 'regla': pol_regla,
             'no-miope': pol_nomiope, 'motor2': pol_motor2}


def correr(con, items, P, años, pols, sims, cfg=CFG, guardar=None):
    """Corrida pareada. Devuelve {(año,pol): {métrica: [valores]}}."""
    personas = personalidades()
    res = defaultdict(lambda: defaultdict(list))
    for año in años:
        jug, val, rank, pts = universo(con, año, items, P, cfg=cfg)
        print(f"\n=== {año} · universo {len(jug)} ===", flush=True)
        for nom in pols:
            fn = POLITICAS[nom]
            for s in range(sims):
                rng = np.random.default_rng(1000 + s)      # PAREADO
                ros = draftear(jug, val, fn, personas, rng, rank, cfg=cfg)
                dinero, puesto, pf, vic, camp = temporada(
                    ros, pts, np.random.default_rng(5000 + s), cfg=cfg)
                t = cfg.mi_asiento
                r = res[(año, nom)]
                r['dinero'].append(dinero[t]); r['puesto'].append(puesto[t])
                r['pf'].append(pf[t]); r['vic'].append(vic[t])
                r['campeon'].append(1 if camp == t else 0)
                if guardar is not None:
                    guardar.append((año, nom, s, ros[t], dinero[t], puesto[t], pf[t]))
            d = res[(año, nom)]
            print(f"  {nom:9} E[$]={np.mean(d['dinero']):>7.0f} · "
                  f"puesto {np.mean(d['puesto']):>4.1f} · vict {np.mean(d['vic']):>4.1f}"
                  f" · pf {np.mean(d['pf']):>6.0f} · top8 "
                  f"{np.mean([p <= 8 for p in d['puesto']])*100:>3.0f}% · campeón "
                  f"{np.mean(d['campeon'])*100:>3.0f}%", flush=True)
    return res


def informe(res, pols, años):
    print("\n" + "=" * 78)
    print("AGREGADO — dinero esperado por temporada")
    print("=" * 78)
    print(f"  {'política':10}{'E[$]':>9}{'sd':>8}{'p10':>8}{'p50':>8}{'p90':>8}"
          f"{'puesto':>8}{'top8':>7}{'campeón':>9}")
    agg = {}
    for nom in pols:
        d = defaultdict(list)
        for año in años:
            for k, v in res[(año, nom)].items():
                d[k] += v
        agg[nom] = d
        m = np.array(d['dinero'])
        print(f"  {nom:10}{m.mean():>9.0f}{m.std():>8.0f}"
              f"{np.percentile(m,10):>8.0f}{np.percentile(m,50):>8.0f}"
              f"{np.percentile(m,90):>8.0f}{np.mean(d['puesto']):>8.1f}"
              f"{np.mean([p<=8 for p in d['puesto']])*100:>6.0f}%"
              f"{np.mean(d['campeon'])*100:>8.1f}%")

    print("\n" + "=" * 78)
    print("COMPARACIÓN PAREADA (misma sala, mismo calendario: la única")
    print("diferencia es mi decisión). Δ$ por temporada, con su error.")
    print("=" * 78)
    base = pols[0]
    print(f"  {'':22}{'Δ$ medio':>11}{'error':>9}{'t':>7}{'% temporadas gana':>19}")
    for nom in pols[1:]:
        a = np.array(agg[base]['dinero']); b = np.array(agg[nom]['dinero'])
        d = b - a
        se = d.std(ddof=1) / np.sqrt(len(d))
        print(f"  {nom + ' vs ' + base:22}{d.mean():>+11.0f}{se:>9.0f}"
              f"{(d.mean()/se if se else 0):>7.1f}{np.mean(d > 0)*100:>18.0f}%")
    return agg


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=150)
    ap.add_argument('--anios', default='2021,2022,2023,2025')
    ap.add_argument('--politicas', default='greedy,motor,regla,no-miope')
    a = ap.parse_args()
    años = [int(x) for x in a.anios.split(',')]
    pols = a.politicas.split(',')
    print('cargando temporadas reales bajo nuestras reglas...', flush=True)
    con, items, P = cargar_todo(2020, 2025)
    res = correr(con, items, P, años, pols, a.sims)
    informe(res, pols, años)
