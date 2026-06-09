# Automatizar el llenado de formularios web (guía reutilizable)

Receta para que **Claude llene formularios web por ti** — pollas, aplicaciones a
trabajos, encuestas repetitivas, etc. — cuando el formulario corre JavaScript en
**tu** navegador y no tiene API. Probada en la polla CSC (web app de Google Apps
Script, 72×2 casillas llenadas en 1 pegada).

---

## Cuándo usar esto (y cuándo no)

| Situación | Método |
|---|---|
| Formulario JS, detrás de TU sesión, irreversible | **Snippet de consola** (esta guía) |
| Tienes la URL de envío y parámetros (POST simple) | `curl`/script directo |
| Hay API oficial | Usar la API |
| Quieres que un agente haga TODO incluido el submit | **Browser-use / Computer-use** (ver §6) |

El snippet de consola es el punto dulce: Claude escribe la automatización; tú
solo la pegas y revisas. **Para acciones irreversibles, conviene que el último
clic (Enviar) lo des tú** — no es descargarte trabajo, es la red de seguridad.

---

## El patrón en 4 pasos

1. **Inspeccionar el DOM** (1 pegada): cuántos inputs, sus `id`/`name`, y la
   estructura de un item. Esto evita adivinar.
2. **Construir los datos** keyed por una **ancla estable** (no por posición):
   nombre de equipo, etiqueta de pregunta, etc. Así el orden no importa.
3. **Snippet que llena**: empareja cada campo con su dato por la ancla, pone el
   valor y **dispara eventos** (`input`/`change`), y **NO envía**. Reporta
   cuántos llenó y cuáles faltaron.
4. **Tú revisas y envías.**

---

## Gotchas que SIEMPRE aparecen (y su solución)

1. **El form vive en un iframe** → `document.querySelectorAll('input')` da 0.
   *Solución:* en la consola de Chrome, cambia el **contexto** (desplegable
   `top` arriba a la izquierda) al iframe (`googleusercontent.com`/`sandboxFrame`)
   y corre ahí.
2. **`const X already declared`** al pegar 2 veces.
   *Solución:* envuelve todo en `(function(){ ... })();` (IIFE) y usa `var`. Así
   se re-pega infinitas veces sin error.
3. **Chrome bloquea pegar en consola** ("self-XSS").
   *Solución:* escribe a mano `allow pasting`, Enter, y vuelve a pegar.
4. **Llenó 0 / los nombres salen vacíos** → el contenedor inmediato del input no
   tiene el texto (la etiqueta está en un div hermano/padre).
   *Solución:* sube en el DOM hasta el contenedor que **contenga el texto ancla**
   (ej. `"vs"`, o el label de la pregunta), y lee los nombres de ahí.
5. **Setear `.value` no "registra"** el dato en apps reactivas.
   *Solución:* dispara `new Event('input',{bubbles:true})` y `'change'`.
6. **Emparejar por posición es frágil** (el form puede ordenar distinto).
   *Solución:* emparejar por **ancla normalizada** (minúsculas, sin acentos, con
   un diccionario de sinónimos para idiomas: `Qatar=Catar`, `Scotland=Escocia`).
   Maneja también la orientación invertida (si no encuentra `A|B`, prueba `B|A` y
   voltea el valor).

---

## Plantilla genérica del snippet

```javascript
(function(){
  var DATOS = { /* "ancla1|ancla2":[v1,v2], ... */ };
  function canon(s){ // normaliza la ancla (ajusta sinónimos a tu caso)
    s=s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'').replace(/[^a-z]/g,'');
    return SINONIMOS[s]||s;
  }
  function setVal(el,v){el.value=v;
    el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true}));}
  var ok=0, miss=[];
  // localizar cada item por su ancla y llenar sus inputs...
  // (subir al contenedor con el texto ancla; leer la(s) etiqueta(s); buscar en DATOS)
  console.log('llené '+ok); if(miss.length) console.warn('faltan:',miss);
})();  // NO envía: revisa y dale Enviar tú
```

Ejemplo real completo: el generador
`pollas/CSC/` (lo arma Claude a partir del CSV de marcadores) produce el snippet
con los 5 cupos y empareja por nombre de equipo.

---

## Flujo de trabajo con Claude (cómo pedirlo)

1. "Tengo este formulario [URL]. Quiero llenarlo con [estos datos]."
2. Claude te da un **snippet de inspección** → pegas, le mandas el output.
3. Claude te da el **snippet llenador** a la medida → pegas, revisas, envías.
4. Para repetir (otro registro/variante): solo cambias 1 variable y re-pegas.

Tu interacción baja a: **pegar 2 veces + revisar + enviar.**

---

## §6 — "¿Por qué no lo hace un agente y yo solo apruebo?"

Sí se puede, pero depende del **entorno**:

- **Claude Code (este entorno):** corre en un contenedor en la nube sin
  navegador conectado a TU sesión. Aunque instalara un navegador headless ahí,
  sería una sesión nueva (sin tus cookies/login), y servicios como Google
  bloquean IPs de datacenter / navegadores automatizados. Por eso el snippet
  corre en **tu** navegador (donde está tu sesión). Claude hace lo difícil
  (toda la lógica); tú aportas el contexto autenticado y el clic final.
- **Browser-use / Computer-use (agente de navegador):** ahí SÍ un agente
  controla un navegador real y puede hacer todo, incluido el submit, y tú solo
  apruebas. Es un **montaje distinto** (la extensión/agente de navegador de
  Claude, o frameworks tipo Playwright manejados por un agente con TU perfil).
  Para tu proyecto futuro de "llenar formatos / aplicar a trabajos / responder
  LinkedIn", ESE es el camino: un agente con navegador propio + perfil logueado.
- **Acciones irreversibles:** aun con agente total, conviene un paso de
  "revisar y aprobar" antes de enviar algo que no se puede deshacer. No es
  limitación técnica, es buena práctica.

**Resumen:** en Code, el snippet ya te deja en "pegar + aprobar". Para bajar a
"solo aprobar", el siguiente paso es un agente de navegador (computer-use), que
es justo lo que vale la pena montar para el proyecto de automatización que tienes
en mente.
