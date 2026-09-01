# CHECKLIST DEL 7-SEP (draft 7:00 pm Bogotá · pick 5 · 45 s)

## Montaje en el computador de Andrés (una vez, ANTES del día)
```bash
git clone <repo> && cd Apuestas-mundial/fantasy-nfl
pip install requests numpy
gunzip -k data/espn_applied_2025.json.gz          # corpus ESPN (ADP + proyecciones)
# crear fantasy-nfl/.env con: ESPN_LEAGUE_ID / ESPN_S2 / ESPN_SWID
python optimize/tablero_vivo.py --demo             # ensayo: http://localhost:8787
```
✅ El montaje está COMPLETO solo cuando la demo corre en TU máquina con los
tres candados verdes — ese es el recibo. (Regla de los $4.56M: nada está
"listo" hasta verificar el recibo del receptor.)

## 🚨 CANDADO NUEVO (31-ago, descubierto por la liga de prueba de Andrés)
**Regla documentada de ESPN**: una liga que no tenga TODOS sus cupos
reclamados 60 minutos antes del draft ve su draft RESETEADO y hay que
reagendarlo (support.espn.com, "Draft Schedule Issues"). Peace and Love está
**15/16** — falta que Santi Gut reclame "The Nest".
- ACCIÓN YA: avisar al commish para que Santi Gut entre ANTES del 7-sep.
- CANDADO del día: a las **5:30 pm** verificar por API `teamsJoined == 16`.
  Si a las 5:45 no está lleno, ESCALAR al commish — a las 6:00 pm ESPN
  borra el draft y el caos es total.

## El día del draft (en orden)
1. `git pull` (por si hubo correcciones de última hora).
2. `python ingest/check_settings.py` — si truena: NO draftear con el tablero
   viejo; avisar a Claude para regenerar (protocolo T1, ya ensayado).
3. `python ingest/archivo.py` — snapshot del día (proyecciones frescas).
4. Regenerar tablero si la proyección cambió: `python optimize/proyeccion_v2.py
   && python optimize/distribuciones.py && python optimize/notas.py`.
5. `python optimize/tablero_vivo.py` → abrir http://localhost:8787.
6. Ctrl+Shift+R en cada pick (la página además se refresca sola cada 10 s).
7. Si la API se congela: `python optimize/live_draft.py --manual` (teclado).

## Reglas acordadas (no se negocian en caliente)
- R1: mejor WR. R2: QB si el mejor QB vivo tiene VBD ≥ 110; si no, WR.
- 1 IDP por posición, CERO IDP en banca (regla de Andrés, en código).
- IDP/DST/K: rondas 12-18. Nunca antes (post-T1 valen 20-42 VBD).
- K: priorizar pierna larga (FG 50-59 = 10 pts sigue vivo).
- La banca es RB/WR (+3er QB si el tablero lo pide).

## El puente del navegador (fuente EN VIVO — construido 1-sep)

La API no publica picks mid-draft (medido 28-ago); el DOM del draft room sí.
El puente son 2 piezas ya probadas de punta a punta en local:

1. **Tablero**: `python optimize/tablero_vivo.py --puente`
2. **Snippet**: con el draft room abierto, F12 → Console → pegar TODO
   `optimize/puente.js` → Enter. Aparece un badge "🌉 N picks · último: …"
   en la esquina. Ese badge ES el candado visual: si el número no coincide
   con los picks reales, se ajusta el parser (avisar a Claude, ~1 min).
3. El tablero resuelve nombres (sufijos, tildes, apóstrofes, D/ST probados;
   homónimos por posición). Un nombre sin resolver GRITA en consola y se
   corrige al momento. Si el puente calla >20s, el tablero avisa.

CALIBRACIÓN OBLIGATORIA (task #8): entrar a un mock de ESPN días antes,
pegar el snippet y verificar badge + overall del "R#, P#" (chequear que
"R2, P1" = pick 17). Los selectores exactos del draft room no son
verificables sin una sala abierta — por diseño el parser es genérico y el
badge existe para calibrarlo en minutos.

Cadena del 7-sep: puente (primario) → pantallazos+escaleras (respaldo
probado 15 rondas) → --manual (teclado). API: candados de arranque,
inProgress y RECIBO final.
