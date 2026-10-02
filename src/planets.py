"""
Mappe di altri corpi celesti per "Oltre la Terra" (catalogo in planet_layers.py).

Il server:
1. scarica i dati originali una sola volta (memoria + disco), dal PDS della NASA
   per le griglie numeriche e da NASA Solar System Treks per i mosaici di immagini;
2. porta ogni griglia alla stessa forma: nord in alto, longitudine da −180 a 180,
   NaN dove non ci sono dati, al massimo 720 × 1440 pixel (4 per grado);
3. la colora con una scala nota (soglie fisse o calcolate sui dati, dal 2° al
   98° percentile) e prepara la legenda con i numeri;
4. dice il valore di una griglia in un punto, per il "tocca un punto" del globo.
"""

from __future__ import annotations

import hashlib
import io
import math
import os
import threading
import warnings
from pathlib import Path

import numpy as np
import requests
from PIL import Image

from src.planet_layers import BODIES

TREK_TILES = "https://trek.nasa.gov/tiles"
CACHE_DIR = Path(os.environ.get("PLANETS_CACHE_DIR", "/tmp/earthpulse-planets"))
MAX_ROWS, MAX_COLS = 720, 1440
NO_DATA_COLOR = (80, 80, 80)
TREK_LEVEL = 2                 # 8 × 4 tessere da 256 pixel = 2048 × 1024

_grids: dict = {}              # (corpo, mappa) -> {"grid", "stops"}
_images: dict = {}             # (corpo, mappa) -> JPEG
_lock = threading.Lock()


class PlanetDataUnavailable(Exception):
    """Il server dei dati (PDS o Trek) non ha risposto come previsto."""


def layer_spec(body: str, layer: str) -> dict:
    try:
        return BODIES[body]["layers"][layer]
    except KeyError as exc:
        raise KeyError(f"{body}/{layer}") from exc


# ------------------------------------------------------------------
# Download con cache su disco
# ------------------------------------------------------------------

def download(url: str, session=requests) -> bytes:
    path = CACHE_DIR / hashlib.sha1(url.encode()).hexdigest()
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    try:
        response = session.get(url, timeout=180)
    except requests.RequestException as exc:
        raise PlanetDataUnavailable(f"Archivio dei dati non raggiungibile: {exc}") from exc
    if response.status_code != 200:
        raise PlanetDataUnavailable(f"Archivio dei dati: errore {response.status_code}")
    data = response.content
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError:
        pass
    return data


# ------------------------------------------------------------------
# Lettura dei formati
# ------------------------------------------------------------------

def to_west_left(grid: np.ndarray, lon0: float) -> np.ndarray:
    """Griglia che parte da longitudine lon0 (0 o −180) -> griglia che parte da −180."""
    if lon0 == 0:
        return np.roll(grid, grid.shape[1] // 2, axis=1)
    return grid


def read_img(raw: bytes, src: dict) -> np.ndarray:
    rows, cols = src["shape"]
    dtype = np.dtype(src["dtype"])
    if len(raw) != rows * cols * dtype.itemsize:
        raise PlanetDataUnavailable(f"File di dati inatteso ({len(raw)} byte)")
    values = np.frombuffer(raw, dtype=dtype).reshape(rows, cols)
    grid = values.astype(np.float32)
    invalid = np.zeros(grid.shape, dtype=bool)
    if "nodata" in src:
        invalid |= values == src["nodata"]
    grid = grid * src.get("scale", 1.0)
    invalid |= ~np.isfinite(grid)
    if "valid_min" in src:
        invalid |= grid < src["valid_min"]
    if "valid_max" in src:
        invalid |= grid > src["valid_max"]
    grid[invalid] = np.nan
    if rows % 2 == 1:                  # griglie "sui nodi" (721 righe): togliamo l'ultima
        grid = grid[:-1]
    grid = to_west_left(grid, src.get("lon0", -180))
    if "lat_top" in src:               # copertura parziale in latitudine: inseriamo nel globo intero
        ppd = grid.shape[1] / 360.0
        full = np.full((int(round(180 * ppd)), grid.shape[1]), np.nan, dtype=np.float32)
        top = int(round((90 - src["lat_top"]) * ppd))
        full[top:top + grid.shape[0]] = grid[: full.shape[0] - top]
        grid = full
    return grid


def parse_table(raw: bytes, min_columns: int) -> np.ndarray:
    """Tabella di testo -> matrice di numeri (salta intestazioni e righe non numeriche)."""
    rows = []
    for line in raw.decode("latin-1").splitlines():
        parts = line.replace(",", " ").split()
        if len(parts) < min_columns:
            continue
        try:
            rows.append([float(p) for p in parts[:min_columns]])
        except ValueError:
            continue
    if not rows:
        raise PlanetDataUnavailable("Tabella di dati vuota o in un formato inatteso")
    return np.array(rows, dtype=np.float64)


def normalize_lon(lon):
    return ((np.asarray(lon) + 180.0) % 360.0) - 180.0


def read_cells(raw: bytes, src: dict) -> np.ndarray:
    """Celle con limiti (lat min, lat max, lon min, lon max, valore) -> griglia."""
    i_lat0, i_lat1, i_lon0, i_lon1, i_val = src["columns"]
    table = parse_table(raw, max(src["columns"]) + 1)
    res = src["res"]
    rows, cols = int(round(180 / res)), int(round(360 / res))
    grid = np.full((rows, cols), np.nan, dtype=np.float32)
    lon0 = table[:, i_lon0]
    lon1 = table[:, i_lon1]
    if lon1.max() > 180.5:             # longitudini 0–360
        lon0 = np.where(lon0 >= 180, lon0 - 360, lon0)
        lon1 = lon0 + (table[:, i_lon1] - table[:, i_lon0])
    r0 = np.clip(np.round((90 - table[:, i_lat1]) / res).astype(int), 0, rows)
    r1 = np.clip(np.round((90 - table[:, i_lat0]) / res).astype(int), 0, rows)
    c0 = np.clip(np.round((lon0 + 180) / res).astype(int), 0, cols)
    c1 = np.clip(np.round((lon1 + 180) / res).astype(int), 0, cols)
    values = table[:, i_val]
    if np.all(r1 - r0 == 1) and np.all(c1 - c0 == 1):       # celle grandi come la griglia
        grid[r0, c0] = values
    else:
        for a, b, c, d, v in zip(r0, np.maximum(r1, r0 + 1), c0, np.maximum(c1, c0 + 1), values):
            grid[a:b, c:d] = v
    return mask_values(grid, src)


def read_points(raw: bytes, src: dict) -> np.ndarray:
    """Centri delle celle (lat, lon, valore) -> griglia di passo res."""
    i_lat, i_lon, i_val = src["columns"]
    table = parse_table(raw, max(src.get("min_columns", 0), max(src["columns"]) + 1))
    res = src["res"]
    rows, cols = int(round(180 / res)), int(round(360 / res))
    grid = np.full((rows, cols), np.nan, dtype=np.float32)
    r = np.clip(np.floor((90 - table[:, i_lat]) / res).astype(int), 0, rows - 1)
    c = np.clip(np.floor((normalize_lon(table[:, i_lon]) + 180) / res).astype(int), 0, cols - 1)
    values = table[:, i_val].copy()
    if "zero_is_nodata_beyond" in src:     # zeri = nessun dato, ma solo vicino ai poli
        values[(values == 0) & (np.abs(table[:, i_lat]) > src["zero_is_nodata_beyond"])] = np.nan
    grid[r, c] = values
    return mask_values(grid, src)


def mask_values(grid: np.ndarray, src: dict) -> np.ndarray:
    if "nodata_above" in src:
        grid[grid > src["nodata_above"]] = np.nan
    if src.get("zero_is_nodata"):
        grid[grid == 0] = np.nan
    return grid


def shrink(grid: np.ndarray) -> np.ndarray:
    """Riduce le griglie più fitte di 4 pixel per grado (media dei pixel validi)."""
    factor = int(math.ceil(grid.shape[0] / MAX_ROWS))
    if factor <= 1:
        return grid
    rows, cols = grid.shape[0] // factor, grid.shape[1] // factor
    blocks = grid[: rows * factor, : cols * factor].reshape(rows, factor, cols, factor)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)      # blocchi tutti vuoti
        return np.nanmean(blocks, axis=(1, 3)).astype(np.float32)


READERS = {"img": read_img, "cells": read_cells, "points": read_points}


# ------------------------------------------------------------------
# Scala dei colori e legenda
# ------------------------------------------------------------------

def nice_step(span: float, count: int) -> float:
    raw = span / max(count, 1)
    magnitude = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * magnitude:
            return m * magnitude
    return 10 * magnitude


def auto_stops(grid: np.ndarray, count: int, diverging: bool) -> list:
    """Soglie arrotondate dal 2° al 98° percentile dei valori validi."""
    values = grid[np.isfinite(grid)]
    if values.size == 0:
        return list(np.linspace(0, 1, count))
    low, high = np.percentile(values, [2, 98])
    if diverging:
        top = max(abs(low), abs(high)) or 1.0
        step = nice_step(2 * top, count - 1)
        half = (count - 1) // 2
        return [step * (i - half) for i in range(count)]
    if high <= low:
        high = low + 1
    step = nice_step(high - low, count - 1)
    start = math.floor(low / step) * step
    return [start + step * i for i in range(count)]


def colorize(grid: np.ndarray, stops: list, colors: list) -> np.ndarray:
    out = np.empty(grid.shape + (3,), dtype=np.float32)
    ramp = np.array(colors, dtype=np.float32)
    filled = np.nan_to_num(grid, nan=stops[0])
    for channel in range(3):
        out[..., channel] = np.interp(filled, stops, ramp[:, channel])
    out[~np.isfinite(grid)] = NO_DATA_COLOR
    return out


def hillshade(height_m: np.ndarray, radius_km: float, exaggeration: float = 3.0) -> np.ndarray:
    """Ombreggiatura del rilievo (luce da nord-ovest), valori 0–1."""
    rows, cols = height_m.shape
    pixel_m = radius_km * 1000 * np.deg2rad(360.0 / cols)
    lat = np.deg2rad(90 - (np.arange(rows) + 0.5) * 180.0 / rows)
    dx = pixel_m * np.maximum(np.cos(lat), 0.05)[:, None]
    gy, gx = np.gradient(np.nan_to_num(height_m) * exaggeration)
    gx = gx / dx
    gy = gy / pixel_m
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azimuth, altitude = np.deg2rad(315.0), np.deg2rad(45.0)
    shade = (np.sin(altitude) * np.cos(slope)
             + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect))
    return np.clip(shade, 0, 1)


def format_number(value: float, digits: int) -> str:
    text = f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")
    return text.replace("-", "−")


def legend(spec: dict, stops: list, has_gaps: bool) -> dict:
    scale = spec.get("label_scale", 1.0)
    unit = spec.get("legend_unit", spec["unit"])
    span = (stops[-1] - stops[0]) * scale / max(len(stops) - 1, 1)
    digits = 0 if abs(span) >= 1 or span == 0 else max(0, -int(math.floor(math.log10(abs(span)))))
    labels = []
    for i, s in enumerate(stops):
        text = format_number(s * scale, digits)
        if s > 0 and stops[0] < 0:          # scale con valori negativi: segno anche sui positivi
            text = "+" + text
        labels.append(text + (f" {unit}" if i == len(stops) - 1 else ""))
    return {
        "color_stops": ["#%02x%02x%02x" % tuple(c) for c in spec["colors"]],
        "positions": [i / (len(stops) - 1) for i in range(len(stops))],
        "labels": labels,
        "no_data": "#%02x%02x%02x" % NO_DATA_COLOR if has_gaps else None,
    }


# ------------------------------------------------------------------
# Griglie e immagini
# ------------------------------------------------------------------

def load_grid(body: str, layer: str, session=requests) -> dict:
    key = (body, layer)
    with _lock:
        if key in _grids:
            return _grids[key]
        spec = layer_spec(body, layer)
        src = spec["source"]
        grid = shrink(READERS[src["format"]](download(src["url"], session), src))
        if spec["stops"] == "auto":
            stops = auto_stops(grid, len(spec["colors"]), diverging=False)
        elif spec["stops"] == "auto_diverging":
            stops = auto_stops(grid, len(spec["colors"]), diverging=True)
        else:
            stops = spec["stops"]
        _grids[key] = {"grid": grid, "stops": [float(s) for s in stops]}
        return _grids[key]


def to_jpeg(image: np.ndarray, size=(2048, 1024)) -> bytes:
    picture = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
    if size and picture.size != size:
        # Celle grandi (es. 5°) restano nette: si vede la risoluzione vera del dato
        resample = Image.NEAREST if picture.width < 200 else Image.BILINEAR
        picture = picture.resize(size, resample)
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def grid_image(body: str, layer: str, session=requests) -> bytes:
    spec = layer_spec(body, layer)
    data = load_grid(body, layer, session)
    color = colorize(data["grid"], data["stops"], spec["colors"])
    if spec.get("hillshade"):
        shade = hillshade(data["grid"], BODIES[body]["radius_km"])
        color = color * (0.55 + 0.45 * shade[..., None])
    return to_jpeg(color)


def trek_tile_url(body: str, layer_id: str, level: int, row: int, col: int, ext: str) -> str:
    return (f"{TREK_TILES}/{body}/EQ/{layer_id}/1.0.0/default/default028mm/"
            f"{level}/{row}/{col}.{ext}")


def trek_mosaic(spec: dict, session=requests, level: int = TREK_LEVEL) -> bytes:
    """Unisce le tessere di un livello in un'unica mappa equirettangolare."""
    cols, rows = 2 ** (level + 1), 2 ** level
    canvas = Image.new("RGB", (cols * 256, rows * 256))
    for row in range(rows):
        for col in range(cols):
            url = trek_tile_url(spec["trek_body"], spec["trek_id"], level, row, col, spec["ext"])
            try:
                response = session.get(url, timeout=30)
            except requests.RequestException as exc:
                raise PlanetDataUnavailable(f"NASA Trek non raggiungibile: {exc}") from exc
            if response.status_code != 200:
                raise PlanetDataUnavailable(f"NASA Trek: errore {response.status_code}")
            tile = Image.open(io.BytesIO(response.content))
            if tile.mode in ("RGBA", "LA", "P"):
                tile = tile.convert("RGBA")
                background = Image.new("RGBA", tile.size, NO_DATA_COLOR + (255,))
                tile = Image.alpha_composite(background, tile)
            canvas.paste(tile.convert("RGB"), (col * 256, row * 256))
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def layer_image(body: str, layer: str, session=requests) -> bytes:
    key = (body, layer)
    if key not in _images:
        spec = layer_spec(body, layer)
        data = grid_image(body, layer, session) if spec["kind"] == "grid" else trek_mosaic(spec, session)
        _images[key] = data
    return _images[key]


# ------------------------------------------------------------------
# Interfaccia per l'API
# ------------------------------------------------------------------

def value_at(body: str, layer: str, lat: float, lon: float, session=requests):
    """Valore della griglia nel pixel che contiene il punto (None se non c'è il dato)."""
    grid = load_grid(body, layer, session)["grid"]
    rows, cols = grid.shape
    row = int(np.clip((90 - lat) * rows / 180, 0, rows - 1))
    col = int(np.clip((float(normalize_lon(lon)) + 180) * cols / 360, 0, cols - 1))
    value = float(grid[row, col])
    return value if math.isfinite(value) else None


def point(body: str, lat: float, lon: float, layers: list, session=requests) -> list:
    """Valori nel punto per le mappe numeriche richieste (nell'ordine del catalogo)."""
    result = []
    for key, spec in BODIES[body]["layers"].items():
        if spec["kind"] != "grid" or key not in layers:
            continue
        rows = load_grid(body, key, session)["grid"].shape[0]
        result.append({
            "key": key, "label": spec["label"], "unit": spec["unit"], "digits": spec["digits"],
            "value": value_at(body, key, lat, lon, session),
            "reference": spec.get("reference") or spec.get("note_point"),
            "pixel_km": round(math.pi * BODIES[body]["radius_km"] / rows, 1),
        })
    return result


def catalog(body: str) -> list:
    """Mappe disponibili per un corpo, con legenda e didascalia."""
    result = []
    for key, spec in BODIES[body]["layers"].items():
        item = {
            "key": key, "label": spec["label"],
            "image": f"/api/v1/space/layer?body={body}&layer={key}",
            "caption": spec.get("caption"),
            "numeric": spec["kind"] == "grid",
            "attribution": spec["attribution"],
            "legend": spec.get("legend"),
        }
        if spec["kind"] == "grid" and (body, key) in _grids:
            data = _grids[(body, key)]
            item["legend"] = legend(spec, data["stops"], bool(np.isnan(data["grid"]).any()))
        elif spec["kind"] == "grid" and isinstance(spec["stops"], list):
            item["legend"] = legend(spec, spec["stops"], False)
        result.append(item)
    return result


def layer_legend(body: str, layer: str, session=requests) -> dict:
    """Legenda di una griglia (scarica i dati se servono: le soglie possono dipendere da loro)."""
    spec = layer_spec(body, layer)
    data = load_grid(body, layer, session)
    return legend(spec, data["stops"], bool(np.isnan(data["grid"]).any()))
