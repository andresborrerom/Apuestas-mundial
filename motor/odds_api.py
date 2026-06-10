"""
Fuente de datos de cuotas: The Odds API (https://the-odds-api.com).

Por qué The Odds API y no Rushbet: Rushbet no expone API pública y scrapearla
es frágil y contra sus términos. The Odds API agrega varias casas; usar el
CONSENSO (mediana) es más robusto que una sola casa y Rushbet se mueve cerca
de ese consenso.

Este módulo solo baja y normaliza datos; no sabe nada de pollas. La conversión
a probabilidades y el relleno óptimo los hace el resto del motor.

Necesitas una API key gratuita: https://the-odds-api.com  (variable de entorno
ODDS_API_KEY o argumento --api-key del comando).
"""

import json
import urllib.request
import urllib.parse
from statistics import median

BASE = "https://api.the-odds-api.com/v4"

# Clave del torneo en The Odds API. En 2022 fue "soccer_fifa_world_cup".
# Si cambia para 2026, úsala con --sport o míra la lista con --list-sports.
SPORT_MUNDIAL = "soccer_fifa_world_cup"


def _get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def listar_deportes(api_key):
    """Lista las claves de deporte/torneo disponibles (para encontrar la del Mundial)."""
    return _get(f"{BASE}/sports/?apiKey={urllib.parse.quote(api_key)}")


def bajar_eventos(api_key, sport=SPORT_MUNDIAL,
                  regions="us,uk,eu,au", markets="h2h,totals"):
    """Descarga los eventos con cuotas. Devuelve la lista cruda de la API."""
    q = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    })
    return _get(f"{BASE}/sports/{sport}/odds/?{q}")


def bajar_evento_mercados(api_key, event_id, sport=SPORT_MUNDIAL,
                          regions="eu",
                          markets="h2h,alternate_totals,team_totals"):
    """Descarga mercados ADICIONALES de UN evento (gratis en tu plan): la curva
    completa de Over/Under (`alternate_totals`) y el O/U por equipo
    (`team_totals`). Requiere el endpoint por-evento. Devuelve el dict del evento.
    """
    q = urllib.parse.urlencode({
        "apiKey": api_key, "regions": regions, "markets": markets,
        "oddsFormat": "decimal", "dateFormat": "iso",
    })
    return _get(f"{BASE}/sports/{sport}/events/{event_id}/odds/?{q}")


def _devig_par(over, under):
    """De-vig de un par Over/Under -> P(over)."""
    io, iu = 1.0 / over, 1.0 / under
    return io / (io + iu)


def consenso_rico(evento):
    """Consenso (mediana de casas) de un evento con mercados adicionales.

    Devuelve dict con: cuotas_1x2 [L,E,V], totales [(linea, p_over), ...] (curva
    Over/Under), team_local [(linea, p_over), ...] y team_visita [...]. Listo
    para `marcadores.ajustar_lambdas_rico`.
    """
    home, away = evento.get("home_team"), evento.get("away_team")
    h2h = {home: [], "Draw": [], away: []}
    tot = {}                  # punto -> {"Over":[odds], "Under":[odds]}
    team = {home: {}, away: {}}  # equipo -> punto -> {"Over":[],"Under":[]}
    for casa in evento.get("bookmakers", []):
        for m in casa.get("markets", []):
            k = m["key"]
            for o in m["outcomes"]:
                nm, pt, pr = o.get("name"), o.get("point"), o.get("price")
                if k == "h2h" and nm in h2h:
                    h2h[nm].append(pr)
                elif k in ("totals", "alternate_totals") and pt is not None:
                    tot.setdefault(pt, {}).setdefault(nm, []).append(pr)
                elif k == "team_totals" and pt is not None:
                    eq = o.get("description")
                    if eq in team:
                        team[eq].setdefault(pt, {}).setdefault(nm, []).append(pr)

    def curva(d):
        out = []
        for pt, oc in sorted(d.items()):
            if oc.get("Over") and oc.get("Under"):
                out.append((pt, _devig_par(median(oc["Over"]), median(oc["Under"]))))
        return out

    c1x2 = None
    if all(h2h[k] for k in (home, "Draw", away)):
        c1x2 = [median(h2h[home]), median(h2h["Draw"]), median(h2h[away])]
    return {
        "home": home, "away": away, "inicio": evento.get("commence_time"),
        "cuotas_1x2": c1x2,
        "totales": curva(tot),
        "team_local": curva(team[home]),
        "team_visita": curva(team[away]),
        "n_casas": len(evento.get("bookmakers", [])),
    }


# --------------------------------------------------------------------------
# Consenso de casas (parsing puro, testeable sin red)
# --------------------------------------------------------------------------

def consenso_evento(evento, linea_pref=2.5):
    """Resume un evento en cuotas de consenso (mediana de todas las casas).

    Devuelve dict:
      home, away, inicio (ISO UTC),
      cuotas_1x2 = [local, empate, visita] o None,
      cuotas_ou  = [under, over] o None, linea (la línea de totales usada),
      n_casas
    """
    home = evento.get("home_team")
    away = evento.get("away_team")
    casas = evento.get("bookmakers", [])

    precios_h2h = {home: [], "Draw": [], away: []}
    # totales agrupados por línea (point): {2.5: {"Over": [...], "Under": [...]}}
    totales = {}

    for casa in casas:
        for mercado in casa.get("markets", []):
            if mercado["key"] == "h2h":
                for o in mercado["outcomes"]:
                    if o["name"] in precios_h2h:
                        precios_h2h[o["name"]].append(o["price"])
            elif mercado["key"] == "totals":
                for o in mercado["outcomes"]:
                    punto = o.get("point")
                    if punto is None:
                        continue
                    totales.setdefault(punto, {}).setdefault(o["name"], [])
                    totales[punto][o["name"]].append(o["price"])

    cuotas_1x2 = None
    if all(precios_h2h[k] for k in (home, "Draw", away)):
        cuotas_1x2 = [median(precios_h2h[home]),
                      median(precios_h2h["Draw"]),
                      median(precios_h2h[away])]

    cuotas_ou, linea = None, None
    # elegir la línea con Over y Under, más cercana a linea_pref (preferir 2.5)
    candidatas = [p for p, d in totales.items()
                  if "Over" in d and "Under" in d]
    if candidatas:
        linea = min(candidatas, key=lambda p: (abs(p - linea_pref), -len(totales[p]["Over"])))
        cuotas_ou = [median(totales[linea]["Under"]), median(totales[linea]["Over"])]

    return {
        "home": home,
        "away": away,
        "inicio": evento.get("commence_time"),
        "cuotas_1x2": cuotas_1x2,
        "cuotas_ou": cuotas_ou,
        "linea": linea,
        "n_casas": len(casas),
    }
