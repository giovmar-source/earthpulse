"""
Anteprima delle storie: per ogni storia cerca le scene prima/dopo,
genera le immagini e crea un'unica tavola di confronto:

    colori reali PRIMA | colori reali DOPO | variazione NDVI

Uso (dalla cartella principale del progetto):
    python scripts/preview_stories.py              # tutte le storie
    python scripts/preview_stories.py noto-2024    # una sola storia

Le tavole sono salvate in data/story_previews/ (cartella esclusa da Git).
Alla fine lo script stampa gli item_id scelti: se la tavola è buona,
si possono copiare in data/stories.json come before_item_id / after_item_id.
"""

import io
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import api.main as api  # noqa: E402
from src.stories import load_stories  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "data" / "story_previews"
TILE = 500   # lato di ogni immagine nella tavola (pixel)
LABEL_H = 34


def fetch_png(url: str) -> Image.Image:
    """Genera l'immagine chiamando direttamente l'endpoint (senza server)."""
    from urllib.parse import parse_qs, urlparse

    query = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    response = api.get_imagery_image(
        item_id=query["item_id"],
        lat=float(query["lat"]),
        lon=float(query["lon"]),
        side_km=float(query["side_km"]),
        kind=query["kind"],
        compare_id=query.get("compare_id"),
    )
    return Image.open(io.BytesIO(response.body)).convert("RGB")


def labeled(image: Image.Image, text: str) -> Image.Image:
    tile = Image.new("RGB", (TILE, TILE + LABEL_H), (16, 60, 50))
    tile.paste(image.resize((TILE, TILE), Image.BILINEAR), (0, LABEL_H))
    ImageDraw.Draw(tile).text((10, 10), text, fill=(255, 255, 255))
    return tile


def preview(story_id: str) -> None:
    started = time.monotonic()
    print(f"\n=== {story_id} ===")
    result = api.get_story(story_id)

    before, after = result["before"], result["after"]
    for name, info in (("PRIMA", before), ("DOPO", after)):
        if info:
            print(f"{name:6s} {info['date']}  {info['item_id']}  "
                  f"pixel validi: {info['valid_percentage']}%")
        else:
            print(f"{name:6s} nessuna scena nitida trovata")

    if not (before and after):
        print("Tavola non generata: manca una delle due date.")
        return

    tiles = [
        labeled(fetch_png(before["images"]["rgb"]), f"PRIMA  {before['date']}"),
        labeled(fetch_png(after["images"]["rgb"]), f"DOPO  {after['date']}"),
        labeled(fetch_png(after["images"]["diff"]), "VARIAZIONE NDVI (rosso = calo)"),
    ]
    board = Image.new("RGB", (TILE * 3 + 20, TILE + LABEL_H), (255, 255, 255))
    for i, tile in enumerate(tiles):
        board.paste(tile, (i * (TILE + 10), 0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{story_id}.png"
    board.save(path)
    print(f"Tavola salvata: {path}  ({time.monotonic() - started:.0f} s)")
    print(f'  "before_item_id": "{before["item_id"]}",')
    print(f'  "after_item_id": "{after["item_id"]}",')


def main() -> None:
    ids = sys.argv[1:] or [story["id"] for story in load_stories()]
    for story_id in ids:
        try:
            preview(story_id)
        except Exception as exc:  # noqa: BLE001
            print(f"ERRORE per {story_id}: {exc}")


if __name__ == "__main__":
    main()
