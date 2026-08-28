"""Perfil INDIVIDUAL de cada rival por asiento del draft.

Antes el simulador trataba a los 15 rivales como clones (solo se calibraba
el agregado). Aquí cada asiento recibe su propia avidez de QB e IDP, medida
en las temporadas comparables — SOLO las que tenían el slot OP: 2021, 2022,
2023 y 2025 (2024 no lo tenía y la conducta cambia por completo).

Peso w_s: mezcla de (qué tan temprano toma su 1er QB) y (cuántos QB toma en
R1-R3), relativo a la sala, con ENCOGIMIENTO n/(n+2) hacia 1 para los que
tienen pocas temporadas. Se normaliza a media 1 para no alterar la
calibración agregada (~20 QBs en R1-R3): redistribuye, no infla.
"""
import csv
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
OP_ANOS = (2021, 2022, 2023, 2025)

# Asiento del sorteo (27-ago) -> manager histórico. None = sin historia.
ASIENTOS = ['Camilo', 'JHJ', 'Nicholas', 'Luis Carlos', None,          # 1-5 (5=yo)
            'Diego', 'Santiago, Steve', 'Sergio', 'Brian', 'Rodrigo',  # 6-10
            'Gabriel', 'Santiago, Steve', 'Santiago E', 'Kike',        # 11-14
            'Big Daddy James', None]                                   # 15-16


def perfiles():
    D = list(csv.DictReader(open(RAIZ / 'data' / 'historia_drafts.csv')))
    for r in D:
        r['season'] = int(r['season']); r['ronda'] = int(r['ronda'])
    st = {}
    for m in {r['manager'] for r in D if r['season'] in OP_ANOS}:
        q1, q3, i1 = [], [], []
        for y in OP_ANOS:
            dd = [r for r in D if r['season'] == y and r['manager'] == m]
            if not dd:
                continue
            q = [r['ronda'] for r in dd if r['pos'] == 'QB']
            if q:
                q1.append(min(q)); q3.append(sum(1 for x in q if x <= 3))
            i = [r['ronda'] for r in dd if r['pos'] in ('DL', 'LB', 'DB')]
            if i:
                i1.append(min(i))
        if q1:
            f = lambda v: sum(v) / len(v) if v else None
            st[m] = dict(n=len(q1), qb1=f(q1), qb3=f(q3), idp1=f(i1))
    return st


def pesos():
    """(w_qb, w_idp) por asiento 0..15. 1.0 = como el promedio de la sala."""
    st = perfiles()
    m_qb1 = sum(s['qb1'] for s in st.values()) / len(st)
    m_qb3 = sum(s['qb3'] for s in st.values()) / len(st)
    idps = [s['idp1'] for s in st.values() if s['idp1']]
    m_idp = sum(idps) / len(idps)
    wq, wi = [], []
    for m in ASIENTOS:
        s = st.get(m)
        if not s:
            wq.append(1.0); wi.append(1.0); continue
        w = 0.5 * (m_qb1 / s['qb1']) + 0.5 * (s['qb3'] / m_qb3 if m_qb3 else 1)
        k = s['n'] / (s['n'] + 2)                       # encogimiento
        wq.append(1 + (w - 1) * k)
        # IDP: toma antes que la sala -> penalización MENOR
        v = (s['idp1'] / m_idp) if s['idp1'] else 1.0
        wi.append(1 + (v - 1) * k)
    # normalizar a media 1 sobre los rivales (excluye mi asiento)
    idx = [i for i in range(len(ASIENTOS)) if i != 4]
    mq = sum(wq[i] for i in idx) / len(idx)
    mi = sum(wi[i] for i in idx) / len(idx)
    return [w / mq for w in wq], [w / mi for w in wi]


if __name__ == '__main__':
    from optimize.sala import ORDEN
    wq, wi = pesos()
    print(f"{'#':>3} {'asiento':12}{'manager':18}{'w_QB':>7}{'w_IDP':>7}")
    for i, (nom, m) in enumerate(zip(ORDEN, ASIENTOS)):
        print(f"{i+1:>3} {nom:12}{str(m or '—'):18}{wq[i]:>7.2f}{wi[i]:>7.2f}")
