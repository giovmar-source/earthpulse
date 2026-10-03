"""
Nomi ufficiali dei luoghi sugli altri corpi celesti e siti di atterraggio.

Nomi: Gazetteer of Planetary Nomenclature (IAU WGPSN / USGS Astrogeology),
file "center points" in formato shapefile, rigenerati ogni notte:
https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/{BODY}_nomenclature_center_pts.zip
Coordinate planetocentriche, longitudine est da 0 a 360: le portiamo a −180…180.
Dati USGS di pubblico dominio; i nomi sono decisioni dell'IAU.

Siti di atterraggio: data/landing_sites.json, con la fonte di ogni coordinata
(NSSDCA e LROC per la Luna, NASA Mars24 per Marte, coordinate approssimate per Venere).
"""

from __future__ import annotations

import io
import json
import math
import struct
import threading
import zipfile
from pathlib import Path

import requests

from src.planets import PlanetDataUnavailable, download

GAZETTEER = "https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/{name}_nomenclature_center_pts.zip"
ATTRIBUTION = "Nomi: IAU WGPSN, Gazetteer of Planetary Nomenclature (USGS Astrogeology)"

# Corpi per cui la mappa del sito usa longitudini da −180 a 180 verificate
NAMED_BODIES = {
    "moon": "MOON", "mars": "MARS", "mercury": "MERCURY", "venus": "VENUS",
    "ceres": "CERES", "vesta": "VESTA", "phobos": "PHOBOS", "enceladus": "ENCELADUS",
}
RADIUS_KM = {"moon": 1737.4, "mars": 3389.5, "mercury": 2439.4, "venus": 6051.8,
             "ceres": 469.7, "vesta": 262.7, "phobos": 11.1, "enceladus": 252.1}

LANDING_FILE = Path(__file__).resolve().parent.parent / "data" / "landing_sites.json"

_features: dict = {}
_lock = threading.Lock()


# ------------------------------------------------------------------
# Lettura del file DBF (tabella degli attributi dello shapefile)
# ------------------------------------------------------------------

def read_dbf(raw: bytes) -> list:
    """File .dbf (dBase III) -> lista di dizionari, con i nomi dei campi in minuscolo."""
    records, header_len, record_len = struct.unpack("<xxxxIHH", raw[:12])
    fields = []
    pos = 32
    while raw[pos] != 0x0D:
        name = raw[pos:pos + 11].split(b"\x00", 1)[0].decode("ascii", "replace").strip().lower()
        ftype = chr(raw[pos + 11])
        length = raw[pos + 16]
        fields.append((name, ftype, length))
        pos += 32
    rows = []
    offset = header_len
    for _ in range(records):
        record = raw[offset:offset + record_len]
        offset += record_len
        if not record or record[:1] == b"*":        # record cancellato
            continue
        row = {}
        cursor = 1
        for name, ftype, length in fields:
            text = record[cursor:cursor + length].decode("utf-8", "replace").strip()
            cursor += length
            if ftype in ("N", "F"):
                try:
                    row[name] = float(text) if text else None
                except ValueError:
                    row[name] = None
            else:
                row[name] = text
        rows.append(row)
    return rows


def pick(row: dict, *names):
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return None


def normalize(rows: list) -> list:
    """Righe del Gazetteer -> elementi con nome, tipo, diametro, coordinate (−180…180)."""
    features = []
    for row in rows:
        name = pick(row, "clean_name", "name")
        lat = pick(row, "center_lat", "lat", "latitude")
        lon = pick(row, "center_lon", "lon", "longitude")
        if name is None or lat is None or lon is None:
            continue
        approval = str(pick(row, "approval", "approvalst", "approval_s") or "")
        if approval and "dropped" in approval.lower():
            continue
        features.append({
            "name": str(name),
            "type": str(pick(row, "type", "feature_ty", "featuretyp", "ftype") or ""),
            "diameter_km": float(pick(row, "diameter", "diam") or 0) or None,
            "lat": float(lat),
            "lon": ((float(lon) + 180.0) % 360.0) - 180.0,
            "origin": str(pick(row, "origin") or "") or None,
        })
    return features


def load_features(body: str, session=requests) -> list:
    with _lock:
        if body in _features:
            return _features[body]
    raw = download(GAZETTEER.format(name=NAMED_BODIES[body]), session)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            dbf_name = next(n for n in archive.namelist() if n.lower().endswith(".dbf"))
            rows = read_dbf(archive.read(dbf_name))
    except (zipfile.BadZipFile, StopIteration, struct.error, IndexError) as exc:
        raise PlanetDataUnavailable(f"Archivio dei nomi in un formato inatteso: {exc}") from exc
    features = normalize(rows)
    with _lock:
        _features[body] = features
    return features


def great_circle_km(lat1, lon1, lat2, lon2, radius_km):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return radius_km * math.acos(max(-1.0, min(1.0, c)))


def place_at(body: str, lat: float, lon: float, session=requests) -> dict | None:
    """
    Il luogo con nome che contiene il punto (il più piccolo, se più d'uno),
    altrimenti il più vicino. Restituisce anche la distanza dal suo centro.
    """
    if body not in NAMED_BODIES:
        return None
    radius = RADIUS_KM[body]
    best_inside = None
    nearest = None
    for f in load_features(body, session):
        d = great_circle_km(lat, lon, f["lat"], f["lon"], radius)
        if f["diameter_km"] and d <= f["diameter_km"] / 2:
            if best_inside is None or f["diameter_km"] < best_inside[0]["diameter_km"]:
                best_inside = (f, d)
        if nearest is None or d < nearest[1]:
            nearest = (f, d)
    chosen = best_inside or nearest
    if chosen is None:
        return None
    f, d = chosen
    return {**f, "distance_km": round(d, 1), "inside": best_inside is not None}


# ------------------------------------------------------------------
# Siti di atterraggio
# ------------------------------------------------------------------

def landing_sites(body: str) -> list:
    data = json.loads(LANDING_FILE.read_text(encoding="utf-8"))
    return [s for s in data["sites"] if s["body"] == body]


def nearest_landing(body: str, lat: float, lon: float, max_km: float) -> dict | None:
    if body not in RADIUS_KM:
        return None
    best = None
    for site in landing_sites(body):
        d = great_circle_km(lat, lon, site["lat"], site["lon"], RADIUS_KM[body])
        if d <= max_km and (best is None or d < best[1]):
            best = (site, d)
    return {**best[0], "distance_km": round(best[1], 1)} if best else None
