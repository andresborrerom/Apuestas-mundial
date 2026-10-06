# Cómo extraer las credenciales ESPN (una vez, ~2 minutos)

1. Abre **espn.com/fantasy** en Chrome y entra a tu liga (logueado).
2. F12 → pestaña **Application** → panel izquierdo **Cookies** → `https://fantasy.espn.com`.
3. Copia dos cookies:
   - **`espn_s2`** — valor largo (~300 chars). Cópialo COMPLETO (doble clic en el valor).
   - **`SWID`** — con el formato `{XXXXXXXX-XXXX-...}`. **Con las llaves.**
4. El **league_id** está en la URL de la liga: `...leagueId=XXXXXXX...`
5. Crea `fantasy-nfl/.env` (ya está en .gitignore):
   ```
   ESPN_LEAGUE_ID=1234567
   ESPN_S2=AEB...   (pégalo entero, sin comillas)
   ESPN_SWID={ABCD-...}
   ```
6. Verifica: `python ingest/espn_auth.py` → debe imprimir el nombre de la liga.

Notas: las cookies caducan (semanas/meses) — si el diagnóstico falla, re-extraer.
Si usas el celular: no sirve la app; tiene que ser navegador de escritorio.
