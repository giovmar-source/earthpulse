"""Mappa del Sistema solare, Sole, nomi IAU e siti di atterraggio."""
import io
import json
import struct
import zipfile
from datetime import date
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import api.main as main
from src import nomenclature, planets, solar_system


class Reply:
    def __init__(self, content=b"", status_code=200, payload=None, headers=None):
        self.content = content
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.setattr(planets, "CACHE_DIR", tmp_path)
    for cache in (solar_system._elements, solar_system._tracks, solar_system._sun, nomenclature._features):
        cache.clear()
    yield


# ------------------------------------------------------------------ Cerere e Vesta

SBDB = {"orbit": {"epoch": "2461000.5", "elements": [
    {"name": "e", "value": "0.0796"}, {"name": "a", "value": "2.766"}, {"name": "i", "value": "10.59"},
    {"name": "om", "value": "80.25"}, {"name": "w", "value": "73.3"}, {"name": "ma", "value": "231.5"},
    {"name": "n", "value": "0.2142"}, {"name": "q", "value": "2.55"}]}}


def test_small_bodies_from_jpl_and_fallback():
    ok = mock.Mock(get=mock.Mock(return_value=Reply(payload=SBDB)))
    bodies = solar_system.small_bodies(ok, today=date(2026, 10, 2))
    assert bodies[0]["key"] == "ceres" and bodies[0]["elements"]["epoch"] == 2461000.5
    assert bodies[0]["epoch_date"] == "2025-11-21" and "salvati" not in bodies[0]["source"]
    solar_system._elements.clear()
    down = mock.Mock(get=mock.Mock(side_effect=solar_system.requests.ConnectionError("giù")))
    bodies = solar_system.small_bodies(down, today=date(2026, 10, 2))
    assert bodies[1]["elements"] == solar_system.FALLBACK_ELEMENTS["vesta"] and "salvati" in bodies[1]["source"]


# ------------------------------------------------------------------ Horizons

HORIZONS_TEXT = """header
 JDTDB, Calendar Date (TDB), X, Y, Z,
$$SOE
2461314.500000000, A.D. 2026-Oct-01 00:00:00.0000,  1.234567890123456E+00, -2.5E-01,  3.0E-02,
2461319.500000000, A.D. 2026-Oct-06 00:00:00.0000,  1.24E+00, -2.4E-01,  3.1E-02,
$$EOE
footer"""


def test_parse_vectors_and_params():
    points = solar_system.parse_vectors(HORIZONS_TEXT)
    assert len(points) == 2 and points[0]["x"] == pytest.approx(1.2345678901) and points[1]["jd"] == 2461319.5
    assert solar_system.parse_vectors("No ephemeris for target") == []
    params = solar_system.horizons_params("-159", date(2025, 10, 2), date(2027, 10, 2))
    assert params["CENTER"] == "'500@10'" and params["REF_PLANE"] == "'ECLIPTIC'" and params["COMMAND"] == "'-159'"


def test_spacecraft_skips_missing_and_retries_past_only():
    calls = []

    def get(url, params, timeout):
        calls.append((params["COMMAND"], params["STOP_TIME"]))
        if params["COMMAND"] == "'-31'":
            return Reply(payload={"result": HORIZONS_TEXT})
        if params["COMMAND"] == "'-61'" and params["STOP_TIME"] == "'2026-10-02'":
            return Reply(payload={"result": HORIZONS_TEXT})        # solo passato
        return Reply(payload={"result": "No ephemeris for target"})
    crafts = solar_system.spacecraft(mock.Mock(get=get), today=date(2026, 10, 2), pause=0)
    keys = [c["key"] for c in crafts]
    assert keys == ["voyager1", "juno"] and len(crafts[0]["track"][0]) == 4
    count = len(calls)
    solar_system.spacecraft(mock.Mock(get=get), today=date(2026, 10, 2), pause=0)
    assert len(calls) == count                                   # tutto in cache


# ------------------------------------------------------------------ Sole

def test_sun_image_cached_with_observation_time():
    get = mock.Mock(return_value=Reply(b"jpeg", headers={"Last-Modified": "Fri, 02 Oct 2026 14:58:07 GMT"}))
    data, observed = solar_system.sun_image("0193", mock.Mock(get=get))
    assert data == b"jpeg" and observed.startswith("2026-10-02T14:58:07")
    solar_system.sun_image("0193", mock.Mock(get=get))
    assert get.call_count == 1


def test_sun_endpoint(monkeypatch):
    monkeypatch.setattr(solar_system.requests, "get",
                        lambda url, timeout: Reply(b"jpeg", headers={"Last-Modified": "Fri, 02 Oct 2026 14:58:07 GMT"}))
    client = TestClient(main.app)
    response = client.get("/api/v1/space/sun", params={"product": "0304"})
    assert response.status_code == 200 and response.headers["x-observed"].startswith("2026-10-02")
    assert client.get("/api/v1/space/sun", params={"product": "9999"}).status_code == 422
    assert len(client.get("/api/v1/space/sun/products").json()["products"]) == 5


# ------------------------------------------------------------------ nomi IAU

def make_dbf(rows):
    fields = [("clean_name", "C", 40), ("type", "C", 20), ("diameter", "N", 10),
              ("center_lat", "N", 12), ("center_lon", "N", 12), ("approval", "C", 30), ("origin", "C", 60)]
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(f[2] for f in fields)
    out = bytearray(struct.pack("<BBBBIHH20x", 3, 126, 10, 2, len(rows), header_len, record_len))
    for name, ftype, length in fields:
        out += struct.pack("<11sc4xB15x", name.upper().encode(), ftype.encode(), length)
    out += b"\x0d"
    for row in rows:
        out += b" "
        for name, ftype, length in fields:
            value = row.get(name, "")
            text = (f"{value:>{length}}" if ftype == "N" else f"{value:<{length}}")[:length]
            out += text.encode("utf-8")
    out += b"\x1a"
    return bytes(out)


def gazetteer_zip(rows):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("MOON_nomenclature_center_pts.dbf", make_dbf(rows))
        archive.writestr("MOON_nomenclature_center_pts.shp", b"")
    return buffer.getvalue()


MOON_ROWS = [
    {"clean_name": "Copernicus", "type": "Crater, craters", "diameter": 96.07, "center_lat": 9.62,
     "center_lon": 339.92, "approval": "Adopted by IAU", "origin": "Nicolaus Copernicus, astronomer"},
    {"clean_name": "Mare Imbrium", "type": "Mare, maria", "diameter": 1145.53, "center_lat": 34.72,
     "center_lon": 345.09, "approval": "Adopted by IAU", "origin": "Sea of Showers"},
    {"clean_name": "Old name", "type": "Crater, craters", "diameter": 5, "center_lat": 9.6,
     "center_lon": 339.9, "approval": "Dropped, disallowed", "origin": ""},
]


def test_dbf_reader_and_normalize():
    rows = nomenclature.read_dbf(make_dbf(MOON_ROWS))
    assert rows[0]["clean_name"] == "Copernicus" and rows[0]["center_lon"] == 339.92
    features = nomenclature.normalize(rows)
    assert len(features) == 2 and features[0]["lon"] == pytest.approx(-20.08)


def test_place_inside_smallest_feature_or_nearest():
    session = mock.Mock(get=mock.Mock(return_value=Reply(gazetteer_zip(MOON_ROWS))))
    inside = nomenclature.place_at("moon", 9.7, -20.0, session)
    assert inside["name"] == "Copernicus" and inside["inside"]
    far = nomenclature.place_at("moon", -60, 100, session)
    assert not far["inside"] and far["distance_km"] > 1000
    assert nomenclature.place_at("titan", 0, 0, session) is None


def test_landing_sites_file_is_complete():
    data = json.loads(nomenclature.LANDING_FILE.read_text(encoding="utf-8"))
    for site in data["sites"]:
        assert site["source"].startswith("https://") and site["precision"] and -90 <= site["lat"] <= 90
        assert -180 <= site["lon"] <= 180 and len(site["date"]) == 10
    apollo = nomenclature.nearest_landing("moon", 0.67, 23.47, max_km=50)
    assert apollo["name"] == "Apollo 11" and apollo["distance_km"] < 1


def test_point_endpoint_adds_place_and_landing(monkeypatch):
    monkeypatch.setattr(planets.requests, "get", lambda url, timeout: Reply(gazetteer_zip(MOON_ROWS)))
    data = TestClient(main.app).get("/api/v1/space/point", params={"body": "moon", "lat": 0.67, "lon": 23.47}).json()
    assert data["values"] == [] and data["landing"]["name"] == "Apollo 11" and data["place"]["name"]
    sites = TestClient(main.app).get("/api/v1/space/sites", params={"body": "mars"}).json()
    assert sites["markers"] and any(s["name"] == "Curiosity" for s in sites["sites"])
