# COLFONDOS — rutina diaria (cómo correr cada mañana)

## El comando (1 sola línea, cada día)
```
ODDS_API_KEY=tu_key python pollas/COLFONDOS/dia.py --fecha AAAA-MM-DD
```
- Sin `--fecha` → muestra todos los partidos próximos con cuotas.
- `--tz -5` ya es Colombia por defecto (las fechas calzan con tu calendario).
- `--mock /tmp/wc_grupos.json` → prueba sin gastar API.

Te imprime, por partido: **PLAZA 1 (España, EV-máx)** y **PLAZA 2 (Inglaterra,
2º mejor = decorrelada)**. Copias esos marcadores a Pollaya y listo.

## Recordatorio de qué es de "una sola vez" (ya está puesto)
- Campeón/Sub/3º, goleador, asistente, MVP, arquero, joven, malla, clasificados.
  NO se tocan día a día. Solo los **marcadores** se cargan por jornada.

## Cuando empiecen las eliminatorias
El mismo comando sirve: cuando se conocen los equipos de cada llave, aparecen con
cuotas y te da el marcador. Ahí los marcadores de plaza 1 siguen el bracket
España-campeón y plaza 2 el Inglaterra-campeón (te lo confirmo en su momento).

## Nota
No puedo correrlo yo solo todos los días (este entorno es efímero, se borra). Dos
opciones: (1) lo corres tú cada mañana — pega un recordatorio en el celular; o
(2) montamos un GitHub Action programado (cron diario) que escriba el archivo del
día al repo — requiere meter la API key como secreto del repo. Avísame si quieres
la opción 2.
