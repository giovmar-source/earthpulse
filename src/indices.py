"""
Indici spettrali Sentinel-2 e descrizione dei livelli mostrati nell'app.

Tutti gli indici sono differenze normalizzate:  (A - B) / (A + B)
calcolate sulla griglia comune (src/imagery.Grid), con:
- correzione dello scostamento radiometrico 2022, verificata sui dati
  (src/ndvi.effective_offset);
- maschera SCL (nuvole, ombre, neve, dati mancanti);
- bande a 20 m (B11, B12) ricampionate in modo bilineare sulla griglia a 10 m.

Il backend descrive i livelli (nome, legenda, didascalia): l'app li mostra
senza doverli conoscere in anticipo.
"""

from __future__ import annotations

import numpy as np
from rasterio.enums import Resampling

from src.imagery import (
    DIFF_COLOR_STOPS,
    INVALID_COLOR,
    NDVI_COLOR_STOPS,
    Grid,
    colorize,
    color_stops_hex,
    read_on_grid,
    to_png,
    valid_mask_from_scl,
)
from src.ndvi import effective_offset


# Asset STAC di Earth Search per ogni banda usata.
BAND_ASSETS = {
    "B03": "green",
    "B04": "red",
    "B08": "nir",
    "B11": "swir16",
    "B12": "swir22",
}
BANDS_20M = {"B11", "B12"}


# ------------------------------------------------------------------
# Scale di colori
# ------------------------------------------------------------------

NDWI_COLOR_STOPS = [          # acqua in blu
    (-0.60, (150, 120, 90)),
    (-0.20, (225, 210, 180)),
    (0.00, (235, 240, 240)),
    (0.20, (130, 190, 230)),
    (0.50, (40, 110, 190)),
    (0.80, (10, 50, 120)),
]

NDMI_COLOR_STOPS = [          # dal secco (marrone) all'umido (blu-verde)
    (-0.40, (140, 80, 40)),
    (-0.10, (215, 170, 90)),
    (0.10, (240, 230, 160)),
    (0.25, (140, 200, 150)),
    (0.40, (40, 150, 150)),
    (0.60, (10, 80, 120)),
]

NDBI_COLOR_STOPS = [          # dalla vegetazione (verde) al costruito (rosso)
    (-0.50, (40, 120, 60)),
    (-0.20, (150, 200, 140)),
    (0.00, (240, 235, 220)),
    (0.10, (240, 180, 120)),
    (0.25, (210, 90, 50)),
    (0.40, (140, 30, 30)),
]

# dNBR: classi di gravità secondo USGS (Key & Benson, FIREMON).
DNBR_COLOR_STOPS = [
    (-0.25, (30, 120, 60)),     # ricrescita
    (-0.10, (150, 200, 140)),
    (0.10, (240, 240, 235)),    # non bruciato
    (0.27, (250, 220, 90)),     # bassa gravità
    (0.44, (245, 150, 50)),     # moderata-bassa
    (0.66, (215, 50, 40)),      # moderata-alta
    (0.90, (120, 20, 90)),      # alta gravità
]


# ------------------------------------------------------------------
# Definizione degli indici
# ------------------------------------------------------------------

INDICES = {
    "ndvi": {
        "bands": ("B08", "B04"),
        "formula": "NDVI = (B08 − B04) / (B08 + B04)",
        "stops": NDVI_COLOR_STOPS,
    },
    "ndwi": {
        "bands": ("B03", "B08"),
        "formula": "NDWI = (B03 − B08) / (B03 + B08)",
        "stops": NDWI_COLOR_STOPS,
    },
    # mask_water: indici pensati per la terraferma. Sull'acqua libera non
    # hanno significato (es. NDMI molto negativo = "secco" su un lago):
    # quei pixel vengono mostrati a parte, in azzurro-grigio.
    "ndmi": {
        "bands": ("B08", "B11"),
        "formula": "NDMI = (B08 − B11) / (B08 + B11)",
        "stops": NDMI_COLOR_STOPS,
        "mask_water": True,
    },
    "ndbi": {
        "bands": ("B11", "B08"),
        "formula": "NDBI = (B11 − B08) / (B11 + B08)",
        "stops": NDBI_COLOR_STOPS,
        "mask_water": True,
    },
    "nbr": {
        "bands": ("B08", "B12"),
        "formula": "NBR = (B08 − B12) / (B08 + B12)",
        "stops": NDVI_COLOR_STOPS,
        "mask_water": True,
    },
}

# Colore dell'acqua negli indici che non si applicano all'acqua.
WATER_COLOR = (170, 195, 215)
SCL_WATER = 6

# Asset richiesti perché una scena possa produrre tutti i livelli.
REQUIRED_ASSETS = ("visual", "scl") + tuple(sorted(set(BAND_ASSETS.values())))


# ------------------------------------------------------------------
# Livelli per l'app (ordine di visualizzazione)
# ------------------------------------------------------------------

def _layer(key, label, mode, caption, stops=None, legend=("", "", ""), formula=None):
    return {
        "key": key,
        "label": label,
        # "compare": cursore prima/dopo; "single": un'immagine sola
        "mode": mode,
        "caption": caption,
        "formula": formula,
        "color_stops": color_stops_hex(stops) if stops else [],
        "legend_labels": list(legend),
    }


LAYERS = {
    "rgb": _layer(
        "rgb", "Colori reali", "compare",
        "Come l'occhio vedrebbe l'area dallo spazio (bande B04, B03, B02). "
        "I colori della data precedente sono armonizzati a quelli della più "
        "recente (luce, foschia): solo per la visualizzazione.",
    ),
    "ndvi": _layer(
        "ndvi", "Vegetazione", "compare",
        "NDVI: vigore della vegetazione, pixel per pixel (10 m). In grigio i "
        "pixel esclusi: nuvole, ombre, neve o dati mancanti.",
        NDVI_COLOR_STOPS, ("Suolo, acqua", "Vegetazione rada", "Vegetazione densa"),
        INDICES["ndvi"]["formula"],
    ),
    "ndwi": _layer(
        "ndwi", "Acqua", "compare",
        "NDWI: evidenzia le superfici d'acqua (laghi, fiumi, allagamenti). "
        "Valori positivi indicano acqua libera; in aree urbane può dare falsi "
        "positivi su tetti e ombre.",
        NDWI_COLOR_STOPS, ("Terra asciutta", "", "Acqua"),
        INDICES["ndwi"]["formula"],
    ),
    "ndmi": _layer(
        "ndmi", "Umidità", "compare",
        "NDMI: contenuto d'acqua della vegetazione, sensibile allo stress "
        "idrico. Usa la banda SWIR B11 (20 m, ricampionata a 10 m). "
        "In azzurro-grigio l'acqua libera, dove l'indice non è significativo.",
        NDMI_COLOR_STOPS, ("Secco", "", "Umido"),
        INDICES["ndmi"]["formula"],
    ),
    "ndbi": _layer(
        "ndbi", "Costruito", "compare",
        "NDBI: evidenzia edifici, strade e superfici impermeabili. Anche il "
        "suolo nudo e le rocce danno valori alti: va letto insieme ai colori reali. "
        "In azzurro-grigio l'acqua libera, dove l'indice non è significativo.",
        NDBI_COLOR_STOPS, ("Vegetazione", "", "Costruito, suolo nudo"),
        INDICES["ndbi"]["formula"],
    ),
    "diff": _layer(
        "diff", "Variazione", "single",
        "Differenza di NDVI tra le due date, solo dove entrambe le immagini "
        "sono valide. Un calo non indica da solo la causa: stagione, sfalci, "
        "siccità, tagli o incendi possono produrlo.",
        DIFF_COLOR_STOPS, ("NDVI in calo", "Stabile", "NDVI in aumento"),
        "ΔNDVI = NDVI(dopo) − NDVI(prima)",
    ),
    "dnbr": _layer(
        "dnbr", "Gravità incendio", "single",
        "dNBR: differenza del Normalized Burn Ratio prima e dopo l'incendio, "
        "con le classi di gravità USGS (0,10 bassa · 0,27 moderata-bassa · "
        "0,44 moderata-alta · 0,66 alta). Indica l'effetto sulla vegetazione, "
        "non l'intensità delle fiamme.",
        DNBR_COLOR_STOPS, ("Ricrescita", "Non bruciato", "Gravità alta"),
        "dNBR = NBR(prima) − NBR(dopo)",
    ),
}

DEFAULT_LAYERS = ["rgb", "ndvi", "ndwi", "ndmi", "ndbi", "diff"]


def layer_list(keys) -> list:
    return [LAYERS[key] for key in keys if key in LAYERS]


# ------------------------------------------------------------------
# Calcolo
# ------------------------------------------------------------------

def read_band(item, band: str, grid: Grid) -> np.ndarray:
    resampling = Resampling.bilinear if band in BANDS_20M else Resampling.nearest
    return read_on_grid(item.assets[BAND_ASSETS[band]].href, grid, resampling=resampling)


def _index_arrays(item, grid: Grid, key: str):
    """(valori, valid, acqua) dell'indice sulla griglia."""
    if key not in INDICES:
        raise ValueError(f"Indice non supportato: {key}")

    band_a, band_b = INDICES[key]["bands"]
    raw_a = read_band(item, band_a, grid).astype(np.float32)
    raw_b = read_band(item, band_b, grid).astype(np.float32)
    scl = read_on_grid(item.assets["scl"].href, grid)

    has_data = (raw_a > 0) & (raw_b > 0)
    offset = effective_offset(item, raw_a, raw_b)
    a = np.clip(raw_a - offset, 0, None)
    b = np.clip(raw_b - offset, 0, None)
    denominator = a + b

    valid = valid_mask_from_scl(scl) & has_data & (denominator > 0)
    values = np.full(a.shape, np.nan, dtype=np.float32)
    values[valid] = (a[valid] - b[valid]) / denominator[valid]

    water = np.zeros(values.shape, dtype=bool)
    if INDICES[key].get("mask_water"):
        water = water_mask(item, grid, scl, offset_hint=offset)
    return values, valid, water


def water_mask(item, grid: Grid, scl: np.ndarray, offset_hint: float = 0.0) -> np.ndarray:
    """
    Acqua libera: classe SCL "acqua" (6) oppure NDWI > 0.
    L'NDWI serve per laghi torbidi o con alghe, che la SCL non sempre
    classifica come acqua.
    """
    green = read_band(item, "B03", grid).astype(np.float32)
    nir = read_band(item, "B08", grid).astype(np.float32)
    has_data = (green > 0) & (nir > 0)
    offset = effective_offset(item, green, nir)
    g = np.clip(green - offset, 0, None)
    n = np.clip(nir - offset, 0, None)
    total = g + n
    ndwi = np.full(g.shape, -1.0, dtype=np.float32)
    ok = has_data & (total > 0)
    ndwi[ok] = (g[ok] - n[ok]) / total[ok]
    return has_data & ((scl == SCL_WATER) | (ndwi > 0))


def index_on_grid(item, grid: Grid, key: str):
    """
    Restituisce (valori, valid) dell'indice sulla griglia.
    Per gli indici "da terraferma" l'acqua libera è esclusa dai valori validi.
    """
    values, valid, water = _index_arrays(item, grid, key)
    return values, valid & ~water


def render_index_png(item, grid: Grid, key: str) -> bytes:
    values, valid, water = _index_arrays(item, grid, key)
    image = colorize(values, valid & ~water, INDICES[key]["stops"])
    image[water] = WATER_COLOR
    return to_png(image)


def change_on_grid(after_item, before_item, grid: Grid, key: str):
    """
    Variazione dell'indice sui pixel validi in entrambe le date.
    Per "nbr" restituisce il dNBR = NBR(prima) - NBR(dopo) (positivo = bruciato).
    """
    after, valid_after = index_on_grid(after_item, grid, key)
    before, valid_before = index_on_grid(before_item, grid, key)
    valid = valid_after & valid_before
    change = np.full(after.shape, np.nan, dtype=np.float32)
    if key == "nbr":
        change[valid] = before[valid] - after[valid]
    else:
        change[valid] = after[valid] - before[valid]
    return change, valid


def render_dnbr_png(after_item, before_item, grid: Grid) -> bytes:
    dnbr, valid = change_on_grid(after_item, before_item, grid, "nbr")
    return to_png(colorize(dnbr, valid, DNBR_COLOR_STOPS))


def dnbr_severity_share(dnbr: np.ndarray, valid: np.ndarray) -> dict:
    """Percentuale di pixel validi in ogni classe di gravità USGS."""
    values = dnbr[valid]
    total = values.size
    if total == 0:
        return {}
    classes = {
        "ricrescita": values < -0.10,
        "non_bruciato": (values >= -0.10) & (values < 0.10),
        "bassa": (values >= 0.10) & (values < 0.27),
        "moderata_bassa": (values >= 0.27) & (values < 0.44),
        "moderata_alta": (values >= 0.44) & (values < 0.66),
        "alta": values >= 0.66,
    }
    return {name: round(100.0 * mask.sum() / total, 1) for name, mask in classes.items()}


__all__ = [
    "INDICES", "LAYERS", "DEFAULT_LAYERS", "REQUIRED_ASSETS",
    "index_on_grid", "render_index_png", "change_on_grid",
    "render_dnbr_png", "dnbr_severity_share", "layer_list", "INVALID_COLOR",
]
