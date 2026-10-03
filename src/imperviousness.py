"""
Suolo impermeabilizzato (cemento, asfalto, edifici) da Copernicus Land Monitoring
Service: High Resolution Layer Imperviousness Density 2018, pixel di 10 m,
percentuale di superficie impermeabile in ogni pixel (0–100).

Servizio pubblico dell'Agenzia europea dell'ambiente (ArcGIS ImageServer). È
l'ultima annata con un servizio di consultazione: le edizioni successive sono solo
da scaricare. Copertura: paesi EEA38 e Regno Unito. Valori sopra 100 = fuori
copertura. Licenza Copernicus: libera anche per uso commerciale, con citazione.
"""

from __future__ import annotations

import io
from collections import OrderedDict

import numpy as np
import requests
from PIL import Image

from src.sentinel5p import area_bbox

SERVICE = ("https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLandPublic/"
           "HRL_ImperviousnessDensity_2018/ImageServer/exportImage")
SIDE_KM = 2.0
SIZE = 200                      # 10 m per pixel
YEAR = 2018
ATTRIBUTION = ("Generato con informazioni del Copernicus Land Monitoring Service dell'Unione europea "
               "(HRL Imperviousness Density 2018)")
STOPS = [(0, (250, 240, 200)), (20, (250, 200, 90)), (50, (230, 110, 50)), (80, (170, 40, 60)), (100, (80, 10, 60))]

_cache: OrderedDict = OrderedDict()


class ImperviousnessUnavailable(Exception):
    pass


def export_params(bbox: list) -> dict:
    return {
        "bbox": ",".join(f"{v:.6f}" for v in bbox), "bboxSR": "4326", "imageSR": "4326",
        "size": f"{SIZE},{SIZE}", "format": "tiff", "pixelType": "U8",
        "interpolation": "RSP_NearestNeighbor", "f": "image",
    }


def read_values(content: bytes) -> np.ndarray:
    from rasterio.io import MemoryFile
    try:
        with MemoryFile(content) as memfile, memfile.open() as dataset:
            values = dataset.read(1).astype(np.float32)
    except Exception as exc:                       # risposta non TIFF (es. messaggio di errore)
        raise ImperviousnessUnavailable("Il servizio europeo non ha restituito un'immagine valida.") from exc
    values[values > 100] = np.nan
    return values


def colorize(values: np.ndarray) -> np.ndarray:
    xs = [s[0] for s in STOPS]
    out = np.zeros(values.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(np.nan_to_num(values, nan=0), xs, [s[1][c] for s in STOPS])
    out[np.isnan(values)] = (90, 90, 90)
    return out


def analyse(lat: float, lon: float, session=requests) -> dict:
    key = (round(lat, 4), round(lon, 4))
    if key in _cache:
        return _cache[key]
    bbox = area_bbox(lat, lon, half_km=SIDE_KM / 2)
    try:
        response = session.get(SERVICE, params=export_params(bbox), timeout=60)
    except requests.RequestException as exc:
        raise ImperviousnessUnavailable(f"Servizio europeo non raggiungibile: {exc}") from exc
    if response.status_code != 200:
        raise ImperviousnessUnavailable(f"Servizio europeo: errore {response.status_code}")
    values = read_values(response.content)
    valid = np.isfinite(values)
    if valid.mean() < 0.5:
        result = {"status": "outside", "year": YEAR,
                  "message": "Il luogo è fuori dall'area coperta (paesi dell'Agenzia europea dell'ambiente)."}
    else:
        pixel_ha = (SIDE_KM * 1000 / SIZE) ** 2 / 10000
        buffer = io.BytesIO()
        Image.fromarray(colorize(values).astype(np.uint8)).save(buffer, format="PNG")
        center = values[SIZE // 2 - 5:SIZE // 2 + 5, SIZE // 2 - 5:SIZE // 2 + 5]
        result = {
            "status": "ok", "year": YEAR, "side_km": SIDE_KM,
            "mean_percent": round(float(np.nanmean(values)), 1),
            "sealed_ha": round(float(np.nansum(values) / 100 * pixel_ha), 1),
            "area_ha": round(float(valid.sum()) * pixel_ha, 1),
            "built_share_percent": round(100 * float((values[valid] > 0).mean()), 1),
            "center_percent": round(float(np.nanmean(center)), 1) if np.isfinite(center).any() else None,
            "legend": {"color_stops": [[s[0], "#%02x%02x%02x" % s[1]] for s in STOPS],
                       "labels": ["0%", "50%", "100%"]},
            "png": buffer.getvalue(),
            "attribution": ATTRIBUTION,
        }
    _cache[key] = result
    while len(_cache) > 200:
        _cache.popitem(last=False)
    return result
