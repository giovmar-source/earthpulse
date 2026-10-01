from datetime import date
from unittest import mock

import numpy as np
from fastapi.testclient import TestClient

from api import main
from src import sentinel5p


class FakeResponse:
    def __init__(self, status, payload=None, content=b""):
        self.status_code = status
        self._payload = payload or {}
        self.content = content
        self.text = str(payload)

    def json(self):
        return self._payload


def test_area_bbox_is_wider_in_longitude_far_from_equator():
    west, south, east, north = sentinel5p.area_bbox(60.0, 10.0)
    assert round(north - south, 2) == round(2 * 150 / 110.574, 2)
    assert (east - west) > 1.9 * (north - south)


def test_request_body_uses_orbit_average_and_float_output():
    body = sentinel5p.request_body("no2", [1, 2, 3, 4], date(2026, 9, 24), date(2026, 9, 30))
    assert body["input"]["data"][0]["type"] == "sentinel-5p-l2"
    assert body["input"]["data"][0]["dataFilter"]["timeRange"]["from"] == "2026-09-24T00:00:00Z"
    assert 'mosaicking: "ORBIT"' in body["evalscript"] and "samples[i].NO2" in body["evalscript"]
    assert body["output"]["responses"][0]["format"]["type"] == "image/tiff"


def test_period_ends_yesterday():
    assert sentinel5p.period(7, today=date(2026, 10, 1)) == (date(2026, 9, 24), date(2026, 9, 30))


def test_summary_place_and_region():
    values = np.full((100, 100), 50.0, dtype=np.float32)
    values[45:55, 45:55] = 150.0          # città al centro
    values[:10] = np.nan                  # striscia senza dati
    with mock.patch.object(sentinel5p, "HALF_SIDE_KM", 150.0):
        info = sentinel5p.summary("no2", values)
    assert info["place"] > info["region"] > 50
    assert info["coverage_percentage"] == 90.0
    assert "volte" in sentinel5p.describe("no2", info)


def test_describe_methane_uses_difference():
    assert "in linea" in sentinel5p.describe("ch4", {"place": 1885, "region": 1880, "place_vs_region": 1.0})
    assert "sopra" in sentinel5p.describe("ch4", {"place": 1920, "region": 1880, "place_vs_region": 1.02})


def test_colorize_marks_missing_data():
    values = np.array([[0.0, np.nan], [220.0, 1000.0]], dtype=np.float32)
    image = sentinel5p.colorize("no2", values)
    assert tuple(image[0, 1]) == sentinel5p.NO_DATA_COLOR
    assert tuple(image[1, 0]) == tuple(image[1, 1])     # oltre la scala: colore massimo


def test_token_is_reused(monkeypatch):
    monkeypatch.setenv("CDSE_CLIENT_ID", "id")
    monkeypatch.setenv("CDSE_CLIENT_SECRET", "secret")
    sentinel5p._token.update({"value": None, "expires": 0.0})
    session = mock.Mock()
    session.post.return_value = FakeResponse(200, {"access_token": "abc", "expires_in": 600})
    assert sentinel5p.get_token(session) == "abc"
    assert sentinel5p.get_token(session) == "abc"
    assert session.post.call_count == 1


def test_endpoint_without_credentials(monkeypatch):
    monkeypatch.delenv("CDSE_CLIENT_ID", raising=False)
    monkeypatch.delenv("CDSE_CLIENT_SECRET", raising=False)
    response = TestClient(main.app).get("/api/v1/s5p", params={"lat": 40.7, "lon": 14.8})
    assert response.status_code == 503
    assert "credenziali" in response.json()["detail"]


def test_endpoint_returns_numbers_and_image(monkeypatch):
    monkeypatch.setenv("CDSE_CLIENT_ID", "id")
    monkeypatch.setenv("CDSE_CLIENT_SECRET", "secret")
    main._S5P_CACHE.clear()
    grid = np.full((64, 64), 40e-6, dtype=np.float32)
    with mock.patch.object(sentinel5p, "fetch_grid", return_value=grid) as fetch:
        client = TestClient(main.app)
        data = client.get("/api/v1/s5p", params={"lat": 40.68, "lon": 14.77}).json()
        image = client.get(data["image"])
    assert data["unit"] == "µmol/m²" and data["place"] == 40.0 and data["region"] == 40.0
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"
    assert fetch.call_count == 1          # l'immagine usa i valori già in memoria
