"""
Archivio storico Landsat: com'era un luogo dal 1984 a oggi.

Dati: Landsat Collection 2 Level-2 (riflettanza della superficie), catalogo
Microsoft Planetary Computer (accesso anonimo, vedi src/heat.py per il token).

- Landsat 4-5 TM (1982-2011), Landsat 7 ETM+ (1999-oggi), Landsat 8-9 OLI.
  Il catalogo usa gli stessi nomi di banda per tutti i sensori
  ("red", "green", "blue", "nir08"), quindi il calcolo è identico.
- Riflettanza = DN * 0.0000275 - 0.2 (tutti i sensori, Collection 2).
- Landsat 7 dal 31 maggio 2003 ha un guasto (SLC-off) che lascia strisce
  vuote nelle immagini: lo usiamo solo se quell'anno non c'è altro.

Per ogni anno scegliamo una giornata della stagione estiva (giugno-settembre
nell'emisfero nord, dicembre-marzo nel sud), così la vegetazione è
confrontabile tra anni diversi.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from rasterio.enums import Resampling

from src.heat import (
    COLLECTION, PC_STAC_URL, QA_FILL, QA_INVALID, QA_WATER, box_mean, signed,
)
from src.imagery import (
    NDVI_COLOR_STOPS, Grid, colorize, read_on_grid, to_png,
)
from src.indices import _layer
from src.limits import heavy_task


FIRST_YEAR = 1984
SR_SCALE = 0.0000275
SR_OFFSET = -0.2
ARCHIVE_PLATFORMS = ["landsat-4", "landsat-5", "landsat-7", "landsat-8", "landsat-9"]
L7_SLC_OFF = date(2003, 5, 31)
MAX_CLOUD = 20.0
MIN_VALID = 85.0
CANDIDATES_PER_YEAR = 4
# Anni decodificati tenuti in memoria (a 12 km ~12 MB ciascuno): pochi, per
# restare nei 512 MB del server gratuito. Le immagini PNG restano in cache a parte.
SCENE_CACHE_SIZE = 6

# Colori reali: riflettanza 0 -> nero, RGB_WHITE -> bianco (uguale per tutti gli anni)
RGB_WHITE = 0.25
RGB_GAMMA = 0.8
INVALID_COLOR = (180, 180, 180)

SENSORS = {
    "landsat-4": "Landsat 4 TM",
    "landsat-5": "Landsat 5 TM",
    "landsat-7": "Landsat 7 ETM+",
    "landsat-8": "Landsat 8 OLI",
    "landsat-9": "Landsat 9 OLI-2",
}

ATTRIBUTION = ("Archivio: Landsat 4-9 Collection 2 (USGS/NASA), "
               "via Microsoft Planetary Computer")


class ArchiveUnavailable(RuntimeError):
    pass


# ------------------------------------------------------------------
# Scelta delle scene
# ------------------------------------------------------------------

def season_months(lat: float) -> tuple:
    """Mesi della stagione "estiva" dell'emisfero."""
    return (6, 7, 8, 9) if lat >= 0 else (12, 1, 2, 3)


def season_year(day: date, lat: float) -> int:
    """Anno di riferimento: nell'emisfero sud dicembre conta per l'anno dopo."""
    if lat < 0 and day.month == 12:
        return day.year + 1
    return day.year


def is_slc_off(item) -> bool:
    return (item.properties.get("platform") == "landsat-7"
            and item.datetime is not None
            and item.datetime.date() > L7_SLC_OFF)


def rank(item) -> tuple:
    """Ordine di preferenza: niente strisce L7, poi meno nuvole."""
    return (is_slc_off(item), item.properties.get("eo:cloud_cover", 100.0))


def group_by_year(items, lat: float, per_year: int = CANDIDATES_PER_YEAR) -> dict:
    """{anno: [candidati migliori]} solo per le giornate della stagione."""
    months = season_months(lat)
    years: dict = {}
    for item in items:
        if item.datetime is None:
            continue
        day = item.datetime.date()
        if day.month not in months:
            continue
        years.setdefault(season_year(day, lat), []).append(item)
    return {
        year: sorted(candidates, key=rank)[:per_year]
        for year, candidates in sorted(years.items())
        if year >= FIRST_YEAR
    }


def search_archive(lat: float, lon: float, today: date | None = None) -> list:
    from pystac_client import Client

    today = today or date.today()
    catalog = Client.open(PC_STAC_URL)
    search = catalog.search(
        collections=[COLLECTION],
        intersects={"type": "Point", "coordinates": [lon, lat]},
        datetime=f"{FIRST_YEAR - 1}-12-01/{today.isoformat()}",
        query={
            "eo:cloud_cover": {"lt": MAX_CLOUD},
            "platform": {"in": ARCHIVE_PLATFORMS},
        },
        max_items=3000,
    )
    return list(search.items())


_years_cache: dict = {}
_years_lock = threading.Lock()


def archive_years(lat: float, lon: float) -> dict:
    """{anno: candidati} per il punto (cache per luogo, ~1 km)."""
    key = (round(lat, 2), round(lon, 2))
    with _years_lock:
        if key in _years_cache:
            return _years_cache[key]
    items = search_archive(lat, lon)
    years = group_by_year(items, lat)
    with _years_lock:
        if len(_years_cache) > 50:
            _years_cache.clear()
        _years_cache[key] = years
    return years


# ------------------------------------------------------------------
# Lettura e immagini
# ------------------------------------------------------------------

@dataclass
class ArchiveScene:
    item_id: str
    date: str
    platform: str
    rgb: np.ndarray          # (3, righe, colonne) riflettanza
    red: np.ndarray
    nir: np.ndarray
    valid: np.ndarray
    water: np.ndarray
    valid_pct: float
    # Date delle altre giornate usate per riempire i vuoti (Landsat 7)
    filled_from: list = field(default_factory=list)

    @property
    def sensor(self) -> str:
        return SENSORS.get(self.platform, self.platform)


def reflectance(dn: np.ndarray) -> np.ndarray:
    values = dn.astype(np.float32) * SR_SCALE + SR_OFFSET
    values[dn == 0] = np.nan
    return values


def read_archive_scene(item, grid: Grid) -> ArchiveScene:
    def band(key, resampling=Resampling.bilinear):
        return read_on_grid(signed(item.assets[key].href), grid, resampling=resampling)

    qa = band("qa_pixel", Resampling.nearest).astype(np.uint16)
    red, green, blue, nir = (reflectance(band(k)) for k in ("red", "green", "blue", "nir08"))
    # Vicino ai buchi (bordi della scena, strisce di Landsat 7) l'interpolazione
    # mescola dati validi e vuoti e crea linee scure: escludiamo 2 pixel attorno.
    no_data = (qa == 0) | ((qa & QA_FILL) != 0)
    near_gap = box_mean(no_data, 5) > 0
    valid = ~near_gap & ((qa & QA_INVALID) == 0) & np.isfinite(red) & np.isfinite(nir)
    water = (qa & QA_WATER) != 0
    pct = 100.0 * float(valid.mean()) if valid.size else 0.0
    rgb = np.stack([red, green, blue])
    del green, blue
    return ArchiveScene(
        item_id=item.id,
        date=item.datetime.date().isoformat(),
        platform=item.properties.get("platform", ""),
        rgb=rgb,
        red=rgb[0], nir=nir, valid=valid, water=water,
        valid_pct=round(pct, 1),
    )


def fill_gaps(base: ArchiveScene, other: ArchiveScene) -> ArchiveScene:
    """
    Riempie i pixel non validi di "base" con quelli validi di "other"
    (stessa griglia). Serve per le strisce vuote di Landsat 7 SLC-off:
    in giornate diverse le strisce cadono in punti diversi.
    """
    take = ~base.valid & other.valid
    if not take.any():
        return base
    both = base.valid & other.valid

    def matched(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """Porta i valori dell'altra giornata al livello della prima (media e contrasto)."""
        if both.sum() < 200:
            return source
        s, r = source[both], reference[both]
        s_std = float(np.std(s))
        gain = float(np.std(r)) / s_std if s_std > 1e-6 else 1.0
        gain = min(max(gain, 0.5), 2.0)
        return (source - float(np.mean(s))) * gain + float(np.mean(r))

    rgb = base.rgb.copy()
    for band in range(3):
        rgb[band, take] = matched(other.rgb[band], base.rgb[band])[take]
    red = base.red.copy()
    red[take] = matched(other.red, base.red)[take]
    nir = base.nir.copy()
    nir[take] = matched(other.nir, base.nir)[take]
    valid = base.valid | take
    water = base.water.copy()
    water[take] = other.water[take]
    return ArchiveScene(
        item_id=base.item_id, date=base.date, platform=base.platform,
        rgb=rgb, red=red, nir=nir, valid=valid, water=water,
        valid_pct=round(100.0 * float(valid.mean()), 1),
        filled_from=base.filled_from + [other.date],
    )


def best_scene_for_year(candidates, grid: Grid, min_valid: float = MIN_VALID):
    """
    Prima candidata con abbastanza pixel validi. Se è Landsat 7 con le
    strisce (o comunque incompleta) si completano i vuoti con le candidate
    successive della stessa stagione.
    """
    base = None
    for item in candidates:
        try:
            scene = read_archive_scene(item, grid)
        except Exception:
            continue
        if base is None:
            base = scene
        elif not base.valid.all():
            base = fill_gaps(base, scene)
        if base.valid_pct >= min_valid and not is_slc_off(item):
            return base
        if base.valid_pct >= 99.9:
            return base
    return base


SATURATION_LIMIT = 0.05      # come per Sentinel-2 (src/imagery.py)
MAX_WHITE = 0.6


def white_point(scene: ArchiveScene) -> float:
    """
    Riflettanza che diventa bianco. Fissa (RGB_WHITE) nelle scene normali;
    nei deserti e sulla neve, dove oltre il 5% dei pixel la supererebbe,
    sale al 99° percentile del canale più luminoso (massimo MAX_WHITE).
    Va calcolata una volta per luogo e usata per tutti gli anni.
    """
    brightest = np.nanmax(scene.rgb, axis=0)[scene.valid]
    brightest = brightest[np.isfinite(brightest)]
    if brightest.size < 100 or float(np.mean(brightest >= RGB_WHITE)) <= SATURATION_LIMIT:
        return RGB_WHITE
    # Margine del 20% sopra il 99° percentile: la sabbia resta color sabbia,
    # senza schiacciarsi verso il bianco-giallo.
    return float(min(MAX_WHITE, max(RGB_WHITE, 1.2 * np.percentile(brightest, 99))))


def render_rgb(scene: ArchiveScene, white: float = RGB_WHITE) -> bytes:
    """Colori reali con la stessa scala per tutti gli anni e i sensori."""
    # Nelle scene chiare (bianco adattato) niente schiarimento dei mezzitoni:
    # renderebbe la sabbia ancora più pallida.
    gamma = RGB_GAMMA if white <= RGB_WHITE else 1.0
    rgb = np.clip(np.nan_to_num(scene.rgb, nan=0.0) / white, 0, 1) ** gamma
    image = np.transpose(rgb * 255, (1, 2, 0)).astype(np.uint8)
    no_data = ~np.isfinite(scene.rgb).all(axis=0) | ~scene.valid & (np.nan_to_num(scene.rgb).sum(axis=0) == 0)
    cloudy = ~scene.valid & ~no_data
    # Vuoti rimasti (per esempio strisce non coperte da nessuna giornata): grigio
    image[no_data] = INVALID_COLOR
    # Nuvole e ombre: velo grigio chiaro, per non confonderle con il terreno
    image[cloudy] = (0.5 * image[cloudy] + 0.5 * np.array(INVALID_COLOR)).astype(np.uint8)
    return to_png(image)


def ndvi(scene: ArchiveScene) -> np.ndarray:
    with np.errstate(all="ignore"):
        values = (scene.nir - scene.red) / (scene.nir + scene.red)
    values[~scene.valid] = np.nan
    return values


def render_ndvi(scene: ArchiveScene) -> bytes:
    values = ndvi(scene)
    valid = np.isfinite(values)
    return to_png(colorize(values, valid, NDVI_COLOR_STOPS))


_scene_cache: dict = {}
_scene_lock = threading.Lock()


def scene_for_year(lat: float, lon: float, side_km: float, year: int) -> ArchiveScene:
    key = (round(lat, 4), round(lon, 4), round(side_km, 1), year)
    with _scene_lock:
        if key in _scene_cache:
            return _scene_cache[key]
    candidates = archive_years(lat, lon).get(year)
    if not candidates:
        raise ArchiveUnavailable(f"Nessuna immagine Landsat limpida per il {year}.")
    grid = Grid(lat, lon, side_km)
    with heavy_task():
        scene = best_scene_for_year(candidates, grid)
    if scene is None:
        raise ArchiveUnavailable(f"Immagini del {year} non leggibili.")
    with _scene_lock:
        if len(_scene_cache) >= SCENE_CACHE_SIZE:
            _scene_cache.clear()
        _scene_cache[key] = scene
    return scene


# ------------------------------------------------------------------
# Descrizione dei livelli per l'app (stesso formato di src/indices.py)
# ------------------------------------------------------------------

LAYERS = [
    _layer(
        "rgb", "Colori reali", "compare",
        "Colori reali Landsat (pixel di 30 m), con lo stesso contrasto per tutti "
        "gli anni e i sensori. Le nuvole restano visibili sotto un velo grigio.",
    ),
    _layer(
        "ndvi", "Vegetazione", "compare",
        "NDVI da Landsat (30 m): vigore della vegetazione. In grigio nuvole, "
        "ombre e dati mancanti. I sensori di epoche diverse (TM, OLI) hanno bande "
        "leggermente diverse: piccole differenze non sono significative.",
        NDVI_COLOR_STOPS, ("Suolo, acqua", "Vegetazione rada", "Vegetazione densa"),
        "NDVI = (NIR − Rosso) / (NIR + Rosso)",
    ),
]
