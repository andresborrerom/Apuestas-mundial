# Qué puede (y qué NO) hacer Claude para bajar la carga operativa

> Material para enseñar. Captura el aprendizaje real de estas pollas sobre **dónde
> Claude te ahorra trabajo operativo y dónde no**. Pensado para convertirse en un
> "to-do list" / módulo de curso cuando se pida.

## El caso estrella (CSC, ayer): 5 formularios × 146 datos → casi cero esfuerzo
**El dolor:** llenar a mano 5 planillas de fase de grupos, ~146 marcadores en
total, en un formulario web (Google Apps Script embebido en iframe).

**Lo que hizo Claude:** en vez de pasar un CSV para copiar a mano, **escribió un
snippet de JavaScript de consola** que, pegado en las DevTools del navegador del
usuario (ya logueado), **llenó el formulario solo**. El usuario solo revisó y
envió. De ~146 pegues manuales a 1 paste + revisar.

**Por qué funcionó:** el formulario era una web app en la sesión autenticada del
usuario; el snippet corre EN esa sesión, así que no necesita login ni API.
(Detalle técnico que costó depurar: el form estaba en un iframe de
googleusercontent → hubo que apuntar la consola a ese contexto; y leer el nombre
de cada equipo subiendo en el DOM hasta el contenedor con "vs".)

## Los pasos a enseñar (el "to-do list" de operatividad)

1. **Nombra el dolor operativo concreto:** ¿cuántas planillas × cuántos campos?
   ¿con qué frecuencia (una vez / día a día)? Eso decide cuánto vale automatizar.
2. **Identifica el CANAL de entrada:**
   - **API** (p. ej. The Odds API para bajar; algunos forms tienen endpoint) →
     Claude llena/baja directo.
   - **Formulario web en TU navegador** (Google Forms, Apps Script) → **snippet
     de consola** que Claude escribe y tú pegas en DevTools. Máximo ahorro.
   - **App con login** (Pollaya) → **no se automatiza el envío**; Claude genera
     los valores del día y tú los pegas a mano (poco por día).
   - **Archivo** (Excel/PDF) → Claude lo llena por celda con código (openpyxl) y
     te devuelve el archivo listo.
3. **Genera el artefacto correcto** para ese canal: snippet JS / archivo .xlsx /
   CSV / lista del día. Que el último paso humano sea mínimo (un paste, un click).
4. **Verifica la salida real**, no solo el modelo (el bug del marcador incoherente
   apareció mirando el Excel lleno, no la simulación).
5. **Cuantifica "el costo de tu pereza":** si no automatizas / no compras más
   plazas, ¿cuánto E[utilidad] dejas? (matriz de deciles). A veces la pereza es
   barata y la decisión correcta.

## Qué puede hacer Claude (operativo)
- **Generar todos los datos** (marcadores EV-máx, outrights, extras) y un
  artefacto **pegable**: snippet de consola, Excel lleno, CSV, lista del día.
- **Escribir un snippet de navegador** que llena un form web en TU sesión.
- **Llenar archivos** (Excel) por celda, con la orientación/formato correctos.
- **Bajar cuotas en vivo** y **calcular** (un comando por día: `dia.py`).
- **Investigar** con sub-agentes (mercados de jugador, datos históricos).

## Qué NO puede hacer Claude (y hay que decirlo)
- **Actuar dentro de tu app logueada** (no hace clics en tu sesión de Pollaya;
  no envía por ti a una app con login).
- **Reaccionar en vivo en segundos** (la trivia de 10s: el ida-y-vuelta no cabe).
- **Correr solo todos los días**: el entorno es **efímero** (se borra). Opciones:
  lo corres tú cada día, o se monta un **GitHub Action programado** (cron) con la
  API key como secreto del repo.
- **Inventar datos que no tiene** (goleador/MVP sin mercado → se buscan gratis o
  se marcan como conjetura; nunca se inventan sin avisar).

## La regla de oro
**Automatiza hasta donde el canal lo permita; el resto, Claude te deja el valor
listo para pegar.** El humano queda como cerebro+revisor, no como operario.
