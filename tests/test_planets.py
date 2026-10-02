"""Mappe di Luna e Marte: lettura delle griglie PDS, colori, altitudine di un punto, API."""
import io
from unittest import mock

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import api.main as main
from src import planets


def _raw(body, value_at=lambda lat, lon: 0.0):
    """File IMG sintetico come quelli del PDS (longitudine da 0 a 360)."""
    lats = 90 - (np.arange(planets.ROWS) + 0.5) / 4
    lons = (np.arange(planets.COLS) + 0.5) / 4
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    metres = np.vectorize(value_at)(lat_grid, ((lon_grid + 180) % 360) - 180)
    raw = (metres / planets.DEMS[body]["scale"]).astype(planets.DEMS[body]["dtype"])
    return raw.tobytes()


class Reply:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


def _reset(tmp_path, monkeypatch):
    monkeypatch.setattr(planets, "CACHE_DIR", tmp_path)
    planets._dems.clear()
    planets._images.clear()


def test_parse_dem_shifts_to_minus_180_and_scales(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    # Luna: valori grezzi a mezzo metro; un rilievo a 90° est
    raw = _raw("moon", lambda lat, lon: 4000.0 if abs(lon - 90) < 1 and abs(lat) < 1 else 0.0)
    grid = planets.parse_dem(raw, "moon")
    assert grid.shape == (720, 1440)
    row, col = np.unravel_index(np.argmax(grid), grid.shape)
    assert abs(col / 4 - 180 - 90) < 1.5 and abs(90 - row / 4) < 1.5
    assert grid.max() == 4000.0


def test_wrong_size_is_rejected():
    try:
        planets.parse_dem(b"\\x00" * 10, "mars")
    except planets.PlanetDataUnavailable:
        return
    raise AssertionError("dimensione sbagliata accettata")


def test_dem_downloaded_once_then_cached_on_disk(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    session = mock.Mock()
    session.get.return_value = Reply(_raw("mars", lambda lat, lon: 21000.0 if lat > 80 else -500.0))
    assert planets.elevation_at("mars", 85, 10, session) == 21000.0
    assert planets.elevation_at("mars", 0, -170, session) == -500.0
    assert session.get.call_count == 1 and (tmp_path / "mars_dem.img").exists()
    planets._dems.clear()                         # come dopo un riavvio
    assert planets.elevation_at("mars", 85, 10, session) == 21000.0
    assert session.get.call_count == 1            # letto dal disco


def test_colorize_follows_stops():
    stops = planets.DEMS["moon"]["stops_km"]
    colors = planets.colorize(np.array([[-20000.0, 0.0, 20000.0]]), stops)
    assert tuple(colors[0, 0].astype(int)) == planets.RAMP[0]
    assert tuple(colors[0, 2].astype(int)) == planets.RAMP[-1]
    assert tuple(colors[0, 1].astype(int)) == planets.RAMP[stops.index(0)]


def test_hillshade_lights_north_west_slopes():
    y, x = np.mgrid[0:200, 0:400]
    hill = 3000 * np.exp(-(((x - 200) / 15) ** 2 + ((y - 100) / 15) ** 2))
    shade = planets.hillshade(hill.astype(np.float32), 1737.4)
    assert shade[90, 190] > shade[110, 210]       # versante nord-ovest più chiaro


def test_legend_labels_in_km():
    legend = planets.elevation_legend("mars")
    assert legend["labels"][0] == "−8" and legend["labels"][3] == "0" and legend["labels"][-1] == "+21 km"
    assert legend["positions"][0] == 0 and legend["positions"][-1] == 1


def test_trek_mosaic_joins_tiles(monkeypatch):
    tile = io.BytesIO()
    Image.new("RGB", (256, 256), (200, 200, 200)).save(tile, format="PNG")
    session = mock.Mock()
    session.get.return_value = Reply(tile.getvalue())
    data = planets.trek_mosaic(planets.LAYERS["mars"]["night_ir"], session)
    assert Image.open(io.BytesIO(data)).size == (2048, 1024)
    assert session.get.call_count == 32
    assert "THEMIS_NightIR" in session.get.call_args_list[0].args[0]


def test_api_layers_image_and_elevation(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    monkeypatch.setattr(planets.requests, "get", lambda url, timeout: Reply(_raw("moon", lambda lat, lon: -2000.0)))
    client = TestClient(main.app)
    layers = client.get("/api/v1/space/layers", params={"body": "moon"}).json()["layers"]
    assert layers[0]["key"] == "elevation" and layers[0]["pickable"]
    image = client.get(layers[0]["image"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    point = client.get("/api/v1/space/elevation", params={"body": "moon", "lat": 10, "lon": 20}).json()
    assert point["elevation_m"] == -2000
    assert client.get("/api/v1/space/layer", params={"body": "moon", "layer": "night_ir"}).status_code == 404


def test_api_reports_unreachable_archive(tmp_path, monkeypatch):
    _reset(tmp_path, monkeypatch)
    monkeypatch.setattr(planets.requests, "get", lambda url, timeout: Reply(b"", 500))
    response = TestClient(main.app).get("/api/v1/space/elevation", params={"body": "mars", "lat": 0, "lon": 0})
    assert response.status_code == 503
