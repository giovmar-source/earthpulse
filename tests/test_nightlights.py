import io
import re

import numpy as np
import pytest

h5py = pytest.importorskip("h5py")

from src import nightlights as nl


# ------------------------------------------------------------------
# Geometria
# ------------------------------------------------------------------

def test_tile_for_point_matches_black_marble_grid():
    # Napoli: lon 10-20, lat 40-50 -> h19v04 (tile verificato su CMR)
    assert nl.tile_for_point(40.85, 14.27) == (19, 4)
    assert nl.tile_for_point(89.9, -179.9) == (0, 0)
    assert nl.tile_for_point(-89.9, 179.9) == (35, 17)
    # Giappone (Noto): lon 130-140, lat 30-40 -> h31v05
    assert nl.tile_for_point(37.35, 136.75) == (31, 5)


def test_area_bbox_is_square_in_km():
    west, south, east, north = nl.area_bbox(60.0, 10.0, 60)
    lat_km = (north - south) * nl.KM_PER_DEGREE_LAT
    lon_km = (east - west) * nl.KM_PER_DEGREE_LAT * np.cos(np.radians(60.0))
    assert lat_km == pytest.approx(60, rel=1e-6)
    assert lon_km == pytest.approx(60, rel=1e-6)


def test_global_window_pixel_size():
    window = nl.global_window((14.0, 40.5, 14.5, 41.0))
    assert window.shape == (120, 120)       # 0.5 gradi = 120 pixel da 15"
    assert window.col0 == (14.0 + 180) * 240
    assert window.row0 == (90 - 41.0) * 240


def test_tile_pieces_single_tile():
    window = nl.global_window((14.0, 40.5, 14.5, 41.0))
    pieces = nl.tile_pieces(window)
    assert len(pieces) == 1
    h, v, tile_rows, tile_cols, out_rows, out_cols = pieces[0]
    assert (h, v) == (19, 4)
    # lat 41 e' a 1 grado dal bordo sud (40) -> 9 gradi dal bordo nord (50)
    assert tile_rows.start == (50 - 41.0) * 240
    assert tile_cols.start == (14.0 - 10) * 240
    assert out_rows == slice(0, 120) and out_cols == slice(0, 120)


def test_tile_pieces_cross_tile_corner():
    # Area a cavallo di lon 20 e lat 40: quattro tile.
    window = nl.global_window((19.8, 39.8, 20.2, 40.2))
    pieces = nl.tile_pieces(window)
    tiles = sorted((h, v) for h, v, *_ in pieces)
    assert tiles == [(19, 4), (19, 5), (20, 4), (20, 5)]
    covered = np.zeros(window.shape, dtype=int)
    for *_, out_rows, out_cols in pieces:
        covered[out_rows, out_cols] += 1
    assert (covered == 1).all()


def test_tile_pieces_across_antimeridian():
    window = nl.global_window((179.8, -17.2, 180.2, -16.8))
    tiles = sorted((h, v) for h, v, *_ in nl.tile_pieces(window))
    assert tiles == [(0, 10), (35, 10)]


# ------------------------------------------------------------------
# Ricerca file (CMR)
# ------------------------------------------------------------------

def test_parse_granule_name():
    parsed = nl.parse_granule_name(
        "VNP46A4.A2014001.h19v04.002.2025090174551.h5")
    assert parsed == (2014, "h19v04", "2025090174551")
    assert nl.parse_granule_name("VNP46A4.A2014001.h19v04.002.x.h5.html") is None


def test_pick_granule_urls_filters_and_keeps_latest():
    base = "https://data.laadsdaac.earthdatacloud.nasa.gov/prod-lads/VNP46A4/"
    entries = [
        {"links": [
            {"href": base + "VNP46A4.A2014001.h19v04.002.2025090174551.h5"},
            {"href": "s3://prod-lads/VNP46A4/VNP46A4.A2014001.h19v04.002.2025090174551.h5"},
            {"href": "https://ladsweb.modaps.eosdis.nasa.gov/opendap/x/"
                     "VNP46A4.A2014001.h19v04.002.2025090174551.h5.html"},
        ]},
        {"links": [{"href": base + "VNP46A4.A2014001.h19v04.002.2026001000000.h5"}]},
        {"links": [{"href": base + "VNP46A4.A2015001.h20v04.002.2025090174551.h5"}]},
        {"links": [{"href": base + "VNP46A4.A2012001.h19v04.002.2025086172036.h5"}]},
    ]
    urls = nl.pick_granule_urls(entries, "h19v04")
    assert list(urls) == [2012, 2014]
    assert urls[2014].endswith("2026001000000.h5")


# ------------------------------------------------------------------
# Lettura remota a blocchi (server finto)
# ------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status, content=b"", headers=None, url=""):
        self.status_code = status
        self.content = content
        self.headers = headers or {}
        self.url = url

    def close(self):
        pass


class FakeRangeSession:
    """Serve un file in memoria rispettando l'header Range."""

    def __init__(self, payload: bytes, url="https://example.test/file.h5"):
        self.payload = payload
        self.url = url
        self.headers = {}
        self.calls = 0

    def get(self, url, headers=None, **kwargs):
        self.calls += 1
        match = re.match(r"bytes=(\d+)-(\d+)", (headers or {}).get("Range", ""))
        if not match:
            return FakeResponse(200, self.payload, url=self.url)
        start, end = int(match.group(1)), int(match.group(2))
        end = min(end, len(self.payload) - 1)
        return FakeResponse(
            206, self.payload[start:end + 1],
            {"Content-Range": f"bytes {start}-{end}/{len(self.payload)}"},
            url=self.url,
        )


def test_http_range_file_reads_like_a_file():
    payload = bytes(range(256)) * 5000         # 1.28 MB
    remote = nl.HttpRangeFile("https://example.test/file.h5",
                              FakeRangeSession(payload), block_size=4096)
    assert remote.size == len(payload)
    remote.seek(10_000)
    assert remote.read(50) == payload[10_000:10_050]
    remote.seek(-100, io.SEEK_END)
    assert remote.read() == payload[-100:]
    assert remote.bytes_downloaded < len(payload) // 10


def make_black_marble_h5(values, quality=None, land_water=None, fill=-999.9,
                         chunks=(2, 2)):
    buffer = io.BytesIO()
    with h5py.File(buffer, "w") as h5file:
        group = h5file.create_group(nl.GRID_PATH)
        dataset = group.create_dataset(
            nl.VARIABLE, data=np.asarray(values, dtype=np.float32),
            chunks=chunks, compression="gzip")
        dataset.attrs["_FillValue"] = np.float32(fill)
        if quality is not None:
            group.create_dataset(nl.QUALITY_VARIABLE,
                                 data=np.asarray(quality, dtype=np.uint8),
                                 chunks=chunks, compression="gzip")
        if land_water is not None:
            group.create_dataset(nl.LAND_WATER_VARIABLE,
                                 data=np.asarray(land_water, dtype=np.uint8),
                                 chunks=chunks, compression="gzip")
    return buffer.getvalue()


def test_read_tile_window_masks_fill_and_quality():
    values = [[1.0, 2.0, -999.9, 4.0],
              [5.0, 6.0, 7.0, 8.0]]
    quality = [[0, 0, 0, 255],
               [0, 1, 0, 0]]
    land_water = [[1, 1, 3, 3],
                  [1, 2, 3, 5]]
    payload = make_black_marble_h5(values, quality, land_water)
    remote = nl.HttpRangeFile("https://example.test/f.h5",
                              FakeRangeSession(payload), block_size=1024)
    with h5py.File(remote, "r") as h5file:
        scene = nl.read_tile_window(h5file, slice(0, 2), slice(1, 4), remote)
    data = scene.radiance
    # Solo il codice 3 (Sea Water) e' mare; 2 (acque interne) e 5 (costa) no.
    np.testing.assert_array_equal(scene.sea, [[False, True, True],
                                              [False, True, False]])
    expected = np.array([[2.0, np.nan, np.nan],
                         [6.0, 7.0, 8.0]], dtype=np.float32)
    np.testing.assert_array_equal(np.isnan(data), np.isnan(expected))
    np.testing.assert_allclose(data[~np.isnan(data)], expected[~np.isnan(expected)])


def test_prefetch_downloads_chunks_in_few_requests():
    rng = np.random.default_rng(1)
    values = rng.gamma(0.5, 5, (240, 480)).astype(np.float32)
    payload = make_black_marble_h5(values, np.zeros((240, 480)),
                                   np.ones((240, 480)), chunks=(30, 480))
    session = FakeRangeSession(payload)
    remote = nl.HttpRangeFile("https://example.test/f.h5", session,
                              block_size=4096)
    with h5py.File(remote, "r") as h5file:
        fields = h5file[nl.GRID_PATH]
        ranges = nl.chunk_byte_ranges(fields[nl.VARIABLE],
                                      slice(40, 100), slice(10, 50))
        assert len(ranges) == 3            # righe 30-60, 60-90, 90-120
        scene = nl.read_tile_window(h5file, slice(40, 100), slice(10, 50), remote)
    np.testing.assert_allclose(scene.radiance, values[40:100, 10:50], rtol=1e-6)
    assert remote.bytes_downloaded < len(payload)


def test_make_session_requires_credentials(monkeypatch):
    for name in ("EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    assert not nl.has_credentials()
    with pytest.raises(nl.NightLightsUnavailable):
        nl.make_session()
    monkeypatch.setenv("EARTHDATA_TOKEN", "abc")
    session = nl.make_session()
    assert session.headers["Authorization"] == "Bearer abc"


# ------------------------------------------------------------------
# Immagine e numeri
# ------------------------------------------------------------------

def test_render_radiance_png_is_square():
    radiance = np.full((40, 60), 5.0, dtype=np.float32)
    radiance[0, 0] = np.nan
    sea = np.zeros((40, 60), dtype=bool)
    sea[30:] = True
    png = nl.render_radiance_png(nl.NightScene(radiance, sea), size=120)
    from PIL import Image
    picture = Image.open(io.BytesIO(png))
    assert picture.size == (120, 120)


def test_colorize_radiance_dark_to_bright():
    radiance = np.array([[0.1, 1.0, 10.0, 200.0]], dtype=np.float32)
    image = nl.colorize_radiance(radiance, np.ones_like(radiance, dtype=bool))
    brightness = image.astype(int).sum(axis=-1)[0]
    assert list(brightness) == sorted(brightness)


def test_dark_sea_is_flat_but_bright_ships_remain():
    radiance = np.array([[0.5, 1.5, 40.0]], dtype=np.float32)
    sea = np.array([[True, True, True]])
    image = nl.colorize_radiance(radiance, np.ones_like(sea), sea)
    assert tuple(image[0, 0]) == nl.NIGHT_SEA_COLOR
    assert tuple(image[0, 1]) == nl.NIGHT_SEA_COLOR
    assert tuple(image[0, 2]) != nl.NIGHT_SEA_COLOR


def test_light_summary_and_change():
    radiance = np.array([[0.5, 2.0, 99.0], [np.nan, 10.0, 99.0]], dtype=np.float32)
    sea = np.array([[False, False, True], [False, False, True]])
    summary = nl.light_summary(nl.NightScene(radiance, sea))   # mare escluso
    assert summary["valid_percentage"] == 75.0
    assert summary["total_radiance"] == 12.5
    assert summary["lit_percentage"] == pytest.approx(66.7, abs=0.1)
    assert nl.percent_change(100.0, 120.0) == 20.0
    assert nl.percent_change(0.0, 5.0) is None


# ------------------------------------------------------------------
# Endpoint (senza rete: dati finti)
# ------------------------------------------------------------------

def fake_scene(level):
    radiance = np.full((20, 20), level, dtype=np.float32)
    sea = np.zeros((20, 20), dtype=bool)
    sea[15:] = True
    return nl.NightScene(radiance, sea)


def test_nightlights_endpoints(monkeypatch):
    from api import main

    monkeypatch.setenv("EARTHDATA_TOKEN", "test")
    monkeypatch.setattr(nl, "available_years", lambda lat, lon: [2012, 2018, 2025])
    monkeypatch.setattr(
        nl, "night_scene_for_area",
        lambda lat, lon, side, year, **kw: fake_scene(10.0 if year == 2012 else 12.0))

    info = main.get_nightlights(lat=40.85, lon=14.27, side_km=60)
    assert info["years"] == [2012, 2018, 2025]
    assert info["default_before"] == 2012 and info["default_after"] == 2025
    assert "{year}" in info["image_template"]
    assert "{before}" in info["compare_template"]

    response = main.get_nightlights_image(lat=40.85, lon=14.27, side_km=60, year=2012)
    assert response.media_type == "image/png"
    assert response.body[:8] == b"\x89PNG\r\n\x1a\n"

    result = main.compare_nightlights(lat=40.85, lon=14.27, side_km=60,
                                      before=2012, after=2025)
    assert result["total_change_percent"] == 20.0
    assert "aumentata del 20%" in result["message"]


def test_nightlights_without_credentials_is_503(monkeypatch):
    from fastapi import HTTPException
    from api import main

    for name in ("EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(HTTPException) as error:
        main.get_nightlights(lat=40.85, lon=14.27, side_km=60)
    assert error.value.status_code == 503


def test_describe_light_change():
    from api.main import describe_light_change
    assert "quasi invariata" in describe_light_change(2012, 2025, 3.0)
    assert "diminuita del 12%" in describe_light_change(2012, 2025, -12.0)
