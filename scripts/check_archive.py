"""
Prova dell'archivio storico Landsat (dal 1984) dal tuo PC.

Uso (Anaconda Prompt, dalla cartella del progetto):
    python scripts/check_archive.py                          # Salerno, 6 km
    python scripts/check_archive.py --lat 25.08 --lon 55.14 --side 10   # Dubai Marina

Salva in data/archive_preview/ i colori reali e la vegetazione (NDVI)
del primo anno, di un anno intermedio e dell'ultimo.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import archive  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=40.6780)
    parser.add_argument("--lon", type=float, default=14.7680)
    parser.add_argument("--side", type=float, default=6.0)
    args = parser.parse_args()

    started = time.time()
    items = archive.search_archive(args.lat, args.lon)
    print(f"Scene trovate (nuvole < {archive.MAX_CLOUD:.0f}%): {len(items)} "
          f"in {time.time() - started:.1f} s")
    years = archive.group_by_year(items, args.lat)
    print(f"Anni con almeno una scena estiva: {len(years)}")
    for year, candidates in years.items():
        best = candidates[0]
        print(f"  {year}: {best.properties.get('platform')} {best.datetime.date()} "
              f"nuvole {best.properties.get('eo:cloud_cover'):.1f}% "
              f"({len(candidates)} candidate){'  [strisce L7]' if archive.is_slc_off(best) else ''}")
    if not years:
        print("Nessun anno: mandami questo output.")
        return 1

    all_years = list(years)
    chosen = sorted({all_years[0], all_years[len(all_years) // 2], all_years[-1]})
    out_dir = ROOT / "data" / "archive_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    latest_scene = archive.best_scene_for_year(
        years[all_years[-1]], archive.Grid(args.lat, args.lon, args.side))
    white = archive.white_point(latest_scene) if latest_scene else archive.RGB_WHITE
    print(f"Bianco dei colori reali per questo luogo: riflettanza {white:.2f}")

    for year in chosen:
        started = time.time()
        scene = archive.best_scene_for_year(
            years[year], archive.Grid(args.lat, args.lon, args.side))
        if scene is None:
            print(f"{year}: nessuna scena leggibile")
            continue
        (out_dir / f"{year}_colori.png").write_bytes(archive.render_rgb(scene, white))
        (out_dir / f"{year}_ndvi.png").write_bytes(archive.render_ndvi(scene))
        print(f"{year}: {scene.sensor} {scene.date}, validi {scene.valid_pct}% "
              f"{'+ vuoti riempiti con ' + ', '.join(scene.filled_from) + ' ' if scene.filled_from else ''}"
              f"({time.time() - started:.1f} s) -> {year}_colori.png, {year}_ndvi.png")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
