from datetime import date
from unittest import mock

import numpy as np
import pytest

from src import heat


def test_celsius_from_dn():
    # 300 K = 26.85 °C  ->  DN = (300 - 149) / 0.00341802
    dn = np.array([[round((300 - 149) / heat.ST_SCALE), 0]], dtype=np.uint16)
    c = heat.celsius_from_dn(dn)
    assert c[0, 0] == pytest.approx(26.85, abs=0.01)
    assert np.isnan(c[0, 1])


def test_masks_from_qa_bits():
    clear_land = 21824        # valore tipico Landsat C2: terra limpida
    clear_water = 21952       # acqua limpida (bit 7)
    cloud = clear_land | heat.QA_CLOUD
    shadow = clear_land | heat.QA_CLOUD_SHADOW
    fill = 1
    qa = np.array([[clear_land, clear_water, cloud, shadow, fill, 0]], dtype=np.uint16)
    valid, water = heat.masks_from_qa(qa)
    assert valid.tolist() == [[True, True, False, False, False, False]]
    assert water.tolist() == [[False, True, False, False, False, False]]


def make_scene(values, water=None):
    values = np.asarray(values, dtype=np.float32)
    water = np.zeros(values.shape, bool) if water is None else np.asarray(water)
    return heat.HeatScene("x", "2025-07-01", "landsat-9", values, water, 100.0)


def test_anomaly_ignores_sea_in_the_median():
    land = np.full((10, 10), 30.0, dtype=np.float32)
    land[:, 5:] = 22.0                                  # mare fresco
    water = np.zeros((10, 10), bool)
    water[:, 5:] = True
    land[0, 0] = 40.0                                    # tetto caldo
    values, median = heat.anomaly(make_scene(land, water))
    assert median == 30.0
    assert values[0, 0] == pytest.approx(10.0)


def test_typical_anomaly_is_median_of_days():
    base = np.full((10, 10), 30.0, dtype=np.float32)
    a, b, c = base.copy(), base.copy() + 5, base.copy() - 2
    a[0, 0], b[0, 0], c[0, 0] = 36.0, 41.0, np.nan      # sempre ~+6 °C, un giorno nuvola
    typical = heat.typical_anomaly([make_scene(a), make_scene(b), make_scene(c)])
    assert typical[0, 0] == pytest.approx(6.0)
    assert typical[5, 5] == pytest.approx(0.0)


def test_summer_ranges():
    ranges = heat.summer_ranges(date(2026, 9, 30))
    assert ranges[0] == (date(2026, 6, 1), date(2026, 8, 31))
    assert ranges[-1][0] == date(2024, 6, 1)
    early = heat.summer_ranges(date(2026, 3, 1))
    assert early[0][0] == date(2025, 6, 1)


def test_colors_water_and_invalid():
    values = np.array([[np.nan, 0.0, 9.0, np.nan]], dtype=np.float32)
    water = np.array([[True, False, False, False]])
    image = heat.colorize_heat(values, water, heat.ANOMALY_STOPS)
    assert tuple(image[0, 0]) == heat.WATER_COLOR
    assert tuple(image[0, 3]) == heat.INVALID_COLOR
    assert image[0, 2, 0] > image[0, 2, 2]              # caldo = rosso


def test_signed_href_uses_cached_token():
    fake = mock.Mock()
    fake.json.return_value = {"token": "se=2099&sig=abc", "msft:expiry": "2099-01-01T00:00:00Z"}
    fake.raise_for_status.return_value = None
    heat._token.update({"value": None, "expires": 0.0})
    with mock.patch.object(heat.requests, "get", return_value=fake) as get:
        a = heat.signed("https://x.blob.core.windows.net/a.tif")
        b = heat.signed("https://x.blob.core.windows.net/b.tif?x=1")
    assert a.endswith(".tif?se=2099&sig=abc")
    assert b.endswith("?x=1&se=2099&sig=abc")
    assert get.call_count == 1
    heat._token.update({"value": None, "expires": 0.0})


def test_water_union_masks_port_seen_as_water_only_some_days():
    base = np.full((6, 6), 35.0, dtype=np.float32)
    day1 = make_scene(base.copy())
    water2 = np.zeros((6, 6), bool)
    water2[0, :] = True                                  # il porto, visto come acqua solo qui
    day2 = make_scene(base.copy(), water2)
    union = heat.water_union([day1, day2])
    assert union[0].all() and not union[1:].any()
    fixed = heat.with_water(day1, union)
    assert np.isnan(fixed.celsius[0]).all()
    assert fixed.water[0].all()


def test_heat_endpoints_with_fake_data(monkeypatch):
    from api import main

    base = np.full((20, 20), 35.0, dtype=np.float32)
    base[:5, :5] = 44.0
    water = np.zeros((20, 20), bool)
    water[15:] = True
    base[water] = np.nan
    scene = heat.HeatScene("LC09_X", "2026-07-25", "landsat-9", base, water, 99.0)
    result = heat.HeatResult([scene], heat.typical_anomaly([scene]), water)
    monkeypatch.setattr(heat, "heat_for_area", lambda lat, lon, side: result)
    monkeypatch.setattr(main, "heat_context_scene", lambda *a: None)

    info = main.get_heat(lat=40.678, lon=14.768, side_km=8)
    assert info["latest_date"] == "2026-07-25"
    assert info["images"]["rgb"] is None
    assert "kind=anomaly" in info["images"]["anomaly"]
    assert info["days"][0]["land_median_c"] == 35.0
    assert "più caldo" in info["message"]

    png = main.get_heat_image(lat=40.678, lon=14.768, side_km=8, kind="temperature")
    assert png.body[:4] == b"\x89PNG"


def test_mask_piers_keeps_coastline_but_removes_jetty():
    water = np.zeros((30, 30), bool)
    water[15:, :] = True                 # mare nella metà bassa
    water[5:15, 20:] = True              # un golfo a destra
    water[20:29, 10] = False             # molo largo 1 pixel nel mare
    masked = heat.mask_piers(water)
    assert masked[20:29, 10].all()       # il molo diventa acqua
    assert not masked[14, 5]             # la riva (acqua da un solo lato) resta terra
    assert not masked[5, 5]              # l'entroterra resta terra


def test_box_mean_matches_bruteforce():
    rng = np.random.default_rng(3)
    mask = rng.random((12, 9)) > 0.5
    fast = heat.box_mean(mask, 3)
    padded = np.pad(mask.astype(float), 1, mode="edge")
    slow = np.array([[padded[r:r + 3, c:c + 3].mean() for c in range(9)] for r in range(12)])
    np.testing.assert_allclose(fast, slow, atol=1e-6)
