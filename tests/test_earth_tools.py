"""Acqua dal radar, pioggia e suolo (NASA POWER), incendi (FIRMS), mare (ERDDAP), suolo impermeabile (HRL)."""
import io
from datetime import date
from unittest import mock

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api.main as main
from src import fires, imperviousness, sar_water, sea, sentinel5p, water_cycle


class Reply:
    def __init__(self, content=b"", status_code=200, payload=None, text=None):
        self.content = content
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else (content.decode("latin-1") if isinstance(content, bytes) else "")

    def json(self):
        return self._payload


def tiff(*bands, dtype="float32"):
    from rasterio.io import MemoryFile
    rows, cols = bands[0].shape
    with MemoryFile() as memfile:
        with memfile.open(driver="GTiff", width=cols, height=rows, count=len(bands), dtype=dtype) as ds:
            for i, b in enumerate(bands, start=1):
                ds.write(b.astype(dtype), i)
        return memfile.read()


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    for cache in (sar_water._cache, water_cycle._cache, fires._cache, sea._cache, imperviousness._cache):
        cache.clear()
    sentinel5p._token.update({"value": "t", "expires": 9e12})
    yield
    sentinel5p._token.update({"value": None, "expires": 0})


# ------------------------------------------------------------------ radar

def test_windows_year_and_month():
    w = sar_water.windows("year", date(2026, 10, 2))
    assert w["now"] == (date(2026, 9, 20), date(2026, 10, 2)) and w["reference"][1] == date(2025, 10, 2)
    m = sar_water.windows("month", date(2026, 10, 2))
    assert m["reference"] == (date(2026, 8, 21), date(2026, 9, 2))


def test_classify_new_permanent_and_lost_water():
    now = np.full((300, 300), -10.0, np.float32)
    ref = now.copy()
    now[0:100, 0:100] = -22                      # acqua in entrambi
    ref[0:100, 0:100] = -22
    now[150:250, 150:250] = -21                  # acqua nuova (allagamento)
    ref[200:260, 0:60] = -23                     # acqua sparita
    c = sar_water.classify(now, ref)
    pixel_ha = (6000 / 300) ** 2 / 10000
    assert c["stats"]["permanent"] == pytest.approx(10000 * pixel_ha, rel=0.03)
    assert c["stats"]["new"] == pytest.approx(10000 * pixel_ha, rel=0.03)
    assert c["stats"]["lost"] == pytest.approx(3600 * pixel_ha, rel=0.05)
    assert c["stats"]["valid_percent"] == 100.0
    png = sar_water.render(now, c["classes"], c["valid"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_smooth_removes_isolated_pixels():
    mask = np.zeros((20, 20), bool)
    mask[5, 5] = True
    mask[10:15, 10:15] = True
    out = sar_water.smooth(mask)
    assert not out[5, 5] and out[12, 12]


def test_analyse_with_catalog_and_process(monkeypatch):
    vv_now = np.full((300, 300), 0.1, np.float32)
    vv_now[:50] = 0.005                          # −23 dB: acqua
    good = tiff(vv_now, np.ones((300, 300)))
    session = mock.Mock()
    session.post.side_effect = lambda url, **kw: (
        Reply(payload={"features": [{"properties": {"datetime": "2026-09-28T05:30:00Z"}}]})
        if "catalog" in url else Reply(good))
    result = sar_water.analyse(45.0, 12.0, "year", session=session, today=date(2026, 10, 2))
    assert result["status"] == "ok" and result["acquired"]["now"] == "2026-09-28T05:30:00Z"
    assert result["stats"]["permanent"] > 0 and result["stats"]["new"] == 0
    empty = mock.Mock()
    empty.post.return_value = Reply(payload={"features": []})
    assert sar_water.analyse(10.0, 10.0, "month", session=empty, today=date(2026, 10, 2))["status"] == "no_data"


# ------------------------------------------------------------------ pioggia e suolo

POWER_DAILY = {"header": {"fill_value": -999.0}, "properties": {"parameter": {
    "PRECTOTCORR": {"20260901": 10.0, "20260902": 0.0, "20260903": -999.0, "20260904": 5.5},
    "GWETTOP": {"20260901": 0.8, "20260902": 0.7, "20260903": -999.0, "20260904": 0.65},
    "GWETROOT": {"20260901": 0.6, "20260902": 0.6, "20260903": -999.0, "20260904": 0.58}}}}
POWER_CLIM = {"header": {"fill_value": -999.0}, "properties": {"parameter": {
    "PRECTOTCORR": {m: 2.0 for m in water_cycle.MONTHS} | {"ANN": 2.0},
    "GWETTOP": {m: 0.5 for m in water_cycle.MONTHS}, "GWETROOT": {m: 0.55 for m in water_cycle.MONTHS}}}}


def test_water_cycle_totals_against_normal():
    def get(url, params, timeout):
        return Reply(payload=POWER_CLIM if "climatology" in url else POWER_DAILY)
    result = water_cycle.analyse(41.9, 12.5, 90, session=mock.Mock(get=get), today=date(2026, 9, 5))
    rain = result["rain"]
    assert rain["total_mm"] == 15.5 and rain["normal_mm"] == 6.0 and rain["percent_of_normal"] == 258
    assert rain["rainy_days"] == 2 and len(rain["series"]) == 3 and rain["last_date"] == "2026-09-04"
    assert result["soil"]["surface"]["latest"] == {"date": "2026-09-04", "value": 65.0}
    assert result["soil"]["surface"]["normal"] == 50.0 and result["soil"]["root"]["normal"] == 55.0


# ------------------------------------------------------------------ incendi

FIRMS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight
38.10,15.60,330.1,0.4,0.4,2026-10-01,0142,N20,VIIRS,n,2.0NRT,290.1,12.5,N
38.50,16.90,340.2,0.4,0.4,2026-10-02,1236,N20,VIIRS,h,2.0NRT,300.2,40.0,D
"""


def test_fires_need_key_then_parse(monkeypatch):
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    with pytest.raises(fires.FiresUnavailable):
        fires.detections(38.1, 15.65)
    monkeypatch.setenv("FIRMS_MAP_KEY", "abc")
    session = mock.Mock(get=mock.Mock(return_value=Reply(text=FIRMS_CSV)))
    result = fires.detections(38.1, 15.65, radius_km=50, session=session)
    assert result["count"] == 3                       # una per fonte (3 satelliti), la seconda è fuori raggio
    first = result["points"][0]
    assert first["confidence"] == "nominale" and first["night"] and first["time_utc"] == "01:42"
    assert result["nearest_km"] < 5
    assert "/abc/VIIRS_SNPP_NRT/" in session.get.call_args_list[0].args[0]


# ------------------------------------------------------------------ mare

SST_CSV = """time,zlev,latitude,longitude,sst,anom
UTC,m,degrees_north,degrees_east,degree_C,degree_C
2026-09-29T12:00:00Z,0.0,41.125,12.125,24.5,1.2
2026-09-30T12:00:00Z,0.0,41.125,12.125,24.1,1.0
2026-10-01T12:00:00Z,0.0,41.125,12.125,NaN,NaN
"""
CHL_CSV = """time,altitude,latitude,longitude,chlor_a
UTC,m,degrees_north,degrees_east,mg m^-3
2026-09-20T12:00:00Z,0.0,41.0,12.0,0.12
"""


def test_sea_parse_and_land():
    def get(url, timeout):
        return Reply(text=SST_CSV if "Oisst" in url else CHL_CSV)
    result = sea.analyse(41.1, 12.1, session=mock.Mock(get=get))
    assert result["status"] == "ok" and result["sst"]["summary"]["latest"] == 24.1
    assert result["sst"]["anomaly"]["latest"] == 1.0 and result["chlorophyll"]["summary"]["latest"] == 0.12
    assert "[last-59:1:last]" in sea.sst_url(41, 12) and "(348.000)" in sea.sst_url(41, -12)
    sea._cache.clear()
    land = SST_CSV.replace("24.5,1.2", "NaN,NaN").replace("24.1,1.0", "NaN,NaN")
    result = sea.analyse(45.0, 10.0, session=mock.Mock(get=lambda url, timeout: Reply(text=land)))
    assert result["status"] == "land"


# ------------------------------------------------------------------ suolo impermeabilizzato

def test_imperviousness_stats_and_outside():
    values = np.zeros((200, 200), np.uint8)
    values[:100] = 100                           # metà area completamente costruita
    session = mock.Mock(get=mock.Mock(return_value=Reply(tiff(values, dtype="uint8"))))
    result = imperviousness.analyse(45.46, 9.19, session=session)
    assert result["status"] == "ok" and result["mean_percent"] == 50.0
    assert result["sealed_ha"] == pytest.approx(200.0) and result["built_share_percent"] == 50.0
    params = session.get.call_args.kwargs["params"]
    assert params["format"] == "tiff" and params["bboxSR"] == "4326"
    imperviousness._cache.clear()
    out = mock.Mock(get=mock.Mock(return_value=Reply(tiff(np.full((200, 200), 255, np.uint8), dtype="uint8"))))
    assert imperviousness.analyse(10.0, 10.0, session=out)["status"] == "outside"
    imperviousness._cache.clear()
    bad = mock.Mock(get=mock.Mock(return_value=Reply(b'{"error": "x"}')))
    with pytest.raises(imperviousness.ImperviousnessUnavailable):
        imperviousness.analyse(1.0, 1.0, session=bad)


# ------------------------------------------------------------------ API

def test_endpoints_report_service_errors(monkeypatch):
    client = TestClient(main.app)
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    assert client.get("/api/v1/fires", params={"lat": 38, "lon": 15}).status_code == 503
    monkeypatch.setattr(water_cycle.requests, "get", mock.Mock(side_effect=water_cycle.requests.ConnectionError()))
    assert client.get("/api/v1/water-cycle", params={"lat": 41, "lon": 12}).status_code == 503
    assert client.get("/api/v1/sea", params={"lat": 41, "lon": 12}).status_code == 503
    assert client.get("/api/v1/sar/water", params={"lat": 41, "lon": 12, "reference": "week"}).status_code == 422
