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
import time

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
from rasterio.errors import RasterioIOError
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform, transform_bounds
from rasterio.windows import Window

from src.ndvi import INVALID_SCL_CLASSES, effective_offset


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
# Scene molto chiare (deserti, neve, saline): se oltre questa quota di pixel
# supera RGB_HIGH, il bianco si sposta al 99° percentile per non "bruciarle".
RGB_SATURATION_LIMIT = 0.05

TARGET_RESOLUTION_M = 10.0

# Lato massimo delle immagini in pixel: per aree grandi (storie fino a
# 12 km) la risoluzione si riduce (es. 15 m), per immagini più leggere.
MAX_IMAGE_PIXELS = 800

# Tentativi per ogni lettura remota di una banda.
READ_ATTEMPTS = 3


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


def read_on_grid(href: str, grid: Grid, indexes=1,
                 resampling: Resampling = Resampling.nearest) -> np.ndarray:
    """
    Legge un raster ricampionandolo sulla griglia comune
    (nearest per classi e bande a 10 m, bilinear per le bande a 20 m).
    WarpedVRT legge solo i blocchi necessari del file remoto.
    Le zone fuori dalla scena valgono 0 (= nessun dato).
    """
    # Le letture remote a volte si interrompono (file ricevuto troncato):
    # si riprova fino a READ_ATTEMPTS volte prima di arrendersi.
    for attempt in range(READ_ATTEMPTS):
        try:
            with rasterio.open(href) as src:
                with WarpedVRT(
                    src,
                    crs=grid.crs,
                    transform=grid.transform,
                    width=grid.width,
                    height=grid.height,
                    resampling=resampling,
                ) as vrt:
                    return vrt.read(indexes)
        except RasterioIOError:
            if attempt == READ_ATTEMPTS - 1:
                raise
            time.sleep(0.5 * (attempt + 1))


# ------------------------------------------------------------------
# Lettura delle finestre raster
# ------------------------------------------------------------------

def pixel_window(src, bbox_wgs84) -> Window:
    """Finestra (in pixel) del raster che copre il bbox WGS84."""
    left, bottom, right, top = transform_bounds(
        "EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21
    )
    inverse = ~src.transform
    # Coordinate -> (colonna, riga) con i coefficienti della trasformazione
    # inversa: compatibile con tutte le versioni della libreria affine.
    def to_pixel(x, y):
        return inverse.a * x + inverse.b * y + inverse.c, \
            inverse.d * x + inverse.e * y + inverse.f

    c0, r0 = to_pixel(left, top)
    c1, r1 = to_pixel(right, bottom)

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

def rgb_white_point(rgb: np.ndarray) -> float:
    """
    Valore della TCI che diventa bianco.

    Di norma e' fisso (RGB_HIGH), cosi' tutte le date e tutti i luoghi
    verdi hanno lo stesso contrasto. Nelle scene molto chiare (deserti,
    neve) quel valore brucerebbe l'immagine: se piu' del 5% dei pixel lo
    supera, usiamo il 99° percentile del canale piu' luminoso.
    """
    has_data = np.any(rgb > 0, axis=0)
    brightest = rgb.max(axis=0)[has_data]
    if brightest.size < 100:
        return RGB_HIGH
    if float(np.mean(brightest >= RGB_HIGH)) <= RGB_SATURATION_LIMIT:
        return RGB_HIGH
    return float(min(255.0, max(RGB_HIGH, np.percentile(brightest, 99))))


def stretch_rgb(rgb: np.ndarray, high: float = RGB_HIGH) -> np.ndarray:
    """
    Contrasto per la True Color Image: schiarisce la TCI, che per la
    vegetazione risulta scura. "high" e' il valore che diventa bianco
    (vedi rgb_white_point); per due date si usa lo stesso valore.

    rgb: array (3, righe, colonne) uint8 -> (righe, colonne, 3) uint8
    """
    data = rgb.astype(np.float32)
    has_data = np.any(rgb > 0, axis=0)

    stretched = (data - RGB_LOW) / (high - RGB_LOW)
    stretched = np.clip(stretched, 0, 1) ** RGB_GAMMA * 255
    stretched[:, ~has_data] = 0
    return np.transpose(stretched, (1, 2, 0)).astype(np.uint8)


# ------------------------------------------------------------------
# Colori reali dalla riflettanza (B04, B03, B02) con curva tonale morbida
# ------------------------------------------------------------------
#
# La TCI di Sentinel-2 ("visual", 8 bit) satura già a riflettanza ~0,31:
# nei deserti rosso e verde valgono 255 e l'immagine diventa un quadrato
# giallo chiaro, senza dettagli da recuperare. Per questo i colori reali
# si calcolano dalle bande a 16 bit, con una curva che comprime le alte
# luci invece di tagliarle, applicata alla luminosità (il canale più
# chiaro) per non sbiadire i colori.

TONE_SOFTNESS = 0.06       # sotto questo valore la curva è quasi lineare
TONE_MIN_WHITE = 0.30      # riflettanza minima del "bianco" (scene verdi)
TONE_MAX_WHITE = 0.90      # massima (neve, saline)


def scene_white(reflectance: np.ndarray) -> float:
    """Riflettanza che diventa bianco: 99,5° percentile del canale più chiaro."""
    brightest = np.nanmax(reflectance, axis=0)
    brightest = brightest[np.isfinite(brightest) & (brightest > 0)]
    if brightest.size < 100:
        return TONE_MIN_WHITE
    return float(np.clip(np.percentile(brightest, 99.5), TONE_MIN_WHITE, TONE_MAX_WHITE))


def tone_map_rgb(reflectance: np.ndarray, white: float) -> np.ndarray:
    """
    Riflettanza (3, righe, colonne) -> immagine (righe, colonne, 3) uint8.

    Curva arcoseno iperbolico sulla luminosità: le zone scure (vegetazione,
    acqua) vengono schiarite, quelle chiare (sabbia, roccia, cemento)
    compresse gradualmente fino a "white". I rapporti tra i canali restano
    invariati, quindi la sabbia resta color sabbia e non vira al bianco.
    """
    data = np.nan_to_num(reflectance.astype(np.float32), nan=0.0)
    data = np.clip(data, 0, None)
    luminance = data.max(axis=0)
    scale_top = np.arcsinh(white / TONE_SOFTNESS)
    mapped = np.arcsinh(luminance / TONE_SOFTNESS) / scale_top
    gain = np.divide(mapped, luminance, out=np.zeros_like(luminance), where=luminance > 1e-6)
    image = np.clip(data * gain, 0, 1) * 255
    image[:, ~np.isfinite(reflectance).all(axis=0) | (luminance <= 0)] = 0
    return np.transpose(image, (1, 2, 0)).astype(np.uint8)


def harmonize_reflectance(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Come harmonize_rgb, ma su riflettanze in virgola mobile (NaN = nessun dato)."""
    both = np.isfinite(source).all(axis=0) & np.isfinite(reference).all(axis=0)
    if both.sum() < 100:
        return source
    result = source.astype(np.float32).copy()
    for band in range(3):
        s_low, s_high = np.percentile(source[band][both], [2, 98])
        r_low, r_high = np.percentile(reference[band][both], [2, 98])
        if s_high - s_low < 1e-4:
            continue
        result[band] = (result[band] - s_low) * (r_high - r_low) / (s_high - s_low) + r_low
    return np.clip(result, 0, None)


def read_reflectance_rgb(item, grid: Grid) -> np.ndarray:
    """Bande B04, B03, B02 come riflettanza (0-1), NaN dove non ci sono dati."""
    from src.ndvi import effective_offset
    bands = [read_on_grid(item.assets[key].href, grid).astype(np.float32)
             for key in ("red", "green", "blue")]
    raw = np.stack(bands)
    has_data = (raw > 0).all(axis=0)
    offset = effective_offset(item, *bands)
    reflectance = (raw - offset) / 10000.0
    reflectance[:, ~has_data] = np.nan
    return reflectance


def has_reflectance_bands(item) -> bool:
    return all(key in getattr(item, "assets", {}) for key in ("red", "green", "blue"))


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
    return compute_ndvi_grid(red, nir, scl, offset=effective_offset(item, red, nir))


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
    """
    Colori reali; con reference_item i colori vengono armonizzati a quella
    data e usano lo stesso bianco, così le due immagini restano confrontabili.
    """
    if has_reflectance_bands(item) and (reference_item is None or has_reflectance_bands(reference_item)):
        refl = read_reflectance_rgb(item, grid)
        if reference_item is not None:
            reference = read_reflectance_rgb(reference_item, grid)
            refl = harmonize_reflectance(refl, reference)
            return to_png(tone_map_rgb(refl, scene_white(reference)))
        return to_png(tone_map_rgb(refl, scene_white(refl)))
    # Riserva: immagine TCI a 8 bit (scene senza bande separate)
    rgb = read_on_grid(item.assets["visual"].href, grid, indexes=[1, 2, 3])
    if reference_item is not None:
        reference = read_on_grid(
            reference_item.assets["visual"].href, grid, indexes=[1, 2, 3]
        )
        rgb = harmonize_rgb(rgb, reference)
        # Stesso bianco della data di riferimento: le due immagini restano confrontabili.
        return to_png(stretch_rgb(rgb, rgb_white_point(reference)))
    return to_png(stretch_rgb(rgb, rgb_white_point(rgb)))


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
