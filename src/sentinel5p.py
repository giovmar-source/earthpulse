"""
Gas in atmosfera misurati da Sentinel-5P (strumento TROPOMI), tramite le API
Sentinel Hub di Copernicus Data Space Ecosystem (account gratuito).

Credenziali (variabili d'ambiente, mai nel codice):
    CDSE_CLIENT_ID, CDSE_CLIENT_SECRET   (client OAuth creato nella Dashboard)

Per ogni richiesta chiediamo a Sentinel Hub la MEDIA dei passaggi del periodo
(mosaicking ORBIT) come numeri in virgola mobile (GeoTIFF FLOAT32): i colori e
i numeri li calcoliamo noi, così da una sola richiesta otteniamo immagine e
valori. Il piano gratuito ha 10.000 richieste al mese: i risultati restano in
memoria per tutta la giornata.
"""

from __future__ import annotations

import io
import math
import os
import threading
import time
from datetime import date, datetime, timedelta, timezone

import numpy as np
import requests

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

ATTRIBUTION = ("Contiene dati Copernicus Sentinel-5P modificati, "
               "elaborati con Sentinel Hub (Copernicus Data Space Ecosystem)")

IMAGE_SIZE = 256          # pixel per lato (i pixel TROPOMI sono di circa 5 × 3,5 km)
HALF_SIDE_KM = 150.0      # area di 300 × 300 km intorno al luogo
PLACE_RADIUS_KM = 15.0    # "sul luogo": media entro 15 km dal punto

# Gas disponibili: banda Sentinel Hub, conversione dell'unità, scala dei colori
GASES = {
    "no2": {
        "band": "NO2", "label": "Biossido di azoto (NO₂)",
        "unit": "µmol/m²", "factor": 1e6, "digits": 0,
        "stops": [(0, "#0d1440"), (20, "#253a8c"), (40, "#2f7fc1"), (70, "#7cc47a"),
                  (100, "#f2d15c"), (150, "#f08a3c"), (220, "#c8323c")],
        "labels": ["Pulito", "", "Inquinato"],
        "caption": ("Colonna di NO₂ nella bassa atmosfera, media dei passaggi del periodo. "
                    "Viene soprattutto da traffico, centrali e industrie: le città e i porti "
                    "spiccano come macchie."),
        "default_days": 7,
    },
    "ch4": {
        "band": "CH4", "label": "Metano (CH₄)",
        "unit": "ppb", "factor": 1.0, "digits": 0,
        "stops": [(1800, "#1b2a5c"), (1850, "#3e6db0"), (1880, "#7cc4a4"),
                  (1910, "#f2d15c"), (1940, "#f08a3c"), (1980, "#c8323c")],
        "labels": ["1800 ppb", "", "1980 ppb"],
        "caption": ("Concentrazione media di metano nella colonna d'aria. Fonti: allevamenti, "
                    "discariche, risaie, estrazione di gas e petrolio. Le nuvole lasciano "
                    "molti buchi: per questo usiamo un mese."),
        "default_days": 30,
    },
    "co": {
        "band": "CO", "label": "Monossido di carbonio (CO)",
        "unit": "mmol/m²", "factor": 1e3, "digits": 1,
        "stops": [(20, "#1b2a5c"), (26, "#3e6db0"), (30, "#7cc4a4"),
                  (34, "#f2d15c"), (40, "#f08a3c"), (50, "#c8323c")],
        "labels": ["Basso", "", "Alto"],
        "caption": ("Colonna totale di CO. Viene da combustioni incomplete: incendi, traffico, "
                    "riscaldamento. I fumi degli incendi si vedono anche a centinaia di km."),
        "default_days": 7,
    },
}
NO_DATA_COLOR = (40, 46, 56)
PERIODS = (7, 30)


class S5PUnavailable(Exception):
    """Servizio non configurato o non raggiungibile: messaggio per l'utente."""


def has_credentials() -> bool:
    return bool(os.environ.get("CDSE_CLIENT_ID") and os.environ.get("CDSE_CLIENT_SECRET"))


# ------------------------------------------------------------------
# Token OAuth (riutilizzato finché vale: le richieste di token sono limitate)
# ------------------------------------------------------------------

_token = {"value": None, "expires": 0.0}
_token_lock = threading.Lock()


def get_token(session=requests) -> str:
    with _token_lock:
        if _token["value"] and time.time() < _token["expires"] - 60:
            return _token["value"]
        if not has_credentials():
            raise S5PUnavailable("Sentinel-5P non ancora attivo su questo server "
                                 "(mancano le credenziali Copernicus Data Space).")
        response = session.post(TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": os.environ["CDSE_CLIENT_ID"],
            "client_secret": os.environ["CDSE_CLIENT_SECRET"],
        }, timeout=20)
        if response.status_code != 200:
            raise S5PUnavailable(f"Accesso a Copernicus Data Space non riuscito ({response.status_code}): "
                                 "controlla CDSE_CLIENT_ID e CDSE_CLIENT_SECRET.")
        body = response.json()
        _token["value"] = body["access_token"]
        _token["expires"] = time.time() + float(body.get("expires_in", 600))
        return _token["value"]


# ------------------------------------------------------------------
# Richiesta a Sentinel Hub
# ------------------------------------------------------------------

def area_bbox(lat: float, lon: float, half_km: float = HALF_SIDE_KM) -> list:
    """Quadrato di 2 × half_km intorno al punto, in gradi [O, S, E, N]."""
    dlat = half_km / 110.574
    dlon = half_km / (111.320 * max(0.2, math.cos(math.radians(lat))))
    return [round(lon - dlon, 4), round(lat - dlat, 4), round(lon + dlon, 4), round(lat + dlat, 4)]


def evalscript(band: str) -> str:
    """Media dei passaggi validi (dataMask = 1) nel periodo, come numero."""
    return f"""//VERSION=3
function setup() {{
  return {{
    input: [{{ bands: ["{band}", "dataMask"] }}],
    output: {{ bands: 1, sampleType: "FLOAT32" }},
    mosaicking: "ORBIT"
  }};
}}
function evaluatePixel(samples) {{
  var sum = 0, n = 0;
  for (var i = 0; i < samples.length; i++) {{
    if (samples[i].dataMask === 1) {{ sum += samples[i].{band}; n++; }}
  }}
  return [n > 0 ? sum / n : NaN];
}}
"""


def request_body(gas: str, bbox: list, start: date, end: date, size: int = IMAGE_SIZE) -> dict:
    return {
        "input": {
            "bounds": {"bbox": bbox,
                       "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"}},
            "data": [{
                "type": "sentinel-5p-l2",
                "dataFilter": {"timeRange": {
                    "from": f"{start.isoformat()}T00:00:00Z",
                    "to": f"{end.isoformat()}T23:59:59Z",
                }},
            }],
        },
        "output": {"width": size, "height": size,
                   "responses": [{"identifier": "default", "format": {"type": "image/tiff"}}]},
        "evalscript": evalscript(GASES[gas]["band"]),
    }


def read_tiff(content: bytes) -> np.ndarray:
    from rasterio.io import MemoryFile
    with MemoryFile(content) as memfile, memfile.open() as dataset:
        return dataset.read(1).astype(np.float32)


def fetch_grid(gas: str, bbox: list, start: date, end: date, session=requests) -> np.ndarray:
    """Valori medi del periodo (unità di Sentinel Hub), NaN dove non ci sono dati."""
    token = get_token(session)
    response = session.post(
        PROCESS_URL, json=request_body(gas, bbox, start, end),
        headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff"}, timeout=90,
    )
    if response.status_code == 401:
        _token["value"] = None
    if response.status_code == 429:
        raise S5PUnavailable("Quota mensile o limite al minuto di Copernicus Data Space "
                             "raggiunto: riprova più tardi.")
    if response.status_code != 200:
        raise S5PUnavailable(f"Sentinel Hub ha risposto con errore {response.status_code}: "
                             f"{response.text[:200]}")
    grid = read_tiff(response.content)
    grid[~np.isfinite(grid)] = np.nan
    return grid


# ------------------------------------------------------------------
# Numeri e immagine
# ------------------------------------------------------------------

def to_display_units(gas: str, grid: np.ndarray) -> np.ndarray:
    return grid * GASES[gas]["factor"]


def place_mask(shape, radius_km: float = PLACE_RADIUS_KM, half_km: float = HALF_SIDE_KM) -> np.ndarray:
    """Cerchio di radius_km intorno al centro dell'immagine."""
    rows, cols = shape
    y, x = np.mgrid[0:rows, 0:cols]
    km_per_px = 2 * half_km / cols
    distance = np.hypot((x - (cols - 1) / 2) * km_per_px, (y - (rows - 1) / 2) * km_per_px)
    return distance <= radius_km


def summary(gas: str, values: np.ndarray) -> dict:
    """Valore sul luogo, nella regione e quota di area coperta da dati."""
    finite = np.isfinite(values)
    near = place_mask(values.shape) & finite
    digits = GASES[gas]["digits"]

    def stat(mask):
        return round(float(np.mean(values[mask])), digits) if mask.sum() >= 3 else None

    place = stat(near)
    region = stat(finite)
    ratio = round(place / region, 2) if place is not None and region not in (None, 0) else None
    return {
        "place": place,
        "region": region,
        "place_vs_region": ratio,
        "coverage_percentage": round(100.0 * float(finite.mean()), 1),
    }


def describe(gas: str, info: dict) -> str | None:
    """Frase semplice sul confronto tra luogo e regione."""
    ratio = info.get("place_vs_region")
    if ratio is None:
        return None
    if gas == "ch4":
        # Il metano varia di pochi punti percentuali: si confronta la differenza
        diff = info["place"] - info["region"]
        if abs(diff) < 10:
            return "Sul luogo il metano è in linea con la media della regione."
        return (f"Sul luogo il metano è {abs(diff):.0f} ppb {'sopra' if diff > 0 else 'sotto'} "
                "la media della regione.")
    if ratio >= 1.5:
        return f"Sul luogo il valore è {ratio:.1f} volte la media della regione."
    if ratio >= 1.15:
        return "Sul luogo il valore è un po' più alto della media della regione."
    if ratio <= 0.7:
        return "Sul luogo il valore è più basso della media della regione."
    return "Sul luogo il valore è in linea con la media della regione."


def _hex(color: str) -> tuple:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def colorize(gas: str, values: np.ndarray) -> np.ndarray:
    stops = GASES[gas]["stops"]
    xs = [v for v, _c in stops]
    rgb = np.array([_hex(c) for _v, c in stops], dtype=np.float32)
    clipped = np.clip(np.nan_to_num(values, nan=xs[0]), xs[0], xs[-1])
    image = np.stack([np.interp(clipped, xs, rgb[:, k]) for k in range(3)], axis=-1)
    image[~np.isfinite(values)] = NO_DATA_COLOR
    return image.astype(np.uint8)


def render_png(gas: str, values: np.ndarray) -> bytes:
    from PIL import Image
    buffer = io.BytesIO()
    Image.fromarray(colorize(gas, values)).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def legend(gas: str) -> dict:
    spec = GASES[gas]
    return {"unit": spec["unit"], "color_stops": [[v, c] for v, c in spec["stops"]],
            "labels": spec["labels"], "no_data_color": "#%02x%02x%02x" % NO_DATA_COLOR}


def period(days: int, today: date | None = None) -> tuple:
    """Ultimi `days` giorni fino a ieri (i dati di oggi arrivano nel corso della giornata)."""
    end = (today or datetime.now(timezone.utc).date()) - timedelta(days=1)
    return end - timedelta(days=days - 1), end
