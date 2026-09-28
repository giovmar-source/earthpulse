
from datetime import date, datetime
from math import cos, radians
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pystac_client import Client
from src.ndvi import calculate_ndvi_for_item

# --------------------------------------------------
# CONFIGURAZIONE
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STAC_URL = "https://earth-search.aws.element84.com/v1"
SENTINEL_COLLECTION = "sentinel-2-l2a"

app = FastAPI(
    title="EarthPulse API",
    description=(
        "API per la ricerca di osservazioni Sentinel-2 "
        "e l'analisi di indicatori di vegetazione."
    ),
    version="0.2.0",
)

# Configurazione utile durante lo sviluppo.
# Prima della pubblicazione limiteremo le origini autorizzate.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# --------------------------------------------------
# FUNZIONI DI SUPPORTO
# --------------------------------------------------

def load_json_file(filename: str):
    """Carica un file JSON dalla cartella dei risultati."""
    path = PROCESSED_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"File non disponibile: {filename}",
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Impossibile leggere {filename}: {exc}",
        ) from exc


def make_bbox(lat: float, lon: float, side_km: float):
    """
    Crea un bounding box approssimativamente quadrato
    intorno al centro indicato.

    Il bounding box è espresso in WGS84:
    [longitudine_min, latitudine_min,
     longitudine_max, latitudine_max].
    """
    half_side_km = side_km / 2

    lat_delta = half_side_km / 111.32

    # Correzione approssimata della longitudine in funzione
    # della latitudine. Evitiamo aree troppo vicine ai poli.
    cos_lat = cos(radians(lat))

    if abs(cos_lat) < 0.01:
        raise HTTPException(
            status_code=422,
            detail="Latitudine non supportata per questo tipo di area.",
        )

    lon_delta = half_side_km / (111.32 * abs(cos_lat))

    bbox = [
        lon - lon_delta,
        lat - lat_delta,
        lon + lon_delta,
        lat + lat_delta,
    ]

    if bbox[0] < -180 or bbox[2] > 180:
        raise HTTPException(
            status_code=422,
            detail="L'area supera i limiti delle longitudini.",
        )

    if bbox[1] < -90 or bbox[3] > 90:
        raise HTTPException(
            status_code=422,
            detail="L'area supera i limiti delle latitudini.",
        )

    return bbox


# --------------------------------------------------
# ENDPOINT DI BASE
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "EarthPulse API",
        "version": app.version,
    }


@app.get("/api/v1/forest-demo")
def forest_demo():
    return load_json_file("forest_demo.json")


@app.get("/api/v1/forest-demo/timeseries")
def forest_demo_timeseries():
    return load_json_file("forest_demo_timeseries.json")


# --------------------------------------------------
# RICERCA DINAMICA SENTINEL-2
# --------------------------------------------------

@app.get("/api/v1/sentinel-2/observations")
def search_sentinel_observations(
    lat: float = Query(..., ge=-85, le=85),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=20),
    start_date: date = Query(...),
    end_date: date = Query(...),
    max_cloud: float = Query(30.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Cerca le osservazioni Sentinel-2 L2A per un'area,
    un periodo e una copertura nuvolosa massima.
    """

    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date deve precedere end_date.",
        )

    bbox = make_bbox(lat, lon, side_km)

    try:
        catalog = Client.open(STAC_URL)

        search = catalog.search(
            collections=[SENTINEL_COLLECTION],
            bbox=bbox,
            datetime=(
                f"{start_date.isoformat()}/"
                f"{end_date.isoformat()}"
            ),
            query={
                "eo:cloud_cover": {
                    "lte": max_cloud
                }
            },
            max_items=limit,
        )

        items = list(search.items())

    except Exception as exc:
        # Il catalogo è un servizio esterno:
        # non trasformiamo un problema di rete in una lista vuota.
        raise HTTPException(
            status_code=502,
            detail=(
                "Non è stato possibile interrogare il catalogo "
                f"Sentinel-2: {type(exc).__name__}: {exc}"
            ),
        ) from exc

    observations = []

    for item in items:
        properties = item.properties or {}
        cloud_cover = properties.get("eo:cloud_cover")

        acquired = properties.get("datetime")

        if not acquired and item.datetime:
            acquired = item.datetime.isoformat()

        observations.append({
            "item_id": item.id,
            "collection": item.collection_id,
            "datetime": acquired,
            "cloud_cover_percent": cloud_cover,
            "bbox": item.bbox,
            "assets_available": sorted(item.assets.keys()),
            "has_red_band": "red" in item.assets,
            "has_nir_band": "nir" in item.assets,
            "has_scl": "scl" in item.assets,
        })

    # Ordine cronologico, utile per la serie temporale.
    observations.sort(
        key=lambda observation: observation["datetime"] or ""
    )

    return {
        "status": "ok",
        "source": STAC_URL,
        "collection": SENTINEL_COLLECTION,
        "search": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox_wgs84": bbox,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "max_cloud_cover_percent": max_cloud,
            "limit": limit,
        },
        "count": len(observations),
        "observations": observations,
        "note": (
            "Questi sono metadati delle osservazioni trovate. "
            "La presenza di un item non garantisce che ogni pixel "
            "dell'area sia valido o privo di nuvole."
        ),
    }


@app.get("/api/v1/ndvi/latest")
def latest_ndvi(
    lat: float = Query(..., ge=-85, le=85),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=20),
    start_date: date = Query(...),
    end_date: date = Query(...),
    max_cloud: float = Query(30.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=100),
):
    """Calcola l'NDVI dell'osservazione idonea più recente."""

    if start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="start_date deve precedere end_date.",
        )

    bbox = make_bbox(lat, lon, side_km)

    try:
        catalog = Client.open(STAC_URL)

        search = catalog.search(
            collections=[SENTINEL_COLLECTION],
            bbox=bbox,
            datetime=(
                f"{start_date.isoformat()}/"
                f"{end_date.isoformat()}"
            ),
            query={
                "eo:cloud_cover": {"lte": max_cloud}
            },
            max_items=limit,
        )

        items = list(search.items())

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca STAC: {exc}",
        ) from exc

    # Consideriamo soltanto gli item che contengono
    # tutte le bande necessarie al calcolo.
    candidates = [
        item for item in items
        if all(
            asset in item.assets
            for asset in ["red", "nir", "scl"]
        )
    ]

    # Dal più recente al meno recente
    candidates.sort(
        key=lambda item: (
            item.properties.get("datetime") or ""
        ),
        reverse=True,
    )

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=(
                "Nessuna osservazione con le bande necessarie "
                "trovata per i parametri selezionati."
            ),
        )

    selected_item = candidates[0]

    try:
        result = calculate_ndvi_for_item(
            selected_item,
            bbox,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "L'osservazione è stata trovata, ma "
                f"l'elaborazione NDVI non è riuscita: {exc}"
            ),
        ) from exc

    return {
        "status": "ok",
        "source": STAC_URL,
        "collection": SENTINEL_COLLECTION,
        "search": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox_wgs84": bbox,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "max_cloud_cover_percent": max_cloud,
        },
        "result": result,
        "methodology": {
            "indicator": "NDVI",
            "red_band": "B04",
            "nir_band": "B08",
            "cloud_mask": "SCL",
            "spatial_resolution_m": 10,
        },
        "note": (
            "Il risultato descrive l'osservazione selezionata. "
            "La copertura nuvolosa dell'intero item non "
            "garantisce che l'area sia priva di nuvole."
        ),
    }