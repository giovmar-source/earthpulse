"""
Isole di calore: temperatura della superficie da Landsat 8 e 9.

Dati
----
- Landsat Collection 2 Level-2 (USGS), catalogo Microsoft Planetary Computer.
  Accesso gratuito: gli indirizzi dei file vanno "firmati" con un token SAS
  anonimo, chiesto al servizio di Planetary Computer (nessun account).
- Banda "lwir11" (ST_B10): temperatura della superficie in kelvin,
  valore = DN * 0.00341802 + 149.0. Il sensore termico (TIRS) misura a
  100 m; USGS distribuisce il prodotto ricampionato a 30 m.
- Banda "qa_pixel": maschera di nuvole, ombre, neve e acqua (bit).

Cosa calcoliamo
---------------
- Temperatura della superficie (°C) di una giornata estiva limpida.
- Anomalia: quanto ogni punto è più caldo o più fresco della mediana della
  terraferma dell'area. Con più giornate estive facciamo la mediana delle
  anomalie: un'immagine "tipica" dell'estate, meno legata a un solo giorno.

Attenzione: è la temperatura delle SUPERFICI (tetti, asfalto, prati) verso
le 10:30-11 del mattino, non la temperatura dell'aria.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import numpy as np
import requests
from rasterio.enums import Resampling

from src.imagery import Grid, colorize, read_on_grid, to_png, color_stops_hex


PC_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"
PC_SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{collection}"
COLLECTION = "landsat-c2-l2"
PLATFORMS = ["landsat-8", "landsat-9"]

ST_SCALE = 0.00341802
ST_OFFSET = 149.0
KELVIN = 273.15

# Bit di qa_pixel (Landsat Collection 2)
QA_FILL = 1 << 0
QA_DILATED_CLOUD = 1 << 1
QA_CIRRUS = 1 << 2
QA_CLOUD = 1 << 3
QA_CLOUD_SHADOW = 1 << 4
QA_SNOW = 1 << 5
QA_WATER = 1 << 7
QA_INVALID = QA_FILL | QA_DILATED_CLOUD | QA_CIRRUS | QA_CLOUD | QA_CLOUD_SHADOW | QA_SNOW

HEAT_RESOLUTION_M = 15.0        # griglia di visualizzazione (dato nativo 30 m)
DEFAULT_SIDE_KM = 8.0
MAX_SIDE_KM = 20.0
SUMMER_MONTHS = (6, 7, 8)
YEARS_BACK = 3
MAX_CLOUD = 30.0
MIN_VALID = 80.0                # % minima di pixel validi sulla terraferma
MAX_SCENES = 4                  # giornate usate per l'anomalia "tipica"

# Scale di colore
ANOMALY_STOPS = [
    (-8.0, (40, 90, 170)),
    (-4.0, (120, 170, 220)),
    (0.0, (245, 245, 235)),
    (3.0, (250, 200, 90)),
    (6.0, (235, 110, 45)),
    (9.0, (170, 30, 40)),
]
TEMPERATURE_STOPS = [
    (15.0, (45, 80, 160)),
    (25.0, (110, 180, 200)),
    (32.0, (245, 235, 170)),
    (40.0, (240, 150, 60)),
    (50.0, (190, 40, 40)),
    (60.0, (110, 10, 40)),
]
WATER_COLOR = (170, 195, 215)
INVALID_COLOR = (180, 180, 180)

ATTRIBUTION = ("Temperatura: Landsat 8-9 Collection 2 (USGS/NASA), "
               "via Microsoft Planetary Computer")


class HeatUnavailable(RuntimeError):
    """Dati Landsat non raggiungibili o nessuna scena utile."""


# ------------------------------------------------------------------
# Token SAS anonimo di Planetary Computer
# ------------------------------------------------------------------

_token_lock = threading.Lock()
_token = {"value": None, "expires": 0.0}


def sas_token() -> str:
    with _token_lock:
        if _token["value"] and time.time() < _token["expires"] - 300:
            return _token["value"]
    try:
        response = requests.get(PC_SAS_URL.format(collection=COLLECTION),
                                timeout=(10, 30))
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise HeatUnavailable(f"Token Planetary Computer non ottenuto: {error}") from error

    expires = time.time() + 30 * 60
    expiry_text = data.get("msft:expiry")
    if expiry_text:
        try:
            expires = datetime.fromisoformat(
                expiry_text.replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    with _token_lock:
        _token["value"] = data["token"]
        _token["expires"] = expires
    return data["token"]


def signed(href: str) -> str:
    separator = "&" if "?" in href else "?"
    return f"{href}{separator}{sas_token()}"


# ------------------------------------------------------------------
# Ricerca delle scene estive
# ------------------------------------------------------------------

def summer_ranges(today: date, years_back: int = YEARS_BACK) -> list:
    """Intervalli giugno-agosto degli ultimi anni (l'estate in corso inclusa se iniziata)."""
    ranges = []
    last_year = today.year if today >= date(today.year, SUMMER_MONTHS[0], 15) else today.year - 1
    for year in range(last_year, last_year - years_back, -1):
        start = date(year, SUMMER_MONTHS[0], 1)
        end = min(date(year, SUMMER_MONTHS[-1], 31), today)
        ranges.append((start, end))
    return ranges


def search_summer_items(lat: float, lon: float, today: date | None = None,
                        max_cloud: float = MAX_CLOUD) -> list:
    """Scene Landsat 8/9 estive sul punto, ordinate per nuvolosità."""
    from pystac_client import Client

    today = today or date.today()
    catalog = Client.open(PC_STAC_URL)
    items = []
    for start, end in summer_ranges(today):
        search = catalog.search(
            collections=[COLLECTION],
            intersects={"type": "Point", "coordinates": [lon, lat]},
            datetime=f"{start.isoformat()}/{end.isoformat()}",
            query={
                "eo:cloud_cover": {"lt": max_cloud},
                "platform": {"in": PLATFORMS},
            },
            max_items=40,
        )
        items.extend(search.items())
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    return items


# ------------------------------------------------------------------
# Lettura e calcolo
# ------------------------------------------------------------------

@dataclass
class HeatScene:
    item_id: str
    date: str
    platform: str
    celsius: np.ndarray      # temperatura della superficie (NaN = non valido)
    water: np.ndarray        # acqua (mare, laghi, fiumi)
    valid_land_pct: float


def celsius_from_dn(dn: np.ndarray) -> np.ndarray:
    values = dn.astype(np.float32) * ST_SCALE + ST_OFFSET - KELVIN
    values[dn == 0] = np.nan
    return values


def masks_from_qa(qa: np.ndarray):
    """(valido, acqua) dalla banda qa_pixel."""
    qa = qa.astype(np.uint16)
    valid = (qa != 0) & ((qa & QA_INVALID) == 0)
    water = (qa & QA_WATER) != 0
    return valid, water


def read_heat_scene(item, grid: Grid) -> HeatScene:
    st = read_on_grid(signed(item.assets["lwir11"].href), grid,
                      resampling=Resampling.bilinear)
    qa = read_on_grid(signed(item.assets["qa_pixel"].href), grid,
                      resampling=Resampling.nearest)
    valid, water = masks_from_qa(qa)
    celsius = celsius_from_dn(st)
    celsius[~valid] = np.nan

    land = ~water & (qa != 0)
    land_count = int(land.sum())
    valid_land = int((np.isfinite(celsius) & land).sum())
    pct = 100.0 * valid_land / land_count if land_count else 0.0
    return HeatScene(
        item_id=item.id,
        date=item.datetime.date().isoformat() if item.datetime else "",
        platform=item.properties.get("platform", ""),
        celsius=celsius,
        water=water,
        valid_land_pct=round(pct, 1),
    )


def anomaly(scene: HeatScene) -> tuple:
    """(anomalia °C rispetto alla mediana della terraferma, mediana)."""
    land_values = scene.celsius[np.isfinite(scene.celsius) & ~scene.water]
    if land_values.size < 50:
        raise HeatUnavailable("Troppi pochi pixel validi sulla terraferma.")
    median = float(np.median(land_values))
    return scene.celsius - median, median


def water_union(scenes: list) -> np.ndarray:
    """
    Acqua secondo QUALSIASI giornata: la maschera Landsat a volte non
    riconosce l'acqua (porti, foci) o la scarta come nuvola in un giorno solo.
    """
    water = np.zeros(scenes[0].water.shape, dtype=bool)
    for scene in scenes:
        water |= scene.water
    return water


PIER_WINDOW = 7            # finestra 7 x 7 pixel (~105 m) attorno a ogni punto
PIER_WATER_SHARE = 0.5     # oltre metà acqua attorno = molo, diga o pontile


def box_mean(mask: np.ndarray, size: int) -> np.ndarray:
    """Media di una maschera su una finestra quadrata (bordi replicati)."""
    pad = size // 2
    padded = np.pad(mask.astype(np.float32), pad, mode="edge")
    total = padded.cumsum(axis=0).cumsum(axis=1)
    total = np.pad(total, ((1, 0), (1, 0)))
    h, w = mask.shape
    window = (total[size:size + h, size:size + w] - total[:h, size:size + w]
              - total[size:size + h, :w] + total[:h, :w])
    return window / (size * size)


def mask_piers(water: np.ndarray) -> np.ndarray:
    """
    Aggiunge all'acqua moli, dighe e pontili: strisce di terra sottili
    circondate dal mare. Il sensore termico misura a 100 m, quindi lì la
    temperatura è mescolata con quella dell'acqua e risulterebbe falsamente
    fresca. La costa normale (acqua solo da un lato) resta terraferma.
    """
    return water | (box_mean(water, PIER_WINDOW) > PIER_WATER_SHARE)


def with_water(scene: HeatScene, water: np.ndarray) -> HeatScene:
    """Stessa giornata, con la maschera dell'acqua comune a tutte le giornate."""
    celsius = scene.celsius.copy()
    celsius[water] = np.nan
    return HeatScene(scene.item_id, scene.date, scene.platform, celsius,
                     water, scene.valid_land_pct)


def typical_anomaly(scenes: list) -> np.ndarray:
    """Mediana, pixel per pixel, delle anomalie di più giornate."""
    stack = np.stack([anomaly(scene)[0] for scene in scenes])
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return np.nanmedian(stack, axis=0)


def choose_scenes(items, grid: Grid, max_scenes: int = MAX_SCENES,
                  min_valid: float = MIN_VALID, max_checks: int = 10) -> list:
    """Legge le scene più limpide finché ne trova max_scenes utili sull'area."""
    chosen = []
    for item in items[:max_checks]:
        try:
            scene = read_heat_scene(item, grid)
        except Exception:
            continue
        if scene.valid_land_pct >= min_valid:
            chosen.append(scene)
        if len(chosen) >= max_scenes:
            break
    chosen.sort(key=lambda s: s.date, reverse=True)
    if chosen:
        water = mask_piers(water_union(chosen))
        chosen = [with_water(scene, water) for scene in chosen]
    return chosen


# ------------------------------------------------------------------
# Immagini e numeri
# ------------------------------------------------------------------

def colorize_heat(values: np.ndarray, water: np.ndarray, stops) -> np.ndarray:
    valid = np.isfinite(values)
    image = colorize(values, valid, stops)
    image[water] = WATER_COLOR
    image[~valid & ~water] = INVALID_COLOR
    return image


def render_temperature_png(scene: HeatScene) -> bytes:
    return to_png(colorize_heat(scene.celsius, scene.water, TEMPERATURE_STOPS))


def render_anomaly_png(values: np.ndarray, water: np.ndarray) -> bytes:
    return to_png(colorize_heat(values, water, ANOMALY_STOPS))


def heat_summary(values: np.ndarray, water: np.ndarray) -> dict:
    """Quota di terraferma molto calda o fresca rispetto alla mediana."""
    land = np.isfinite(values) & ~water
    if land.sum() == 0:
        return {"hot_share": None, "cool_share": None, "p95": None, "p05": None}
    v = values[land]
    return {
        "hot_share": round(100.0 * float((v >= 3.0).mean()), 1),     # >= +3 °C
        "cool_share": round(100.0 * float((v <= -3.0).mean()), 1),   # <= -3 °C
        "p95": round(float(np.percentile(v, 95)), 1),
        "p05": round(float(np.percentile(v, 5)), 1),
    }


def legend() -> dict:
    return {
        "anomaly": {
            "unit": "°C rispetto alla mediana",
            "color_stops": color_stops_hex(ANOMALY_STOPS),
            "labels": ["Più fresco", "Nella media", "Più caldo"],
        },
        "temperature": {
            "unit": "°C (superficie)",
            "color_stops": color_stops_hex(TEMPERATURE_STOPS),
            "labels": ["15 °C", "37 °C", "60 °C"],
        },
        "water_color": "#%02x%02x%02x" % WATER_COLOR,
    }


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


# ------------------------------------------------------------------
# Risultato completo per un'area (usato dall'API, con cache)
# ------------------------------------------------------------------

@dataclass
class HeatResult:
    scenes: list
    typical: np.ndarray
    water: np.ndarray

    @property
    def latest(self) -> HeatScene:
        return self.scenes[0]


_result_cache: dict = {}
_result_lock = threading.Lock()
RESULT_CACHE_SIZE = 12


def heat_for_area(lat: float, lon: float, side_km: float) -> HeatResult:
    key = (round(lat, 4), round(lon, 4), round(side_km, 1))
    with _result_lock:
        if key in _result_cache:
            return _result_cache[key]

    items = search_summer_items(lat, lon, today_utc())
    if not items:
        raise HeatUnavailable("Nessuna scena Landsat estiva senza nuvole su quest'area.")
    grid = Grid(lat, lon, side_km, resolution=HEAT_RESOLUTION_M)
    scenes = choose_scenes(items, grid)
    if not scenes:
        raise HeatUnavailable("Nessuna giornata estiva abbastanza limpida su quest'area.")

    result = HeatResult(scenes, typical_anomaly(scenes), scenes[0].water)
    with _result_lock:
        if len(_result_cache) >= RESULT_CACHE_SIZE:
            _result_cache.clear()
        _result_cache[key] = result
    return result
