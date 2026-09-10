"""Parser de la historia rescatada de fantasy.nfl.com (liga vieja 250007).

Fuente: tarball data/nfl_raw_250007_rescate_2026-08-10.tar.gz (943 páginas,
2010-2025) bajado con rescate_nfl*.py. Extrae:
  - drafts por ronda (h{y}_draft_r01..r17): season, ronda, pick, jugador,
    pos, equipo NFL, teamId, equipo fantasy, manager
  - standings finales (h{y}_standings_...final): puesto, equipo, manager,
    récord y puntos de temporada regular

Uso:
    python fantasy-nfl/ingest/parse_historia.py <dir_extraido>
Escribe data/historia_drafts.csv y data/historia_standings.csv.
"""
import csv, html as H, re, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

RX_PICK = re.compile(
    r'<span class="count">(\d+)\.</span>.*?'
    r'playerNameId-(\d+)[^>]*>([^<]+)</a>\s*<em>([^<]*)</em>.*?'
    r'class="teamName teamId-(\d+)">([^<]*)</a><ul>(.*?)</ul>', re.S)
RX_RONDA = re.compile(r'Round (\d+): Players Drafted')
RX_MGR = re.compile(r'<li[^>]*>([^<]*)</li>')
RX_PLACE = re.compile(
    r'<li class="place-(\d+)[^"]*"><div class="place">.*?'
    r'class="teamName teamId-(\d+)">([^<]*)</a>((?:<em>.*?</em>)*)', re.S)
RX_EM = re.compile(r'<em>(.*?)</em>')


def parse_drafts(src: Path):
    filas = []
    for y in range(2010, 2026):
        paginas = sorted(src.glob(f'h{y}_draft_r[0-9][0-9].html'))
        for pg in paginas:
            if pg.name.endswith('_r00.html'):
                continue                      # r00 = "todas las rondas" (duplicaría)
            txt = pg.read_text(errors='replace')
            m = RX_RONDA.search(txt)
            if not m:
                continue                      # ronda inexistente ese año
            ronda = int(m.group(1))
            for pk in RX_PICK.finditer(txt):
                cnt, pid, nombre, posteam, tid, tname, mgrs = pk.groups()
                pt = [s.strip() for s in posteam.split(' - ')]
                pos = pt[0] if pt else ''
                nfl = pt[1] if len(pt) > 1 else ''
                mgr = ' & '.join(s.strip() for s in RX_MGR.findall(mgrs) if s.strip())
                filas.append(dict(season=y, ronda=ronda, pick=int(cnt),
                                  jugador=H.unescape(nombre).strip(), pos=pos, nfl=nfl,
                                  team_id=int(tid), equipo=H.unescape(tname).strip(),
                                  manager=H.unescape(mgr)))
    return filas


def parse_standings(src: Path):
    filas = []
    for y in range(2010, 2026):
        f = src / f'h{y}_standings_historyStandingsType_final.html'
        if not f.exists():
            continue
        txt = f.read_text(errors='replace')
        for m in RX_PLACE.finditer(txt):
            place, tid, tname, ems = m.groups()
            ems = [H.unescape(e).strip() for e in RX_EM.findall(ems)]
            mgr = ems[0] if ems else ''
            rec = next((e for e in ems if 'Reg. Season' in e), '')
            rm = re.search(r'(\d+)-(\d+)-(\d+), ([\d,.]+) Points', rec)
            filas.append(dict(season=y, puesto=int(place), team_id=int(tid),
                              equipo=H.unescape(tname).strip(), manager=mgr,
                              w=int(rm.group(1)) if rm else None,
                              l=int(rm.group(2)) if rm else None,
                              pf=float(rm.group(4).replace(',', '')) if rm else None))
    return filas


def main():
    src = Path(sys.argv[1])
    drafts, stands = parse_drafts(src), parse_standings(src)
    for nombre, filas in [('historia_drafts.csv', drafts), ('historia_standings.csv', stands)]:
        out = RAIZ / 'data' / nombre
        with open(out, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader(); w.writerows(filas)
        print(f'{out.name}: {len(filas)} filas')
    # sanity: picks por temporada y managers únicos
    from collections import Counter
    por_y = Counter(r['season'] for r in drafts)
    print('picks/temporada:', dict(sorted(por_y.items())))
    mgrs = sorted({r['manager'] for r in drafts})
    print(f'managers únicos ({len(mgrs)}):', mgrs)


if __name__ == '__main__':
    main()
