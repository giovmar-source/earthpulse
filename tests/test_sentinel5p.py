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
    assert fetch.call_count == 2          # periodo attuale + stesso periodo dell'anno prima
    assert data["previous"]["change_percent"] == 0.0 and data["image_previous"]
    assert data["level"] == "medio"       # 40 µmol/m²


STATS_RESPONSE = {"data": [
    {"interval": {"from": "2026-09-28T00:00:00Z", "to": "2026-09-29T00:00:00Z"},
     "outputs": {"default": {"bands": {"B0": {"stats": {"mean": 5e-5, "sampleCount": 144, "noDataCount": 20}}}}}},
    {"interval": {"from": "2026-09-29T00:00:00Z", "to": "2026-09-30T00:00:00Z"},
     "outputs": {"default": {"bands": {"B0": {"stats": {"mean": "NaN", "sampleCount": 144, "noDataCount": 144}}}}}},
    {"interval": {"from": "2026-09-27T00:00:00Z", "to": "2026-09-28T00:00:00Z"}, "error": {"type": "EXECUTION_ERROR"}},
]}


def test_parse_statistics_skips_empty_days():
    series = sentinel5p.parse_statistics("no2", STATS_RESPONSE)
    assert series == [{"date": "2026-09-28", "value": 50.0}]


def test_statistics_body_daily_on_place():
    body = sentinel5p.statistics_body("ch4", [1, 2, 3, 4], date(2026, 7, 1), date(2026, 9, 30))
    assert body["aggregation"]["aggregationInterval"] == {"of": "P1D"}
    assert "dataMask" in body["aggregation"]["evalscript"] and ".CH4" in body["aggregation"]["evalscript"]


def test_timeseries_endpoint_compares_with_last_year(monkeypatch):
    monkeypatch.setenv("CDSE_CLIENT_ID", "id")
    monkeypatch.setenv("CDSE_CLIENT_SECRET", "secret")
    main._S5P_SERIES_CACHE.clear()
    now = [{"date": "2026-09-28", "value": 60.0}, {"date": "2026-09-29", "value": 40.0}]
    before = [{"date": "2025-09-28", "value": 40.0}]
    with mock.patch.object(sentinel5p, "fetch_timeseries", side_effect=[now, before]):
        data = TestClient(main.app).get("/api/v1/s5p/timeseries",
                                        params={"lat": 40.68, "lon": 14.77, "days": 90}).json()
    assert data["mean"] == 50.0 and data["previous_mean"] == 40.0 and data["change_percent"] == 25.0
    assert data["valid_days"] == 2 and data["level"] == "medio"


def test_parse_statistics_counts_errors_and_empty_days():
    diag = {}
    sentinel5p.parse_statistics("no2", STATS_RESPONSE, diag)
    assert diag["intervals"] == 3 and diag["error_days"] == 1 and diag["empty_days"] == 1
    assert diag["error_sample"] == "EXECUTION_ERROR"


def test_statistics_use_orbit_mosaicking():
    script = sentinel5p.statistics_evalscript("NO2")
    assert 'mosaicking: "ORBIT"' in script and "samples[i].dataMask" in script


def test_chunks_cover_period_without_gaps():
    blocks = sentinel5p.chunks(date(2026, 1, 1), date(2026, 3, 31))
    assert blocks[0] == (date(2026, 1, 1), date(2026, 1, 30))
    assert blocks[-1][1] == date(2026, 3, 31)
    days = sum((b - a).days + 1 for a, b in blocks)
    assert days == 90 and all((b - a).days < 30 for a, b in blocks)


def test_fetch_timeseries_requests_one_block_per_month(monkeypatch):
    monkeypatch.setattr(sentinel5p, "get_token", lambda session=None: "t")

    class Reply:
        status_code = 200
        text = ""

        def json(self):
            return STATS_RESPONSE

    session = mock.Mock()
    session.post.return_value = Reply()
    diag = {}
    sentinel5p.fetch_timeseries("no2", 40.0, 14.0, date(2026, 7, 3), date(2026, 9, 30),
                                session=session, diagnostics=diag)
    assert session.post.call_count == 3 and diag["intervals"] == 9
