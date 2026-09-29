
from datetime import date, datetime


def parse_observation_date(value: str) -> date:
    """
    Converte una data ISO in un oggetto date.

    Supporta entrambi i formati:
    YYYY-MM-DD
    YYYY-MM-DDTHH:MM:SS.sssZ
    """
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Data dell'osservazione non valida: {value!r}"
        )

    # Gestisce date con timestamp e suffisso Z.
    normalized = value.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        # Compatibilità con date che contengono solo l'anno,
        # il mese e il giorno.
        return date.fromisoformat(value)


def day_of_year(value: str) -> int:
    """Restituisce il giorno dell'anno da una data ISO."""
    return parse_observation_date(value).timetuple().tm_yday


def circular_day_distance(day_a: int, day_b: int) -> int:
    """Calcola la distanza tra giorni dell'anno, considerando dicembre/gennaio."""
    difference = abs(day_a - day_b)
    return min(difference, 365 - difference)


def add_seasonal_baseline(
    observations: list[dict],
    window_days: int = 30,
    min_samples: int = 3,
) -> list[dict]:
    """
    Aggiunge una baseline stagionale alle osservazioni.

    La baseline utilizza osservazioni di altri anni raccolte
    entro window_days dal giorno dell'anno dell'osservazione.

    L'anomalia è espressa in percentuale rispetto alla baseline.
    """

    if window_days < 0 or window_days > 183:
        raise ValueError(
            "window_days deve essere compreso tra 0 e 183."
        )

    if min_samples < 1:
        raise ValueError(
            "min_samples deve essere almeno 1."
        )

    prepared = []

    for observation in observations:
        item = dict(observation)

        value = item.get("date")

        if value is None or item.get("ndvi_mean") is None:
            item["_parsed_date"] = None
            item["_day_of_year"] = None
        else:
            parsed_date = parse_observation_date(value)
            item["_parsed_date"] = parsed_date
            item["_day_of_year"] = parsed_date.timetuple().tm_yday

        prepared.append(item)

    result = []

    for current in prepared:
        current_date = current["_parsed_date"]
        current_day = current["_day_of_year"]

        if current_date is None:
            current["baseline_ndvi"] = None
            current["anomaly_percent"] = None
            current["historical_observations"] = 0
            current["historical_support"] = "insufficiente"
            result.append(current)
            continue

        historical_values = []

        for reference in prepared:
            reference_date = reference["_parsed_date"]

            if reference_date is None:
                continue

            # Non confrontare l'osservazione con dati dello stesso anno.
            if reference_date.year == current_date.year:
                continue

            ndvi_value = reference.get("ndvi_mean")

            if ndvi_value is None:
                continue

            distance = circular_day_distance(
                current_day,
                reference["_day_of_year"],
            )

            if distance <= window_days:
                historical_values.append(float(ndvi_value))

        sample_count = len(historical_values)

        if sample_count < min_samples:
            current["baseline_ndvi"] = None
            current["anomaly_percent"] = None
            current["historical_observations"] = sample_count
            current["historical_support"] = "insufficiente"

        else:
            baseline = sum(historical_values) / sample_count
            current_ndvi = float(current["ndvi_mean"])

            current["baseline_ndvi"] = baseline

            if baseline != 0:
                current["anomaly_percent"] = (
                    (current_ndvi - baseline) / abs(baseline)
                ) * 100
            else:
                current["anomaly_percent"] = None

            current["historical_observations"] = sample_count

            if sample_count >= 5:
                current["historical_support"] = "forte"
            else:
                current["historical_support"] = "moderato"

        result.append(current)

    # Rimuove i campi temporanei prima di restituire i risultati.
    for observation in result:
        observation.pop("_parsed_date", None)
        observation.pop("_day_of_year", None)

    return result