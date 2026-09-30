"""
Verifica l'accesso ai dati NASA Black Marble (luci notturne) dal tuo PC.

Uso (Anaconda Prompt, dalla cartella del progetto, con il token impostato):
    set EARTHDATA_TOKEN=il_tuo_token
    python scripts/check_nightlights.py
    python scripts/check_nightlights.py --lat 40.85 --lon 14.27 --side 60

Cosa fa:
1. cerca su NASA CMR i file annuali del tile che contiene il luogo;
2. apre il file del primo e dell'ultimo anno leggendo SOLO i pezzi utili;
3. stampa quanti MB ha scaricato e i numeri principali;
4. salva due PNG in data/nightlights_preview/ da guardare.
"""

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import nightlights as nl  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=40.85)   # Napoli
    parser.add_argument("--lon", type=float, default=14.27)
    parser.add_argument("--side", type=float, default=60)
    args = parser.parse_args()

    print("Credenziali presenti:", nl.has_credentials())
    if not nl.has_credentials():
        print("Imposta prima EARTHDATA_TOKEN (vedi istruzioni).")
        return 1

    h, v = nl.tile_for_point(args.lat, args.lon)
    print(f"Tile: {nl.tile_id(h, v)}")

    started = time.time()
    urls = nl.find_granules(h, v)
    print(f"Anni trovati su CMR ({time.time() - started:.1f} s):", list(urls))
    if not urls:
        print("Nessun file trovato: copia questo output e mandamelo.")
        return 1
    first_year, last_year = min(urls), max(urls)
    print("Esempio URL:", urls[last_year])

    # Struttura del file (una sola volta, per conferma dei nomi).
    session = nl.make_session()
    remote, h5file = nl.open_remote_h5(urls[last_year], session)
    try:
        print(f"Dimensione file: {remote.size / 1e6:.1f} MB")
        print("URL finale (dopo redirect):", remote.url.split("?")[0][:120])
        fields = h5file[nl.GRID_PATH]
        print("Variabili in", nl.GRID_PATH)
        for name in sorted(fields):
            dataset = fields[name]
            print(f"  {name}: shape={dataset.shape} dtype={dataset.dtype} "
                  f"chunks={dataset.chunks} compression={dataset.compression}")
        dataset = fields[nl.VARIABLE]
        print("Attributi", nl.VARIABLE, {
            key: dataset.attrs[key] for key in dataset.attrs
            if key in ("_FillValue", "scale_factor", "add_offset",
                       "offset", "units", "valid_range")})
        print("Attributi globali tile:",
              h5file.attrs.get("HorizontalTileNumber"),
              h5file.attrs.get("VerticalTileNumber"))
    finally:
        h5file.close()
    print(f"Scaricati per leggere la struttura: "
          f"{remote.bytes_downloaded / 1e6:.2f} MB in {remote.requests_made} richieste")

    out_dir = ROOT / "data" / "nightlights_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = {}
    for year in (first_year, last_year):
        stats = {}
        started = time.time()
        scene = nl.night_scene_for_area(args.lat, args.lon, args.side, year,
                                        session=session, stats=stats)
        elapsed = time.time() - started
        summaries[year] = nl.light_summary(scene)
        png_path = out_dir / f"luci_{year}.png"
        png_path.write_bytes(nl.render_radiance_png(scene))
        print(f"{year}: finestra {scene.radiance.shape}, "
              f"mare {100 * scene.sea.mean():.0f}%, "
              f"{stats.get('bytes', 0) / 1e6:.2f} MB, "
              f"{stats.get('requests', 0)} richieste, {elapsed:.1f} s")
        print(f"      {summaries[year]}")
        print(f"      salvato {png_path}")

    change = nl.percent_change(summaries[first_year]["total_radiance"],
                               summaries[last_year]["total_radiance"])
    print(f"Variazione luce totale {first_year} -> {last_year}: {change} %")
    print("OK: accesso ai dati luci notturne funzionante.")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
