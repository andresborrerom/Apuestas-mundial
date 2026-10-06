"""META-POLÍTICA — ¿basta con elegir UNA política, o conviene cambiar de
política según lo que quede en el tablero?

Pregunta de Andrés (28-ago): *"hacemos random forest a ver si elegir uno de
los 3 basta o existe forma de recomendar condicionado a lo que quede"*.

Cómo se responde, sin trampa:

  1. Se generan miles de DECISIONES reales del draft. En cada uno de mis
     turnos se anota el ESTADO (qué ronda es, qué tengo, qué queda vivo en
     cada posición, cuánto vale el mejor de cada una, cuántos picks faltan
     para mi próximo turno) y qué habría elegido cada política.
  2. Cada decisión se etiqueta con el resultado FINAL de esa temporada
     (dinero). Como la comparación es pareada, la diferencia entre políticas
     en el mismo estado es atribuible a la decisión.
  3. Se entrena un bosque aleatorio para predecir qué política gana en cada
     estado, con VALIDACIÓN CRUZADA POR TEMPORADA: se entrena en tres años y
     se prueba en el cuarto. Sin esto el bosque memoriza el año.
  4. 🚨 El veredicto no es la exactitud del clasificador: es si la política
     resultante GANA MÁS DINERO que la mejor política fija, medido con la
     misma comparación pareada. Un clasificador con 60% de acierto puede
     perder plata si se equivoca justo en las decisiones que pesan.

    python optimize/meta_politica.py --sims 120
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
from optimize.liga import (CFG, cargar_todo, universo, draftear, temporada,
                           OFE, IDP)
from optimize.politicas import POLITICAS, pol_motor, informe
from optimize.managers import personalidades

POSICIONES = list(OFE) + list(IDP) + ['DST', 'K']
CANDIDATAS = ['motor', 'motor2', 'regla', 'no-miope']


def rasgos(el, vivos, val, cnt, roster, gp, mis, rank, cfg=CFG):
    """El ESTADO del draft en un turno mío, como números."""
    porpos = defaultdict(list)
    for k in el:
        porpos[vivos[k][1]].append(val.get(k, 0))
    for p in porpos:
        porpos[p].sort(reverse=True)
    sig = next((p for p in mis if p > gp), None)
    x = [gp / (cfg.equipos * cfg.rondas),          # avance del draft
         len(roster) / cfg.rondas,                 # mis picks hechos
         ((sig - gp) / cfg.equipos) if sig else 0]  # cuánto falta a mi turno
    for p in POSICIONES:
        l = porpos.get(p, [])
        x += [l[0] if l else 0.0,                              # mejor vivo
              (l[0] - l[min(len(l) - 1, 5)]) if l else 0.0,    # caída a 6 más
              float(len(l)),                                   # profundidad
              float(cnt.get(p, 0))]                            # los que ya tengo
    return x


def recolectar(con, items, P, años, sims, cfg=CFG):
    """[(año, sim, turno, rasgos, {pol: elección}, {pol: dinero_final})]"""
    personas = personalidades()
    filas = []
    for año in años:
        jug, val, rank, pts = universo(con, año, items, P, cfg=cfg)
        # dinero final de cada política en cada semilla (pareado)
        dinero = {}
        for nom in CANDIDATAS:
            for s in range(sims):
                ros = draftear(jug, val, POLITICAS[nom], personas,
                               np.random.default_rng(1000 + s), rank, cfg=cfg)
                d, _, _, _, _ = temporada(ros, pts, np.random.default_rng(5000 + s),
                                          cfg=cfg)
                dinero[(nom, s)] = d[cfg.mi_asiento]
        # estados: se recorre el draft con la política motor y se anota el
        # estado en cada turno mío (el estado no depende de qué política se
        # evalúe después; es la foto de la sala).
        for s in range(sims):
            estados = []

            def espia(el, vivos, val_, cnt, roster, gp, mis, rank_, **kw):
                estados.append(rasgos(el, vivos, val_, cnt, roster, gp, mis,
                                      rank_, cfg))
                return pol_motor(el, vivos, val_, cnt, roster, gp, mis, rank_)

            draftear(jug, val, espia, personas, np.random.default_rng(1000 + s),
                     rank, cfg=cfg)
            for t, x in enumerate(estados):
                filas.append((año, s, t, x,
                              {nom: dinero[(nom, s)] for nom in CANDIDATAS}))
        print(f"  {año}: {sims} semillas · {len(estados)} turnos por draft",
              flush=True)
    return filas


def entrenar_y_evaluar(filas, años):
    from sklearn.ensemble import RandomForestClassifier
    print("\n" + "=" * 78)
    print("BOSQUE ALEATORIO — validación cruzada DEJANDO UNA TEMPORADA FUERA")
    print("=" * 78)
    aciertos, mejoras = [], []
    for prueba in años:
        tr = [f for f in filas if f[0] != prueba]
        te = [f for f in filas if f[0] == prueba]
        Xtr = np.array([f[3] for f in tr])
        ytr = np.array([max(f[4], key=f[4].get) for f in tr])
        Xte = np.array([f[3] for f in te])
        yte = np.array([max(f[4], key=f[4].get) for f in te])
        rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=20,
                                    random_state=0, n_jobs=-1)
        rf.fit(Xtr, ytr)
        pred = rf.predict(Xte)
        acc = (pred == yte).mean()
        # dinero que habría dado seguir la recomendación del bosque, contra la
        # MEJOR política fija medida en el mismo conjunto
        porsim = defaultdict(list)
        for f, p in zip(te, pred):
            porsim[f[1]].append((p, f[4]))
        meta_d, fijas = [], defaultdict(list)
        for s, lst in porsim.items():
            # la política que el bosque recomienda en la MAYORÍA de mis turnos
            votos = defaultdict(int)
            for p, _ in lst:
                votos[p] += 1
            elegida = max(votos, key=votos.get)
            meta_d.append(lst[0][1][elegida])
            for nom in CANDIDATAS:
                fijas[nom].append(lst[0][1][nom])
        mejor_fija = max(CANDIDATAS, key=lambda n: np.mean(fijas[n]))
        dif = np.mean(meta_d) - np.mean(fijas[mejor_fija])
        se = np.std(np.array(meta_d) - np.array(fijas[mejor_fija]), ddof=1) / \
            np.sqrt(len(meta_d))
        print(f"  prueba {prueba}: acierto {acc*100:>4.0f}% · meta ${np.mean(meta_d):>6.0f}"
              f" vs mejor fija ({mejor_fija}) ${np.mean(fijas[mejor_fija]):>6.0f}"
              f" → {dif:>+7.0f} ± {se:.0f}")
        aciertos.append(acc); mejoras.append(dif)
    print(f"\n  acierto medio {np.mean(aciertos)*100:.0f}% · "
          f"ganancia media sobre la mejor fija {np.mean(mejoras):+.0f} $")
    print(f"  VEREDICTO: {'✅ la meta-política aporta' if np.mean(mejoras) > 0 else '❌ NO aporta: basta con la mejor política fija'}")
    return np.mean(mejoras)


def por_anio_quien_gana(filas, años):
    """¿Qué política gana en cada semilla? Si la respuesta cambia por año y no
    por estado, ninguna meta-política condicionada al tablero puede servir."""
    from collections import Counter
    print("\n" + "=" * 78)
    print("¿QUÉ POLÍTICA GANA EN CADA SEMILLA? (% de semillas del año)")
    print("=" * 78)
    print(f"  {'año':6}" + ''.join(f"{c:>11}" for c in CANDIDATAS))
    for a in años:
        sem = {}
        for f in filas:
            if f[0] == a:
                sem[f[1]] = max(f[4], key=f[4].get)
        c = Counter(sem.values())
        print(f"  {a:<6}" + ''.join(f"{c.get(n,0)/max(1,len(sem))*100:>10.0f}%"
                                   for n in CANDIDATAS))


def meta_de_verdad(con, items, P, filas, años, sims, cfg=CFG):
    """El test RIGUROSO: no un voto de mayoría por temporada sino una política
    que CAMBIA TURNO A TURNO según lo que el bosque ve en el tablero.

    El voto de mayoría que evalúa `entrenar_y_evaluar` mide otra cosa: elegir
    UNA política por temporada. Aquí el bosque decide en cada uno de mis 18
    turnos, que es lo que Andrés preguntó de verdad.
    """
    from sklearn.ensemble import RandomForestClassifier
    personas = personalidades()
    print("\n" + "=" * 78)
    print("META-POLÍTICA DE VERDAD — el bosque decide en CADA turno")
    print("=" * 78)
    difs = []
    for prueba in años:
        tr = [f for f in filas if f[0] != prueba]
        rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=20,
                                    random_state=0, n_jobs=-1)
        rf.fit(np.array([f[3] for f in tr]),
               np.array([max(f[4], key=f[4].get) for f in tr]))
        jug, val, rank, pts = universo(con, prueba, items, P, cfg=cfg)

        def pol_meta(el, vivos, v, cnt, roster, gp, mis, rk, **kw):
            x = np.array([rasgos(el, vivos, v, cnt, roster, gp, mis, rk, cfg)])
            nom = rf.predict(x)[0]
            return POLITICAS[nom](el, vivos, v, cnt, roster, gp, mis, rk, **kw)

        meta_d, fijas = [], defaultdict(list)
        for s in range(sims):
            ros = draftear(jug, val, pol_meta, personas,
                           np.random.default_rng(1000 + s), rank, cfg=cfg)
            d, _, _, _, _ = temporada(ros, pts, np.random.default_rng(5000 + s),
                                      cfg=cfg)
            meta_d.append(d[cfg.mi_asiento])
        for f in filas:
            if f[0] == prueba and f[2] == 0:
                for n in CANDIDATAS:
                    fijas[n].append(f[4][n])
        mejor = max(CANDIDATAS, key=lambda n: np.mean(fijas[n]))
        n = min(len(meta_d), len(fijas['motor']))
        d = np.array(meta_d[:n]) - np.array(fijas['motor'][:n])
        se = d.std(ddof=1) / np.sqrt(n)
        print(f"  {prueba}: meta ${np.mean(meta_d):>6.0f} · motor "
              f"${np.mean(fijas['motor']):>6.0f} (Δ{d.mean():>+6.0f} ± {se:.0f})"
              f" · mejor fija del año: {mejor} ${np.mean(fijas[mejor]):>6.0f}")
        difs.append(d.mean())
    print(f"\n  ganancia media de la meta sobre el motor: {np.mean(difs):+.0f} $")
    print(f"  VEREDICTO: {'✅ aporta' if np.mean(difs) > 0 else '❌ NO aporta'}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sims', type=int, default=120)
    ap.add_argument('--anios', default='2021,2022,2023,2025')
    a = ap.parse_args()
    años = [int(x) for x in a.anios.split(',')]
    print('cargando temporadas reales bajo nuestras reglas...', flush=True)
    con, items, P = cargar_todo(2020, 2025)
    filas = recolectar(con, items, P, años, a.sims)
    print(f"\n{len(filas)} decisiones recolectadas")
    entrenar_y_evaluar(filas, años)
    por_anio_quien_gana(filas, años)
    meta_de_verdad(con, items, P, filas, años, a.sims)
