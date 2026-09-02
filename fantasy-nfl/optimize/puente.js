/* PUENTE DEL NAVEGADOR — draft real ESPN, 7-sep-2026.
 *
 * Qué hace: lee el panel "Pick History" del draft room (el DOM sí tiene los
 * picks al segundo; la API no los publica hasta el cierre — medido 28-ago) y
 * los POSTea a http://localhost:8787/puente cada segundo. El tablero resuelve
 * nombres contra el pool y recalcula la recomendación.
 *
 * Cómo se usa (UNA vez, con el draft room abierto):
 *   1. F12 → pestaña Console de la PESTAÑA DEL DRAFT.
 *   2. Pegar TODO este archivo y Enter.
 *   3. Verificar el badge flotante "🌉 N picks · último: ..." (abajo-derecha).
 *      Si el número no sube cuando hay picks nuevos, avísame: se ajusta
 *      PARSEAR en 1 minuto (los selectores de ESPN se calibran en el mock).
 *   Para pararlo: clearInterval(window.__puente)
 *
 * ⚠️ CANDADO DECLARADO: los selectores del draft room NO son verificables
 * hasta estar dentro de una sala real/mock. Por eso el parser es genérico
 * (regex sobre el texto del panel) y el badge existe: la calibración se hace
 * en el mock del task #8, en minutos, ANTES del 7-sep.
 */
(() => {
  const URL_TABLERO = 'http://localhost:8787/puente';
  const EQUIPOS = 14;   // ⚠️ HOY 2-sep: Cheap-Sheet=14. Para P&L (7-sep): 16.
  const POSICIONES = ['QB', 'RB', 'WR', 'TE', 'DT', 'DE', 'LB', 'CB', 'S', 'D/ST', 'K'];

  // --- localizar el contenedor del historial (varias estrategias) ---------
  function contenedor() {
    // 1) por encabezado visible
    for (const el of document.querySelectorAll('h1,h2,h3,h4,div,span,button')) {
      const t = (el.textContent || '').trim();
      if (/^(pick history|historial)/i.test(t) && t.length < 30) {
        let c = el.closest('section,aside,div');
        for (let k = 0; k < 4 && c; k++) {
          if (c.innerText && c.innerText.length > 200) return c;
          c = c.parentElement;
        }
      }
    }
    // 2) clases habituales de ESPN
    for (const sel of ['[class*="pick-history" i]', '[class*="pickHistory" i]',
                       '[class*="history" i]']) {
      const c = document.querySelector(sel);
      if (c && c.innerText && c.innerText.length > 200) return c;
    }
    return document.body;                    // 3) último recurso: toda la página
  }

  // --- parsear texto → [{n, nombre, pos}] --------------------------------
  // El historial de ESPN lista, por pick: "R1, P5" (o "1.5"), nombre, "POS - EQ".
  function PARSEAR(texto) {
    const lineas = texto.split('\n').map(s => s.trim()).filter(Boolean);
    const picks = [];
    let n = null, ronda = null, enRonda = null;
    for (const ln of lineas) {
      let m;
      if ((m = ln.match(/^R(?:ound)?\s*(\d+)\s*[,·]?\s*P(?:ick)?\s*(\d+)$/i))) {
        ronda = +m[1]; enRonda = +m[2];
        // "P" cuenta el ORDEN CRONOLÓGICO dentro de la ronda (el snake ya
        // está aplicado por ESPN) → overall directo. ⚠️ VERIFICAR en el mock
        // con el badge: el "último" debe coincidir con el pick real.
        n = (ronda - 1) * EQUIPOS + enRonda;
        continue;
      }
      if ((m = ln.match(/^(\d{1,3})(?:\.|:)?$/)) && +m[1] >= 1 && +m[1] <= EQUIPOS * 20) {
        n = +m[1];                                   // número overall directo
        continue;
      }
      const pm = ln.match(/^(QB|RB|WR|TE|DT|DE|LB|CB|S|D\/ST|K)\b/);
      if (pm && picks.length && picks[picks.length - 1].pos === null) {
        picks[picks.length - 1].pos = pm[1];
        continue;
      }
      // nombre: 2+ palabras con mayúscula inicial, o "XXX D/ST"
      if (n !== null &&
          (/^[A-Z][\w.'-]+(\s+[A-Z][\w.'-]+)+/.test(ln) || /D\/ST$/.test(ln))) {
        const pos = (ln.match(/\b(QB|RB|WR|TE|DT|DE|LB|CB|S|D\/ST|K)\b/) || [])[1] || null;
        const nombre = ln.replace(/\b(QB|RB|WR|TE|DT|DE|LB|CB|S|K)\b.*$/, '').trim();
        picks.push({ n, nombre, pos });
        n = null;
      }
    }
    return picks.filter(p => p.nombre && p.n >= 1 && p.n <= EQUIPOS * 20);
  }

  // --- badge de verificación ---------------------------------------------
  let badge = document.getElementById('__puente_badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = '__puente_badge';
    badge.style.cssText = 'position:fixed;bottom:8px;right:8px;z-index:99999;' +
      'background:#111;color:#7fdc9a;font:12px monospace;padding:6px 10px;' +
      'border-radius:6px;opacity:.92;pointer-events:none';
    document.body.appendChild(badge);
  }

  let ultimoEnvio = '', tablero = '?';
  async function tick() {
    let picks = [];
    try {
      picks = PARSEAR(contenedor().innerText || '');
    } catch (e) {
      badge.textContent = '🌉 ERROR parser: ' + e.message;
      badge.style.color = '#e05555';
      return;
    }
    // el badge SIEMPRE refleja lo leído — sirve para calibrar en un mock
    // aunque el tablero no esté corriendo todavía
    badge.textContent = `🌉 ${picks.length} picks · último: ` +
      (picks.length ? `${picks[picks.length - 1].n} ${picks[picks.length - 1].nombre}` : '—') +
      `  [tablero ${tablero}]`;
    badge.style.color = picks.length ? '#7fdc9a' : '#e0b040';
    const cuerpo = JSON.stringify({ picks, t: Date.now() });
    if (cuerpo !== ultimoEnvio) {
      try {
        await fetch(URL_TABLERO, { method: 'POST', mode: 'no-cors',
                                   headers: { 'Content-Type': 'text/plain' },
                                   body: cuerpo });
        ultimoEnvio = cuerpo; tablero = '✓';
      } catch (e) { tablero = 'sin conexión'; }
    }
  }
  if (window.__puente) clearInterval(window.__puente);
  window.__puente = setInterval(tick, 1000);
  tick();
  console.log('🌉 puente activo → ' + URL_TABLERO + '  (parar: clearInterval(window.__puente))');
})();
