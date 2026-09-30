from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import json
import time
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pystac_client import Client

from src.ndvi import calculate_ndvi_for_item
from src.baseline import add_seasonal_baseline
from src.analysis import (
    best_item_per_day,
    build_analysis,
    compute_many,
    pick_baseline_candidates,
    pick_recent_candidates,
    seasonal_windows,
)
from src.geocoding import GeocodingUnavailable, search_places
from src.stories import MAX_STORY_SIDE_KM, load_stories, story_summary
from src.indices import (
    DEFAULT_LAYERS,
    INDICES,
    REQUIRED_ASSETS,
    layer_list,
    render_dnbr_png,
    render_index_png,
)
from src.imagery import (
    DIFF_COLOR_STOPS,
    Grid,
    choose_clear_scene,
    color_stops_hex,
    render_png,
    scl_valid_percentage,
)

import requests


# ============================================================
# CONFIGURAZIONE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STAC_URL = "https://earth-search.aws.element84.com/v1"
SENTINEL_COLLECTION = "sentinel-2-l2a"

# Tempo massimo per le richieste al catalogo STAC (connessione, lettura).
STAC_TIMEOUT = (10, 30)


def open_catalog():
    """Apre il catalogo STAC con un tempo massimo di attesa."""
    try:
        return Client.open(STAC_URL, timeout=STAC_TIMEOUT)
    except TypeError:
        # Versioni di pystac-client senza il parametro timeout.
        return Client.open(STAC_URL)


# ============================================================
# APPLICAZIONE FASTAPI
# ============================================================

app = FastAPI(
    title="EarthPulse API",
    description=(
        "API per esplorare la vegetazione attraverso "
        "dati satellitari Sentinel-2 e l'indice NDVI."
    ),
    version="0.6.0",
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
    catalog = open_catalog()

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


# ============================================================
# ENDPOINT 7: ANALISI NDVI DI UN LUOGO (usato dall'app)
# ============================================================

@app.get("/api/v1/ndvi/analysis")
def get_ndvi_analysis(
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(1.0, gt=0, le=5),
    reference_date: date | None = Query(
        None,
        description="Data di riferimento (default: oggi, UTC).",
    ),
    recent_days: int = Query(45, ge=5, le=180),
    recent_candidates: int = Query(4, ge=1, le=10),
    baseline_years: int = Query(3, ge=1, le=6),
    baseline_window_days: int = Query(15, ge=5, le=45),
    baseline_per_year: int = Query(3, ge=1, le=6),
    min_baseline_samples: int = Query(3, ge=1, le=20),
    max_cloud: float = Query(60.0, ge=0, le=100),
    min_valid_percentage: float = Query(70.0, ge=0, le=100),
):
    """
    Osservazione NDVI valida più recente + baseline stagionale
    (stessa finestra dell'anno negli anni precedenti, mediana).
    """
    started = time.monotonic()
    today = datetime.now(timezone.utc).date()
    reference = reference_date or today

    if reference > today:
        raise HTTPException(
            status_code=400,
            detail="reference_date non può essere nel futuro.",
        )

    bbox = make_bbox(lat, lon, side_km)

    # ---------- 1. ricerca delle scene (catalogo STAC) ----------
    try:
        recent_items = search_sentinel_items(
            bbox=bbox,
            start_date=reference - timedelta(days=recent_days),
            end_date=reference,
            max_cloud=max_cloud,
            max_items=60,
        )

        baseline_items = []
        for _year, start, end in seasonal_windows(
            reference, baseline_years, baseline_window_days
        ):
            baseline_items.extend(
                search_sentinel_items(
                    bbox=bbox,
                    start_date=start,
                    end_date=end,
                    max_cloud=max_cloud,
                    max_items=60,
                )
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca STAC: {str(exc)}",
        ) from exc

    recent_items = [
        i for i in recent_items if i.datetime and item_has_required_bands(i)
    ]
    baseline_items = [
        i for i in baseline_items if i.datetime and item_has_required_bands(i)
    ]

    recent_selected = pick_recent_candidates(recent_items, recent_candidates)
    baseline_selected = pick_baseline_candidates(
        baseline_items, baseline_per_year
    )

    # ---------- 2. calcolo NDVI in parallelo ----------
    computed = compute_many(
        recent_selected + baseline_selected,
        lambda item: calculate_ndvi_for_item(item, bbox),
    )
    n_recent = len(recent_selected)
    recent_computed = computed[:n_recent]
    baseline_computed = computed[n_recent:]

    errors = []
    rejected = {"recent": 0, "baseline": 0}

    def accepted(rows, role):
        good = []
        for item, result, error in rows:
            if result is None:
                # "Nessun pixel valido" = area coperta: è un problema
                # di qualità, non un errore tecnico.
                if error and "Nessun pixel valido" in error:
                    rejected[role] += 1
                else:
                    errors.append({
                        "item_id": item.id,
                        "date": item.datetime.date().isoformat(),
                        "role": role,
                        "reason": error,
                    })
            elif result["valid_percentage"] < min_valid_percentage:
                rejected[role] += 1
            else:
                good.append(result)
        return good

    recent_ok = accepted(recent_computed, "recent")
    baseline_ok = accepted(baseline_computed, "baseline")

    # recent_selected è ordinato dal più recente: il primo valido vince.
    recent_result = recent_ok[0] if recent_ok else None

    analysis = build_analysis(
        recent_result=recent_result,
        baseline_results=baseline_ok,
        reference_date=reference,
        window_days=baseline_window_days,
        min_baseline_samples=min_baseline_samples,
    )

    return {
        **analysis,
        "place": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox": bbox,
        },
        "quality": {
            "min_valid_percentage": min_valid_percentage,
            "max_cloud_percent": max_cloud,
            "recent_period": {
                "start_date": (reference - timedelta(days=recent_days)).isoformat(),
                "end_date": reference.isoformat(),
            },
            "recent_scenes_found": len(recent_items),
            "recent_scenes_evaluated": len(recent_selected),
            "recent_scenes_rejected_quality": rejected["recent"],
            "baseline_scenes_found": len(baseline_items),
            "baseline_scenes_evaluated": len(baseline_selected),
            "baseline_scenes_rejected_quality": rejected["baseline"],
            "errors": errors,
        },
        "methodology": {
            "indicator": "NDVI",
            "formula": "(B08 - B04) / (B08 + B04)",
            "source": "Sentinel-2 L2A (Element84 Earth Search, STAC)",
            "spatial_resolution_m": 10,
            "cloud_mask": "Sentinel-2 Scene Classification Layer (SCL)",
            "aggregation": "Media NDVI dei pixel validi nell'area",
            "latest_selection": (
                "Scena più recente con pixel validi >= min_valid_percentage"
            ),
            "baseline": (
                f"Mediana NDVI di osservazioni valide dei {baseline_years} "
                f"anni precedenti, entro ±{baseline_window_days} giorni "
                f"dalla stessa data"
            ),
            "anomaly": "(NDVI osservato - baseline) / |baseline| * 100",
        },
        "processing_seconds": round(time.monotonic() - started, 1),
        "warning": (
            "L'NDVI è un indicatore della risposta spettrale della "
            "vegetazione, non una misura diretta della sua salute. "
            "Una variazione non dimostra da sola la causa del cambiamento."
        ),
    }


# ============================================================
# ENDPOINT 8: RICERCA LOCALITÀ (Nominatim / OpenStreetMap)
# ============================================================

@app.get("/api/v1/geocode")
def geocode(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(5, ge=1, le=10),
    language: str = Query("it", max_length=10),
):
    """Cerca una località per nome. Una richiesta per ricerca confermata."""
    try:
        results = search_places(q, limit=limit, language=language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeocodingUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "query": q,
        "count": len(results),
        "results": results,
        "attribution": (
            "Dati © OpenStreetMap contributors (ODbL) · Ricerca: Nominatim / Photon"
        ),
    }


# ============================================================
# ENDPOINT 9-10: IMMAGINI "DALL'ALTO" (colori reali e NDVI)
# ============================================================

# Bande necessarie per tutti i livelli (colori reali, NDVI, NDWI, NDMI, NDBI, NBR).
IMAGERY_ASSETS = REQUIRED_ASSETS

# Indici mostrati come immagini per ogni scena (oltre a colori reali e NDVI).
EXTRA_INDEX_LAYERS = ("ndwi", "ndmi", "ndbi")

# Cache in memoria: evita di rileggere il catalogo e di ricalcolare
# le stesse immagini. Si svuota quando il server si riavvia.
_ITEM_CACHE: dict = {}
_PNG_CACHE: dict = {}
MAX_ITEM_CACHE = 200
MAX_PNG_CACHE = 64


def remember_item(item) -> None:
    if len(_ITEM_CACHE) >= MAX_ITEM_CACHE:
        _ITEM_CACHE.clear()
    _ITEM_CACHE[item.id] = item


def get_item_by_id(item_id: str):
    """Recupera un item Sentinel-2 dalla cache o dal catalogo STAC."""
    if item_id in _ITEM_CACHE:
        return _ITEM_CACHE[item_id]

    catalog = open_catalog()
    items = list(
        catalog.search(
            collections=[SENTINEL_COLLECTION],
            ids=[item_id],
            max_items=1,
        ).items()
    )
    if not items:
        return None
    remember_item(items[0])
    return items[0]


def find_clear_scene(bbox, start_date, end_date, target_date,
                     max_candidates: int = 6, min_valid: float = 95.0):
    """
    Cerca una scena quasi senza nuvole sull'area, preferendo le date più
    vicine a target_date. Restituisce (scelta, scene_trovate, valutate).
    """
    items = search_sentinel_items(
        bbox=bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud=40.0,
        max_items=80,
    )
    items = [
        i for i in items
        if i.datetime and all(a in i.assets for a in IMAGERY_ASSETS)
    ]

    best = best_item_per_day(items)
    days = sorted(
        best.keys(),
        key=lambda d: (abs((d - target_date).days), -d.toordinal()),
    )[:max_candidates]
    candidates = [best[d] for d in days]

    rows = compute_many(
        candidates, lambda item: scl_valid_percentage(item, bbox)
    )
    return choose_clear_scene(rows, min_valid=min_valid), len(items), len(candidates)


def describe_scene(chosen, lat: float, lon: float, side_km: float):
    """Scena scelta -> dizionario per l'app, con gli indirizzi delle immagini."""
    if chosen is None:
        return None
    item, valid_percentage = chosen
    remember_item(item)
    params = urlencode({
        "item_id": item.id,
        "lat": lat,
        "lon": lon,
        "side_km": side_km,
    })
    return {
        "item_id": item.id,
        "date": item.datetime.date().isoformat(),
        "valid_percentage": (
            round(valid_percentage, 1) if valid_percentage is not None else None
        ),
        "cloud_cover_percent": item.properties.get("eo:cloud_cover"),
        "images": {
            "rgb": f"/api/v1/imagery/image?{params}&kind=rgb",
            "ndvi": f"/api/v1/imagery/image?{params}&kind=ndvi",
            **{
                key: f"/api/v1/imagery/image?{params}&kind=index&index={key}"
                for key in EXTRA_INDEX_LAYERS
            },
        },
    }


def add_diff_url(after_info, before_info, lat: float, lon: float, side_km: float,
                 include_dnbr: bool = False):
    """
    Aggiunge la mappa della variazione (e, per gli incendi, il dNBR)
    se ci sono entrambe le date.
    """
    if not (after_info and before_info):
        return
    diff_params = urlencode({
        "item_id": after_info["item_id"],
        "compare_id": before_info["item_id"],
        "lat": lat,
        "lon": lon,
        "side_km": side_km,
    })
    after_info["images"]["diff"] = f"/api/v1/imagery/image?{diff_params}&kind=diff"
    if include_dnbr:
        after_info["images"]["dnbr"] = f"/api/v1/imagery/image?{diff_params}&kind=dnbr"

    # Colori reali della data precedente armonizzati alla più recente
    # (solo visualizzazione: NDVI e variazione usano i dati originali).
    rgb_params = urlencode({
        "item_id": before_info["item_id"],
        "compare_id": after_info["item_id"],
        "lat": lat,
        "lon": lon,
        "side_km": side_km,
    })
    before_info["images"]["rgb"] = f"/api/v1/imagery/image?{rgb_params}&kind=rgb"
    before_info["rgb_harmonized_to"] = after_info["item_id"]


def imagery_legend() -> dict:
    return {
        "ndvi_color_stops": color_stops_hex(),
        "diff_color_stops": color_stops_hex(DIFF_COLOR_STOPS),
        "invalid_color": "#b4b4b4",
        "invalid_meaning": "Nuvole, ombre, neve o dati mancanti (SCL)",
    }


def imagery_attribution(*infos) -> str:
    years = sorted({info["date"][:4] for info in infos if info})
    return (
        "Contiene dati Copernicus Sentinel modificati"
        + (f" ({', '.join(years)})" if years else "")
    )


@app.get("/api/v1/imagery/scenes")
def get_imagery_scenes(
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(3.0, gt=0, le=10),
    reference_date: date | None = Query(None),
    years_back: int = Query(1, ge=1, le=5),
    recent_days: int = Query(60, ge=10, le=365),
    window_days: int = Query(30, ge=5, le=90),
):
    """
    Sceglie due scene nitide dell'area per il confronto prima/dopo:
    - "after": la più vicina alla data di riferimento (default oggi);
    - "before": la più vicina alla stessa data, years_back anni prima.
    Restituisce gli indirizzi delle immagini PNG (colori reali e NDVI).
    """
    started = time.monotonic()
    today = datetime.now(timezone.utc).date()
    reference = reference_date or today
    if reference > today:
        raise HTTPException(
            status_code=400,
            detail="reference_date non può essere nel futuro.",
        )

    bbox = make_bbox(lat, lon, side_km)
    _year, before_start, before_end = seasonal_windows(
        reference, years_back, window_days
    )[-1]
    before_target = before_start + timedelta(days=window_days)

    try:
        after, after_found, after_checked = find_clear_scene(
            bbox, reference - timedelta(days=recent_days), reference, reference
        )
        before, before_found, before_checked = find_clear_scene(
            bbox, before_start, before_end, before_target
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca delle immagini: {str(exc)}",
        ) from exc

    after_info = describe_scene(after, lat, lon, side_km)
    before_info = describe_scene(before, lat, lon, side_km)
    add_diff_url(after_info, before_info, lat, lon, side_km)

    messages = []
    if after_info is None:
        messages.append(
            "Nessuna immagine abbastanza nitida (nuvole) negli ultimi "
            f"{recent_days} giorni."
        )
    if before_info is None:
        messages.append(
            f"Nessuna immagine abbastanza nitida {years_back} "
            f"{'anno' if years_back == 1 else 'anni'} prima."
        )

    return {
        "place": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox": bbox,
        },
        "reference_date": reference.isoformat(),
        "years_back": years_back,
        "after": after_info,
        "before": before_info,
        "messages": messages,
        "search": {
            "after_scenes_found": after_found,
            "after_scenes_checked": after_checked,
            "before_scenes_found": before_found,
            "before_scenes_checked": before_checked,
            "min_valid_percentage": 95.0,
        },
        "legend": imagery_legend(),
        "layers": layer_list(DEFAULT_LAYERS),
        "attribution": imagery_attribution(after_info, before_info),
        "processing_seconds": round(time.monotonic() - started, 1),
    }


@app.get("/api/v1/imagery/image")
def get_imagery_image(
    item_id: str = Query(..., min_length=5, max_length=100,
                         pattern=r"^[A-Za-z0-9_\-]+$"),
    lat: float = Query(..., ge=-80, le=80),
    lon: float = Query(..., ge=-180, le=180),
    side_km: float = Query(3.0, gt=0, le=MAX_STORY_SIDE_KM),
    kind: str = Query("rgb", pattern=r"^(rgb|ndvi|diff|index|dnbr)$"),
    index: str | None = Query(None, pattern=r"^(ndvi|ndwi|ndmi|ndbi|nbr)$"),
    compare_id: str | None = Query(None, min_length=5, max_length=100,
                                   pattern=r"^[A-Za-z0-9_\-]+$"),
):
    """
    Immagine PNG dell'area sulla griglia comune:
    - "rgb": colori reali (con compare_id: armonizzati a quella data);
    - "ndvi": NDVI; "index": indice scelto con index=ndwi|ndmi|ndbi|nbr;
    - "diff": variazione NDVI; "dnbr": gravità dell'incendio
      (item_id = dopo, compare_id = prima).
    """
    if kind in ("diff", "dnbr") and compare_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"kind={kind} richiede compare_id (scena precedente).",
        )
    if kind == "index" and (index is None or index not in INDICES):
        raise HTTPException(status_code=400, detail="kind=index richiede index.")

    uses_compare = kind in ("diff", "rgb", "dnbr")
    key = (item_id, compare_id if uses_compare else None,
           round(lat, 5), round(lon, 5), round(side_km, 3), kind,
           index if kind == "index" else None)
    png = _PNG_CACHE.get(key)

    if png is None:
        def load(identifier):
            try:
                found = get_item_by_id(identifier)
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=f"Errore durante la ricerca STAC: {str(exc)}",
                ) from exc
            if found is None:
                raise HTTPException(
                    status_code=404, detail=f"Scena non trovata: {identifier}"
                )
            if not all(a in found.assets for a in IMAGERY_ASSETS):
                raise HTTPException(
                    status_code=404,
                    detail="La scena non contiene le bande necessarie.",
                )
            return found

        item = load(item_id)
        compare_item = load(compare_id) if uses_compare and compare_id else None
        grid = Grid(lat, lon, side_km)

        try:
            if kind == "index":
                png = render_index_png(item, grid, index)
            elif kind == "dnbr":
                png = render_dnbr_png(item, compare_item, grid)
            else:
                png = render_png(item, grid, kind, compare_item=compare_item)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Impossibile generare l'immagine: {str(exc)}",
            ) from exc

        if len(_PNG_CACHE) >= MAX_PNG_CACHE:
            _PNG_CACHE.clear()
        _PNG_CACHE[key] = png

    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800"},
    )


# ============================================================
# ENDPOINT 11-12: STORIE (eventi reali curati)
# ============================================================

# Le scene scelte per ogni storia non cambiano: si calcolano una volta.
_STORY_SCENES_CACHE: dict = {}


def get_stories() -> list:
    try:
        return load_stories()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Archivio delle storie non valido: {exc}",
        ) from exc


def pinned_or_search(story: dict, window_name: str, bbox):
    """Usa la scena fissata nel JSON, se presente; altrimenti la cerca."""
    pinned_id = story.get(f"{window_name}_item_id")
    if pinned_id:
        item = get_item_by_id(pinned_id)
        if item is None:
            raise HTTPException(
                status_code=500,
                detail=f"Scena fissata non trovata: {pinned_id}",
            )
        return (item, None), 1, 1

    window = story[window_name]
    return find_clear_scene(
        bbox,
        window["start"],
        window["end"],
        window["target"],
        max_candidates=8,
        min_valid=story["min_valid_percentage"],
    )


@app.get("/api/v1/stories")
def list_stories():
    """Elenco delle storie disponibili (senza immagini)."""
    stories = get_stories()
    return {
        "count": len(stories),
        "stories": [story_summary(story) for story in stories],
    }


@app.get("/api/v1/stories/{story_id}")
def get_story(story_id: str):
    """Storia completa con le scene prima/dopo e gli indirizzi delle immagini."""
    stories = {story["id"]: story for story in get_stories()}
    story = stories.get(story_id)
    if story is None:
        raise HTTPException(status_code=404, detail="Storia non trovata.")

    if story_id in _STORY_SCENES_CACHE:
        return _STORY_SCENES_CACHE[story_id]

    started = time.monotonic()
    lat, lon, side_km = story["latitude"], story["longitude"], float(story["side_km"])
    bbox = make_bbox(lat, lon, side_km)

    try:
        before, _bf, _bc = pinned_or_search(story, "before", bbox)
        after, _af, _ac = pinned_or_search(story, "after", bbox)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Errore durante la ricerca delle immagini: {str(exc)}",
        ) from exc

    before_info = describe_scene(before, lat, lon, side_km)
    after_info = describe_scene(after, lat, lon, side_km)
    extra_layers = [key for key in story.get("extra_layers", []) if key in ("dnbr",)]
    add_diff_url(after_info, before_info, lat, lon, side_km,
                 include_dnbr="dnbr" in extra_layers)

    messages = []
    if before_info is None:
        messages.append("Nessuna immagine abbastanza nitida prima dell'evento.")
    if after_info is None:
        messages.append("Nessuna immagine abbastanza nitida dopo l'evento.")

    result = {
        **story_summary(story),
        "what_to_look": story["what_to_look"],
        "caveat": story["caveat"],
        "diff_note": story.get("diff_note"),
        "facts": story["facts"],
        "sources": story["sources"],
        "place_area": {
            "latitude": lat,
            "longitude": lon,
            "side_km": side_km,
            "bbox": bbox,
        },
        "before": before_info,
        "after": after_info,
        "messages": messages,
        "legend": imagery_legend(),
        "layers": layer_list(DEFAULT_LAYERS + extra_layers),
        "attribution": imagery_attribution(before_info, after_info),
        "processing_seconds": round(time.monotonic() - started, 1),
    }

    # Si memorizza solo un risultato completo.
    if before_info and after_info:
        _STORY_SCENES_CACHE[story_id] = result
    return result
