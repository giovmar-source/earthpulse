"""
Dati per la mappa del Sistema solare e per il Sole dal vivo.

- Cerere e Vesta: elementi orbitali osculanti dal JPL Small-Body Database
  (ssd-api.jpl.nasa.gov/sbdb.api), aggiornati una volta al giorno. Se il JPL
  non risponde si usano elementi salvati (epoca indicata nella risposta).
- Sonde nello spazio: traiettorie eliocentriche dal servizio JPL Horizons
  (vettori sull'eclittica J2000, in UA), da un anno prima a un anno dopo la data
  di oggi, un punto ogni 5 giorni. Il sito interpola tra i punti.
- Sole: ultime immagini del Solar Dynamics Observatory (NASA), con la data di
  ripresa letta dall'intestazione Last-Modified. Immagini NASA non coperte da
  copyright; credito richiesto: "Courtesy of NASA/SDO and the AIA, EVE, and HMI
  science teams."
"""

from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

SBDB_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
SDO_LATEST = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_{size}_{product}.jpg"

JPL_ATTRIBUTION = "Orbite: NASA/JPL Solar System Dynamics (Small-Body Database, Horizons)"
SDO_ATTRIBUTION = "Courtesy of NASA/SDO and the AIA, EVE, and HMI science teams."

# Elementi di riserva (JPL SBDB, epoca JD 2460000.5 = 24 febbraio 2023, eclittica J2000)
FALLBACK_ELEMENTS = {
    "ceres": {"a": 2.76718174, "e": 0.07881745, "i": 10.58634327, "om": 80.260148690589,
              "w": 73.470461544247, "ma": 17.215651496148, "n": 0.21411522, "epoch": 2460000.5},
    "vesta": {"a": 2.36303821, "e": 0.08875750, "i": 7.13925798, "om": 103.75730014935,
              "w": 151.59916398802, "ma": 115.13298959749, "n": 0.27133009, "epoch": 2460000.5},
}
SMALL_BODIES = {"ceres": ("Ceres", "Cerere"), "vesta": ("Vesta", "Vesta")}

# Sonde: identificativo Horizons, nome, agenzia, descrizione breve
SPACECRAFT = [
    {"id": "-31", "key": "voyager1", "name": "Voyager 1", "agency": "NASA",
     "note": "Lanciata nel 1977, nello spazio interstellare dal 2012."},
    {"id": "-32", "key": "voyager2", "name": "Voyager 2", "agency": "NASA",
     "note": "Lanciata nel 1977, l'unica ad aver visitato Urano e Nettuno."},
    {"id": "-98", "key": "newhorizons", "name": "New Horizons", "agency": "NASA",
     "note": "Ha sorvolato Plutone nel 2015 e Arrokoth nel 2019."},
    {"id": "-96", "key": "parker", "name": "Parker Solar Probe", "agency": "NASA",
     "note": "La sonda che passa più vicino al Sole."},
    {"id": "-144", "key": "solarorbiter", "name": "Solar Orbiter", "agency": "ESA/NASA",
     "note": "Osserva il Sole da vicino, anche dai poli."},
    {"id": "-121", "key": "bepicolombo", "name": "BepiColombo", "agency": "ESA/JAXA",
     "note": "In viaggio verso Mercurio."},
    {"id": "-61", "key": "juno", "name": "Juno", "agency": "NASA",
     "note": "In orbita intorno a Giove dal 2016."},
    {"id": "-28", "key": "juice", "name": "JUICE", "agency": "ESA",
     "note": "In viaggio verso Giove e le sue lune ghiacciate."},
    {"id": "-159", "key": "clipper", "name": "Europa Clipper", "agency": "NASA",
     "note": "In viaggio verso Giove per studiare Europa."},
    {"id": "-255", "key": "psyche", "name": "Psyche", "agency": "NASA",
     "note": "In viaggio verso l'asteroide metallico Psyche."},
    {"id": "-49", "key": "lucy", "name": "Lucy", "agency": "NASA",
     "note": "Visiterà gli asteroidi troiani di Giove."},
    {"id": "-91", "key": "hera", "name": "Hera", "agency": "ESA",
     "note": "In viaggio verso l'asteroide doppio Didymos-Dimorphos."},
    {"id": "-64", "key": "apex", "name": "OSIRIS-APEX", "agency": "NASA",
     "note": "In viaggio verso l'asteroide Apophis (arrivo nel 2029)."},
]

SDO_PRODUCTS = {
    "0171": {"label": "171 Å · corona", "text": "Ultravioletto estremo: plasma della corona a circa 600 000 °C, con gli archi magnetici."},
    "0193": {"label": "193 Å · corona calda", "text": "Ultravioletto estremo: corona a circa 1,2 milioni di °C; le zone scure sono buchi coronali."},
    "0304": {"label": "304 Å · cromosfera", "text": "Elio ionizzato a circa 50 000 °C: la cromosfera e le protuberanze sul bordo."},
    "HMIIC": {"label": "Luce visibile", "text": "La superficie visibile (fotosfera) con le macchie solari, in falsi colori."},
    "HMIB": {"label": "Campo magnetico", "text": "Magnetogramma: bianco e nero sono le due polarità del campo magnetico in superficie."},
}

_lock = threading.Lock()
_elements: dict = {}       # "data" -> risposta
_tracks: dict = {}         # (id, giorno) -> traiettoria
_sun: dict = {}            # prodotto -> (scadenza, immagine, data)
SUN_CACHE_SECONDS = 600


class SolarDataUnavailable(Exception):
    pass


# ------------------------------------------------------------------
# Cerere e Vesta (JPL SBDB)
# ------------------------------------------------------------------

def parse_sbdb(body: dict) -> dict:
    orbit = body["orbit"]
    values = {item["name"]: float(item["value"]) for item in orbit["elements"]}
    return {"a": values["a"], "e": values["e"], "i": values["i"], "om": values["om"],
            "w": values["w"], "ma": values["ma"], "n": values["n"], "epoch": float(orbit["epoch"])}


def jd_to_date(jd: float) -> str:
    return (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - 2440587.5)).date().isoformat()


def small_bodies(session=requests, today: date | None = None) -> list:
    key = (today or date.today()).isoformat()
    with _lock:
        if key in _elements:
            return _elements[key]
        result = []
        for k, (sstr, name) in SMALL_BODIES.items():
            source = "JPL Small-Body Database"
            try:
                response = session.get(SBDB_URL, params={"sstr": sstr, "full-prec": "1"}, timeout=20)
                elements = parse_sbdb(response.json()) if response.status_code == 200 else None
            except (requests.RequestException, ValueError, KeyError, TypeError):
                elements = None
            if elements is None:
                elements = FALLBACK_ELEMENTS[k]
                source = "JPL Small-Body Database (elementi salvati: il servizio non ha risposto)"
            result.append({"key": k, "name": name, "elements": elements,
                           "epoch_date": jd_to_date(elements["epoch"]), "source": source})
        _elements.clear()
        _elements[key] = result
        return result


# ------------------------------------------------------------------
# Sonde (JPL Horizons)
# ------------------------------------------------------------------

def horizons_params(target: str, start: date, stop: date, step_days: int = 5) -> dict:
    return {
        "format": "json", "COMMAND": f"'{target}'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'", "CENTER": "'500@10'", "REF_PLANE": "'ECLIPTIC'",
        "REF_SYSTEM": "'ICRF'", "OUT_UNITS": "'AU-D'", "VEC_TABLE": "'1'", "VEC_CORR": "'NONE'",
        "VEC_LABELS": "'NO'", "CSV_FORMAT": "'YES'",
        "START_TIME": f"'{start.isoformat()}'", "STOP_TIME": f"'{stop.isoformat()}'",
        "STEP_SIZE": f"'{step_days} d'",
    }


def parse_vectors(text: str) -> list:
    """Righe tra $$SOE e $$EOE -> [{"jd", "x", "y", "z"}] (UA)."""
    if "$$SOE" not in text:
        return []
    block = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    points = []
    for line in block.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            points.append({"jd": float(parts[0]), "x": float(parts[2]), "y": float(parts[3]), "z": float(parts[4])})
        except ValueError:
            continue
    return points


def fetch_track(target: str, start: date, stop: date, session=requests) -> list:
    try:
        response = session.get(HORIZONS_URL, params=horizons_params(target, start, stop), timeout=40)
        if response.status_code != 200:
            return []
        return parse_vectors(response.json().get("result", ""))
    except (requests.RequestException, ValueError):
        return []


def spacecraft(session=requests, today: date | None = None, pause: float = 0.5) -> list:
    """Traiettorie delle sonde da un anno prima a un anno dopo oggi (quelle disponibili)."""
    today = today or date.today()
    result = []
    for craft in SPACECRAFT:
        key = (craft["id"], today.isoformat())
        with _lock:
            cached = _tracks.get(key)
        if cached is None:
            points = fetch_track(craft["id"], today - timedelta(days=365), today + timedelta(days=365), session)
            if not points:      # effemeridi solo fino a oggi (missioni concluse o previsioni assenti)
                points = fetch_track(craft["id"], today - timedelta(days=365), today, session)
            cached = points
            with _lock:
                _tracks[key] = cached
            if pause:
                time.sleep(pause)   # Horizons: richieste una alla volta
        if cached:
            result.append({**{k: craft[k] for k in ("key", "name", "agency", "note")},
                           "track": [[round(p["jd"], 3), round(p["x"], 5), round(p["y"], 5), round(p["z"], 5)] for p in cached]})
    return result


# ------------------------------------------------------------------
# Sole (SDO)
# ------------------------------------------------------------------

def sun_image(product: str, session=requests, size: int = 1024) -> tuple:
    """(immagine JPEG, data di ripresa ISO o None), con cache di 10 minuti."""
    now = time.time()
    with _lock:
        cached = _sun.get(product)
    if cached and cached[0] > now:
        return cached[1], cached[2]
    try:
        response = session.get(SDO_LATEST.format(size=size, product=product), timeout=30)
    except requests.RequestException as exc:
        if cached:
            return cached[1], cached[2]
        raise SolarDataUnavailable(f"SDO non raggiungibile: {exc}") from exc
    if response.status_code != 200:
        if cached:
            return cached[1], cached[2]
        raise SolarDataUnavailable(f"SDO: errore {response.status_code}")
    observed = None
    modified = response.headers.get("Last-Modified") if hasattr(response, "headers") else None
    if modified:
        try:
            observed = parsedate_to_datetime(modified).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            observed = None
    with _lock:
        _sun[product] = (now + SUN_CACHE_SECONDS, response.content, observed)
    return response.content, observed
