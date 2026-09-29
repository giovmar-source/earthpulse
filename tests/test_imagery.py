
import io
import shutil
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin
from rasterio.warp import transform

from api.main import make_bbox
from src.imagery import (
    INVALID_COLOR,
    Grid,
    choose_clear_scene,
    colorize_diff,
    colorize_ndvi,
    diff_on_grid,
    render_ndvi_png,
    render_rgb_png,
    scl_valid_percentage,
    stretch_rgb,
)


LAT, LON = 40.81, 15.007


def write_raster(path, data, transform_, crs="EPSG:32633"):
    """Scrive un GeoTIFF (bande, righe, colonne)."""
    if data.ndim == 2:
        data = data[np.newaxis, ...]
    with rasterio.open(
        path, "w", driver="GTiff",
        height=data.shape[1], width=data.shape[2], count=data.shape[0],
        dtype=data.dtype, crs=crs, transform=transform_,
    ) as dst:
        dst.write(data)


class SyntheticScene:
    """
    Scena sintetica di 6 × 6 km in UTM 33N centrata sul punto di prova:
    - B04/B08/visual a 10 m, SCL a 20 m;
    - vegetazione uniforme (NDVI ≈ 0.714);
    - una "nuvola" (SCL = 9) nell'angolo nord-ovest dell'area di 3 km.
    """

    def __init__(self, folder: Path, crs: str = "EPSG:32633",
                 nir_value: int = 3000):
        (x,), (y,) = transform("EPSG:4326", crs, [LON], [LAT])
        half = 3000
        west, north = x - half, y + half

        n10 = 600   # 6 km / 10 m
        n20 = 300   # 6 km / 20 m
        t10 = from_origin(west, north, 10, 10)
        t20 = from_origin(west, north, 20, 20)

        red = np.full((n10, n10), 500, dtype=np.uint16)
        nir = np.full((n10, n10), nir_value, dtype=np.uint16)
        scl = np.full((n20, n20), 4, dtype=np.uint8)       # 4 = vegetazione
        # Nuvola: 400 × 400 m nell'angolo NO dell'area centrale di 3 km
        # (la zona centrale inizia a 1500 m dal bordo = pixel 75 a 20 m).
        scl[75:95, 75:95] = 9

        visual = np.zeros((3, n10, n10), dtype=np.uint8)
        visual[0], visual[1], visual[2] = 40, 70, 35       # verde scuro

        self.hrefs = {}
        for name, data, tr in [
            ("red", red, t10), ("nir", nir, t10),
            ("scl", scl, t20), ("visual", visual, t10),
        ]:
            path = folder / f"{name}.tif"
            write_raster(path, data, tr, crs=crs)
            self.hrefs[name] = str(path)

    def item(self, item_id="S2_TEST_20250717", day="2025-07-17"):
        return SimpleNamespace(
            id=item_id,
            datetime=datetime.fromisoformat(day).replace(hour=10, tzinfo=timezone.utc),
            properties={"eo:cloud_cover": 3.0},
            assets={k: SimpleNamespace(href=v) for k, v in self.hrefs.items()},
        )


class TestRendering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.scene = SyntheticScene(cls.tmp)
        cls.bbox = make_bbox(LAT, LON, 3.0)
        cls.grid = Grid(LAT, LON, 3.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_ndvi_png_size_colors_and_cloud(self):
        png = render_ndvi_png(self.scene.item(), self.grid)
        image = np.array(Image.open(io.BytesIO(png)).convert("RGB"))

        # 3 km a 10 m = 300 pixel per lato, esatti (griglia comune)
        self.assertEqual(image.shape[:2], (300, 300))

        # Centro: vegetazione (verde) -> canale G dominante
        r, g, b = image[150, 150]
        self.assertGreater(int(g), int(r))
        self.assertGreater(int(g), int(b))

        # Angolo NO: nuvola -> grigio dei pixel non validi
        self.assertEqual(tuple(image[10, 10]), INVALID_COLOR)

    def test_rgb_png(self):
        png = render_rgb_png(self.scene.item(), self.grid)
        image = Image.open(io.BytesIO(png))
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (300, 300))

    def test_diff_aligns_scenes_from_different_projections(self):
        # "Prima": stessa area ma in UTM 34 e con NIR più basso.
        before_dir = self.tmp / "before"
        before_dir.mkdir(exist_ok=True)
        before = SyntheticScene(before_dir, crs="EPSG:32634", nir_value=1500)

        diff, valid = diff_on_grid(self.scene.item(), before.item(), self.grid)

        # NDVI dopo = (3000-500)/3500 = 0.714; prima = (1500-500)/2000 = 0.5
        self.assertEqual(diff.shape, (300, 300))
        self.assertAlmostEqual(float(np.nanmedian(diff)), 0.2143, places=3)
        # La nuvola (presente in entrambe) resta esclusa.
        self.assertFalse(valid[10, 10])
        self.assertTrue(valid[150, 150])

    def test_scl_valid_percentage_sees_cloud(self):
        pct = scl_valid_percentage(self.scene.item(), self.bbox)
        # nuvola ≈ 400×400 m su 3×3 km ≈ 1.8% dell'area
        self.assertLess(pct, 100.0)
        self.assertGreater(pct, 95.0)


class TestImageHelpers(unittest.TestCase):

    def test_colorize_known_values(self):
        ndvi = np.array([[0.85, np.nan]], dtype=np.float32)
        valid = np.array([[True, False]])
        image = colorize_ndvi(ndvi, valid)

        self.assertEqual(tuple(image[0, 0]), (24, 118, 52))
        self.assertEqual(tuple(image[0, 1]), INVALID_COLOR)

    def test_diff_colors(self):
        diff = np.array([[-0.30, 0.0, 0.30]], dtype=np.float32)
        image = colorize_diff(diff, np.array([[True, True, True]]))
        self.assertEqual(tuple(image[0, 0]), (140, 20, 30))   # calo: rosso
        self.assertEqual(tuple(image[0, 1]), (245, 245, 240)) # stabile
        self.assertEqual(tuple(image[0, 2]), (20, 110, 50))   # aumento: verde

    def test_rgb_stretch_is_fixed(self):
        # Lo stesso valore produce lo stesso colore in immagini diverse.
        a = np.full((3, 4, 4), 60, dtype=np.uint8)
        b = np.full((3, 4, 4), 60, dtype=np.uint8)
        b[:, 0, 0] = 250
        self.assertEqual(tuple(stretch_rgb(a)[2, 2]), tuple(stretch_rgb(b)[2, 2]))

    def test_stretch_keeps_nodata_black(self):
        rgb = np.zeros((3, 20, 20), dtype=np.uint8)
        rgb[:, :10, :] = np.arange(10, 210, 10, dtype=np.uint8)[np.newaxis, np.newaxis, :]
        out = stretch_rgb(rgb)
        self.assertEqual(out.shape, (20, 20, 3))
        self.assertEqual(tuple(out[15, 5]), (0, 0, 0))

    def test_choose_clear_scene(self):
        rows = [("a", 80.0, None), ("b", 97.0, None), ("c", None, "err")]
        self.assertEqual(choose_clear_scene(rows), ("b", 97.0))

        rows = [("a", 80.0, None), ("b", 75.0, None)]
        self.assertEqual(choose_clear_scene(rows), ("a", 80.0))

        rows = [("a", 50.0, None)]
        self.assertIsNone(choose_clear_scene(rows))


class TestImageryEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.scene = SyntheticScene(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_scenes_then_image(self):
        import api.main as api

        after_item = self.scene.item("S2_AFTER_20250717", "2025-07-17")
        before_item = self.scene.item("S2_BEFORE_20240715", "2024-07-15")

        def fake_search(bbox, start_date, end_date, max_cloud, max_items):
            return [after_item] if start_date.year == 2025 else [before_item]

        api._ITEM_CACHE.clear()
        api._PNG_CACHE.clear()

        with mock.patch.object(api, "search_sentinel_items", fake_search):
            result = api.get_imagery_scenes(
                lat=LAT, lon=LON, side_km=3.0,
                reference_date=date(2025, 7, 20),
                years_back=1, recent_days=60, window_days=30,
            )

        self.assertEqual(result["after"]["date"], "2025-07-17")
        self.assertEqual(result["before"]["date"], "2024-07-15")
        self.assertIn("kind=ndvi", result["after"]["images"]["ndvi"])
        self.assertIn("compare_id=S2_BEFORE_20240715", result["after"]["images"]["diff"])
        self.assertIn("2024", result["attribution"])

        # L'item è in cache: l'immagine non richiede il catalogo STAC.
        response = api.get_imagery_image(
            item_id="S2_AFTER_20250717",
            lat=LAT, lon=LON, side_km=3.0, kind="ndvi",
        )
        self.assertEqual(response.media_type, "image/png")
        self.assertTrue(response.body.startswith(b"\x89PNG"))

        diff = api.get_imagery_image(
            item_id="S2_AFTER_20250717", compare_id="S2_BEFORE_20240715",
            lat=LAT, lon=LON, side_km=3.0, kind="diff",
        )
        self.assertTrue(diff.body.startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
