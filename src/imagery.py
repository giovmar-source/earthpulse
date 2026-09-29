"""
Immagini Sentinel-2 di un'area: colori reali (RGB) e mappa NDVI.

- RGB: asset "visual" di Sentinel-2 L2A (True Color Image, 8 bit,
  bande B04-B03-B02 a 10 m), con un leggero adattamento del contrasto.
- NDVI: calcolato da B04 e B08 come in src/ndvi.py, colorato con una
  scala marrone -> giallo -> verde; i pixel non validi secondo la SCL
  (nuvole, ombre, neve, dati mancanti) sono grigi.

Le immagini sono restituite come PNG (bytes).
"""

from __future__ import annotations

import io
import math
import os

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MULTIPLEX", "YES")
os.environ.setdefault("VSI_CACHE", "TRUE")

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds
from rasterio.windows import Window

from src.ndvi import INVALID_SCL_CLASSES


# Scala dei colori NDVI: (valore, colore RGB). Tra due valori il colore
# viene interpolato linearmente.
NDVI_COLOR_STOPS = [
    (-0.20, (59, 110, 168)),   # acqua
    (0.00, (200, 184, 154)),   # suolo nudo / urbano
    (0.20, (232, 216, 140)),   # vegetazione molto rada
    (0.40, (166, 217, 106)),   # vegetazione rada
    (0.60, (76, 168, 74)),     # vegetazione
    (0.80, (26, 107, 47)),     # vegetazione densa
    (1.00, (11, 61, 28)),      # vegetazione molto densa
]
INVALID_COLOR = (180, 180, 180)


def color_stops_hex() -> list:
    """Legenda per l'app: [[valore, "#rrggbb"], ...]."""
    return [
        [value, "#%02x%02x%02x" % rgb] for value, rgb in NDVI_COLOR_STOPS
    ]


# ------------------------------------------------------------------
# Lettura delle finestre raster
# ------------------------------------------------------------------

def pixel_window(src, bbox_wgs84) -> Window:
    """Finestra (in pixel) del raster che copre il bbox WGS84."""
    left, bottom, right, top = transform_bounds(
        "EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21
    )
    inverse = ~src.transform
    c0, r0 = inverse * (left, top)
    c1, r1 = inverse * (right, bottom)

    col_off = int(math.floor(min(c0, c1)))
    row_off = int(math.floor(min(r0, r1)))
    width = max(1, int(math.ceil(max(c0, c1))) - col_off)
    height = max(1, int(math.ceil(max(r0, r1))) - row_off)
    return Window(col_off, row_off, width, height)


def read_window(href: str, bbox_wgs84, indexes=1, out_shape=None):
    """
    Legge la porzione di raster che copre il bbox.
    out_shape (righe, colonne) permette di ricampionare (nearest),
    ad esempio la SCL a 20 m sulla griglia delle bande a 10 m.
    Le parti fuori dalla scena sono riempite con 0 (= nessun dato).
    """
    with rasterio.open(href) as src:
        window = pixel_window(src, bbox_wgs84)
        kwargs = {
            "window": window,
            "boundless": True,
            "fill_value": 0,
        }
        if out_shape is not None:
            if isinstance(indexes, int):
                kwargs["out_shape"] = out_shape
            else:
                kwargs["out_shape"] = (len(indexes),) + tuple(out_shape)
            kwargs["resampling"] = Resampling.nearest
        return src.read(indexes, **kwargs)


def valid_mask_from_scl(scl: np.ndarray) -> np.ndarray:
    return (scl != 0) & ~np.isin(scl, INVALID_SCL_CLASSES)


def scl_valid_percentage(item, bbox_wgs84) -> float:
    """Percentuale di pixel validi (SCL) nell'area: lettura leggera a 20 m."""
    scl = read_window(item.assets["scl"].href, bbox_wgs84)
    if scl.size == 0:
        return 0.0
    return float(100.0 * valid_mask_from_scl(scl).mean())


# ------------------------------------------------------------------
# Elaborazione delle immagini
# ------------------------------------------------------------------

def stretch_rgb(rgb: np.ndarray) -> np.ndarray:
    """
    Adatta il contrasto dell'immagine a colori reali
    (percentili 2–98 calcolati sui pixel con dati), per immagini
    leggibili anche quando la TCI risulta scura.

    rgb: array (3, righe, colonne) uint8 -> (righe, colonne, 3) uint8
    """
    data = rgb.astype(np.float32)
    has_data = np.any(rgb > 0, axis=0)

    if has_data.sum() < 10:
        return np.transpose(rgb, (1, 2, 0)).astype(np.uint8)

    values = data[:, has_data]
    low, high = np.percentile(values, [2, 98])
    if high - low < 1:
        high = low + 1

    stretched = (data - low) / (high - low)
    stretched = np.clip(stretched, 0, 1) ** 0.9 * 255
    stretched[:, ~has_data] = 0
    return np.transpose(stretched, (1, 2, 0)).astype(np.uint8)


def colorize_ndvi(ndvi: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """NDVI (righe, colonne) -> immagine RGB uint8 con la scala del progetto."""
    values = np.array([v for v, _ in NDVI_COLOR_STOPS], dtype=np.float32)
    colors = np.array([c for _, c in NDVI_COLOR_STOPS], dtype=np.float32)

    clipped = np.clip(np.nan_to_num(ndvi, nan=0.0), values[0], values[-1])
    image = np.zeros(ndvi.shape + (3,), dtype=np.float32)
    for channel in range(3):
        image[..., channel] = np.interp(clipped, values, colors[:, channel])

    image[~valid] = INVALID_COLOR
    return image.astype(np.uint8)


def compute_ndvi_grid(red: np.ndarray, nir: np.ndarray, scl: np.ndarray):
    """Restituisce (ndvi, valid) sulla griglia a 10 m."""
    red = red.astype(np.float32)
    nir = nir.astype(np.float32)
    denominator = nir + red

    valid = (
        valid_mask_from_scl(scl)
        & (red > 0)
        & (nir > 0)
        & (denominator != 0)
    )
    ndvi = np.full(red.shape, np.nan, dtype=np.float32)
    ndvi[valid] = (nir[valid] - red[valid]) / denominator[valid]
    return ndvi, valid


def to_png(image: np.ndarray, upscale: int = 1) -> bytes:
    """Array (righe, colonne, 3) uint8 -> PNG. upscale: ingrandimento nearest."""
    picture = Image.fromarray(np.ascontiguousarray(image, dtype=np.uint8))
    if upscale > 1:
        picture = picture.resize(
            (picture.width * upscale, picture.height * upscale),
            Image.NEAREST,
        )
    buffer = io.BytesIO()
    picture.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


# ------------------------------------------------------------------
# Scelta della scena
# ------------------------------------------------------------------

def choose_clear_scene(rows, min_valid: float = 95.0,
                       fallback_min_valid: float = 70.0):
    """
    rows: [(item, percentuale_valida o None, errore o None)] nell'ordine
    di preferenza (ad esempio dalla più recente).

    Restituisce (item, percentuale) della prima scena quasi senza nuvole
    (>= min_valid); altrimenti la scena con più pixel validi, purché
    >= fallback_min_valid; altrimenti None.
    """
    measured = [(item, pct) for item, pct, _err in rows if pct is not None]

    for item, pct in measured:
        if pct >= min_valid:
            return item, pct

    if measured:
        item, pct = max(measured, key=lambda row: row[1])
        if pct >= fallback_min_valid:
            return item, pct

    return None


# ------------------------------------------------------------------
# Rendering di un item Sentinel-2
# ------------------------------------------------------------------

def render_rgb_png(item, bbox_wgs84) -> bytes:
    rgb = read_window(item.assets["visual"].href, bbox_wgs84, indexes=[1, 2, 3])
    return to_png(stretch_rgb(rgb))


def render_ndvi_png(item, bbox_wgs84) -> bytes:
    red = read_window(item.assets["red"].href, bbox_wgs84)
    nir = read_window(item.assets["nir"].href, bbox_wgs84, out_shape=red.shape)
    scl = read_window(item.assets["scl"].href, bbox_wgs84, out_shape=red.shape)
    ndvi, valid = compute_ndvi_grid(red, nir, scl)
    return to_png(colorize_ndvi(ndvi, valid))


def render_png(item, bbox_wgs84, kind: str) -> bytes:
    if kind == "rgb":
        return render_rgb_png(item, bbox_wgs84)
    if kind == "ndvi":
        return render_ndvi_png(item, bbox_wgs84)
    raise ValueError(f"Tipo di immagine non supportato: {kind}")
