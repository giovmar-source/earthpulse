"""
Storie curate di EarthPulse (data/stories.json).

Ogni storia descrive un evento reale con:
- luogo, area (side_km) e data dell'evento;
- una finestra temporale "prima" e una "dopo" in cui cercare
  scene Sentinel-2 nitide (target = data preferita);
- testi brevi (sintesi, cosa osservare, limiti) e fonti verificabili;
- opzionalmente before_item_id / after_item_id per fissare le scene
  scelte dopo la verifica visiva (risposte più rapide e stabili).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


STORIES_PATH = Path(__file__).resolve().parents[1] / "data" / "stories.json"

MAX_STORY_SIDE_KM = 12.0

# Livelli aggiuntivi consentiti per le storie (oltre a quelli standard).
ALLOWED_EXTRA_LAYERS = {"dnbr"}

# Sorgente delle immagini: Sentinel-2 (predefinita) o archivio Landsat,
# per le storie che guardano indietro di decenni (dal 1984).
ALLOWED_SOURCES = {"sentinel-2", "landsat"}

REQUIRED_FIELDS = [
    "id", "category", "title", "place", "country",
    "latitude", "longitude", "side_km", "event_date",
    "summary", "what_to_look", "caveat", "facts", "sources",
    "before", "after",
]


class StoryError(ValueError):
    """Storia non valida."""


def parse_window(window: dict, story_id: str, name: str) -> dict:
    try:
        start = date.fromisoformat(window["start"])
        end = date.fromisoformat(window["end"])
        target = date.fromisoformat(window["target"])
    except (KeyError, TypeError, ValueError) as exc:
        raise StoryError(f"{story_id}: finestra '{name}' non valida") from exc

    if not (start <= target <= end):
        raise StoryError(
            f"{story_id}: in '{name}' deve valere start <= target <= end"
        )
    return {"start": start, "end": end, "target": target}


def validate_story(story: dict) -> dict:
    """Controlla una storia e restituisce una copia con le date convertite."""
    story_id = story.get("id", "?")

    missing = [f for f in REQUIRED_FIELDS if f not in story]
    if missing:
        raise StoryError(f"{story_id}: campi mancanti {missing}")

    if not (-80 <= float(story["latitude"]) <= 80):
        raise StoryError(f"{story_id}: latitudine fuori intervallo")
    if not (-180 <= float(story["longitude"]) <= 180):
        raise StoryError(f"{story_id}: longitudine fuori intervallo")
    if not (0 < float(story["side_km"]) <= MAX_STORY_SIDE_KM):
        raise StoryError(f"{story_id}: side_km deve essere tra 0 e {MAX_STORY_SIDE_KM}")
    if not story["sources"]:
        raise StoryError(f"{story_id}: servono fonti verificabili")

    unknown = set(story.get("extra_layers", [])) - ALLOWED_EXTRA_LAYERS
    if unknown:
        raise StoryError(f"{story_id}: livelli sconosciuti {sorted(unknown)}")

    if story.get("source", "sentinel-2") not in ALLOWED_SOURCES:
        raise StoryError(f"{story_id}: sorgente sconosciuta {story.get('source')!r}")

    event = date.fromisoformat(story["event_date"])
    before = parse_window(story["before"], story_id, "before")
    after = parse_window(story["after"], story_id, "after")

    # "Prima" deve chiudersi prima dell'evento; "dopo" deve includerlo o seguirlo.
    if not before["end"] < event:
        raise StoryError(f"{story_id}: la finestra 'before' deve terminare prima dell'evento")
    if not event <= after["end"]:
        raise StoryError(f"{story_id}: la finestra 'after' deve terminare dopo l'evento")
    if not before["end"] < after["start"]:
        raise StoryError(f"{story_id}: le finestre 'before' e 'after' si sovrappongono")

    parsed = dict(story)
    parsed["event_date"] = event
    parsed["before"] = before
    parsed["after"] = after
    parsed["min_valid_percentage"] = float(story.get("min_valid_percentage", 85))
    return parsed


def load_stories(path: Path = STORIES_PATH) -> list:
    """Carica e valida tutte le storie. Solleva StoryError se qualcosa non va."""
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    stories = [validate_story(story) for story in data.get("stories", [])]

    ids = [story["id"] for story in stories]
    if len(ids) != len(set(ids)):
        raise StoryError("Identificativi delle storie duplicati")
    return stories


def story_summary(story: dict) -> dict:
    """Campi per l'elenco delle storie nell'app (senza scene)."""
    return {
        "id": story["id"],
        "category": story["category"],
        "title": story["title"],
        "place": story["place"],
        "country": story["country"],
        "latitude": story["latitude"],
        "longitude": story["longitude"],
        "side_km": story["side_km"],
        "event_date": story["event_date"].isoformat(),
        # Testo della data quando l'evento dura anni (es. "2001–2010")
        "event_label": story.get("event_label"),
        "source": story.get("source", "sentinel-2"),
        "summary": story["summary"],
    }
