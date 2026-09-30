"""
Verifica dello scostamento radiometrico (baseline 04.00) su scene reali.

Confronta i valori grezzi (DN) delle stesse superfici in due date:
se una scena contiene lo scostamento, i suoi valori sono circa 1000 più alti.

Uso (dalla cartella principale del progetto):
    python scripts/check_offset.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from api.main import get_item_by_id  # noqa: E402
from src.imagery import Grid, read_on_grid  # noqa: E402

# Pergusa (4 km) e bosco di Salerno (3 km): stesse aree in date diverse.
CASES = [
    ("Pergusa", 37.517, 14.305, 4.0,
     ["S2B_33SVB_20220716_0_L2A", "S2B_33SVB_20240715_0_L2A"]),
    ("Bosco Salerno", 40.81, 15.007, 3.0,
     ["S2B_33TVF_20250918_1_L2A", "S2C_33TVF_20260928_0_L2A"]),
]

for name, lat, lon, side, ids in CASES:
    grid = Grid(lat, lon, side)
    print(f"\n=== {name} ===")
    for item_id in ids:
        item = get_item_by_id(item_id)
        if item is None:
            print(item_id, "non trovato")
            continue
        props = item.properties
        print(f"{item_id}  baseline={props.get('s2:processing_baseline')}  "
              f"offset_applied={props.get('earthsearch:boa_offset_applied')}")
        for band in ("green", "red", "nir"):
            values = read_on_grid(item.assets[band].href, grid).astype(float)
            values = values[values > 0]
            p1, p50, p99 = np.percentile(values, [1, 50, 99])
            print(f"   {band:5s}  min={values.min():6.0f}  p1={p1:6.0f}  "
                  f"mediana={p50:6.0f}  p99={p99:6.0f}")
