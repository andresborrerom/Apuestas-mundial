#!/usr/bin/env python3
"""
LEMAITRE — "¿qué resultado nos conviene?" (análisis competitivo vs rivales).

Como nuestra planilla está LOCKED (se mandó completa antes del Mundial), para un
partido NO elegimos marcador: rooteamos por el resultado que más AMPLÍA nuestra
ventaja sobre los perseguidores, dado lo que ellos predijeron y los puntos de la
fase. Esta es la versión "a qué hacerle barra / a qué temerle".

(En pollas donde SÍ elegimos cada ronda —CSC, INGENIERO— la pregunta se invierte:
"qué marcador mandar" = EV-máximo bajo esas reglas. Eso va en sus carpetas.)

    python pollas/LEMAITRE/que_marcador.py --match 80          # por número de partido
    python pollas/LEMAITRE/que_marcador.py --match 80 --chasers 8

Lee la data validada (lemaitre_data.json). Refresca con puntos_lemaitre.py --refresh.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from pollas.LEMAITRE.puntos_lemaitre import calc_marcador, calc_todo, PTS

AQUI = os.path.dirname(os.path.abspath(__file__))


def analizar(BD, P, n_chasers=5, maxg=4):
    sc = calc_todo(BD)
    rank = sorted(sc.items(), key=lambda kv: -kv[1]['total'])
    yo = next(n for n, v in sc.items() if v['name'] == 'Pocho')
    chasers = [n for n, v in rank if v['name'] != 'Pocho'][:n_chasers]
    ph, pm, lab = BD['partido_phases'], BD['predictions_m'], BD['partido_labels']
    P = str(P)
    fase = ph[P]; t = lab.get(P, ['?', '?']); nuestro = pm[yo].get(P)
    pp = PTS[fase]
    print(f"P#{P}: {t[0]} vs {t[1]}  ·  fase {fase} (exacto {pp['e']}/gan {pp['g']}/parc {pp['p']})")
    print(f"  Nuestro pick (locked): {nuestro['e1']}-{nuestro['e2']}")
    print("  Perseguidores: " + ", ".join(
        f"{sc[n]['name'].split()[0]} {pm[n].get(P, {}).get('e1')}-{pm[n].get(P, {}).get('e2')}"
        for n in chasers))
    filas = []
    for g1 in range(maxg + 1):
        for g2 in range(maxg + 1):
            real = {'g1': g1, 'g2': g2}
            nos = calc_marcador(nuestro, real, fase)
            chas = [calc_marcador(pm[n].get(P), real, fase) for n in chasers]
            avg = sum(chas) / len(chas)
            filas.append((g1, g2, nos, avg, nos - avg))
    filas.sort(key=lambda x: -x[4])
    print("\n  TOP-3 resultados que más nos CONVIENEN (ganancia neta de ventaja):")
    for g1, g2, nos, avg, d in filas[:3]:
        print(f"    {g1}-{g2}:  nosotros +{nos:>2}  ·  perseguidores +{avg:4.1f}  ·  NETO {d:+.1f}")
    print("  PELIGRO — resultados donde nos sacan ventaja:")
    for g1, g2, nos, avg, d in [f for f in filas if f[4] < 0][-3:]:
        print(f"    {g1}-{g2}:  nosotros +{nos:>2}  ·  perseguidores +{avg:4.1f}  ·  NETO {d:+.1f}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--match", required=True, help="número de partido (73-104)")
    ap.add_argument("--chasers", type=int, default=5)
    args = ap.parse_args(argv)
    BD = json.load(open(os.path.join(AQUI, "lemaitre_data.json"), encoding="utf-8"))
    analizar(BD, args.match, args.chasers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
