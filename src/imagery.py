"""
Immagini Sentinel-2 di un'area: colori reali (RGB) e mappa NDVI.

- RGB: asset "visual" di Sentinel-2 L2A (True Color Image, 8 bit,
  bande B04-B03-B02 a 10 m), con un contrasto FISSO uguale per tutte
  le date, così le immagini sono confrontabili.
- NDVI: calcolato da B04 e B08 come in src/ndvi.py, con scala di colori
  FISSA; i pixel non validi secondo la SCL (nuvole, ombre, neve, dati
  mancanti) sono grigi.
- Variazione: NDVI(dopo) - NDVI(prima), solo sui pixel validi in
  entrambe le date, con scala divergente rosso -> bianco -> verde.

Tutte le immagini sono ricampionate sulla STESSA griglia (UTM, 10 m,
centrata sul punto), anche se le scene provengono da tile Sentinel-2
diversi: così prima e dopo coincidono pixel per pixel.
"""

from __future__ import annotations

import io
import math
import os

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("VSI_CACHE", "TRUE")
# Tempi massimi: una lettura remota bloccata diventa un errore
# dopo pochi secondi invece di bloccare il server.
os.environ.setdefault("GDAL_HTTP_CONNECTTIMEOUT", "10")
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "30")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "2")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "1")

import numpy as np
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform, transform_bounds
from rasterio.windows import Window

from src.ndvi import INVALID_SCL_CLASSES, reflectance_offset


# Scala dei colori NDVI: (valore, colore RGB). Tra due valori il colore
# viene interpolato linearmente.
# Più sfumature tra 0,5 e 1, dove cade la vegetazione.
NDVI_COLOR_STOPS = [
    (-0.20, (59, 110, 168)),   # acqua
    (0.00, (166, 140, 110)),   # suolo nudo / urbano
    (0.20, (214, 196, 128)),   # vegetazione molto rada
    (0.35, (240, 224, 110)),   # vegetazione rada
    (0.50, (190, 220, 90)),
    (0.65, (120, 196, 80)),
    (0.75, (60, 160, 70)),
    (0.85, (24, 118, 52)),
    (0.95, (8, 68, 32)),       # vegetazione molto densa
]
INVALID_COLOR = (180, 180, 180)

# Variazione NDVI (dopo - prima): scala divergente.
DIFF_COLOR_STOPS = [
    (-0.30, (140, 20, 30)),    # forte calo
    (-0.15, (215, 90, 70)),
    (-0.05, (245, 200, 180)),
    (0.00, (245, 245, 240)),   # nessuna variazione
    (0.05, (205, 235, 200)),
    (0.15, (110, 190, 110)),
    (0.30, (20, 110, 50)),     # forte aumento
]

# Contrasto fisso per i colori reali (valori TCI 8 bit).
RGB_LOW, RGB_HIGH, RGB_GAMMA = 0.0, 145.0, 0.8

TARGET_RESOLUTION_M = 10.0

# Lato massimo delle immagini in pixel: per aree grandi (storie fino a
# 12 km) la risoluzione si riduce (es. 15 m), per immagini più leggere.
MAX_IMAGE_PIXELS = 800


def color_stops_hex(stops=None) -> list:
    """Legenda per l'app: [[valore, "#rrggbb"], ...]."""
    stops = NDVI_COLOR_STOPS if stops is None else stops
    return [[value, "#%02x%02x%02x" % rgb] for value, rgb in stops]


# ------------------------------------------------------------------
# Griglia comune
# ------------------------------------------------------------------

class Grid:
    """Griglia UTM a 10 m, quadrata, centrata sul punto."""

    def __init__(self, lat: float, lon: float, side_km: float,
                 resolution: float = TARGET_RESOLUTION_M):
        zone = int((lon + 180) // 6) + 1
        epsg = (32600 if lat >= 0 else 32700) + zone
        self.crs = CRS.from_epsg(epsg)

        (x,), (y,) = transform("EPSG:4326", self.crs, [lon], [lat])
        resolution = max(resolution, side_km * 1000 / MAX_IMAGE_PIXELS)
        size = max(1, int(round(side_km * 1000 / resolution)))
        half = size * resolution / 2

        self.width = size
        self.height = size
        self.transform = from_origin(x - half, y + half, resolution, resolution)


def read_on_grid(href: str, grid: Grid, indexes=1) -> np.ndarray:
    """
    Legge un raster ricampionandolo (nearest) sulla griglia comune.
    WarpedVRT legge solo i blocchi necessari del file remoto.
    Le zone fuori dalla scena valgono 0 (= nessun dato).
    """
    with rasterio.open(href) as src:
        with WarpedVRT(
            src,
            crs=grid.crs,
            transform=grid.transform,
            width=grid.width,
            height=grid.height,
            resampling=Resampling.nearest,
        ) as vrt:
            return vrt.read(indexes)


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
    Contrasto FISSO per la True Color Image (uguale per tutte le date):
    schiarisce la TCI, che per la vegetazione risulta scura, senza
    adattarsi alla singola immagine (renderebbe falsi i confronti).

    rgb: array (3, righe, colonne) uint8 -> (righe, colonne, 3) uint8
    """
    data = rgb.astype(np.float32)
    has_data = np.any(rgb > 0, axis=0)

    stretched = (data - RGB_LOW) / (RGB_HIGH - RGB_LOW)
    stretched = np.clip(stretched, 0, 1) ** RGB_GAMMA * 255
    stretched[:, ~has_data] = 0
    return np.transpose(stretched, (1, 2, 0)).astype(np.uint8)


def colorize(values_grid: np.ndarray, valid: np.ndarray, stops) -> np.ndarray:
    """Valori (righe, colonne) -> RGB uint8 interpolando la scala data."""
    values = np.array([v for v, _ in stops], dtype=np.float32)
    colors = np.array([c for _, c in stops], dtype=np.float32)

    clipped = np.clip(np.nan_to_num(values_grid, nan=0.0), values[0], values[-1])
    image = np.zeros(values_grid.shape + (3,), dtype=np.float32)
    for channel in range(3):
        image[..., channel] = np.interp(clipped, values, colors[:, channel])

    image[~valid] = INVALID_COLOR
    return np.round(image).astype(np.uint8)


def colorize_ndvi(ndvi: np.ndarray, valid: np.ndarray) -> np.ndarray:
    return colorize(ndvi, valid, NDVI_COLOR_STOPS)


def colorize_diff(diff: np.ndarray, valid: np.ndarray) -> np.ndarray:
    return colorize(diff, valid, DIFF_COLOR_STOPS)


def compute_ndvi_grid(red: np.ndarray, nir: np.ndarray, scl: np.ndarray,
                      offset: float = 0.0):
    """
    Restituisce (ndvi, valid) sulla griglia.
    offset: scostamento radiometrico da sottrarre (vedi src/ndvi.py).
    """
    has_data = (red > 0) & (nir > 0)       # 0 = nessun dato
    red = np.clip(red.astype(np.float32) - offset, 0, None)
    nir = np.clip(nir.astype(np.float32) - offset, 0, None)
    denominator = nir + red

    valid = (
        valid_mask_from_scl(scl)
        & has_data
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

def ndvi_on_grid(item, grid: Grid):
    red = read_on_grid(item.assets["red"].href, grid)
    nir = read_on_grid(item.assets["nir"].href, grid)
    scl = read_on_grid(item.assets["scl"].href, grid)
    return compute_ndvi_grid(red, nir, scl, offset=reflectance_offset(item))


def harmonize_rgb(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """
    Armonizzazione radiometrica relativa (solo per la visualizzazione).

    Adatta i colori di "source" a quelli di "reference" banda per banda,
    allineando i percentili 2 e 98 calcolati sui pixel con dati in
    entrambe le immagini. Riduce le differenze dovute a illuminazione,
    foschia e stagione; i cambiamenti reali, che riguardano solo una
    parte dei pixel, restano visibili.

    source, reference: array (3, righe, colonne) uint8 sulla stessa griglia.
    """
    both = np.all(source > 0, axis=0) & np.all(reference > 0, axis=0)
    if both.sum() < 100:
        return source

    result = source.astype(np.float32)
    for band in range(3):
        s_low, s_high = np.percentile(source[band][both], [2, 98])
        r_low, r_high = np.percentile(reference[band][both], [2, 98])
        if s_high - s_low < 1:
            continue
        gain = (r_high - r_low) / (s_high - s_low)
        result[band] = (result[band] - s_low) * gain + r_low

    result = np.clip(result, 1, 255)
    result[:, ~np.any(source > 0, axis=0)] = 0     # nessun dato resta nero
    return result.astype(np.uint8)


def render_rgb_png(item, grid: Grid, reference_item=None) -> bytes:
    """Colori reali; con reference_item i colori vengono armonizzati a quella data."""
    rgb = read_on_grid(item.assets["visual"].href, grid, indexes=[1, 2, 3])
    if reference_item is not None:
        reference = read_on_grid(
            reference_item.assets["visual"].href, grid, indexes=[1, 2, 3]
        )
        rgb = harmonize_rgb(rgb, reference)
    return to_png(stretch_rgb(rgb))


def render_ndvi_png(item, grid: Grid) -> bytes:
    ndvi, valid = ndvi_on_grid(item, grid)
    return to_png(colorize_ndvi(ndvi, valid))


def diff_on_grid(after_item, before_item, grid: Grid):
    """Variazione NDVI sui soli pixel validi in entrambe le date."""
    ndvi_after, valid_after = ndvi_on_grid(after_item, grid)
    ndvi_before, valid_before = ndvi_on_grid(before_item, grid)
    valid = valid_after & valid_before
    diff = np.full(ndvi_after.shape, np.nan, dtype=np.float32)
    diff[valid] = ndvi_after[valid] - ndvi_before[valid]
    return diff, valid


def render_diff_png(after_item, before_item, grid: Grid) -> bytes:
    diff, valid = diff_on_grid(after_item, before_item, grid)
    return to_png(colorize_diff(diff, valid))


def render_png(item, grid: Grid, kind: str, compare_item=None) -> bytes:
    if kind == "rgb":
        # compare_item, se presente, è la data a cui armonizzare i colori.
        return render_rgb_png(item, grid, reference_item=compare_item)
    if kind == "ndvi":
        return render_ndvi_png(item, grid)
    if kind == "diff":
        if compare_item is None:
            raise ValueError("La variazione richiede una seconda scena.")
        return render_diff_png(item, compare_item, grid)
    raise ValueError(f"Tipo di immagine non supportato: {kind}")
