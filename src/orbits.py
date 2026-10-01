"""
Dati orbitali (TLE) dei satelliti usati da EarthPulse, presi da CelesTrak.

Il sito web calcola la posizione dei satelliti nel browser (libreria
satellite.js) a partire da questi elementi orbitali. Il server li scarica
da CelesTrak e li tiene in memoria per alcune ore: CelesTrak aggiorna gli
elementi circa una volta al giorno e chiede di non interrogarlo troppo spesso.
"""

from __future__ import annotations

import threading
import time

import requests

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
CACHE_SECONDS = 6 * 3600
USER_AGENT = "EarthPulse/0.10 (+https://github.com/giovmar-source/earthpulse)"

# Satelliti mostrati sul globo. "card" collega la scheda descrittiva del sito.
SATELLITES = [
    {"norad": 40697, "name": "Sentinel-2A", "card": "sentinel-2"},
    {"norad": 42063, "name": "Sentinel-2B", "card": "sentinel-2"},
    {"norad": 60989, "name": "Sentinel-2C", "card": "sentinel-2"},
    {"norad": 39084, "name": "Landsat 8", "card": "landsat"},
    {"norad": 49260, "name": "Landsat 9", "card": "landsat"},
    {"norad": 37849, "name": "Suomi NPP", "card": "suomi-npp"},
]

_cache: dict = {"time": 0.0, "data": []}
_lock = threading.Lock()


def parse_tle(text: str):
    """Testo TLE di CelesTrak (nome + 2 righe) -> (riga1, riga2) oppure None."""
    lines = [line.rstrip() for line in text.strip().splitlines() if line.strip()]
    line1 = next((l for l in lines if l.startswith("1 ")), None)
    line2 = next((l for l in lines if l.startswith("2 ")), None)
    if not line1 or not line2 or len(line1) < 69 or len(line2) < 69:
        return None
    return line1[:69], line2[:69]


def fetch_tle(norad: int, session=requests) -> tuple | None:
    response = session.get(
        CELESTRAK_URL, params={"CATNR": norad, "FORMAT": "tle"},
        headers={"User-Agent": USER_AGENT}, timeout=(10, 20),
    )
    response.raise_for_status()
    return parse_tle(response.text)


def satellites_with_tle(force: bool = False) -> list:
    """Elenco dei satelliti con le righe TLE (dalla cache se recente)."""
    with _lock:
        if not force and _cache["data"] and time.time() - _cache["time"] < CACHE_SECONDS:
            return _cache["data"]
        previous = {s["norad"]: s for s in _cache["data"]}

    result = []
    for sat in SATELLITES:
        entry = dict(sat)
        try:
            tle = fetch_tle(sat["norad"])
        except requests.RequestException:
            tle = None
        if tle is None and sat["norad"] in previous:
            # CelesTrak non risponde: teniamo gli elementi precedenti
            old = previous[sat["norad"]]
            tle = (old["line1"], old["line2"])
        if tle is None:
            continue
        entry["line1"], entry["line2"] = tle
        result.append(entry)

    with _lock:
        if result:
            _cache["data"] = result
            _cache["time"] = time.time()
    return result
