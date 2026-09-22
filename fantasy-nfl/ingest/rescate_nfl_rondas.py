"""Pasada 2: todas las rondas de cada draft (links leídos de cada página)."""
import re, time
from pathlib import Path
import requests
RAIZ=Path(__file__).resolve().parent.parent
RAW=RAIZ/'data'/'nfl_raw'
CK=(RAIZ/'data'/'nfl_cookies.txt').read_text().strip()
H={'Cookie':CK,'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
BASE='https://fantasy.nfl.com'
tot=0
for f in sorted(RAW.glob('h*_draftresults.html')):
    y=f.name[1:5]; t=f.read_text()
    links=sorted(set(re.findall(r'href="(/league/250007/history/'+y+r'/draftresults\?draftResultsDetail=(\d+)[^"]*)"',t)))
    for path,rnd in links:
        slug=f'h{y}_draft_r{int(rnd):02d}'
        out=RAW/f'{slug}.html'
        if out.exists(): continue
        r=requests.get(BASE+path.replace('&amp;','&'),headers=H,timeout=30)
        if r.status_code==200: out.write_text(r.text); tot+=1
        time.sleep(0.3)
    print(y,'rondas:',len(links))
print('nuevas páginas:',tot)
