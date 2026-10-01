from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

import numpy as np

from src import index_trend


def stat(day, median, clear=95.0, zone=100.0, **extra):
    return {"item_id": f"S2_{day}", "date": day, "zone_percentage": zone,
            "clear_percentage": clear, "pixels": 5000, "median": median, **extra}


BASELINE = [stat("2023-09-20", 0.20), stat("2024-09-22", 0.22), stat("2025-09-25", 0.21)]
REF = date(2026, 10, 1)


def test_classify_delta_thresholds():
    assert index_trend.classify_delta(0.01, "limitato") == {"trend": "same", "strength": None}
    assert index_trend.classify_delta(0.05, "limitato") == {"trend": "up", "strength": "slight"}
    assert index_trend.classify_delta(-0.12, "buono") == {"trend": "down", "strength": "clear"}
    assert index_trend.classify_delta(-0.12, "insufficiente")["trend"] == "unknown"
    assert index_trend.classify_delta(None, "forte")["trend"] == "unknown"


def test_build_trend_compares_with_baseline_median():
    recent = [stat("2026-09-28", 0.05, clear=40.0), stat("2026-09-24", 0.30)]
    result = index_trend.build_trend("ndmi", recent, BASELINE, REF, window_days=15)
    assert result["status"] == "ok"
    assert result["latest"]["date"] == "2026-09-24"      # la prima scena è troppo nuvolosa
    assert result["baseline"]["median"] == 0.21
    assert result["baseline"]["years"] == [2023, 2024, 2025]
    assert result["comparison"]["delta"] == 0.09
    assert result["comparison"]["trend"] == "up" and result["comparison"]["strength"] == "clear"


def test_build_trend_without_enough_history():
    result = index_trend.build_trend("ndbi", [stat("2026-09-24", 0.1)], BASELINE[:2], REF, 15)
    assert result["status"] == "no_baseline"
    assert result["baseline"] is None
    assert result["comparison"]["trend"] == "unknown"
    assert any("Confronto non disponibile" in m for m in result["messages"])


def test_build_trend_reports_old_observation():
    result = index_trend.build_trend("ndre", [stat("2026-08-20", 0.3)], BASELINE, REF, 15)
    assert result["latest"]["is_recent"] is False
    assert any("42 giorni" in m for m in result["messages"])


def test_water_index_without_water():
    dry = [stat("2026-09-24", None, zone=0.0, clear=0.0)]
    result = index_trend.build_trend("ndci", dry, [stat("2025-09-25", None, zone=0.0, clear=0.0)], REF, 15)
    assert result["status"] == "no_water"


def test_ndwi_and_ndsi_extra_fields_in_baseline():
    base = [stat("2023-09-20", -0.3, water_ha=10.0), stat("2024-09-22", -0.3, water_ha=12.0),
            stat("2025-09-25", -0.3, water_ha=14.0)]
    result = index_trend.build_trend("ndwi", [stat("2026-09-24", -0.2, water_ha=20.0)], base, REF, 15)
    assert result["baseline"]["water_ha"] == 12.0
    assert result["latest"]["water_ha"] == 20.0


def test_scene_stat_uses_only_water_for_water_indices():
    values = np.full((10, 10), 0.5, dtype=np.float32)
    values[:5] = -0.2
    valid = np.ones((10, 10), dtype=bool)
    water = np.zeros((10, 10), dtype=bool)
    water[:5] = True
    item = SimpleNamespace(id="S2_x", datetime=datetime(2026, 9, 24))
    with mock.patch.object(index_trend, "_index_arrays", return_value=(values, valid, water)), \
            mock.patch.object(index_trend, "MIN_PIXELS", 10):
        ndci = index_trend.scene_stat(item, None, "ndci")      # solo acqua
        ndmi = index_trend.scene_stat(item, None, "ndmi")      # solo terraferma
    assert ndci["median"] == -0.2 and ndci["zone_percentage"] == 50.0
    assert ndmi["median"] == 0.5 and ndmi["clear_percentage"] == 100.0


def test_index_analysis_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from api import main

    def fake_item(day):
        return SimpleNamespace(id=f"S2_{day}", datetime=datetime.fromisoformat(day),
                               assets={a: None for a in main.IMAGERY_ASSETS},
                               properties={"eo:cloud_cover": 5.0})

    def fake_search(bbox, start_date, end_date, max_cloud, max_items):
        return [fake_item(f"{start_date.year}-{start_date.month:02d}-{min(start_date.day + 5, 28):02d}")]

    def fake_stat(item, grid, key):
        return stat(item.datetime.date().isoformat(), 0.4 if item.datetime.year == 2026 else 0.3)

    main._TREND_CACHE.clear()
    monkeypatch.setattr(main, "search_sentinel_items", fake_search)
    monkeypatch.setattr(index_trend, "scene_stat", fake_stat)
    monkeypatch.setattr(main, "datetime", mock.Mock(now=lambda tz=None: datetime(2026, 10, 1)))
    response = TestClient(main.app).get("/api/v1/index/analysis",
                                        params={"index": "ndre", "lat": 40.68, "lon": 14.77})
    data = response.json()
    assert response.status_code == 200, data
    assert data["status"] == "ok" and data["label"] == "Clorofilla"
    assert data["comparison"]["trend"] == "up" and data["formula"].startswith("NDRE")
