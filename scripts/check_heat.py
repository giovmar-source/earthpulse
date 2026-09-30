"""
Prova delle isole di calore (Landsat 8-9) dal tuo PC.

Uso (Anaconda Prompt, dalla cartella del progetto):
    python scripts/check_heat.py                      # Salerno, 8 km
    python scripts/check_heat.py --lat 41.9 --lon 12.49 --side 12

Salva in data/heat_preview/:
- temperatura_<data>.png  temperatura della superficie della giornata più recente
- anomalia_tipica.png     anomalia "tipica" dell'estate (mediana di più giornate)
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import heat  # noqa: E402
from src.imagery import Grid  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=40.6780)   # Salerno
    parser.add_argument("--lon", type=float, default=14.7680)
    parser.add_argument("--side", type=float, default=heat.DEFAULT_SIDE_KM)
    args = parser.parse_args()

    started = time.time()
    token = heat.sas_token()
    print(f"Token Planetary Computer ottenuto ({len(token)} caratteri)")

    items = heat.search_summer_items(args.lat, args.lon)
    print(f"Scene estive trovate: {len(items)} ({time.time() - started:.1f} s)")
    for item in items[:10]:
        print(f"  {item.id}  {item.datetime.date()}  "
              f"nuvole {item.properties.get('eo:cloud_cover'):.1f}%")
    if not items:
        print("Nessuna scena: mandami questo output.")
        return 1

    grid = Grid(args.lat, args.lon, args.side, resolution=heat.HEAT_RESOLUTION_M)
    print(f"Griglia: {grid.width} x {grid.height} pixel da "
          f"{grid.transform.a:.0f} m ({grid.crs})")

    started = time.time()
    scenes = heat.choose_scenes(items, grid)
    print(f"Giornate utili: {len(scenes)} ({time.time() - started:.1f} s)")
    if not scenes:
        print("Nessuna giornata abbastanza limpida sull'area: mandami questo output.")
        return 1

    out_dir = ROOT / "data" / "heat_preview"
    out_dir.mkdir(parents=True, exist_ok=True)

    for scene in scenes:
        values, median = heat.anomaly(scene)
        print(f"  {scene.date} {scene.platform}: validi {scene.valid_land_pct}% "
              f"mediana terraferma {median:.1f} °C  "
              f"{heat.heat_summary(values, scene.water)}")

    latest = scenes[0]
    path = out_dir / f"temperatura_{latest.date}.png"
    path.write_bytes(heat.render_temperature_png(latest))
    print(f"Salvato {path}")

    typical = heat.typical_anomaly(scenes)
    path = out_dir / "anomalia_tipica.png"
    path.write_bytes(heat.render_anomaly_png(typical, latest.water))
    print(f"Salvato {path}")
    print("Anomalia tipica:", heat.heat_summary(typical, latest.water))
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
