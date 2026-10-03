"""Oltre la Terra: lettura dei formati PDS, scale di colori, valori in un punto, mosaici Trek, API."""
import io
from unittest import mock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import api.main as main
from src import planets
from src.planet_layers import BODIES


class Reply:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(planets, "CACHE_DIR", tmp_path)
    planets._grids.clear()
    planets._images.clear()
    yield
    planets._grids.clear()
    planets._images.clear()


def lonlat_grid(rows, cols, lon_start):
    lats = 90 - (np.arange(rows) + 0.5) * 180 / rows
    lons = lon_start + (np.arange(cols) + 0.5) * 360 / cols
    lon, lat = np.meshgrid(lons, lats)
    return lat, planets.normalize_lon(lon)


def serve(files):
    """Finto requests.get: restituisce il contenuto in base a un pezzo dell'indirizzo."""
    def get(url, timeout=None):
        for part, content in files.items():
            if part in url:
                return Reply(content)
        return Reply(b"", 404)
    return get


# ------------------------------------------------------------------ formati

def moon_dem_bytes(value=lambda lat, lon: 0.0):
    lat, lon = lonlat_grid(720, 1440, 0)
    return (np.vectorize(value)(lat, lon) / 0.5).astype("<i2").tobytes()


def test_img_from_0_360_is_shifted_and_scaled():
    raw = moon_dem_bytes(lambda lat, lon: 4000.0 if abs(lon - 90) < 1 and abs(lat - 10) < 1 else 0.0)
    grid = planets.read_img(raw, BODIES["moon"]["layers"]["elevation"]["source"])
    row, col = np.unravel_index(np.argmax(grid), grid.shape)
    assert grid.max() == 4000.0
    assert abs((col + 0.5) / 4 - 180 - 90) < 1.5 and abs(90 - (row + 0.5) / 4 - 10) < 1.5


def test_img_wrong_size_is_rejected():
    with pytest.raises(planets.PlanetDataUnavailable):
        planets.read_img(b"\x00" * 10, BODIES["mars"]["layers"]["elevation"]["source"])


def test_img_point_registered_and_nodata():
    grav = np.zeros((721, 1440), "<f4")
    grav[0] = 300.0
    grid = planets.read_img(grav.tobytes(), BODIES["moon"]["layers"]["gravity"]["source"])
    assert grid.shape == (720, 1440) and grid[0, 0] == 300.0
    mg = np.full((720, 1440), 100, "u1")
    mg[:, :10] = 0
    grid = planets.read_img(mg.tobytes(), BODIES["mercury"]["layers"]["magnesium"]["source"])
    assert np.isnan(grid[5, 5]) and abs(grid[5, 100] - 0.30668824) < 1e-6


def test_img_partial_latitudes_are_placed_in_full_globe():
    ti = np.full((882, 2880), 250.0, "<f4")
    ti[0, 0] = -1                                   # valore non valido
    grid = planets.read_img(ti.tobytes(), BODIES["mars"]["layers"]["thermal_inertia"]["source"])
    assert grid.shape == (1440, 2880)
    assert np.isnan(grid[100, 500]) and grid[300, 500] == 250.0 and np.isnan(grid[239, 0])
    assert planets.shrink(grid).shape == (720, 1440)


def test_cells_table_like_lunar_prospector():
    lines = ["# Lunar Prospector thorium, 0.5 deg", "# latmin, latmax, lonmin, lonmax, value"]
    for lat0 in np.arange(-90, 90, 0.5):
        for lon0 in (-180.0, 179.5):
            lines.append(f"{lat0:.2f}, {lat0 + 0.5:.2f}, {lon0:.2f}, {lon0 + 0.5:.2f}, {7.5 if lat0 >= 0 else 1.0}")
    grid = planets.read_cells("\n".join(lines).encode(), BODIES["moon"]["layers"]["thorium"]["source"])
    assert grid.shape == (360, 720)
    assert grid[0, 0] == 7.5 and grid[-1, -1] == 1.0 and np.isnan(grid[100, 300])


def test_cells_table_with_index_and_wide_cells_like_dawn():
    rows = ["PIXEL_INDEX MIN_LAT MAX_LAT MIN_LON MAX_LON H SIG"]
    rows += [f"{i} {lat} {lat + 2} -180 180 {abs(lat) / 10:.1f} 0.1" for i, lat in enumerate(range(-90, 90, 2))]
    grid = planets.read_cells("\n".join(rows).encode(), BODIES["ceres"]["layers"]["hydrogen"]["source"])
    assert grid.shape == (180, 360)
    assert grid[0, 0] == pytest.approx(8.8) and grid[89, 200] == pytest.approx(0.0)  # cella 0°–2° N


def test_points_table_like_odyssey_and_magnetometer():
    rows = []
    for lat in np.arange(-87.5, 90, 5):
        for lon in np.arange(2.5, 360, 5):
            value = 9999.999 if abs(lat) > 60 else (7.0 if 170 < lon < 185 else 2.0)
            rows.append(f"{lat:8.2f}{lon:8.2f}{value:12.3f}{0.5:10.3f}{0.6:10.3f}")
    grid = planets.read_points("\n".join(rows).encode(), BODIES["mars"]["layers"]["water"]["source"])
    assert grid.shape == (36, 72) and np.isnan(grid[0, 0])
    assert grid[18, 71] == pytest.approx(7.0)       # 177,5° E -> ultima colonna
    assert grid[18, 0] == pytest.approx(7.0)        # 182,5° E = 177,5° O -> prima colonna
    assert grid[18, 36] == pytest.approx(2.0)       # 2,5° E

    mag = ["Connerney et al. 2001, Br Bt Bp r lat lon"]
    for lat in np.arange(-89.5, 90, 1):
        for lon in np.arange(0.5, 360, 1):
            br = 0.0 if abs(lat) > 85 or lon == 0.5 else (150.0 if lat < -30 and 170 < lon < 200 else 5.0)
            mag.append(f"{br:9.3f} 1.0 2.0 3793.4 {lat:7.2f} {lon:7.2f}")
    grid = planets.read_points("\n".join(mag).encode(), BODIES["mars"]["layers"]["magnetism"]["source"])
    assert grid.shape == (180, 360) and np.isnan(grid[0, 10]) and np.nanmax(grid) == 150.0
    assert grid[90, 180] == 0.0                     # zero vero all'equatore (0,5° E), non "nessun dato"


# ------------------------------------------------------------------ colori e legende

def test_auto_stops_round_and_diverging_is_symmetric():
    grid = np.linspace(1.3, 11.8, 10000).reshape(100, 100).astype(np.float32)
    stops = planets.auto_stops(grid, 8, diverging=False)
    assert len(stops) == 8 and stops[0] <= 1.6 and stops[-1] >= 11.5
    diverging = planets.auto_stops(np.linspace(-420, 380, 1000), 9, diverging=True)
    assert diverging[4] == 0 and diverging[0] == -diverging[-1]


def test_colorize_marks_missing_data_grey():
    image = planets.colorize(np.array([[np.nan, 0.0, 100.0]]), [0, 100], [(0, 0, 0), (255, 255, 255)])
    assert tuple(image[0, 0]) == planets.NO_DATA_COLOR and tuple(image[0, 2]) == (255, 255, 255)


def test_legend_labels_with_units_and_signs():
    spec = BODIES["mars"]["layers"]["elevation"]
    labels = planets.legend(spec, spec["stops"], False)["labels"]
    assert labels[0] == "−8" and labels[3] == "0" and labels[4] == "+2" and labels[-1] == "+21 km"
    spec = BODIES["mars"]["layers"]["water"]
    legend = planets.legend(spec, [2, 3, 4, 5, 6, 7, 8, 9], True)
    assert legend["labels"][-1] == "9 % in peso" and legend["no_data"]


def test_hillshade_lights_north_west_slopes():
    y, x = np.mgrid[0:200, 0:400]
    hill = 3000 * np.exp(-(((x - 200) / 15) ** 2 + ((y - 100) / 15) ** 2))
    shade = planets.hillshade(hill.astype(np.float32), 1737.4)
    assert shade[90, 190] > shade[110, 210]


# ------------------------------------------------------------------ download, punto, mosaici

def test_download_once_then_from_disk():
    get = mock.Mock(return_value=Reply(moon_dem_bytes(lambda lat, lon: 1500.0)))
    session = mock.Mock(get=get)
    assert planets.value_at("moon", "elevation", 10, 20, session) == 1500.0
    planets._grids.clear()
    assert planets.value_at("moon", "elevation", 10, 20, session) == 1500.0
    assert get.call_count == 1


def test_point_returns_requested_layers_and_missing_values():
    session = mock.Mock(get=serve({"ldem_4": moon_dem_bytes(lambda lat, lon: -2000.0)}))
    values = planets.point("moon", 0, 0, ["elevation", "photo"], session)
    assert [v["key"] for v in values] == ["elevation"] and values[0]["value"] == -2000.0
    assert values[0]["pixel_km"] == pytest.approx(7.6, abs=0.1)


def test_trek_mosaic_joins_tiles_and_flattens_transparency():
    tile = io.BytesIO()
    Image.new("RGBA", (256, 256), (200, 200, 200, 0)).save(tile, format="PNG")
    get = mock.Mock(return_value=Reply(tile.getvalue()))
    data = planets.trek_mosaic(BODIES["vesta"]["layers"]["photo"], mock.Mock(get=get))
    picture = Image.open(io.BytesIO(data))
    assert picture.size == (2048, 1024) and get.call_count == 32
    assert abs(picture.getpixel((5, 5))[0] - planets.NO_DATA_COLOR[0]) < 6
    assert "/Vesta/EQ/Vesta_Dawn_HAMO_TrueClr" in get.call_args_list[0].args[0]


def test_every_layer_is_complete():
    for body, info in BODIES.items():
        assert info["radius_km"] > 0
        for key, spec in info["layers"].items():
            assert spec["label"] and spec["attribution"], (body, key)
            if spec["kind"] == "grid":
                assert spec["source"]["format"] in planets.READERS and spec["unit"] and spec["caption"]
                assert spec["stops"] in ("auto", "auto_diverging") or len(spec["stops"]) == len(spec["colors"])
            else:
                assert spec["trek_id"] and spec["ext"] in ("jpg", "png")


# ------------------------------------------------------------------ API

def test_api_catalog_image_legend_and_point(monkeypatch):
    monkeypatch.setattr(planets.requests, "get", serve({"ldem_4": moon_dem_bytes(lambda lat, lon: -2000.0)}))
    client = TestClient(main.app)
    layers = client.get("/api/v1/space/layers", params={"body": "moon"}).json()["layers"]
    keys = [l["key"] for l in layers]
    assert keys[:2] == ["elevation", "thorium"] and layers[0]["numeric"] and layers[0]["legend"]["labels"]
    image = client.get(layers[0]["image"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    legend = client.get("/api/v1/space/legend", params={"body": "moon", "layer": "elevation"}).json()
    assert legend["labels"][-1] == "+10 km"
    data = client.get("/api/v1/space/point", params={"body": "moon", "lat": 10, "lon": 20, "layers": "elevation"}).json()
    assert data["values"][0]["value"] == -2000.0
    assert client.get("/api/v1/space/layer", params={"body": "moon", "layer": "night_ir"}).status_code == 404
    assert client.get("/api/v1/space/layers", params={"body": "pluto"}).status_code == 422


def test_api_reports_unreachable_archive(monkeypatch):
    monkeypatch.setattr(planets.requests, "get", serve({}))
    client = TestClient(main.app)
    response = client.get("/api/v1/space/point", params={"body": "mars", "lat": 0, "lon": 0, "layers": "elevation"})
    assert response.status_code == 503
    # Senza mappe numeriche richieste il punto risponde comunque (nome del luogo non disponibile)
    ok = client.get("/api/v1/space/point", params={"body": "mars", "lat": 0, "lon": 0}).json()
    assert ok["values"] == [] and ok["place"] is None


def test_fixed_width_grid_like_magellan_starts_at_240_east():
    lines = []
    for row in range(180):
        values = []
        for col in range(360):
            lon = (240 + col + 0.5) % 360                   # 0-360 est
            values.append(11.0 if row == 30 and 0 <= lon < 2 else 0.5)
        for k in range(0, 360, 10):
            lines.append("".join(f"{v:8.2f}" for v in values[k:k + 10]))
    grid = planets.read_fixed("\r\n".join(lines).encode(), BODIES["venus"]["layers"]["elevation"]["source"])
    assert grid.shape == (180, 360) and grid.max() == 11000.0
    row, col = np.unravel_index(np.argmax(grid), grid.shape)
    assert row == 30 and col in (180, 181)                  # longitudine 0-2° E dopo la rotazione


def test_to_west_left_for_any_start():
    grid = np.arange(360, dtype=np.float32)[None, :]
    assert planets.to_west_left(grid, 0)[0, 0] == 180          # colonna di −180 = 180° E
    assert planets.to_west_left(grid, -180)[0, 0] == 0
    assert planets.to_west_left(grid, 240)[0, 0] == 300        # 240 + 300 = 540 = 180° = −180°
