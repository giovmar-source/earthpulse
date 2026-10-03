import io
from datetime import datetime
from unittest import mock

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from api import main
from src import fci


def png_with_points(points, size=32):
    image = np.zeros((size, size, 4), dtype=np.uint8)
    for r, c in points:
        image[r, c] = (200, 10, 10, 255)
    buffer = io.BytesIO()
    Image.fromarray(image, mode="RGBA").save(buffer, format="PNG")
    return buffer.getvalue()


def decode(png):
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))


def test_recolor_uses_single_color_and_counts_pixels():
    out, count = fci.recolor(png_with_points([(5, 5), (10, 12)]), "rain")
    image = decode(out)
    assert count == 2
    assert tuple(image[5, 5, :3]) == fci.PRODUCTS["rain"]["color"]
    assert image[0, 0, 3] == 0                         # niente dati: trasparente


def test_fires_are_enlarged():
    out, count = fci.recolor(png_with_points([(16, 16)]), "fires")
    image = decode(out)
    assert count == 1
    assert image[16, 18, 3] > 0 and image[16, 19, 3] == 0   # allargato di 2 pixel


def test_overlay_is_cached():
    session = mock.Mock()
    session.get.return_value = mock.Mock(status_code=200, headers={"Content-Type": "image/png"},
                                         content=png_with_points([(1, 1)]))
    fci._cache.clear()
    when = datetime(2026, 10, 1, 12, 0)
    first = fci.overlay("lightning", [10, 40, 16, 46], when, 32, session=session)
    second = fci.overlay("lightning", [10, 40, 16, 46], when, 32, session=session)
    assert first == second and session.get.call_count == 1
    assert session.get.call_args.kwargs["params"]["time"] == "2026-10-01T12:00:00Z"


def test_endpoint_returns_png_and_pixel_header():
    with mock.patch.object(fci, "overlay", return_value=(b"\x89PNG", 7)):
        response = TestClient(main.app).get("/api/v1/fci/overlay", params={
            "product": "fires", "bbox": "10.5,37.7,19.0,43.7", "time": "2026-10-01T12:00Z"})
    assert response.status_code == 200
    assert response.headers["x-data-pixels"] == "7"


def test_endpoint_rejects_bad_area():
    response = TestClient(main.app).get("/api/v1/fci/overlay", params={
        "product": "rain", "bbox": "10,40,5,45", "time": "2026-10-01T12:00Z"})
    assert response.status_code == 400


def test_commercial_delay_blocks_recent_images(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from fastapi.testclient import TestClient
    import api.main as main
    from src import fci
    monkeypatch.setenv("EUMETSAT_DELAY_MINUTES", "60")
    recent = datetime.now(timezone.utc) - timedelta(minutes=30)
    old = datetime.now(timezone.utc) - timedelta(minutes=90)
    assert not fci.allowed_time(recent) and fci.allowed_time(old)
    response = TestClient(main.app).get("/api/v1/fci/overlay", params={
        "product": "fires", "bbox": "10,40,12,42", "time": recent.strftime("%Y-%m-%dT%H:%MZ")})
    assert response.status_code == 403
    monkeypatch.setenv("EUMETSAT_DELAY_MINUTES", "0")
    assert fci.allowed_time(recent)


def test_air_quality_uses_commercial_endpoint_with_key(monkeypatch):
    from unittest import mock
    from src import air_quality
    air_quality._cache.clear()
    reply = mock.Mock(status_code=200, content=b"{}")
    reply.json.return_value = {"current": {"european_aqi": 20}}
    http = mock.Mock(get=mock.Mock(return_value=reply))
    monkeypatch.delenv("OPENMETEO_API_KEY", raising=False)
    air_quality.fetch({"latitude": 41.9, "longitude": 12.5, "current": "european_aqi", "evil": "x"}, http)
    assert http.get.call_args.args[0] == air_quality.FREE_URL and "evil" not in http.get.call_args.kwargs["params"]
    monkeypatch.setenv("OPENMETEO_API_KEY", "secret")
    air_quality._cache.clear()
    air_quality.fetch({"latitude": 41.9, "longitude": 12.5, "current": "european_aqi"}, http)
    assert http.get.call_args.args[0] == air_quality.COMMERCIAL_URL
    assert http.get.call_args.kwargs["params"]["apikey"] == "secret"
