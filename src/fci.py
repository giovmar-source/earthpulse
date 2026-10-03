"""
Prodotti di Meteosat-12 (MTG-I1) sovrapposti alle immagini delle nuvole:
incendi attivi (FRP), fulmini (Lightning Imager) e pioggia stimata (H40B).

Le immagini vengono dal servizio pubblico EUMETView (EUMETSAT). Il server le
scarica e le ricolora con un colore unico e ben visibile per ogni prodotto
(rosso-arancio, giallo, blu elettrico), così la legenda è semplice e sempre
uguale; conta anche i pixel con dati, così il sito può dire "nessun fulmine
nell'area" invece di mostrare un'immagine vuota senza spiegazioni.
"""

from __future__ import annotations

import io
from collections import OrderedDict
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import requests

EUMETVIEW_WMS = "https://view.eumetsat.int/geoserver/ows"
ATTRIBUTION = "© EUMETSAT (EUMETView), prodotti MTG FCI e LI"

PRODUCTS = {
    "fires": {"layer": "mtg_fd:frp", "color": (255, 69, 0), "grow": 2,
              "label": "Incendi attivi"},
    "lightning": {"layer": "mtg_fd:li_afa", "color": (255, 236, 0), "grow": 1,
                  "label": "Fulmini"},
    "rain": {"layer": "mtg_fd:h40b", "color": (30, 80, 255), "grow": 0,
             "label": "Pioggia"},
}
MIN_ALPHA = 20          # pixel con opacità minore = nessun dato
MAX_SIZE = 640

_cache: OrderedDict = OrderedDict()
MAX_CACHE = 400


def delay_minutes() -> int:
    """
    Ritardo minimo delle immagini (EUMETSAT_DELAY_MINUTES). Politica dati EUMETSAT:
    le immagini con almeno 1 ora di ritardo sono libere anche per uso commerciale;
    più recenti, in un prodotto a pagamento, servono licenze da 4 000–8 000 € l'anno.
    0 = nessun vincolo (beta gratuita); in vendita: 60.
    """
    try:
        return max(0, int(os.environ.get("EUMETSAT_DELAY_MINUTES", "0")))
    except ValueError:
        return 60


def allowed_time(moment: datetime) -> bool:
    latest = datetime.now(timezone.utc) - timedelta(minutes=delay_minutes())
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment <= latest


def wms_params(layer: str, bbox: list, time: str, size: int) -> dict:
    return {
        "service": "WMS", "version": "1.1.1", "request": "GetMap",
        "layers": layer, "styles": "", "srs": "EPSG:4326",
        "bbox": ",".join(f"{v:.4f}" for v in bbox),
        "width": str(size), "height": str(size),
        "format": "image/png", "transparent": "true", "time": time,
    }


def grow(mask: np.ndarray, pixels: int) -> np.ndarray:
    """Allarga i punti (incendi e fulmini sono pochi pixel: così si vedono)."""
    out = mask.copy()
    for _ in range(pixels):
        shifted = out.copy()
        shifted[1:] |= out[:-1]
        shifted[:-1] |= out[1:]
        shifted[:, 1:] |= out[:, :-1]
        shifted[:, :-1] |= out[:, 1:]
        out = shifted
    return out


def recolor(png: bytes, product: str) -> tuple:
    """PNG di EUMETView -> (PNG con colore unico, numero di pixel con dati)."""
    from PIL import Image
    spec = PRODUCTS[product]
    rgba = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))
    data = rgba[:, :, 3] >= MIN_ALPHA
    count = int(data.sum())
    shown = grow(data, spec["grow"])
    out = np.zeros(rgba.shape, dtype=np.uint8)
    out[shown, :3] = spec["color"]
    out[shown, 3] = 235
    buffer = io.BytesIO()
    Image.fromarray(out, mode="RGBA").save(buffer, format="PNG", optimize=True)
    return buffer.getvalue(), count


def overlay(product: str, bbox: list, time: datetime, size: int = 512, session=requests) -> tuple:
    """(PNG ricolorato, pixel con dati) per un prodotto, un'area e un'ora."""
    size = min(int(size), MAX_SIZE)
    stamp = time.strftime("%Y-%m-%dT%H:%M:00Z")
    key = (product, tuple(round(v, 3) for v in bbox), stamp, size)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    response = session.get(EUMETVIEW_WMS, params=wms_params(PRODUCTS[product]["layer"], bbox, stamp, size),
                           timeout=30)
    content_type = response.headers.get("Content-Type", "")
    if response.status_code != 200 or not content_type.startswith("image/png"):
        raise ValueError(f"EUMETView non ha restituito un'immagine ({response.status_code})")
    result = recolor(response.content, product)
    _cache[key] = result
    if len(_cache) > MAX_CACHE:
        _cache.popitem(last=False)
    return result
