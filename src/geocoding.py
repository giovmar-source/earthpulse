"""
Ricerca di località tramite Nominatim (OpenStreetMap).

Rispetta la policy d'uso di Nominatim
(https://operations.osmfoundation.org/policies/nominatim/):
- user-agent identificabile;
- al massimo 1 richiesta al secondo;
- cache dei risultati;
- nessun autocompletamento: l'app invia una ricerca solo quando
  l'utente conferma.
"""

from __future__ import annotations

import threading
import time

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "EarthPulse/0.4 (+https://github.com/giovmar-source/earthpulse)"

MIN_INTERVAL_SECONDS = 1.0
MAX_CACHE_ENTRIES = 500

_cache: dict = {}
_lock = threading.Lock()
_last_request = [0.0]


def normalize_query(query: str) -> str:
    return " ".join((query or "").split())


def search_places(query: str, limit: int = 5, language: str = "it",
                  session=None) -> list:
    """
    Restituisce una lista di luoghi:
    [{"name", "display_name", "latitude", "longitude", "type", "category"}]

    Solleva ValueError per query troppo corte e
    requests.RequestException per errori di rete.
    """
    text = normalize_query(query)
    if len(text) < 2:
        raise ValueError("La ricerca deve contenere almeno 2 caratteri.")

    key = (text.lower(), limit, language)
    if key in _cache:
        return _cache[key]

    http = session or requests

    # Il lock garantisce l'intervallo minimo anche con richieste simultanee.
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request[0])
        if wait > 0:
            time.sleep(wait)
        try:
            response = http.get(
                NOMINATIM_URL,
                params={
                    "q": text,
                    "format": "jsonv2",
                    "limit": limit,
                },
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": language,
                },
                timeout=10,
            )
        finally:
            _last_request[0] = time.monotonic()

    response.raise_for_status()

    results = []
    for place in response.json():
        display_name = place.get("display_name", "")
        results.append({
            "name": place.get("name") or display_name.split(",")[0],
            "display_name": display_name,
            "latitude": float(place["lat"]),
            "longitude": float(place["lon"]),
            "type": place.get("type"),
            "category": place.get("category"),
        })

    if len(_cache) >= MAX_CACHE_ENTRIES:
        _cache.clear()
    _cache[key] = results

    return results
