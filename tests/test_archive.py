from datetime import date, datetime, timezone
from types import SimpleNamespace

import numpy as np

from src import archive


def item(item_id, day, platform, cloud):
    return SimpleNamespace(
        id=item_id,
        datetime=datetime.fromisoformat(day).replace(tzinfo=timezone.utc),
        properties={"platform": platform, "eo:cloud_cover": cloud},
    )


def test_group_by_year_prefers_summer_and_avoids_slc_off():
    items = [
        item("a", "1990-07-10", "landsat-5", 5.0),
        item("b", "1990-01-10", "landsat-5", 0.0),       # inverno: escluso
        item("c", "2010-08-01", "landsat-7", 0.0),       # L7 con strisce
        item("d", "2010-08-17", "landsat-5", 8.0),       # preferito a L7
        item("e", "2012-07-05", "landsat-7", 1.0),       # solo L7: tenuto
        item("f", "1983-07-01", "landsat-4", 1.0),       # prima del 1984
    ]
    years = archive.group_by_year(items, lat=40.0)
    assert list(years) == [1990, 2010, 2012]
    assert years[1990][0].id == "a"
    assert years[2010][0].id == "d"
    assert years[2012][0].id == "e"


def test_southern_hemisphere_season():
    assert archive.season_months(-33.0) == (12, 1, 2, 3)
    assert archive.season_year(date(2019, 12, 20), -33.0) == 2020
    assert archive.season_year(date(2019, 12, 20), 45.0) == 2019
    items = [item("x", "2019-12-20", "landsat-8", 2.0), item("y", "2020-07-01", "landsat-8", 0.0)]
    years = archive.group_by_year(items, lat=-33.0)
    assert list(years) == [2020] and years[2020][0].id == "x"


def test_reflectance_scale():
    dn = np.array([[0, 10000, 43636]], dtype=np.uint16)
    r = archive.reflectance(dn)
    assert np.isnan(r[0, 0])
    assert abs(r[0, 1] - 0.075) < 1e-6
    assert abs(r[0, 2] - 1.0) < 1e-3


def fake_scene(red, nir, valid=None):
    red = np.asarray(red, dtype=np.float32)
    nir = np.asarray(nir, dtype=np.float32)
    valid = np.ones(red.shape, bool) if valid is None else np.asarray(valid)
    rgb = np.stack([red, red, red])
    return archive.ArchiveScene("id", "2020-07-01", "landsat-8", rgb, red, nir,
                                valid, np.zeros(red.shape, bool), 100.0)


def test_ndvi_and_render():
    scene = fake_scene([[0.05, 0.1]], [[0.45, 0.1]], valid=[[True, False]])
    values = archive.ndvi(scene)
    assert abs(values[0, 0] - 0.8) < 1e-6
    assert np.isnan(values[0, 1])
    assert archive.render_rgb(scene)[:4] == b"\x89PNG"
    assert archive.render_ndvi(scene)[:4] == b"\x89PNG"
    assert scene.sensor == "Landsat 8 OLI"


def test_archive_endpoints_and_landsat_story(monkeypatch):
    from api import main

    candidates = {1990: [item("L5", "1990-07-10", "landsat-5", 1.0)],
                  2025: [item("L9", "2025-07-01", "landsat-9", 0.0)]}
    monkeypatch.setattr(archive, "archive_years", lambda lat, lon: candidates)

    def fake_scene_for_year(lat, lon, side, year):
        s = fake_scene([[0.05, 0.1]], [[0.45, 0.1]])
        s.date = f"{year}-07-10"
        s.platform = "landsat-5" if year < 2000 else "landsat-9"
        return s
    monkeypatch.setattr(archive, "scene_for_year", fake_scene_for_year)

    info = main.get_archive(lat=25.1, lon=55.13, side_km=12)
    assert info["years"] == [1990, 2025]
    assert info["sensors"]["1990"] == "Landsat 5 TM"
    assert "{year}" in info["image_template"] and "{kind}" in info["image_template"]
    assert [layer["key"] for layer in info["layers"]] == ["rgb", "ndvi"]

    png = main.get_archive_image(lat=25.1, lon=55.13, side_km=12, year=1990, kind="ndvi")
    assert png.body[:4] == b"\x89PNG"

    main._STORY_SCENES_CACHE.pop("dubai-1990-2025", None)
    story = main.get_story("dubai-1990-2025")
    assert story["before"]["date"] == "1990-07-10"
    assert story["after"]["sensor"] == "Landsat 9 OLI-2"
    assert "year=2025" in story["after"]["images"]["rgb"]
    assert story["event_label"] == "Dal 2001"
    main._STORY_SCENES_CACHE.pop("dubai-1990-2025", None)


def test_fill_gaps_removes_slc_off_stripes():
    red = np.full((6, 6), 0.1, dtype=np.float32)
    stripes = np.ones((6, 6), bool)
    stripes[::3, :] = False                              # righe vuote nel primo giorno
    a = fake_scene(red, red * 3, valid=stripes)
    other_valid = np.ones((6, 6), bool)
    other_valid[1, :] = False                            # vuoti in altri punti
    b = fake_scene(red * 1.1, red * 3, valid=other_valid)
    b.date = "2007-08-10"
    merged = archive.fill_gaps(a, b)
    assert merged.valid.all()
    assert merged.valid_pct == 100.0
    assert merged.filled_from == ["2007-08-10"]
    assert np.isclose(merged.red[0, 0], 0.11)            # preso dal secondo giorno
    assert np.isclose(merged.red[1, 0], 0.1)             # resta il primo


def test_white_point_adapts_only_for_bright_scenes():
    green_land = fake_scene(np.full((20, 20), 0.06), np.full((20, 20), 0.3))
    assert archive.white_point(green_land) == archive.RGB_WHITE
    sand = fake_scene(np.full((20, 20), 0.42), np.full((20, 20), 0.45))
    white = archive.white_point(sand)
    assert archive.RGB_WHITE < white <= archive.MAX_WHITE
    assert abs(white - 0.42) < 1e-3
