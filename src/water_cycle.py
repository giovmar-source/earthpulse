"""
Pioggia e umidità del suolo da NASA POWER (Prediction Of Worldwide Energy Resources).

- PRECTOTCORR: precipitazione giornaliera corretta (mm/giorno), da rianalisi
  NASA MERRA-2 / GEOS corretta con osservazioni; griglia di circa 0,5° × 0,625°.
- GWETTOP: umidità dello strato superficiale del suolo (0–5 cm), 0 = secco, 1 = saturo.
- GWETROOT: umidità nella zona delle radici (fino a circa 1 m), stessa scala.
Sono stime di un modello di rianalisi alimentato da osservazioni, non misure dirette
sul luogo. Ritardo dei dati: da 2 a 7 giorni.

Confronto con la norma: la climatologia POWER del luogo (medie mensili 2001–2020).
Nessuna chiave richiesta. Citazione richiesta da NASA POWER (vedi ATTRIBUTION).
"""

from __future__ import annotations

import threading
import time
from datetime import date, timedelta

import requests

DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
CLIMATOLOGY_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
PARAMETERS = "PRECTOTCORR,GWETTOP,GWETROOT"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
ATTRIBUTION = ("Dati: NASA Langley Research Center, progetto POWER (Prediction Of Worldwide "
               "Energy Resources), finanziato dalla NASA Earth Science Division")

_cache: dict = {}
_lock = threading.Lock()
CACHE_SECONDS = 6 * 3600


class WaterCycleUnavailable(Exception):
    pass


def _get(url: str, params: dict, session) -> dict:
    try:
        response = session.get(url, params=params, timeout=60)
    except requests.RequestException as exc:
        raise WaterCycleUnavailable(f"NASA POWER non raggiungibile: {exc}") from exc
    if response.status_code != 200:
        raise WaterCycleUnavailable(f"NASA POWER: errore {response.status_code}")
    return response.json()


def parse_daily(body: dict) -> dict:
    """Risposta giornaliera -> {parametro: [(data ISO, valore)]}, senza i valori mancanti."""
    fill = body.get("header", {}).get("fill_value", -999.0)
    result = {}
    for name, values in body["properties"]["parameter"].items():
        series = []
        for day, value in sorted(values.items()):
            if value is None or value == fill or value <= -990:
                continue
            series.append((f"{day[:4]}-{day[4:6]}-{day[6:8]}", float(value)))
        result[name] = series
    return result


def parse_climatology(body: dict) -> dict:
    """Climatologia -> {parametro: {mese 1–12: valore}}."""
    fill = body.get("header", {}).get("fill_value", -999.0)
    result = {}
    for name, values in body["properties"]["parameter"].items():
        result[name] = {i + 1: float(values[m]) for i, m in enumerate(MONTHS)
                        if m in values and values[m] is not None and values[m] != fill}
    return result


def analyse(lat: float, lon: float, days: int = 90, session=requests, today: date | None = None) -> dict:
    today = today or date.today()
    key = (round(lat, 2), round(lon, 2), days, today.isoformat())
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
    start = today - timedelta(days=days)
    point = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "community": "AG", "format": "JSON"}
    daily = parse_daily(_get(DAILY_URL, {**point, "parameters": PARAMETERS,
                                         "start": start.strftime("%Y%m%d"), "end": today.strftime("%Y%m%d")}, session))
    climate = parse_climatology(_get(CLIMATOLOGY_URL, {**point, "parameters": PARAMETERS}, session))

    rain = daily.get("PRECTOTCORR", [])
    rain_normal = climate.get("PRECTOTCORR", {})
    total = sum(v for _, v in rain)
    # Norma sugli stessi giorni con dati: media climatologica del mese di ogni giorno
    normal = sum(rain_normal.get(int(d[5:7]), 0.0) for d, _ in rain) if rain_normal else None
    soil = {}
    for name, label in (("GWETTOP", "surface"), ("GWETROOT", "root")):
        series = daily.get(name, [])
        last = series[-1] if series else None
        month_normal = climate.get(name, {}).get(int(last[0][5:7])) if last else None
        soil[label] = {
            "series": [{"date": d, "value": round(v * 100, 1)} for d, v in series],
            "latest": {"date": last[0], "value": round(last[1] * 100, 1)} if last else None,
            "normal": round(month_normal * 100, 1) if month_normal is not None else None,
        }
    result = {
        "period": {"start": start.isoformat(), "end": today.isoformat(), "days": days},
        "rain": {
            "series": [{"date": d, "value": round(v, 1)} for d, v in rain],
            "total_mm": round(total, 1),
            "normal_mm": round(normal, 1) if normal is not None else None,
            "percent_of_normal": round(100 * total / normal) if normal else None,
            "last_date": rain[-1][0] if rain else None,
            "rainy_days": sum(1 for _, v in rain if v >= 1.0),
        },
        "soil": soil,
        "attribution": ATTRIBUTION,
    }
    with _lock:
        _cache[key] = (time.time() + CACHE_SECONDS, result)
        if len(_cache) > 300:
            _cache.clear()
    return result
