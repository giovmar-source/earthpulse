from datetime import date
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pystac_client import Client

from src.ndvi import calculate_ndvi_for_item
from src.baseline import add_seasonal_baseline


# ============================================================
# CONFIGURAZIONE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STAC_URL = "https://earth-search.aws.element84.com/v1"
SENTINEL_COLLECTION = "sentinel-2-l2a"


# ============================================================
# APPLICAZIONE FASTAPI
# ============================================================

app = FastAPI(
    title="EarthPulse API",
    description=(
        "API per esplorare la vegetazione attraverso "
        "dati satellitari Sentinel-2 e l'indice NDVI."
    ),
    version="0.3.1",
)

# Solo per sviluppo. Prima della pubblicazione, limitare
# le origini autorizzate.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# FUNZIONI DI SUPPORTO
# ============================================================

def load_json_file(filename: str) -> dict:
    """Carica un file JSON dalla cartella data/processed."""
    filepath = PROCESSED_DIR / filename

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File non trovato: {filename}",
        )

    try:
        with filepath.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Il file {filename} contiene JSON non valido.",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Impossibile leggere il file {filename}.",
        ) from exc


def make_bbox(
    lat: float,
    lon: float,
    side_km: float,
) -> list[float]:
    """
    Crea un bounding box approssimativo in WGS84.

    Restituisce [min_lon, min_lat, max_lon, max_lat].
    side_km indica la larghezza approssimativa dell'area.
    """
    import math

    half_lat = side_km / 222.0
    cos_lat = max(abs(math.cos(math.radians(lat))), 1e-6)
    half_lon = side_km / (222.0 * cos_lat)

    return [
        lon - half_lon,
        lat - half_lat,
        lon + half_lon,
        lat + half_lat,
    ]


def search_sentinel_items(
    bbox: list[float],
    start_date: date,
    end_date: date,
    max_cloud: float,
    max_items: int,
):
    """Cerca scene Sentinel-2 L2A nel catalogo STAC."""
    catalog = Client.open(STAC_URL)

    search = catalog.search(
        collections=[SENTINEL_COLLECTION],
        bbox=bbox,
        datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
        query={"eo:cloud_cover": {"lte": max_cloud}},
        max_items=max_items,
    )

    return list(search.items())


def item_has_required_bands(item) -> bool:
    """Verifica che la scena contenga le bande necessarie."""
    return all(band in item.assets for band in ("red", "nir", "scl"))


def validate_date_range(start_date: date, end_date: date) -> None:
    """Interrompe la richiesta se l'intervallo temporale non è valido."""
    if start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date deve essere precedente o uguale a end_date.",
        )


# ============================================================
# ENDPOINT 1: CONTROLLO API
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "application": "EarthPulse API",
        "version": app.version,
    }


# ============================================================
# ENDPOINT 2: FOREST DEMO STATICO
# ============================================================

@app.get("/api/v1/forest-demo")
def get_forest_demo():
    """Restituisce il riepilogo statico della demo forestale."""
    return load_json_file("forest_demo.json")


# ============================================================
# ENDPOINT 3: SERIE TEMPORALE FOREST DEMO STATICA
# ============================================================

@app.get("/api/v1/forest-demo/timeseries")
def get_forest_demo_timeseries():
    """Restituisce la serie temporale già salvata su disco."""
    return load_json_file("forest_demo_timeseries.json")


# ============================================================
# ENDPOINT 4: RICERCA METADATI SENTINEL-2
# ============================================================

@app.get("/api/v1/sentinel-2/observations")
def get_sentinel_observations(
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=20),
    start_date: date = Query(...),
    end_date: date = Query(...),
    max_cloud: float = Query(80.0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=100),
):
    """Restituisce i metadati delle scene Sentinel-2 disponibili."""
    validate_date_range(start_date, end_date)
    bbox = make_bbox(lat, lon, side_km)

    try:
        items = search_sentinel_items(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
            max_items=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca STAC: {str(exc)}",
        ) from exc

    observations = []
    for item in items:
        observations.append(
            {
                "item_id": item.id,
                "collection": item.collection_id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "cloud_cover_percent": item.properties.get("eo:cloud_cover"),
                "bbox": item.bbox,
                "assets_available": list(item.assets.keys()),
                "has_red_band": "red" in item.assets,
                "has_nir_band": "nir" in item.assets,
                "has_scl": "scl" in item.assets,
            }
        )

    return {
        "bbox": bbox,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "count": len(observations),
        "observations": observations,
    }


# ============================================================
# ENDPOINT 5: NDVI DELL'OSSERVAZIONE PIÙ RECENTE
# ============================================================

@app.get("/api/v1/ndvi/latest")
def get_latest_ndvi(
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=20),
    start_date: date = Query(...),
    end_date: date = Query(...),
    max_cloud: float = Query(80.0, ge=0, le=100),
    limit: int = Query(30, ge=1, le=100),
):
    """Calcola l'NDVI della scena utilizzabile più recente."""
    validate_date_range(start_date, end_date)
    bbox = make_bbox(lat, lon, side_km)

    try:
        items = search_sentinel_items(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
            max_items=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca STAC: {str(exc)}",
        ) from exc

    candidates = [item for item in items if item.datetime and item_has_required_bands(item)]
    candidates.sort(key=lambda item: item.datetime, reverse=True)

    errors = []
    for item in candidates:
        try:
            result = calculate_ndvi_for_item(item, bbox)
            return {
                **result,
                "bbox": bbox,
                "methodology": {
                    "indicator": "NDVI",
                    "formula": "(B08 - B04) / (B08 + B04)",
                    "red_band": "B04",
                    "nir_band": "B08",
                    "cloud_mask": "Sentinel-2 SCL",
                },
                "warning": (
                    "L'NDVI non dimostra da solo la causa "
                    "di un eventuale cambiamento."
                ),
            }
        except Exception as exc:
            errors.append({"item_id": item.id, "reason": str(exc)})

    raise HTTPException(
        status_code=404,
        detail={
            "message": (
                "Nessuna scena Sentinel-2 utilizzabile "
                "trovata nel periodo richiesto."
            ),
            "scenes_with_required_bands": len(candidates),
            "errors": errors[:5],
        },
    )


# ============================================================
# ENDPOINT 6: SERIE TEMPORALE NDVI + BASELINE STAGIONALE
# ============================================================

@app.get("/api/v1/ndvi/timeseries")
def get_ndvi_timeseries(
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=20),
    start_date: date = Query(...),
    end_date: date = Query(...),
    max_cloud: float = Query(80.0, ge=0, le=100),
    max_scenes: int = Query(30, ge=1, le=60),
    min_valid_percentage: float = Query(70.0, ge=0, le=100),
    baseline_window_days: int = Query(30, ge=0, le=183),
    min_baseline_samples: int = Query(3, ge=1, le=30),
):
    """
    Calcola NDVI su più date e aggiunge una baseline stagionale.
    La selezione temporale cerca di distribuire le scene tra gli anni.
    """
    validate_date_range(start_date, end_date)
    bbox = make_bbox(lat, lon, side_km)

    try:
        # Recupera scene candidate; la selezione giornaliera e temporale
        # viene eseguita successivamente.
        items = search_sentinel_items(
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
            max_items=300,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca STAC: {str(exc)}",
        ) from exc

    candidates = [
        item for item in items
        if item.datetime is not None and item_has_required_bands(item)
    ]

    # Seleziona la scena con meno nuvole per ogni giorno.
    best_item_by_date = {}
    for item in candidates:
        item_date = item.datetime.date().isoformat()
        cloud_cover = item.properties.get("eo:cloud_cover")
        if cloud_cover is None:
            cloud_cover = 100.0

        current = best_item_by_date.get(item_date)
        if current is None:
            best_item_by_date[item_date] = item
            continue

        current_cloud = current.properties.get("eo:cloud_cover")
        if current_cloud is None:
            current_cloud = 100.0

        if cloud_cover < current_cloud:
            best_item_by_date[item_date] = item

    # Raggruppa le date disponibili per anno.
    dates_by_year = {}
    for item_date in best_item_by_date:
        year = item_date[:4]
        dates_by_year.setdefault(year, []).append(item_date)

    for year in dates_by_year:
        dates_by_year[year].sort()

    years = sorted(dates_by_year.keys())

    # Distribuisce il budget di scene tra gli anni. Se ci sono più anni
    # che scene consentite, seleziona prima gli anni più recenti.
    if len(years) > max_scenes:
        years_to_sample = years[-max_scenes:]
    else:
        years_to_sample = years

    selected_dates = []
    if years_to_sample:
        base_count = max_scenes // len(years_to_sample)
        remainder = max_scenes % len(years_to_sample)

        # Assegna le scene aggiuntive agli anni più recenti.
        quotas = {}
        for index, year in enumerate(years_to_sample):
            quotas[year] = base_count + (
                1 if index >= len(years_to_sample) - remainder and remainder > 0 else 0
            )

        for year in years_to_sample:
            year_dates = dates_by_year[year]
            quota = quotas[year]

            if quota <= 0:
                continue
            if len(year_dates) <= quota:
                selected_dates.extend(year_dates)
            elif quota == 1:
                selected_dates.append(year_dates[len(year_dates) // 2])
            else:
                # Campionamento uniforme lungo l'anno, includendo gli estremi.
                last_index = len(year_dates) - 1
                indices = [
                    round(i * last_index / (quota - 1))
                    for i in range(quota)
                ]
                selected_dates.extend(year_dates[index] for index in indices)

    selected_dates = sorted(set(selected_dates))[:max_scenes]

    observations = []
    failed_dates = []
    rejected_quality = 0

    for item_date in selected_dates:
        item = best_item_by_date[item_date]
        try:
            result = calculate_ndvi_for_item(item, bbox)

            if result["valid_percentage"] < min_valid_percentage:
                rejected_quality += 1
                continue

            observations.append(result)
        except Exception as exc:
            failed_dates.append(
                {
                    "date": item_date,
                    "item_id": item.id,
                    "reason": str(exc),
                }
            )

    observations.sort(key=lambda obs: obs["date"])

    # Calcola baseline e anomalie dopo aver raccolto tutte le osservazioni.
    observations = add_seasonal_baseline(
        observations,
        window_days=baseline_window_days,
        min_samples=min_baseline_samples,
    )

    observations_by_year = {
        year: sum(1 for obs in observations if str(obs["date"])[:4] == year)
        for year in years
    }

    return {
        "place": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox": bbox,
        },
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "parameters": {
            "max_cloud_percent": max_cloud,
            "min_valid_percentage": min_valid_percentage,
            "max_scenes": max_scenes,
            "baseline_window_days": baseline_window_days,
            "min_baseline_samples": min_baseline_samples,
        },
        "summary": {
            "stac_items_found": len(items),
            "items_with_required_bands": len(candidates),
            "distinct_dates_available": len(best_item_by_date),
            "scenes_selected_for_processing": len(selected_dates),
            "observations_returned": len(observations),
            "observations_rejected_quality": rejected_quality,
            "observations_failed": len(failed_dates),
            "years_available": years,
            "years_sampled": years_to_sample,
            "observations_by_year": observations_by_year,
            "observations_with_baseline": sum(
                obs.get("baseline_ndvi") is not None for obs in observations
            ),
        },
        "observations": observations,
        "errors": failed_dates,
        "methodology": {
            "indicator": "NDVI",
            "formula": "(B08 - B04) / (B08 + B04)",
            "red_band": "B04",
            "nir_band": "B08",
            "cloud_mask": "Sentinel-2 Scene Classification Layer (SCL)",
            "aggregation": "Media NDVI dei pixel validi nell'area",
            "daily_selection": "Scena con minore copertura nuvolosa dichiarata",
            "quality_filter": "valid_percentage >= min_valid_percentage",
            "temporal_selection": (
                "Campionamento distribuito tra gli anni disponibili; "
                "all'interno di ogni anno le date sono campionate uniformemente"
            ),
            "baseline": (
                "Media NDVI di osservazioni di altri anni "
                "nella finestra stagionale specificata"
            ),
            "anomaly": (
                "(NDVI osservato - baseline) / abs(baseline) * 100"
            ),
        },
        "warning": (
            "Una variazione dell'NDVI non dimostra da sola "
            "la causa del cambiamento osservato."
        ),
    }
