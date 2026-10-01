"""
Andamento di un indice Sentinel-2 in un luogo: valore recente e confronto
con la stessa stagione degli anni precedenti (come l'analisi NDVI, ma per
tutti gli indici: clorofilla, umidità, acqua, costruito, neve, alghe, torbidità).

Per ogni scena si calcola la MEDIANA dell'indice sui pixel validi dell'area
(1 × 1 km). Le regole di validità seguono quelle dell'indice:
- indici "da terraferma" (mask_water): l'acqua libera è esclusa;
- indici dell'acqua (only_water): si usano SOLO i pixel d'acqua;
- neve (keep_snow): la classe "neve" della SCL non viene scartata.

Gli indici non NDVI sono spesso vicini a zero o negativi: la variazione
percentuale non ha senso, quindi il confronto usa la DIFFERENZA ASSOLUTA.
"""

from __future__ import annotations

from datetime import date
from statistics import median

import numpy as np

from src.analysis import FRESH_MAX_DAYS, historical_support
from src.indices import INDICES, _index_arrays, water_area

# Indici analizzabili (l'NDVI ha il suo endpoint dedicato)
TREND_INDICES = ("ndre", "ndmi", "ndwi", "ndbi", "ndsi", "ndci", "ndti")

# Soglie sulla differenza assoluta dell'indice (mediana recente − baseline)
SLIGHT_DELTA = 0.03
CLEAR_DELTA = 0.08

# Una scena è usata se almeno questa parte della zona utile è senza nuvole
MIN_CLEAR_PERCENTAGE = 70.0
# Pixel minimi per una mediana affidabile (100 pixel = 1 ettaro a 10 m)
MIN_PIXELS = 20
# Soglia NDSI oltre la quale un pixel è considerato neve o ghiaccio
SNOW_NDSI = 0.4


def scene_stat(item, grid, key: str) -> dict:
    """
    Mediana dell'indice sull'area per una scena, con le percentuali utili.

    zone_percentage: quota dell'area in cui l'indice ha senso (terraferma
    o acqua); clear_percentage: quota della zona utile senza nuvole.
    """
    values, valid, water = _index_arrays(item, grid, key)
    spec = INDICES[key]
    if spec.get("only_water"):
        zone = water
    elif spec.get("mask_water"):
        zone = ~water
    else:
        zone = np.ones(values.shape, dtype=bool)
    usable = valid & zone
    zone_count = int(zone.sum())
    count = int(usable.sum())

    result = {
        "item_id": item.id,
        "date": item.datetime.date().isoformat(),
        "zone_percentage": round(100.0 * zone_count / zone.size, 1),
        "clear_percentage": round(100.0 * count / zone_count, 1) if zone_count else 0.0,
        "pixels": count,
        "median": round(float(np.median(values[usable])), 4) if count >= MIN_PIXELS else None,
    }
    if key == "ndsi" and count >= MIN_PIXELS:
        result["snow_percentage"] = round(100.0 * float((values[usable] > SNOW_NDSI).mean()), 1)
    if key == "ndwi":
        result["water_ha"] = water_area(item, grid)["water_ha"]
    return result


def is_usable(stat: dict | None) -> bool:
    return bool(stat) and stat["median"] is not None and stat["clear_percentage"] >= MIN_CLEAR_PERCENTAGE


def classify_delta(delta: float | None, support: str) -> dict:
    """Direzione e intensità del cambiamento rispetto agli anni precedenti."""
    if delta is None:
        return {"trend": "unknown", "strength": None}
    if support == "insufficiente":
        return {"trend": "unknown", "strength": None}
    size = abs(delta)
    if size < SLIGHT_DELTA:
        return {"trend": "same", "strength": None}
    return {
        "trend": "up" if delta > 0 else "down",
        "strength": "clear" if size >= CLEAR_DELTA else "slight",
    }


def _median_of(stats: list, field: str):
    values = [s[field] for s in stats if s.get(field) is not None]
    return round(float(median(values)), 4) if values else None


def build_trend(key: str, recent_stats: list, baseline_stats: list,
                reference: date, window_days: int, min_samples: int = 3) -> dict:
    """
    recent_stats: statistiche delle scene recenti, dalla più nuova (None = errore)
    baseline_stats: statistiche delle scene della stessa stagione negli anni passati
    """
    messages = []
    spec = INDICES[key]

    # Indici dell'acqua senza acqua nell'area: niente da analizzare
    seen = [s for s in recent_stats + baseline_stats if s]
    if spec.get("only_water") and seen and max(s["zone_percentage"] for s in seen) < 1.0:
        return {
            "index": key, "status": "no_water", "reference_date": reference.isoformat(),
            "latest": None, "baseline": None, "comparison": classify_delta(None, "insufficiente"),
            "messages": ["Nell'area di 1 km intorno al punto non c'è acqua libera: scegli un "
                         "punto su un lago, un fiume o il mare."],
        }

    latest = next((s for s in recent_stats if is_usable(s)), None)
    good_baseline = sorted((s for s in baseline_stats if is_usable(s)), key=lambda s: s["date"])
    samples = len(good_baseline)
    support = historical_support(samples)

    baseline = None
    if samples >= min_samples:
        baseline = {
            "median": _median_of(good_baseline, "median"),
            "min": min(s["median"] for s in good_baseline),
            "max": max(s["median"] for s in good_baseline),
            "samples": samples,
            "support": support,
            "years": sorted({int(s["date"][:4]) for s in good_baseline}),
            "window_days": window_days,
            "observations": [{"date": s["date"], "median": s["median"]} for s in good_baseline],
        }
        if key == "ndwi":
            baseline["water_ha"] = _median_of(good_baseline, "water_ha")
        if key == "ndsi":
            baseline["snow_percentage"] = _median_of(good_baseline, "snow_percentage")
    else:
        messages.append(
            f"Confronto non disponibile: {samples} osservazioni valide negli anni precedenti "
            f"(ne servono almeno {min_samples})."
        )

    if latest is not None:
        days = (reference - date.fromisoformat(latest["date"])).days
        latest = {**latest, "days_since_observation": days, "is_recent": 0 <= days <= FRESH_MAX_DAYS}
        if not latest["is_recent"]:
            messages.append(f"L'ultima osservazione valida risale a {days} giorni fa: "
                            "non va considerata un valore attuale.")
    else:
        messages.append("Nessuna osservazione recente abbastanza libera da nuvole.")

    delta = None
    if latest is not None and baseline is not None:
        delta = round(latest["median"] - baseline["median"], 4)

    if latest is None:
        status = "no_recent_observation"
    elif baseline is None:
        status = "no_baseline"
    else:
        status = "ok"

    return {
        "index": key,
        "status": status,
        "reference_date": reference.isoformat(),
        "latest": latest,
        "baseline": baseline,
        "comparison": {"delta": delta, **classify_delta(delta, support)},
        "messages": messages,
    }
