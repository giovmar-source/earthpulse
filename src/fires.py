"""
Incendi attivi da NASA FIRMS (Fire Information for Resource Management System).

Punti di calore rilevati dai satelliti VIIRS (Suomi NPP, NOAA-20, NOAA-21), pixel
di 375 m, negli ultimi giorni (massimo 5), entro un raggio dal luogo. Dati NRT
(quasi in tempo reale, circa 3 ore dopo il passaggio). Un punto di calore non è
sempre un incendio di vegetazione: anche fiaccole industriali, vulcani, roghi
agricoli. Serve una chiave gratuita FIRMS (MAP_KEY) nella variabile d'ambiente
FIRMS_MAP_KEY. Dati NASA a uso libero, anche commerciale, con citazione.
"""

from __future__ import annotations

import csv
import io
import math
import os
import threading
import time

import requests

AREA_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{w:.4f},{s:.4f},{e:.4f},{n:.4f}/{days}"
SOURCES = {"VIIRS_SNPP_NRT": "Suomi NPP", "VIIRS_NOAA20_NRT": "NOAA-20", "VIIRS_NOAA21_NRT": "NOAA-21"}
CONFIDENCE = {"l": "bassa", "n": "nominale", "h": "alta"}
ATTRIBUTION = "Punti di calore: NASA FIRMS (VIIRS 375 m, NRT), LANCE / NASA EOSDIS"

_cache: dict = {}
_lock = threading.Lock()
CACHE_SECONDS = 30 * 60


class FiresUnavailable(Exception):
    pass


def has_key() -> bool:
    return bool(os.environ.get("FIRMS_MAP_KEY"))


def bbox(lat: float, lon: float, radius_km: float) -> tuple:
    dlat = radius_km / 110.574
    dlon = radius_km / (111.320 * max(0.2, math.cos(math.radians(lat))))
    return lon - dlon, max(-90, lat - dlat), lon + dlon, min(90, lat + dlat)


def distance_and_bearing(lat1, lon1, lat2, lon2) -> tuple:
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    dist = 6371.0 * math.acos(max(-1.0, min(1.0, c)))
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return dist, (math.degrees(math.atan2(y, x)) + 360) % 360


def parse_csv(text: str, satellite: str, lat: float, lon: float, radius_km: float) -> list:
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            plat, plon = float(row["latitude"]), float(row["longitude"])
        except (KeyError, ValueError):
            continue
        dist, bearing = distance_and_bearing(lat, lon, plat, plon)
        if dist > radius_km:
            continue
        hhmm = (row.get("acq_time") or "").zfill(4)
        rows.append({
            "lat": plat, "lon": plon, "distance_km": round(dist, 1), "bearing": round(bearing),
            "date": row.get("acq_date"), "time_utc": f"{hhmm[:2]}:{hhmm[2:]}",
            "satellite": satellite,
            "confidence": CONFIDENCE.get((row.get("confidence") or "").lower(), row.get("confidence")),
            "frp_mw": float(row["frp"]) if row.get("frp") not in (None, "") else None,
            "night": (row.get("daynight") or "") == "N",
        })
    return rows


def detections(lat: float, lon: float, radius_km: float = 50, days: int = 5, session=requests) -> dict:
    if not has_key():
        raise FiresUnavailable("Incendi non ancora attivi: serve una chiave gratuita NASA FIRMS "
                               "(variabile FIRMS_MAP_KEY sul server).")
    key = (round(lat, 2), round(lon, 2), radius_km, days)
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    w, s, e, n = bbox(lat, lon, radius_km)
    points = []
    errors = 0
    for source, satellite in SOURCES.items():
        url = AREA_URL.format(key=os.environ["FIRMS_MAP_KEY"], source=source, w=w, s=s, e=e, n=n, days=days)
        try:
            response = session.get(url, timeout=40)
        except requests.RequestException:
            errors += 1
            continue
        if response.status_code != 200 or response.text.lstrip().lower().startswith(("invalid", "error")):
            errors += 1
            continue
        points.extend(parse_csv(response.text, satellite, lat, lon, radius_km))
    if errors == len(SOURCES):
        raise FiresUnavailable("NASA FIRMS non ha risposto: riprova più tardi o controlla la chiave.")
    points.sort(key=lambda p: (p["date"] or "", p["time_utc"]), reverse=True)
    result = {"radius_km": radius_km, "days": days, "count": len(points), "points": points[:300],
              "nearest_km": min((p["distance_km"] for p in points), default=None),
              "attribution": ATTRIBUTION}
    with _lock:
        _cache[key] = (time.time() + CACHE_SECONDS, result)
        if len(_cache) > 300:
            _cache.clear()
    return result
