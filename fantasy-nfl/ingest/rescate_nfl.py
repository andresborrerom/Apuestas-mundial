"""RESCATE historia liga NFL — data-driven: los links se LEEN de cada página."""
import re, time, sys
from pathlib import Path
import requests

RAIZ=Path(__file__).resolve().parent.parent
RAW=RAIZ/'data'/'nfl_raw'; RAW.mkdir(parents=True,exist_ok=True)
CK=(RAIZ/'data'/'nfl_cookies.txt').read_text().strip()
H={'Cookie':CK,'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
BASE='https://fantasy.nfl.com'; LID=sys.argv[1] if len(sys.argv)>1 else '250007'
bajados=set()
def get(path,slug):
    f=RAW/f'{slug}.html'
    if slug in bajados or f.exists(): return f.read_text() if f.exists() else ''
    r=requests.get(BASE+path,headers=H,timeout=30)
    if r.status_code==200:
        (RAW/f'{slug}.html').write_text(r.text); bajados.add(slug)
        time.sleep(0.35); return r.text
    print('  ✗',r.status_code,path); time.sleep(0.35); return ''

hist=get(f'/league/{LID}/history','history_index') or open(RAW/'history_index.html').read()
years=sorted(set(re.findall(rf'/league/{LID}/history/(\d{{4}})/standings',hist)))
print('temporadas:',years)
for y in years:
    st=get(f'/league/{LID}/history/{y}/standings',f'h{y}_standings')
    if not st: continue
    # links propios de ese año, leídos de la página (no adivinados)
    sub=sorted(set(re.findall(rf'href="(/league/{LID}/history/{y}/[^"#]*)"',st)))
    extra=0
    for s in sub:
        slug=f"h{y}_"+re.sub(r'[^a-zA-Z0-9]+','_',s.split(f'/history/{y}/')[1])[:60]
        if get(s,slug): extra+=1
    # draft results: probar el path conocido aunque no esté linkeado
    dr=get(f'/league/{LID}/history/{y}/draftresults',f'h{y}_draftresults')
    # schedule semana a semana si existe la vista
    sc=get(f'/league/{LID}/history/{y}/schedule',f'h{y}_schedule')
    weeks=sorted(set(re.findall(r'scheduleDetail=(\d+)',sc or '')))
    for w in weeks:
        get(f'/league/{LID}/history/{y}/schedule?scheduleDetail={w}&scheduleType=week&standingsTab=schedule',f'h{y}_sched_w{int(w):02d}')
    print(f'{y}: standings ✓ · sublinks {extra} · draft {"✓" if dr else "—"} · semanas {len(weeks)}')
print('\nTOTAL ARCHIVOS:',len(list(RAW.glob("*.html"))))
