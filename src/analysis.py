"""
Analisi NDVI di un luogo per l'app EarthPulse.

Logica:
1. osservazione recente: tra le scene degli ultimi giorni si sceglie
   la più recente con copertura valida sufficiente;
2. baseline stagionale: scene della STESSA finestra stagionale
   (± window_days attorno alla stessa data) negli anni precedenti;
   la baseline è la MEDIANA dei valori NDVI (come nel notebook 02);
3. confronto: differenza assoluta e percentuale, con classificazione
   prudente e indicazione del supporto storico.

Le funzioni di questo modulo non accedono alla rete: ricevono gli item
STAC e una funzione di calcolo. Così possono essere testate offline.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from statistics import median


# Un'osservazione più vecchia di così non viene presentata come "recente".
FRESH_MAX_DAYS = 20

# Sotto questa baseline la variazione percentuale è poco significativa
# (suolo nudo, aree urbane, acqua: piccoli valori al denominatore).
LOW_NDVI_THRESHOLD = 0.2


# ------------------------------------------------------------------
# Supporto agli item STAC
# ------------------------------------------------------------------

def item_date(item) -> date:
    return item.datetime.date()


def item_cloud_cover(item) -> float:
    value = (item.properties or {}).get("eo:cloud_cover")
    return 100.0 if value is None else float(value)


def best_item_per_day(items) -> dict:
    """Per ogni giorno conserva la scena con meno nuvole dichiarate."""
    best = {}
    for item in items:
        if item.datetime is None:
            continue
        day = item_date(item)
        current = best.get(day)
        if current is None or item_cloud_cover(item) < item_cloud_cover(current):
            best[day] = item
    return best


def pick_recent_candidates(items, max_candidates: int) -> list:
    """Le scene giornaliere più recenti, dalla più nuova alla più vecchia."""
    best = best_item_per_day(items)
    days = sorted(best.keys(), reverse=True)[:max_candidates]
    return [best[day] for day in days]


def pick_baseline_candidates(items, per_year: int) -> list:
    """
    Per ogni anno sceglie fino a per_year scene giornaliere,
    privilegiando quelle con meno nuvole dichiarate.
    """
    best = best_item_per_day(items)

    by_year = {}
    for day, item in best.items():
        by_year.setdefault(day.year, []).append(item)

    selected = []
    for year in sorted(by_year):
        year_items = sorted(
            by_year[year],
            key=lambda it: (item_cloud_cover(it), item_date(it)),
        )
        selected.extend(year_items[:per_year])

    return sorted(selected, key=item_date)


def seasonal_windows(target: date, years_back: int, window_days: int) -> list:
    """
    Finestre stagionali negli anni precedenti:
    [(anno, inizio, fine), ...] centrate sullo stesso giorno di target.
    """
    windows = []
    for k in range(1, years_back + 1):
        year = target.year - k
        try:
            center = target.replace(year=year)
        except ValueError:
            # 29 febbraio in un anno non bisestile
            center = target.replace(year=year, day=28)
        windows.append((
            year,
            center - timedelta(days=window_days),
            center + timedelta(days=window_days),
        ))
    return windows


# ------------------------------------------------------------------
# Calcolo parallelo
# ------------------------------------------------------------------

# Gruppo FISSO di thread, riutilizzato da tutte le richieste.
# Creare e distruggere thread a ogni richiesta può lasciare in uno stato
# incoerente le connessioni HTTP che GDAL conserva per ogni thread
# (osservato su Windows: "Resolving timed out").
READ_WORKERS = 6
_READ_POOL = ThreadPoolExecutor(
    max_workers=READ_WORKERS, thread_name_prefix="earthpulse-read"
)


def compute_many(items, compute_fn, max_workers: int = READ_WORKERS) -> list:
    """
    Esegue compute_fn(item) in parallelo (lettura di file remoti:
    il tempo è dominato dalla rete, i thread sono efficaci).

    Restituisce [(item, risultato o None, errore o None)] nello stesso
    ordine degli item. compute_fn non deve chiamare a sua volta
    compute_many (userebbe lo stesso gruppo di thread).
    """
    if not items:
        return []

    def run(item):
        try:
            return item, compute_fn(item), None
        except Exception as exc:  # noqa: BLE001 - riportato all'utente
            return item, None, str(exc)

    if max_workers <= 1 or len(items) == 1:
        return [run(item) for item in items]

    return list(_READ_POOL.map(run, items))


# ------------------------------------------------------------------
# Interpretazione
# ------------------------------------------------------------------

def historical_support(sample_count: int) -> str:
    """Stesse soglie del notebook 02 (STEP 54)."""
    if sample_count < 2:
        return "insufficiente"
    if sample_count < 4:
        return "limitato"
    if sample_count < 6:
        return "buono"
    return "forte"


def classify_anomaly(anomaly_percent, support: str, baseline_ndvi) -> str:
    """Classificazione prudente, soglie del notebook 02 (STEP 60)."""
    if anomaly_percent is None or baseline_ndvi is None:
        return "non disponibile"
    if support == "insufficiente":
        return "baseline poco supportata"
    if baseline_ndvi < LOW_NDVI_THRESHOLD:
        return "vegetazione scarsa: confronto percentuale poco significativo"
    if anomaly_percent <= -8:
        return "marcatamente sotto la baseline"
    if anomaly_percent <= -5:
        return "sotto la baseline"
    if anomaly_percent < 0:
        return "leggermente sotto la baseline"
    if anomaly_percent >= 5:
        return "sopra la baseline"
    return "vicino alla baseline"


def freshness(observation_date: date, reference_date: date,
              max_days: int = FRESH_MAX_DAYS) -> dict:
    days = (reference_date - observation_date).days
    return {
        "days_since_observation": days,
        "is_recent": 0 <= days <= max_days,
        "max_days_for_recent": max_days,
    }


def summarize_observation(result: dict) -> dict:
    """Campi dell'osservazione utili all'app."""
    acquired = str(result["date"])
    return {
        "date": acquired[:10],
        "acquisition_datetime": acquired,
        "item_id": result.get("item_id"),
        "ndvi_mean": result.get("ndvi_mean"),
        "ndvi_median": result.get("ndvi_median"),
        "valid_percentage": result.get("valid_percentage"),
        "cloud_cover_percent": result.get("cloud_cover_percent"),
    }


def build_analysis(
    recent_result,
    baseline_results: list,
    reference_date: date,
    window_days: int,
    min_baseline_samples: int,
) -> dict:
    """
    Combina osservazione recente e baseline in un unico risultato.

    recent_result: dict di calculate_ndvi_for_item oppure None
    baseline_results: lista di dict di calculate_ndvi_for_item
                      (già filtrati per qualità)
    """
    messages = []

    # ---------------- baseline ----------------
    baseline_obs = sorted(
        (summarize_observation(r) for r in baseline_results),
        key=lambda o: o["date"],
    )
    values = [o["ndvi_mean"] for o in baseline_obs if o["ndvi_mean"] is not None]
    samples = len(values)
    support = historical_support(samples)

    baseline_value = None
    if samples >= min_baseline_samples:
        baseline_value = float(median(values))
    else:
        messages.append(
            f"Baseline non calcolata: {samples} osservazioni storiche valide "
            f"(minimo richiesto: {min_baseline_samples})."
        )

    baseline = {
        "ndvi_median": baseline_value,
        "ndvi_min": min(values) if values else None,
        "ndvi_max": max(values) if values else None,
        "samples": samples,
        "support": support,
        "years": sorted({int(o["date"][:4]) for o in baseline_obs}),
        "window_days": window_days,
        "observations": [
            {
                "date": o["date"],
                "ndvi_mean": o["ndvi_mean"],
                "valid_percentage": o["valid_percentage"],
            }
            for o in baseline_obs
        ],
    }

    # ---------------- osservazione recente ----------------
    latest = None
    if recent_result is not None:
        latest = summarize_observation(recent_result)
        latest.update(
            freshness(date.fromisoformat(latest["date"]), reference_date)
        )
        if not latest["is_recent"]:
            messages.append(
                f"L'ultima osservazione valida risale a "
                f"{latest['days_since_observation']} giorni fa: "
                f"non va considerata un valore attuale."
            )
    else:
        messages.append(
            "Nessuna osservazione recente con copertura valida sufficiente "
            "(nuvole, ombre o dati mancanti)."
        )

    # ---------------- confronto ----------------
    delta = None
    anomaly_percent = None
    percent_meaningful = False

    if latest is not None and baseline_value is not None and latest["ndvi_mean"] is not None:
        delta = latest["ndvi_mean"] - baseline_value
        if baseline_value != 0:
            anomaly_percent = delta / abs(baseline_value) * 100
        percent_meaningful = (
            anomaly_percent is not None and baseline_value >= LOW_NDVI_THRESHOLD
        )
        if not percent_meaningful:
            messages.append(
                "NDVI della baseline basso (vegetazione scarsa o assente): "
                "la variazione percentuale è poco significativa, "
                "considera la differenza assoluta."
            )

    comparison = {
        "delta_ndvi": delta,
        "anomaly_percent": anomaly_percent,
        "percent_meaningful": percent_meaningful,
        "classification": classify_anomaly(anomaly_percent, support, baseline_value),
    }

    if latest is None:
        status = "no_recent_observation"
    elif baseline_value is None:
        status = "no_baseline"
    else:
        status = "ok"

    return {
        "status": status,
        "reference_date": reference_date.isoformat(),
        "processed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_observation": latest,
        "baseline": baseline,
        "comparison": comparison,
        "messages": messages,
    }
