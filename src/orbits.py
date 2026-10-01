"""
Dati orbitali (TLE) dei satelliti usati da EarthPulse, presi da CelesTrak.

Il sito web calcola la posizione dei satelliti nel browser (libreria
satellite.js) a partire da questi elementi orbitali. Il server li scarica
da CelesTrak e li tiene in memoria per alcune ore: CelesTrak aggiorna gli
elementi circa una volta al giorno e chiede di non interrogarlo troppo spesso.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


BACKUP_URL = "https://tle.ivanstanojevic.me/api/tle/{norad}"
FALLBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "tle_fallback.json"


def fetch_tle(norad: int, session=requests) -> tuple | None:
    """Fonte principale: CelesTrak (a volte rifiuta i server cloud condivisi)."""
    response = session.get(
        CELESTRAK_URL, params={"CATNR": norad, "FORMAT": "tle"},
        headers={"User-Agent": USER_AGENT}, timeout=(10, 20),
    )
    response.raise_for_status()
    return parse_tle(response.text)


def fetch_tle_backup(norad: int, session=requests) -> tuple | None:
    """Fonte di riserva: TLE API (ripubblica i dati di CelesTrak, in JSON)."""
    response = session.get(
        BACKUP_URL.format(norad=norad),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=(10, 20),
    )
    response.raise_for_status()
    data = response.json()
    return parse_tle(f"{data.get('line1', '')}\n{data.get('line2', '')}")


def load_fallback() -> dict:
    """Copia salvata nel progetto: {norad: (riga1, riga2)}."""
    try:
        data = json.loads(FALLBACK_PATH.read_text(encoding="utf-8"))
        return {int(k): tuple(v) for k, v in data.get("satellites", {}).items()}
    except (OSError, ValueError):
        return {}


def epoch_age_days(line1: str, now: float | None = None) -> float | None:
    """Età degli elementi orbitali in giorni (dall'epoca scritta nella riga 1)."""
    try:
        year = int(line1[18:20])
        day_of_year = float(line1[20:32])
    except ValueError:
        return None
    year += 2000 if year < 57 else 1900
    epoch = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day_of_year - 1)
    now_dt = datetime.fromtimestamp(now if now is not None else time.time(), timezone.utc)
    return round((now_dt - epoch).total_seconds() / 86400, 1)


def satellites_with_tle(force: bool = False) -> list:
    """
    Elenco dei satelliti con le righe TLE. Fonti in ordine: CelesTrak, TLE API,
    ultima copia in memoria, copia salvata nel progetto. Così il globo funziona
    anche se le fonti online non rispondono (con posizioni un po' meno precise).
    """
    with _lock:
        if not force and _cache["data"] and time.time() - _cache["time"] < CACHE_SECONDS:
            return _cache["data"]
        previous = {s["norad"]: s for s in _cache["data"]}
    fallback = load_fallback()

    result = []
    for sat in SATELLITES:
        entry = dict(sat)
        tle, source = None, None
        for name, fetcher in (("CelesTrak", fetch_tle), ("TLE API", fetch_tle_backup)):
            try:
                tle = fetcher(sat["norad"])
            except (requests.RequestException, ValueError):
                tle = None
            if tle:
                source = name
                break
        if tle is None and sat["norad"] in previous:
            old = previous[sat["norad"]]
            tle, source = (old["line1"], old["line2"]), old.get("source", "memoria")
        if tle is None and sat["norad"] in fallback:
            tle, source = fallback[sat["norad"]], "copia salvata"
        if tle is None:
            continue
        entry["line1"], entry["line2"] = tle
        entry["source"] = source
        entry["age_days"] = epoch_age_days(tle[0])
        result.append(entry)

    with _lock:
        if result:
            _cache["data"] = result
            _cache["time"] = time.time()
    return result
