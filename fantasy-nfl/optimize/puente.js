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
  // Calibrado 2-sep con el Practice Draft real: la tabla central va
  // PICK · PLAYER · TEAM · 2025 PTS · PROJ · RK. La columna RK también es un
  // entero suelto y el carril derecho "Picks" repite nombres → regla de
  // ADYACENCIA: un número solo cuenta si la línea SIGUIENTE es un nombre; y
  // se deduplica por número de pick (gana la primera aparición = tabla).
  function esNombre(ln) {
    return /^[A-Z][\w.'-]+(\s+[A-Z][\w.'-]+)+/.test(ln) || /D\/ST$/.test(ln);
  }
  function limpiaNombre(ln) {
    return ln.replace(/\b(QB|RB|WR|TE|DT|DE|LB|CB|K)\b.*$/, '')
             .replace(/\s+(Q|O|D|IR|SSPD)$/, '').trim();
  }
  // v3 (practice 2): ESPN VIRTUALIZA la tabla — solo las filas visibles
  // existen en el DOM. El puente ACUMULA todo lo que haya visto (cada pick
  // pasa por la vista cuando ocurre) y también lee el carril derecho
  // "Picks" (nombre y luego "R#, P# - equipo").
  const ACUM = (window.__puente_acum = window.__puente_acum || new Map());
  function PARSEAR(texto) {
    const lineas = texto.split('\n').map(s => s.trim()).filter(Boolean);
    const porN = ACUM;
    for (let i = 0; i < lineas.length - 1; i++) {
      const ln = lineas[i], sig = lineas[i + 1];
      let n = null, m;
      if ((m = ln.match(/^R(?:ound)?\s*(\d+)\s*[,\u00b7]?\s*P(?:ick)?\s*(\d+)$/i))) {
        n = (+m[1] - 1) * EQUIPOS + (+m[2]);
      } else if ((m = ln.match(/^(\d{1,3})(?:\.|:)?$/))) {
        n = +m[1];
      }
      // carril derecho: NOMBRE y luego "R8, P4 - Equipo"
      if (n === null && esNombre(ln)) {
        const mr = sig.match(/^R(\d+),?\s*P(\d+)\s*[-\u2014]/i);
        if (mr) {
          const nn = (+mr[1] - 1) * EQUIPOS + (+mr[2]);
          if (nn >= 1 && nn <= EQUIPOS * 20 && !porN.has(nn)) {
            const pos2 = (ln.match(/\b(QB|RB|WR|TE|DT|DE|LB|CB|S|D\/ST|K)\b/) || [])[1] || null;
            porN.set(nn, { n: nn, nombre: limpiaNombre(ln), pos: pos2 });
          }
          i++;
          continue;
        }
      }
      if (n === null || n < 1 || n > EQUIPOS * 20 || !esNombre(sig)) continue;
      if (porN.has(n)) continue;                  // dedupe: manda la tabla
      const linPos = (sig + ' ' + (lineas[i + 2] || ''));
      const pos = (linPos.match(/\b(QB|RB|WR|TE|DT|DE|LB|CB|S|D\/ST|K)\b/) || [])[1] || null;
      porN.set(n, { n, nombre: limpiaNombre(sig), pos });
      i++;                                        // el nombre ya se consumió
    }
    return [...porN.values()].sort((a, b) => a.n - b.n);
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
