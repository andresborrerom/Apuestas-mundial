"""
Simulador económico de la polla: ¿cuántos cupos comprar para maximizar la
UTILIDAD esperada (premios ganados − costo de los cupos)?

Marco conceptual
----------------
La polla es de SUMA CERO: los premios (50/20/15/10/5% del recaudo) suman el
100% de lo recaudado, no hay comisión. Entonces, en agregado, la utilidad
esperada de todos los participantes es 0. Solo se gana si tu relleno es MEJOR
que el del participante promedio.

Nuestra ventaja (edge) viene de explotar las reglas: rellenar el marcador que
maximiza puntos esperados (p. ej. predecir 1 gol al débil en vez de 0). Un
rival "casual" que pone marcadores plausibles deja puntos sobre la mesa.

Qué hace este módulo (Monte Carlo)
----------------------------------
1. Simula muchos torneos: muestrea el marcador real de cada partido desde su
   distribución (sacada de las cuotas).
2. Genera entradas del "field" (rivales) y nuestras k entradas.
3. Suma puntos de cada entrada, las ordena, paga el top 5 (desempates por rifa
   = ruido aleatorio) y calcula nuestra utilidad.
4. Barre k = 1, 2, ... y recomienda el k* que maximiza la utilidad esperada.

Limitación honesta: por defecto modela la FASE DE GRUPOS (72 partidos, donde
ya hay cuotas). El ranking final real incluye eliminatorias (más puntos y más
ruido), que reordenan la tabla. Usa `ruido_extra` para estresar esa
incertidumbre. La extensión a eliminatorias requiere simular el cuadro.
"""

import numpy as np


PREMIOS = np.array([0.50, 0.20, 0.15, 0.10, 0.05])  # top 5


def _valor(g, cero, base):
    """Puntos por acertar los goles de un equipo que marcó g (vectorizable)."""
    g = np.asarray(g)
    return np.where(g == 0, cero, g + base)


def ev_grid(M, params, G=7):
    """Matriz EV[a,b] = puntos esperados de predecir el marcador (a,b).

    params = (pts_resultado, goles_cero, base_goles).
    """
    res, cero, base = params
    margH = M.sum(axis=1)
    margA = M.sum(axis=0)
    pL = float(np.tril(M, -1).sum())
    pD = float(np.trace(M))
    pV = float(np.triu(M, 1).sum())
    a = np.arange(G + 1)
    valH = _valor(a, cero, base) * margH[a]              # (G+1,)
    valA = _valor(a, cero, base) * margA[a]              # (G+1,)
    A, B = np.meshgrid(a, a, indexing="ij")
    psig = np.where(A > B, pL, np.where(A == B, pD, pV))  # (G+1,G+1)
    return res * psig + valH[:, None] + valA[None, :]


def fill_evmax(matrices, params, G=7):
    """Relleno EV-máximo por partido. Devuelve preds_h, preds_a (M,)."""
    ph, pa = [], []
    for M in matrices:
        EV = ev_grid(M, params, G)
        i, j = np.unravel_index(np.argmax(EV), EV.shape)
        ph.append(i); pa.append(j)
    return np.array(ph), np.array(pa)


def fill_evmax_y_segundo(matrices, params, G=7):
    """EV-máximo, 2º mejor relleno y la brecha de EV (1º-2º) por partido.

    Sirve para la perturbación MÍNIMA: cambiar al 2º solo donde la brecha es
    chica casi no cuesta puntos esperados pero descorrelaciona los cupos.
    """
    e_h, e_a, s_h, s_a, gap = [], [], [], [], []
    for M in matrices:
        EV = ev_grid(M, params, G).ravel()
        orden = np.argsort(-EV)
        b, s = orden[0], orden[1]
        e_h.append(b // (G + 1)); e_a.append(b % (G + 1))
        s_h.append(s // (G + 1)); s_a.append(s % (G + 1))
        gap.append(EV[b] - EV[s])
    return (np.array(e_h), np.array(e_a),
            np.array(s_h), np.array(s_a), np.array(gap))


def muestrear_torneos(matrices, S, rng, G=7):
    """Marcador real de cada partido en S torneos. Devuelve gh, ga (M,S)."""
    Mn = len(matrices)
    gh = np.empty((Mn, S), dtype=int)
    ga = np.empty((Mn, S), dtype=int)
    for m, M in enumerate(matrices):
        flat = M.ravel()
        flat = flat / flat.sum()
        idx = rng.choice(flat.size, size=S, p=flat)
        gh[m] = idx // M.shape[1]
        ga[m] = idx % M.shape[1]
    return gh, ga


def _puntos(preds_h, preds_a, gh, ga, params):
    """Puntos totales por entrada. preds (E,M); gh,ga (M,S) -> (E,S)."""
    res, cero, base = params
    E = preds_h.shape[0]
    S = gh.shape[1]
    total = np.zeros((E, S))
    for m in range(gh.shape[0]):
        i_s = gh[m]; j_s = ga[m]                  # (S,)
        a_e = preds_h[:, m]; b_e = preds_a[:, m]  # (E,)
        val_i = _valor(i_s, cero, base)           # (S,)
        val_j = _valor(j_s, cero, base)
        total += (a_e[:, None] == i_s[None, :]) * val_i[None, :]
        total += (b_e[:, None] == j_s[None, :]) * val_j[None, :]
        sgn_e = np.sign(a_e - b_e)
        sgn_s = np.sign(i_s - j_s)
        total += res * (sgn_e[:, None] == sgn_s[None, :])
    return total


def generar_field(matrices, E, skill, params, rng, G=7, concentracion=3.0):
    """Genera E entradas de rivales.

    Cada partido, el rival con prob `skill` juega EV-máximo (rival "sharp");
    si no, juega "casual": muestrea un marcador de la distribución ELEVADA a
    `concentracion`. Concentración >1 lo acerca al marcador modal (humano que
    le pone al favorito y acierta el resultado seguido, pero no afina los goles
    como el EV-máximo). concentracion=1 => muestreo crudo; alta => casi modal.
    skill=1 => rivales óptimos (edge ~ 0).
    """
    Mn = len(matrices)
    ph = np.empty((E, Mn), dtype=int)
    pa = np.empty((E, Mn), dtype=int)
    evmax_h, evmax_a = fill_evmax(matrices, params, G)
    for m, M in enumerate(matrices):
        flat = M.ravel() ** concentracion
        flat = flat / flat.sum()
        idx = rng.choice(flat.size, size=E, p=flat)
        casual_h = idx // M.shape[1]
        casual_a = idx % M.shape[1]
        usar_evmax = rng.random(E) < skill
        ph[:, m] = np.where(usar_evmax, evmax_h[m], casual_h)
        pa[:, m] = np.where(usar_evmax, evmax_a[m], casual_a)
    return ph, pa


def generar_nuestras(matrices, k, params, estrategia="diversificada",
                     T=0.6, rng=None, G=7, n_swaps=8, pool=25):
    """Genera nuestras k entradas.

    - "evmax": las k idénticas al relleno EV-máximo (media máxima, correlación
      total: los k cupos suben y bajan juntos).
    - "perturbada": cupo 0 = EV-máximo (ancla); cada cupo extra copia el
      EV-máximo pero CAMBIA al 2º mejor relleno en `n_swaps` partidos elegidos
      entre los `pool` más "empatados" (menor brecha de EV). Aleatoriedad MÍNIMA
      que descorrelaciona sin alejarse del modelo.
    - "diversificada": cada cupo extra muestrea por partido desde softmax(EV/T)
      (más diversidad, más pérdida de media; referencia de "demasiado azar").
    """
    Mn = len(matrices)
    ph = np.empty((k, Mn), dtype=int)
    pa = np.empty((k, Mn), dtype=int)
    evmax_h, evmax_a = fill_evmax(matrices, params, G)

    # El cupo 0 SIEMPRE es el relleno EV-máximo (ancla); garantiza que con más
    # cupos nunca empeoramos respecto a tener uno solo.
    ph[0] = evmax_h
    pa[0] = evmax_a
    if k == 1:
        return ph, pa

    if estrategia == "evmax":
        for c in range(1, k):
            ph[c] = evmax_h; pa[c] = evmax_a
        return ph, pa

    if estrategia == "perturbada":
        e_h, e_a, s_h, s_a, gap = fill_evmax_y_segundo(matrices, params, G)
        # candidatos a perturbar: los `pool` partidos con menor brecha de EV
        candidatos = np.argsort(gap)[:min(pool, Mn)]
        for c in range(1, k):
            ph[c] = e_h; pa[c] = e_a
            swaps = rng.choice(candidatos, size=min(n_swaps, len(candidatos)),
                               replace=False)
            ph[c, swaps] = s_h[swaps]
            pa[c, swaps] = s_a[swaps]
        return ph, pa

    # "diversificada": los cupos 1..k-1 muestrean por partido desde softmax(EV/T)
    for m, M in enumerate(matrices):
        EV = ev_grid(M, params, G).ravel()
        w = np.exp((EV - EV.max()) / T)
        w /= w.sum()
        idx = rng.choice(EV.size, size=k - 1, p=w)
        ph[1:, m] = idx // (G + 1)
        pa[1:, m] = idx % (G + 1)
    return ph, pa


def generar_field_mix(matrices, E, pesos, params, rng, G=7, conc_hum=4.0):
    """Field como MEZCLA de arquetipos de rival (más realista y testeable).

    pesos = {"opt":w1, "cal":w2, "hum":w3} (se normalizan). Cada rival es de UN
    arquetipo durante todo el torneo (una persona tiene un estilo consistente):
      - "opt": juega EV-máximo (rival sharp, como nosotros).
      - "cal": muestrea el marcador de M (calibrado a la prob. de ocurrencia;
               la idea del usuario / distribución implícita del mercado).
      - "hum": muestrea de M^conc_hum (concentrado cerca del marcador modal;
               humano que pone el marcador "obvio" y casi nunca gol al débil).
    """
    Mn = len(matrices)
    ph = np.empty((E, Mn), dtype=int)
    pa = np.empty((E, Mn), dtype=int)
    arche = ["opt", "cal", "hum"]
    w = np.array([max(0.0, pesos.get(a, 0.0)) for a in arche], float)
    w = w / w.sum()
    asign = rng.choice(3, size=E, p=w)
    evmax_h, evmax_a = fill_evmax(matrices, params, G)
    for m, M in enumerate(matrices):
        ncol = M.shape[1]
        flat = M.ravel(); flat = flat / flat.sum()
        flath = M.ravel() ** conc_hum; flath = flath / flath.sum()
        opt = asign == 0
        ph[opt, m] = evmax_h[m]; pa[opt, m] = evmax_a[m]
        for arq, fl in ((1, flat), (2, flath)):
            idx = np.where(asign == arq)[0]
            if len(idx):
                s = rng.choice(fl.size, size=len(idx), p=fl)
                ph[idx, m] = s // ncol; pa[idx, m] = s % ncol
    return ph, pa


def simular_utilidad(matrices, k, N, params, field_skill=0.3,
                     estrategia="diversificada", T=0.6, precio=100_000,
                     S=2000, ruido_extra=0.0, semilla=None, G=7,
                     concentracion=3.0, n_swaps=8, pool=25, fills=None,
                     field=None):
    """Utilidad esperada (premio − costo) y métricas de COLA de comprar k cupos.

    N = total de cupos en la polla (incluye los nuestros). pot = N*precio.
    field_skill = qué tan buenos son los rivales (0 casual, 1 óptimos).
    ruido_extra = ruido añadido al puntaje total (emula reordenamiento por
                  eliminatorias). 0 = solo grupos.
    fills = (ph, pa) rellenos nuestros explícitos (para probar estrategias
            hechas a mano); si se pasa, k se infiere de su forma.
    """
    rng = np.random.default_rng(semilla)
    if fills is not None:
        oh, oa = fills
        k = oh.shape[0]
    Ef = N - k
    gh, ga = muestrear_torneos(matrices, S, rng, G)

    if field is not None:   # mezcla de arquetipos (modelo de rivales realista)
        fh, fa = generar_field_mix(matrices, Ef, field, params, rng, G)
    else:
        fh, fa = generar_field(matrices, Ef, field_skill, params, rng, G, concentracion)
    if fills is None:
        oh, oa = generar_nuestras(matrices, k, params, estrategia, T, rng, G,
                                  n_swaps=n_swaps, pool=pool)

    pts_field = _puntos(fh, fa, gh, ga, params)   # (Ef,S)
    pts_ours = _puntos(oh, oa, gh, ga, params)     # (k,S)
    todo = np.vstack([pts_field, pts_ours])        # (N,S); nuestras = filas Ef..N-1

    if ruido_extra > 0:
        todo = todo + rng.normal(0, ruido_extra, size=todo.shape)
    # desempate por rifa: jitter aleatorio minúsculo
    todo = todo + rng.random(todo.shape) * 1e-6

    pot = N * precio
    premio_val = PREMIOS * pot
    orden = np.argsort(-todo, axis=0)              # (N,S)
    top5 = orden[:5, :]                            # (5,S)
    es_nuestra = top5 >= Ef                         # bool (5,S)
    ganancia = (es_nuestra * premio_val[:, None]).sum(axis=0)  # (S,)
    utilidad = ganancia - k * precio

    # métricas de cola: mejor puesto entre nuestros cupos por torneo
    rangos = np.argsort(orden, axis=0)             # rango (0=1º) de cada entrada
    mejor_rango = rangos[Ef:, :].min(axis=0)        # (S,)

    return {
        "k": k,
        "utilidad_media": float(utilidad.mean()),
        "utilidad_p50": float(np.median(utilidad)),
        "utilidad_p10": float(np.percentile(utilidad, 10)),
        "utilidad_p90": float(np.percentile(utilidad, 90)),
        "prob_algun_premio": float((ganancia > 0).mean()),
        "prob_primera": float((mejor_rango == 0).mean()),
        "prob_top3": float((mejor_rango <= 2).mean()),
        "ganancia_media": float(ganancia.mean()),
        "costo": k * precio,
        "slots_top5_medio": float(es_nuestra.sum(axis=0).mean()),
    }


def recomendar_cupos(matrices, N, params, max_cupos=15, **kw):
    """Barre k=1..max_cupos y devuelve la tabla + el k* óptimo."""
    filas = [simular_utilidad(matrices, k, N, params, **kw)
             for k in range(1, max_cupos + 1)]
    mejor = max(filas, key=lambda r: r["utilidad_media"])
    return {"tabla": filas, "k_optimo": mejor["k"], "mejor": mejor}
