"""
Acqua e allagamenti dal radar di Sentinel-1 (Copernicus Data Space, Sentinel Hub).

Il radar vede il suolo anche attraverso le nuvole e di notte. L'acqua calma
riflette il segnale lontano dal satellite e appare molto scura: un pixel è
classificato come acqua se la retrodiffusione VV è sotto −18 dB (soglia fissa
usata in letteratura per Sentinel-1 IW; Twele et al. 2016 e script Sentinel Hub).

Si confrontano due periodi di 12 giorni (un'immagine per orbita più recente):
- adesso: gli ultimi 12 giorni;
- riferimento: gli stessi giorni un anno prima, oppure i 12 giorni di un mese prima.
Acqua presente in entrambi = acqua permanente; solo adesso = acqua nuova
(possibile allagamento); solo prima = acqua sparita.

Limiti dichiarati: superfici molto lisce (asfalto, sabbia asciutta, neve bagnata)
possono sembrare acqua; i rilievi creano ombre radar; il vento increspa l'acqua e
la rende più chiara. Area di 6 × 6 km, pixel di 20 m.
"""

from __future__ import annotations

import io
from collections import OrderedDict
from datetime import date, timedelta

import numpy as np
import requests
from PIL import Image

from src import sentinel5p

CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
SIDE_KM = 6.0
SIZE = 300                      # 20 m per pixel
WATER_DB = -18.0
WINDOW_DAYS = 12
ATTRIBUTION = "Contiene dati Copernicus Sentinel-1 modificati, elaborati con Copernicus Data Space Ecosystem"

COLORS = {"permanent": (31, 79, 209), "new": (255, 59, 48), "lost": (255, 204, 0)}

_cache: OrderedDict = OrderedDict()
MAX_CACHE = 60


class SarUnavailable(Exception):
    pass


def windows(reference: str, today: date | None = None) -> dict:
    today = today or date.today()
    now = (today - timedelta(days=WINDOW_DAYS), today)
    if reference == "month":
        ref = (now[0] - timedelta(days=30), now[1] - timedelta(days=30))
    else:
        ref = (sentinel5p.shift_year(now[0]), sentinel5p.shift_year(now[1]))
    return {"now": now, "reference": ref}


EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV", "dataMask"] }],
    output: { bands: 2, sampleType: "FLOAT32" },
    mosaicking: "SIMPLE"
  };
}
function evaluatePixel(s) {
  return [s.VV, s.dataMask];
}
"""


def request_body(bbox: list, start: date, end: date) -> dict:
    return {
        "input": {
            "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
            "data": [{
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {"from": f"{start.isoformat()}T00:00:00Z", "to": f"{end.isoformat()}T23:59:59Z"},
                    "acquisitionMode": "IW", "polarization": "DV", "resolution": "HIGH",
                    "mosaickingOrder": "mostRecent",
                },
                "processing": {"backCoeff": "SIGMA0_ELLIPSOID", "orthorectify": True, "demInstance": "COPERNICUS"},
            }],
        },
        "output": {"width": SIZE, "height": SIZE,
                   "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        "evalscript": EVALSCRIPT,
    }


def _spend() -> None:
    try:
        sentinel5p._spend()
    except sentinel5p.S5PUnavailable as exc:
        raise SarUnavailable(str(exc)) from exc


def token(session) -> str:
    try:
        return sentinel5p.get_token(session)
    except sentinel5p.S5PUnavailable as exc:
        raise SarUnavailable(str(exc).replace("Sentinel-5P", "Sentinel-1")) from exc


def latest_acquisition(bbox: list, start: date, end: date, session=requests) -> str | None:
    """Data e ora dell'ultimo passaggio di Sentinel-1 sull'area nel periodo (Catalog API)."""
    body = {"bbox": bbox, "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
            "collections": ["sentinel-1-grd"], "limit": 20}
    _spend()
    response = session.post(CATALOG_URL, json=body, headers={"Authorization": f"Bearer {token(session)}"}, timeout=30)
    if response.status_code != 200:
        return None
    dates = sorted(f["properties"]["datetime"] for f in response.json().get("features", [])
                   if f.get("properties", {}).get("datetime"))
    return dates[-1] if dates else None


def read_two_bands(content: bytes) -> tuple:
    from rasterio.io import MemoryFile
    with MemoryFile(content) as memfile, memfile.open() as dataset:
        return dataset.read(1).astype(np.float32), dataset.read(2).astype(np.float32)


def fetch_backscatter(bbox: list, start: date, end: date, session=requests) -> np.ndarray:
    """VV in dB, NaN dove non ci sono dati."""
    _spend()
    response = session.post(sentinel5p.PROCESS_URL, json=request_body(bbox, start, end),
                            headers={"Authorization": f"Bearer {token(session)}", "Accept": "image/tiff"}, timeout=120)
    if response.status_code == 401:
        sentinel5p._token["value"] = None
    if response.status_code == 429:
        raise SarUnavailable("Quota di Copernicus Data Space raggiunta: riprova più tardi.")
    if response.status_code != 200:
        raise SarUnavailable(f"Sentinel Hub ha risposto con errore {response.status_code}: {response.text[:200]}")
    vv, mask = read_two_bands(response.content)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10 * np.log10(np.where(vv > 0, vv, np.nan))
    db[(mask < 0.5) | ~np.isfinite(db)] = np.nan
    return db


def smooth(mask: np.ndarray) -> np.ndarray:
    """Maggioranza su 3 × 3 pixel: toglie il rumore "sale e pepe" del radar."""
    padded = np.pad(mask.astype(np.float32), 1, mode="edge")
    total = sum(padded[i:i + mask.shape[0], j:j + mask.shape[1]] for i in range(3) for j in range(3))
    return total >= 5


def classify(db_now: np.ndarray, db_ref: np.ndarray) -> dict:
    valid = np.isfinite(db_now) & np.isfinite(db_ref)
    water_now = smooth(np.nan_to_num(db_now, nan=0) < WATER_DB) & valid
    water_ref = smooth(np.nan_to_num(db_ref, nan=0) < WATER_DB) & valid
    pixel_ha = (SIDE_KM * 1000 / SIZE) ** 2 / 10000
    classes = {
        "permanent": water_now & water_ref,
        "new": water_now & ~water_ref,
        "lost": water_ref & ~water_now,
    }
    stats = {k: round(float(v.sum()) * pixel_ha, 1) for k, v in classes.items()}
    stats.update({
        "water_now_ha": round(float(water_now.sum()) * pixel_ha, 1),
        "water_ref_ha": round(float(water_ref.sum()) * pixel_ha, 1),
        "valid_percent": round(100.0 * float(valid.mean()), 1),
    })
    return {"classes": classes, "stats": stats, "valid": valid}


def render(db_now: np.ndarray, classes: dict, valid: np.ndarray) -> bytes:
    """Radar di adesso in grigio (−25…0 dB), con l'acqua colorata sopra."""
    grey = np.clip((np.nan_to_num(db_now, nan=-25) + 25) / 25, 0, 1) * 255
    image = np.repeat(grey[..., None], 3, axis=2)
    image[~valid] = (60, 60, 60)
    for key, color in COLORS.items():
        image[classes[key]] = 0.25 * image[classes[key]] + 0.75 * np.array(color)
    buffer = io.BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def analyse(lat: float, lon: float, reference: str = "year", session=requests, today: date | None = None) -> dict:
    today = today or date.today()
    key = (round(lat, 3), round(lon, 3), reference, today.isoformat())
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    bbox = sentinel5p.area_bbox(lat, lon, half_km=SIDE_KM / 2)
    w = windows(reference, today)
    acquired_now = latest_acquisition(bbox, *w["now"], session=session)
    acquired_ref = latest_acquisition(bbox, *w["reference"], session=session)
    if acquired_now is None or acquired_ref is None:
        result = {"status": "no_data", "windows": {k: [d.isoformat() for d in v] for k, v in w.items()},
                  "message": "Nessun passaggio radar di Sentinel-1 su quest'area in uno dei due periodi."}
    else:
        db_now = fetch_backscatter(bbox, *w["now"], session=session)
        db_ref = fetch_backscatter(bbox, *w["reference"], session=session)
        c = classify(db_now, db_ref)
        result = {"status": "ok", "stats": c["stats"], "png": render(db_now, c["classes"], c["valid"]),
                  "acquired": {"now": acquired_now, "reference": acquired_ref},
                  "windows": {k: [d.isoformat() for d in v] for k, v in w.items()}}
    _cache[key] = result
    while len(_cache) > MAX_CACHE:
        _cache.popitem(last=False)
    return result
