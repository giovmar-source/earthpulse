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
    "B05": "rededge1",
    "B08": "nir",
    "B11": "swir16",
    "B12": "swir22",
}
BANDS_20M = {"B05", "B11", "B12"}


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

NDRE_COLOR_STOPS = [          # clorofilla (red-edge): dal giallo-bruno al verde scuro
    (-0.10, (200, 170, 120)),
    (0.10, (235, 225, 150)),
    (0.25, (180, 210, 110)),
    (0.40, (90, 170, 70)),
    (0.55, (30, 115, 50)),
    (0.70, (10, 70, 35)),
]

NDSI_COLOR_STOPS = [          # neve: da terra (bruno) a neve (bianco-azzurro)
    (-0.40, (150, 120, 90)),
    (0.00, (205, 190, 170)),
    (0.30, (200, 215, 225)),
    (0.40, (170, 215, 245)),
    (0.70, (235, 245, 255)),
    (1.00, (255, 255, 255)),
]

NDCI_COLOR_STOPS = [          # clorofilla nell'acqua: da limpida (blu) ad alghe (verde)
    (-0.20, (25, 60, 140)),
    (-0.05, (60, 130, 190)),
    (0.05, (90, 180, 170)),
    (0.15, (120, 200, 90)),
    (0.30, (60, 160, 40)),
    (0.45, (20, 100, 20)),
]

NDTI_COLOR_STOPS = [          # torbidità: da limpida (blu scuro) a torbida (marrone)
    (-0.30, (20, 50, 120)),
    (-0.10, (50, 110, 170)),
    (0.00, (120, 170, 170)),
    (0.10, (190, 170, 110)),
    (0.20, (160, 110, 60)),
    (0.35, (110, 70, 35)),
]

# Colore della terraferma negli indici che valgono solo sull'acqua.
LAND_COLOR = (222, 218, 208)

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
    "ndre": {
        "bands": ("B08", "B05"),
        "formula": "NDRE = (B08 − B05) / (B08 + B05)",
        "stops": NDRE_COLOR_STOPS,
        "mask_water": True,
    },
    # keep_snow: la neve è ciò che vogliamo vedere, non va scartata con la SCL.
    "ndsi": {
        "bands": ("B03", "B11"),
        "formula": "NDSI = (B03 − B11) / (B03 + B11)",
        "stops": NDSI_COLOR_STOPS,
        "keep_snow": True,
    },
    # only_water: indici di qualità dell'acqua, senza significato sulla terra.
    "ndci": {
        "bands": ("B05", "B04"),
        "formula": "NDCI = (B05 − B04) / (B05 + B04)",
        "stops": NDCI_COLOR_STOPS,
        "only_water": True,
    },
    "ndti": {
        "bands": ("B04", "B03"),
        "formula": "NDTI = (B04 − B03) / (B04 + B03)",
        "stops": NDTI_COLOR_STOPS,
        "only_water": True,
    },
}

SCL_SNOW = 11

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
    "ndre": _layer(
        "ndre", "Clorofilla", "compare",
        "NDRE: usa la banda red-edge B05, molto sensibile alla clorofilla. Nelle "
        "colture fitte, dove l'NDVI è già al massimo, distingue meglio le piante ben "
        "nutrite da quelle in difficoltà (per esempio per carenza di azoto). "
        "B05 ha pixel di 20 m. In azzurro-grigio l'acqua.",
        NDRE_COLOR_STOPS, ("Poca clorofilla", "", "Molta clorofilla"),
        INDICES["ndre"]["formula"],
    ),
    "ndsi": _layer(
        "ndsi", "Neve", "compare",
        "NDSI: la neve riflette molto la luce verde e pochissimo l'infrarosso a onde "
        "corte (B11). Valori sopra 0,4 indicano di solito neve o ghiaccio. Anche "
        "l'acqua dà valori alti: va letto insieme ai colori reali.",
        NDSI_COLOR_STOPS, ("Senza neve", "", "Neve, ghiaccio"),
        INDICES["ndsi"]["formula"],
    ),
    "ndci": _layer(
        "ndci", "Alghe", "compare",
        "NDCI, solo sull'acqua: stima la clorofilla nell'acqua (fitoplancton, "
        "fioriture di alghe) con le bande B05 e B04. Valori alti possono indicare "
        "acque ricche di nutrienti. È un indicatore qualitativo: le concentrazioni "
        "richiedono analisi in loco. La terraferma è in grigio chiaro.",
        NDCI_COLOR_STOPS, ("Acqua limpida", "", "Molte alghe"),
        INDICES["ndci"]["formula"],
    ),
    "ndti": _layer(
        "ndti", "Torbidità", "compare",
        "NDTI, solo sull'acqua: l'acqua carica di sedimenti (dopo le piogge, alle "
        "foci dei fiumi) riflette più rosso che verde. Indicatore qualitativo. "
        "La terraferma è in grigio chiaro.",
        NDTI_COLOR_STOPS, ("Limpida", "", "Torbida"),
        INDICES["ndti"]["formula"],
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

# Il livello "Acqua" ha anche un numero: la superficie d'acqua in ettari.
LAYERS["ndwi"]["stat"] = "water"

DEFAULT_LAYERS = ["rgb", "ndvi", "ndwi", "ndmi", "ndbi", "ndre", "ndsi", "ndci", "ndti", "diff"]


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

    good_scl = valid_mask_from_scl(scl)
    if INDICES[key].get("keep_snow"):
        good_scl |= scl == SCL_SNOW
    valid = good_scl & has_data & (denominator > 0)
    values = np.full(a.shape, np.nan, dtype=np.float32)
    values[valid] = (a[valid] - b[valid]) / denominator[valid]

    water = np.zeros(values.shape, dtype=bool)
    if INDICES[key].get("mask_water") or INDICES[key].get("only_water"):
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
    if INDICES[key].get("only_water"):
        return values, valid & water
    return values, valid & ~water


def render_index_png(item, grid: Grid, key: str) -> bytes:
    values, valid, water = _index_arrays(item, grid, key)
    if INDICES[key].get("only_water"):
        image = colorize(values, valid & water, INDICES[key]["stops"])
        image[~water] = LAND_COLOR
        return to_png(image)
    image = colorize(values, valid & ~water, INDICES[key]["stops"])
    image[water] = WATER_COLOR
    return to_png(image)


def water_area(item, grid: Grid) -> dict:
    """Superficie d'acqua libera nell'area (SCL acqua oppure NDWI > 0), in ettari."""
    scl = read_on_grid(item.assets["scl"].href, grid)
    water = water_mask(item, grid, scl)
    observed = (scl != 0) & ~np.isin(scl, (3, 8, 9, 10))   # senza nuvole né ombre
    pixel_ha = abs(grid.transform.a * grid.transform.e) / 10_000
    total_ha = scl.size * pixel_ha
    return {
        "water_ha": round(float((water & observed).sum()) * pixel_ha, 1),
        "observed_percentage": round(100.0 * float(observed.mean()), 1),
        "area_ha": round(total_ha, 1),
    }


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
    "water_area",
]
