"""
Qualità dell'aria (Copernicus CAMS) tramite Open-Meteo, passando dal nostro server.

- Senza chiave: API gratuita di Open-Meteo, consentita solo per uso non commerciale
  (va bene per la beta gratuita).
- Con OPENMETEO_API_KEY: API commerciale (dominio "customer-"), da usare quando il
  prodotto è in vendita. Il sito non cambia: cambia solo questa variabile.
Le risposte restano in cache 30 minuti (i dati CAMS si aggiornano ogni ora).
"""

from __future__ import annotations

import os
import threading
import time

import requests

FREE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
COMMERCIAL_URL = "https://customer-air-quality-api.open-meteo.com/v1/air-quality"
ALLOWED = {"latitude", "longitude", "current", "hourly", "past_days", "forecast_days", "timezone", "domains"}
CACHE_SECONDS = 30 * 60

_cache: dict = {}
_lock = threading.Lock()


class AirQualityUnavailable(Exception):
    pass


def endpoint() -> tuple:
    key = os.environ.get("OPENMETEO_API_KEY")
    return (COMMERCIAL_URL, {"apikey": key}) if key else (FREE_URL, {})


def fetch(params: dict, session=requests) -> dict:
    clean = {k: v for k, v in params.items() if k in ALLOWED}
    for coord in ("latitude", "longitude"):
        clean[coord] = f"{float(clean[coord]):.2f}"          # cache per celle di circa 1 km
    key = tuple(sorted(clean.items()))
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    url, extra = endpoint()
    try:
        response = session.get(url, params={**clean, **extra}, timeout=30)
    except requests.RequestException as exc:
        raise AirQualityUnavailable("Servizio della qualità dell'aria non raggiungibile.") from exc
    body = response.json() if response.content else {}
    if response.status_code != 200 or body.get("error"):
        raise AirQualityUnavailable(body.get("reason") or f"Errore {response.status_code}")
    with _lock:
        _cache[key] = (time.time() + CACHE_SECONDS, body)
        if len(_cache) > 500:
            _cache.clear()
    return body
