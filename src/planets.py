"""
Mappe tematiche di altri corpi celesti per "Oltre la Terra".

Altitudine (Luna e Marte): griglie originali degli altimetri laser, pubblicate
dal Planetary Data System (PDS Geosciences Node, NASA), di pubblico dominio:
- Luna: LRO LOLA, LDEM_4 (4 pixel per grado), metri rispetto al raggio di 1737,4 km;
- Marte: MGS MOLA, MEGDR MEGT90N000CB (4 pixel per grado), metri rispetto all'areoide.
Il server scarica i file una volta (circa 2 MB ciascuno), li tiene in memoria e
su disco, li colora con una scala fissa in chilometri e aggiunge l'ombreggiatura
del rilievo. Così la legenda ha numeri veri e si può leggere l'altitudine di un
punto qualsiasi.

Notte all'infrarosso (Marte): mosaico THEMIS-IR notturno (Mars Odyssey,
NASA/JPL/ASU) dalle tessere WMTS di NASA Solar System Treks, livello 2
(8 × 4 tessere da 256 pixel = 2048 × 1024).
"""

from __future__ import annotations

import io
import os
import threading
from pathlib import Path

import numpy as np
import requests
from PIL import Image

PDS = "https://pds-geosciences.wustl.edu"
TREK_TILES = "https://trek.nasa.gov/tiles"
CACHE_DIR = Path(os.environ.get("PLANETS_CACHE_DIR", "/tmp/earthpulse-planets"))
ROWS, COLS = 720, 1440          # 4 pixel per grado
EXPECTED_BYTES = ROWS * COLS * 2

DEMS = {
    "moon": {
        "url": f"{PDS}/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_4.img",
        "dtype": "<i2", "scale": 0.5,
        "radius_km": 1737.4,
        "reference": "raggio medio di 1737,4 km",
        # Scala dei colori: altitudine in km -> colore
        "stops_km": [-8, -4, -2, 0, 2, 4, 6, 10],
        "attribution": "Altitudine: NASA LRO LOLA (LDEM_4), PDS Geosciences Node · pubblico dominio",
    },
    "mars": {
        "url": f"{PDS}/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg004/megt90n000cb.img",
        "dtype": ">i2", "scale": 1.0,
        "radius_km": 3389.5,
        "reference": "areoide (il \"livello del mare\" di Marte)",
        "stops_km": [-8, -4, -2, 0, 2, 4, 8, 21],
        "attribution": "Altitudine: NASA MGS MOLA (MEGDR), PDS Geosciences Node · pubblico dominio",
    },
}

# Stessa sequenza di colori delle mappe USGS/NASA del rilievo (viola in basso, bianco in cima)
RAMP = [
    (110, 40, 150), (60, 90, 220), (70, 190, 230), (90, 200, 110),
    (240, 230, 110), (230, 140, 70), (190, 70, 60), (255, 255, 255),
]

LAYERS = {
    "moon": {
        "elevation": {"label": "Altitudine", "kind": "dem"},
    },
    "mars": {
        "elevation": {"label": "Altitudine", "kind": "dem"},
        "night_ir": {
            "label": "Roccia o polvere", "kind": "trek",
            "trek_body": "Mars", "trek_id": "THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018",
            "ext": "png", "level": 2,
            "legend": {"gradient": ["#141414", "#f0f0f0"],
                       "labels": ["Polvere e sabbia fine (si raffreddano presto)",
                                  "Roccia e suolo compatto (restano tiepidi)"]},
            "caption": ("Immagine all'infrarosso termico ripresa di notte: le superfici che "
                        "trattengono il calore (roccia, suolo cementato) appaiono chiare, "
                        "quelle che si raffreddano subito (polvere, sabbia fine) scure. "
                        "Misura la cosiddetta inerzia termica."),
            "attribution": "THEMIS-IR notte: NASA/JPL/ASU (Mars Odyssey), tramite NASA Solar System Treks",
        },
    },
}

_dems: dict = {}
_images: dict = {}
_lock = threading.Lock()


class PlanetDataUnavailable(Exception):
    """Il server dei dati (PDS o Trek) non ha risposto come previsto."""


# ------------------------------------------------------------------
# Altitudine
# ------------------------------------------------------------------

def parse_dem(raw: bytes, body: str) -> np.ndarray:
    """File IMG del PDS -> altitudine in metri (righe, colonne), longitudine da −180 a 180."""
    if len(raw) != EXPECTED_BYTES:
        raise PlanetDataUnavailable(f"File di altitudine inatteso ({len(raw)} byte)")
    spec = DEMS[body]
    grid = np.frombuffer(raw, dtype=spec["dtype"]).reshape(ROWS, COLS).astype(np.float32)
    grid *= spec["scale"]
    # Il PDS parte da longitudine 0 verso est: spostiamo metà griglia per partire da −180
    return np.roll(grid, COLS // 2, axis=1)


def load_dem(body: str, session=requests) -> np.ndarray:
    """Griglia di altitudine in metri, dalla memoria, dal disco o dal PDS."""
    with _lock:
        if body in _dems:
            return _dems[body]
        path = CACHE_DIR / f"{body}_dem.img"
        raw = None
        if path.exists() and path.stat().st_size == EXPECTED_BYTES:
            raw = path.read_bytes()
        if raw is None:
            try:
                response = session.get(DEMS[body]["url"], timeout=120)
            except requests.RequestException as exc:
                raise PlanetDataUnavailable(f"Archivio PDS non raggiungibile: {exc}") from exc
            if response.status_code != 200:
                raise PlanetDataUnavailable(f"Archivio PDS: errore {response.status_code}")
            raw = response.content
            grid = parse_dem(raw, body)          # controlla la dimensione prima di salvare
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            except OSError:
                pass
        else:
            grid = parse_dem(raw, body)
        _dems[body] = grid
        return grid


def colorize(height_m: np.ndarray, stops_km: list) -> np.ndarray:
    """Altitudine -> colori della scala RAMP, interpolati tra le soglie in km."""
    km = height_m / 1000.0
    out = np.empty(height_m.shape + (3,), dtype=np.float32)
    ramp = np.array(RAMP, dtype=np.float32)
    for channel in range(3):
        out[..., channel] = np.interp(km, stops_km, ramp[:, channel])
    return out


def hillshade(height_m: np.ndarray, radius_km: float, exaggeration: float = 3.0) -> np.ndarray:
    """Ombreggiatura del rilievo (luce da nord-ovest), valori 0–1."""
    rows, cols = height_m.shape
    pixel_m = radius_km * 1000 * np.deg2rad(360.0 / cols)
    lat = np.deg2rad(90 - (np.arange(rows) + 0.5) * 180.0 / rows)
    dx = pixel_m * np.maximum(np.cos(lat), 0.05)[:, None]
    gy, gx = np.gradient(height_m * exaggeration)
    gx = gx / dx
    gy = gy / pixel_m
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    azimuth, altitude = np.deg2rad(315.0), np.deg2rad(45.0)
    shade = (np.sin(altitude) * np.cos(slope)
             + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect))
    return np.clip(shade, 0, 1)


def to_jpeg(image: np.ndarray, size=(2048, 1024)) -> bytes:
    picture = Image.fromarray(np.clip(image, 0, 255).astype(np.uint8))
    if size and picture.size != size:
        picture = picture.resize(size, Image.BILINEAR)
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def elevation_image(body: str, session=requests) -> bytes:
    height = load_dem(body, session)
    spec = DEMS[body]
    color = colorize(height, spec["stops_km"])
    shade = hillshade(height, spec["radius_km"])
    return to_jpeg(color * (0.55 + 0.45 * shade[..., None]))


def elevation_at(body: str, lat: float, lon: float, session=requests) -> float:
    """Altitudine in metri nel punto (pixel più vicino della griglia a 4 pixel per grado)."""
    grid = load_dem(body, session)
    row = int(np.clip((90 - lat) * ROWS / 180, 0, ROWS - 1))
    lon = ((lon + 180) % 360) - 180
    col = int(np.clip((lon + 180) * COLS / 360, 0, COLS - 1))
    return float(grid[row, col])


def elevation_legend(body: str) -> dict:
    stops = DEMS[body]["stops_km"]
    return {
        "color_stops": ["#%02x%02x%02x" % c for c in RAMP],
        # Soglie equidistanti sulla barra: la scala è lineare tra una soglia e l'altra
        "positions": [i / (len(stops) - 1) for i in range(len(stops))],
        # Numeri brevi (unità solo sull'ultimo) per non sovrapporre le etichette
        "labels": [(f"{s:+d}".replace("+0", "0").replace("-", "−")) + (" km" if i == len(stops) - 1 else "")
                   for i, s in enumerate(stops)],
        "unit": "km",
    }


# ------------------------------------------------------------------
# Mosaici Trek (WMTS)
# ------------------------------------------------------------------

def trek_tile_url(body: str, layer_id: str, level: int, row: int, col: int, ext: str) -> str:
    return (f"{TREK_TILES}/{body}/EQ/{layer_id}/1.0.0/default/default028mm/"
            f"{level}/{row}/{col}.{ext}")


def trek_mosaic(spec: dict, session=requests) -> bytes:
    """Unisce le tessere di un livello in un'unica mappa equirettangolare."""
    level = spec["level"]
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
            tile = Image.open(io.BytesIO(response.content)).convert("RGB")
            canvas.paste(tile, (col * 256, row * 256))
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


# ------------------------------------------------------------------
# Interfaccia per l'API
# ------------------------------------------------------------------

def layer_image(body: str, layer: str, session=requests) -> bytes:
    key = (body, layer)
    if key not in _images:
        spec = LAYERS[body][layer]
        data = elevation_image(body, session) if spec["kind"] == "dem" else trek_mosaic(spec, session)
        _images[key] = data
    return _images[key]


def catalog(body: str) -> list:
    """Mappe disponibili per un corpo, con legenda e didascalia."""
    result = []
    for key, spec in LAYERS.get(body, {}).items():
        if spec["kind"] == "dem":
            dem = DEMS[body]
            result.append({
                "key": key, "label": spec["label"],
                "image": f"/api/v1/space/layer?body={body}&layer={key}",
                "legend": elevation_legend(body),
                "caption": (f"Altitudine rispetto al {dem['reference']}, misurata dall'altimetro laser. "
                            "Il rilievo è ombreggiato con luce da nord-ovest. Tocca un punto del "
                            "globo per leggerne l'altitudine."),
                "pickable": True,
                "attribution": dem["attribution"],
            })
        else:
            result.append({
                "key": key, "label": spec["label"],
                "image": f"/api/v1/space/layer?body={body}&layer={key}",
                "legend": spec["legend"], "caption": spec["caption"],
                "pickable": False, "attribution": spec["attribution"],
            })
    return result
