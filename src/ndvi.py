
import os

# Ottimizzazioni GDAL per leggere i file COG remoti di Sentinel-2:
# evita di elencare le cartelle remote e unisce le richieste HTTP vicine.
# (GDAL_HTTP_MULTIPLEX non viene attivato: con molte letture in parallelo
# può bloccare le connessioni su alcune installazioni.)
# setdefault: non sovrascrive eventuali impostazioni dell'utente.
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

from rasterio.mask import mask
from rasterio.warp import reproject, Resampling, transform_geom
from shapely.geometry import box, mapping


# Manteniamo gli stessi criteri di qualità
# utilizzati nell'analisi Forest Demo.
INVALID_SCL_CLASSES = [0, 1, 3, 7, 8, 9, 10, 11]

# Dal 25 gennaio 2022 (processing baseline 04.00) i prodotti Sentinel-2 L2A
# hanno uno scostamento radiometrico: riflettanza = (DN - 1000) / 10000.
# Senza correzione, l'NDVI dopo quella data risulta più basso sulla
# vegetazione e più alto sull'acqua, e i confronti con anni precedenti
# sono falsati.
BOA_ADD_OFFSET_DN = 1000.0


def reflectance_offset(item) -> float:
    """
    Scostamento (in DN) da sottrarre alle bande di questo item.

    - Se il catalogo dichiara di averlo già applicato
      ("earthsearch:boa_offset_applied" = True): 0.
    - Se la processing baseline è >= 04.00 e non risulta applicato: 1000.
    - Altrimenti (dati precedenti al 2022 o informazione assente): 0.
    """
    properties = getattr(item, "properties", None) or {}

    if properties.get("earthsearch:boa_offset_applied") is True:
        return 0.0

    baseline = properties.get("s2:processing_baseline")
    try:
        if baseline is not None and float(baseline) >= 4.0:
            return BOA_ADD_OFFSET_DN
    except (TypeError, ValueError):
        pass
    return 0.0


# Con lo scostamento presente, anche i pixel più scuri (acqua, ombre)
# valgono circa 1000 DN o più. Se il 1° percentile di una banda è sotto
# questa soglia, la scena NON contiene lo scostamento.
DARK_PIXEL_THRESHOLD_DN = 900.0


def effective_offset(item, *bands) -> float:
    """
    Scostamento da sottrarre, verificato sui dati.

    Il catalogo non è sempre affidabile: su Earth Search alcune scene del
    2022 risultano "offset non applicato" ma i loro valori non contengono
    lo scostamento (verificato: pixel scuri fino a 1-200 DN, mediane uguali
    a quelle del 2024). Sottrarre 1000 in quel caso azzera l'acqua e altera
    tutti gli indici. Quindi:
    - se il catalogo non indica uno scostamento possibile: 0;
    - altrimenti lo si sottrae solo se i pixel più scuri di tutte le bande
      stanno sopra la soglia (lo scostamento è davvero nei dati).
    """
    candidate = reflectance_offset(item)
    if not candidate:
        return 0.0

    lows = []
    for band in bands:
        values = np.asarray(band, dtype=np.float32)
        values = values[np.isfinite(values) & (values > 0)]
        if values.size >= 50:
            lows.append(float(np.percentile(values, 1)))

    if not lows:
        return candidate      # dati insufficienti: si segue il catalogo
    return candidate if min(lows) >= DARK_PIXEL_THRESHOLD_DN else 0.0


def calculate_ndvi_for_item(item, bbox_wgs84):
    """
    Calcola statistiche NDVI per un item Sentinel-2
    e un bounding box espresso in coordinate WGS84.

    Restituisce statistiche aggregate, non una mappa.
    """

    required_assets = ["red", "nir", "scl"]

    missing_assets = [
        name for name in required_assets
        if name not in item.assets
    ]

    if missing_assets:
        raise ValueError(
            f"Asset Sentinel-2 mancanti: {missing_assets}"
        )

    # Poligono dell'area richiesta in WGS84
    aoi_wgs84 = mapping(box(*bbox_wgs84))

    with (
        rasterio.open(item.assets["red"].href) as red_src,
        rasterio.open(item.assets["nir"].href) as nir_src,
        rasterio.open(item.assets["scl"].href) as scl_src,
    ):
        # Trasformiamo il poligono nel CRS delle bande
        aoi = transform_geom(
            "EPSG:4326",
            red_src.crs,
            aoi_wgs84,
        )

        # B04: rosso
        red_masked, transform = mask(
            red_src,
            [aoi],
            crop=True,
            filled=False,
        )

        # B08: vicino infrarosso
        nir_masked, nir_transform = mask(
            nir_src,
            [aoi],
            crop=True,
            filled=False,
        )

        if red_masked.shape != nir_masked.shape:
            raise ValueError(
                "Le bande B04 e B08 hanno dimensioni incompatibili."
            )

        if transform != nir_transform:
            raise ValueError(
                "Le bande B04 e B08 non sono allineate."
            )

        red_band = red_masked[0].astype(np.float32)
        nir_band = nir_masked[0].astype(np.float32)

        red = red_band.filled(np.nan)
        nir = nir_band.filled(np.nan)

        # Armonizzazione radiometrica (baseline >= 04.00), verificata sui dati.
        offset = effective_offset(item, red, nir)
        if offset:
            red = np.clip(red - offset, 0, None)
            nir = np.clip(nir - offset, 0, None)

        # Riproiettiamo la SCL a 20 m sulla griglia B04 a 10 m.
        # Il metodo nearest conserva le classi discrete.
        scl_aligned = np.zeros(
            red.shape,
            dtype=np.uint8,
        )

        reproject(
            source=rasterio.band(scl_src, 1),
            destination=scl_aligned,
            src_transform=scl_src.transform,
            src_crs=scl_src.crs,
            src_nodata=scl_src.nodata,
            dst_transform=transform,
            dst_crs=red_src.crs,
            dst_nodata=0,
            resampling=Resampling.nearest,
        )

        # Pixel appartenenti all'area e leggibili in entrambe
        # le bande spettrali.
        area_pixels = (
            ~np.ma.getmaskarray(red_band)
            & ~np.ma.getmaskarray(nir_band)
        )

        # Pixel esclusi dal controllo SCL
        invalid_scl = np.isin(
            scl_aligned,
            INVALID_SCL_CLASSES,
        )

        denominator = nir + red

        valid = (
            area_pixels
            & ~invalid_scl
            & np.isfinite(red)
            & np.isfinite(nir)
            & (denominator != 0)
        )

        if not valid.any():
            raise ValueError(
                "Nessun pixel valido nell'area e nell'osservazione."
            )

        ndvi = np.full(red.shape, np.nan, dtype=np.float32)

        ndvi[valid] = (
            (nir[valid] - red[valid])
            / denominator[valid]
        )

        # Percentuale riferita ai pixel leggibili nell'area,
        # prima dell'esclusione tramite SCL.
        area_pixel_count = int(area_pixels.sum())
        valid_pixel_count = int(valid.sum())

        valid_percentage = (
            100.0 * valid_pixel_count / area_pixel_count
            if area_pixel_count > 0
            else 0.0
        )

        properties = item.properties or {}

        acquired = properties.get("datetime")

        if not acquired and item.datetime:
            acquired = item.datetime.isoformat()

        return {
            "item_id": item.id,
            "date": acquired,
            "cloud_cover_percent": properties.get(
                "eo:cloud_cover"
            ),
            "ndvi_mean": float(np.nanmean(ndvi)),
            "ndvi_median": float(np.nanmedian(ndvi)),
            "valid_pixels": valid_pixel_count,
            "area_pixels": area_pixel_count,
            "valid_percentage": round(
                valid_percentage, 2
            ),
            "spatial_resolution_m": 10,
        }