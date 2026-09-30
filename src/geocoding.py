"""
Ricerca di località sui dati OpenStreetMap.

Servizio principale: Nominatim. Riserva automatica: Photon (komoot),
usato quando Nominatim rifiuta le richieste (429/403) o non risponde.
Succede spesso dai server cloud, che condividono gli indirizzi IP
con molti altri servizi.

Regole rispettate (policy d'uso dei servizi pubblici):
- user-agent identificabile;
- al massimo 1 richiesta al secondo;
- cache dei risultati;
- nessun autocompletamento: l'app cerca solo quando l'utente conferma;
- dopo un rifiuto di Nominatim, pausa di 10 minuti prima di riprovarlo.

Lingua dei nomi: italiano, altrimenti inglese, altrimenti nome locale.
Così i luoghi in Medio Oriente, Asia, ecc. non compaiono in caratteri
non latini quando esiste una traduzione.
"""

from __future__ import annotations

import threading
import time

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "EarthPulse/0.5 (+https://github.com/giovmar-source/earthpulse)"

MIN_INTERVAL_SECONDS = 1.0
MAX_CACHE_ENTRIES = 500
NOMINATIM_PAUSE_SECONDS = 600
REQUEST_TIMEOUT = 10

_cache: dict = {}
_lock = threading.Lock()
_last_request = [0.0]
_nominatim_blocked_until = [0.0]


class GeocodingUnavailable(Exception):
    """Nessun servizio di ricerca disponibile in questo momento."""


def normalize_query(query: str) -> str:
    return " ".join((query or "").split())


def _accept_language(language: str) -> str:
    """Es. "it" -> "it,en;q=0.8": se manca l'italiano, preferisci l'inglese."""
    return language if language == "en" else f"{language},en;q=0.8"


def _get(http, url, params, language):
    """GET con intervallo minimo di 1 s tra le richieste."""
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        try:
            return http.get(
                url,
                params=params,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": _accept_language(language),
                },
                timeout=REQUEST_TIMEOUT,
            )
        finally:
            _last_request[0] = time.monotonic()


def _search_nominatim(http, text, limit, language) -> list:
    response = _get(
        http, NOMINATIM_URL,
        {"q": text, "format": "jsonv2", "limit": limit, "namedetails": 1},
        language,
    )
    status = getattr(response, "status_code", 200)
    if status in (403, 429):
        raise PermissionError(f"Nominatim ha rifiutato la richiesta ({status}).")
    response.raise_for_status()

    results = []
    for place in response.json():
        display_name = place.get("display_name", "")
        names = place.get("namedetails") or {}
        # Nome nella lingua richiesta, poi inglese, poi quello di Nominatim.
        name = (
            names.get(f"name:{language}")
            or names.get("name:en")
            or place.get("name")
            or display_name.split(",")[0]
        )
        results.append({
            "name": name,
            "display_name": display_name,
            "latitude": float(place["lat"]),
            "longitude": float(place["lon"]),
            "type": place.get("type"),
            "category": place.get("category"),
        })
    return results


def _search_photon(http, text, limit, language) -> list:
    # Il server pubblico di Photon supporta poche lingue: se la lingua
    # richiesta non è disponibile (errore 400) si usa l'inglese.
    response = None
    for lang in dict.fromkeys([language, "en"]):
        response = _get(
            http, PHOTON_URL, {"q": text, "limit": limit, "lang": lang}, language
        )
        if getattr(response, "status_code", 200) != 400:
            break
    response.raise_for_status()

    results = []
    for feature in response.json().get("features", []):
        props = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue

        name = props.get("name") or props.get("city") or props.get("street") or text
        parts = []
        for key in ("name", "city", "county", "state", "country"):
            value = props.get(key)
            if value and value not in parts:
                parts.append(value)

        results.append({
            "name": name,
            "display_name": ", ".join(parts) or name,
            # GeoJSON: [longitudine, latitudine]
            "latitude": float(coordinates[1]),
            "longitude": float(coordinates[0]),
            "type": props.get("osm_value"),
            "category": props.get("osm_key"),
        })
    return results


def search_places(query: str, limit: int = 5, language: str = "it",
                  session=None) -> list:
    """
    Restituisce una lista di luoghi:
    [{"name", "display_name", "latitude", "longitude", "type", "category"}]

    Solleva ValueError per query troppo corte e GeocodingUnavailable
    se né Nominatim né Photon rispondono.
    """
    text = normalize_query(query)
    if len(text) < 2:
        raise ValueError("La ricerca deve contenere almeno 2 caratteri.")

    key = (text.lower(), limit, language)
    if key in _cache:
        return _cache[key]

    http = session or requests
    results = None

    if time.monotonic() >= _nominatim_blocked_until[0]:
        try:
            results = _search_nominatim(http, text, limit, language)
        except PermissionError:
            _nominatim_blocked_until[0] = time.monotonic() + NOMINATIM_PAUSE_SECONDS
        except (requests.RequestException, ValueError, KeyError):
            pass

    if results is None:
        try:
            results = _search_photon(http, text, limit, language)
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise GeocodingUnavailable(
                "Ricerca dei luoghi temporaneamente non disponibile. "
                "Riprova tra qualche minuto oppure tocca la mappa."
            ) from exc

    if len(_cache) >= MAX_CACHE_ENTRIES:
        _cache.clear()
    _cache[key] = results

    return results
