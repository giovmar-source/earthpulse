"""
Mare: temperatura della superficie e clorofilla dai servizi ERDDAP di NOAA CoastWatch.

- Temperatura: NOAA OISST v2.1, versione preliminare (ncdcOisst21NrtAgg), griglia
  di 0,25° (circa 25 km), un valore al giorno da satelliti, navi e boe, con
  l'anomalia rispetto alla climatologia del prodotto. Ritardo: circa un giorno.
- Clorofilla-a: NOAA, VIIRS (Suomi NPP, NOAA-20) e Sentinel-3A OLCI, senza buchi
  per le nuvole (metodo DINEOF), circa 9 km (nesdisNPPN20S3ASCIDINEOFDaily, CC0).
  Ritardo: circa 10 giorni.

Gli ultimi 60 giorni disponibili per la cella più vicina al punto. Sulla terraferma
(o troppo vicino alla costa per la cella) i valori mancano.
"""

from __future__ import annotations

import csv
import io
import math
import threading
import time

import requests

ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
DAYS = 60
ATTRIBUTION = ("Temperatura: NOAA OISST v2.1 · Clorofilla: NOAA CoastWatch (VIIRS, OLCI, DINEOF) · "
               "tramite NOAA CoastWatch ERDDAP")

_cache: dict = {}
_lock = threading.Lock()
CACHE_SECONDS = 6 * 3600


class SeaUnavailable(Exception):
    pass


def sst_url(lat: float, lon: float) -> str:
    lon360 = lon % 360
    where = f"[last-{DAYS - 1}:1:last][(0.0)][({lat:.3f})][({lon360:.3f})]"
    return f"{ERDDAP}/ncdcOisst21NrtAgg.csv?sst{where},anom{where}"


def chl_url(lat: float, lon: float) -> str:
    where = f"[last-{DAYS - 1}:1:last][(0.0)][({lat:.3f})][({lon:.3f})]"
    return f"{ERDDAP}/nesdisNPPN20S3ASCIDINEOFDaily.csv?chlor_a{where}"


def parse_csv(text: str, fields: list) -> list:
    """CSV di ERDDAP (seconda riga = unità) -> [{"date", campo: valore o None}]."""
    lines = text.splitlines()
    if len(lines) < 3:
        return []
    reader = csv.DictReader([lines[0]] + lines[2:])
    rows = []
    for row in reader:
        item = {"date": (row.get("time") or "")[:10]}
        for field in fields:
            try:
                value = float(row.get(field, "nan"))
            except ValueError:
                value = math.nan
            item[field] = None if not math.isfinite(value) else round(value, 3)
        rows.append(item)
    return rows


def _fetch(url: str, fields: list, session) -> list:
    try:
        response = session.get(url, timeout=60)
    except requests.RequestException as exc:
        raise SeaUnavailable(f"NOAA ERDDAP non raggiungibile: {exc}") from exc
    if response.status_code != 200:
        raise SeaUnavailable(f"NOAA ERDDAP: errore {response.status_code}")
    return parse_csv(response.text, fields)


def summary(rows: list, field: str) -> dict | None:
    values = [r[field] for r in rows if r[field] is not None]
    if not values:
        return None
    last = next(r for r in reversed(rows) if r[field] is not None)
    return {"latest": last[field], "latest_date": last["date"], "mean": round(sum(values) / len(values), 3),
            "min": min(values), "max": max(values), "days": len(values)}


def analyse(lat: float, lon: float, session=requests) -> dict:
    key = (round(lat, 2), round(lon, 2))
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    sst = _fetch(sst_url(lat, lon), ["sst", "anom"], session)
    try:
        chl = _fetch(chl_url(lat, lon), ["chlor_a"], session)
    except SeaUnavailable:
        chl = []
    sst_summary = summary(sst, "sst")
    result = {
        "status": "ok" if sst_summary else "land",
        "sst": {"series": [{"date": r["date"], "value": r["sst"], "anomaly": r["anom"]} for r in sst],
                "summary": sst_summary, "anomaly": summary(sst, "anom")},
        "chlorophyll": {"series": [{"date": r["date"], "value": r["chlor_a"]} for r in chl],
                        "summary": summary(chl, "chlor_a")},
        "attribution": ATTRIBUTION,
    }
    with _lock:
        _cache[key] = (time.time() + CACHE_SECONDS, result)
        if len(_cache) > 300:
            _cache.clear()
    return result
