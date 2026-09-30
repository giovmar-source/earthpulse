
import io
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

from src.imagery import Grid
from src.indices import (
    DEFAULT_LAYERS,
    LAYERS,
    change_on_grid,
    dnbr_severity_share,
    index_on_grid,
)
from tests.test_imagery import LAT, LON, SyntheticScene


class TestIndices(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        # Vegetazione sana: NIR 3000, rosso 500, verde 800, SWIR 1500 / 800
        cls.healthy = SyntheticScene(cls.tmp / "healthy")
        # Dopo un incendio: NIR basso, SWIR2 alto
        cls.burned = SyntheticScene(cls.tmp / "burned", nir_value=1200,
                                    swir16_value=2200, swir22_value=2000)
        cls.grid = Grid(LAT, LON, 3.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def median(self, key, scene=None):
        values, _ = index_on_grid((scene or self.healthy).item(), self.grid, key)
        return float(np.nanmedian(values))

    def test_index_values(self):
        self.assertAlmostEqual(self.median("ndvi"), (3000 - 500) / 3500, places=3)
        self.assertAlmostEqual(self.median("ndwi"), (800 - 3000) / 3800, places=3)
        self.assertAlmostEqual(self.median("ndmi"), (3000 - 1500) / 4500, places=3)
        self.assertAlmostEqual(self.median("ndbi"), (1500 - 3000) / 4500, places=3)
        self.assertAlmostEqual(self.median("nbr"), (3000 - 800) / 3800, places=3)

    def test_cloud_is_masked(self):
        _, valid = index_on_grid(self.healthy.item(), self.grid, "ndmi")
        self.assertFalse(valid[10, 10])      # nuvola sintetica nell'angolo NO
        self.assertTrue(valid[150, 150])

    def test_dnbr_positive_after_fire(self):
        dnbr, valid = change_on_grid(self.burned.item(), self.healthy.item(), self.grid, "nbr")
        expected = (3000 - 800) / 3800 - (1200 - 2000) / 3200
        self.assertAlmostEqual(float(np.nanmedian(dnbr)), expected, places=3)

        share = dnbr_severity_share(dnbr, valid)
        self.assertGreater(share["alta"], 95)

    def test_water_is_excluded_from_land_indices(self):
        lake = SyntheticScene(self.tmp / "lake", water_patch=True)
        grid = self.grid
        # Il centro della griglia (150,150) è dentro il lago sintetico.
        ndmi, valid = index_on_grid(lake.item(), grid, "ndmi")
        self.assertFalse(valid[150, 150])        # acqua: esclusa
        self.assertTrue(valid[60, 250])          # terraferma: valida

        # L'NDWI invece vale sull'acqua (ed è positivo).
        ndwi, valid_w = index_on_grid(lake.item(), grid, "ndwi")
        self.assertTrue(valid_w[150, 150])
        self.assertGreater(float(ndwi[150, 150]), 0)

        from src.indices import WATER_COLOR, render_index_png
        png = render_index_png(lake.item(), grid, "ndmi")
        image = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
        self.assertEqual(tuple(image[150, 150]), WATER_COLOR)

    def test_layers_metadata(self):
        for key in DEFAULT_LAYERS + ["dnbr"]:
            with self.subTest(layer=key):
                layer = LAYERS[key]
                self.assertIn(layer["mode"], ("compare", "single"))
                self.assertTrue(layer["caption"])
                if key != "rgb":
                    self.assertGreaterEqual(len(layer["color_stops"]), 2)
                    self.assertEqual(len(layer["legend_labels"]), 3)


class TestIndexEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.before = SyntheticScene(cls.tmp / "before")
        cls.after = SyntheticScene(cls.tmp / "after", nir_value=1200,
                                   swir16_value=2200, swir22_value=2000)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        import api.main as api
        self.api = api
        api._ITEM_CACHE.clear()
        api._PNG_CACHE.clear()
        api._STORY_SCENES_CACHE.clear()

    def test_scenes_list_layers_and_index_urls(self):
        after_item = self.after.item("S2_AFTER_20250717", "2025-07-17")
        before_item = self.before.item("S2_BEFORE_20240715", "2024-07-15")

        def fake_search(bbox, start_date, end_date, max_cloud, max_items):
            return [after_item] if start_date.year == 2025 else [before_item]

        with mock.patch.object(self.api, "search_sentinel_items", fake_search):
            result = self.api.get_imagery_scenes(
                lat=LAT, lon=LON, side_km=3.0, reference_date=date(2025, 7, 20),
                years_back=1, recent_days=60, window_days=30,
            )

        keys = [layer["key"] for layer in result["layers"]]
        self.assertEqual(keys, DEFAULT_LAYERS)
        self.assertIn("kind=index&index=ndmi", result["after"]["images"]["ndmi"])
        self.assertIn("ndwi", result["before"]["images"])
        self.assertNotIn("dnbr", result["after"]["images"])

        png = self.api.get_imagery_image(
            item_id="S2_AFTER_20250717", lat=LAT, lon=LON, side_km=3.0,
            kind="index", index="ndmi", compare_id=None,
        )
        image = Image.open(io.BytesIO(png.body))
        self.assertEqual(image.size, (300, 300))

        dnbr = self.api.get_imagery_image(
            item_id="S2_AFTER_20250717", compare_id="S2_BEFORE_20240715",
            lat=LAT, lon=LON, side_km=3.0, kind="dnbr", index=None,
        )
        self.assertTrue(dnbr.body.startswith(b"\x89PNG"))

    def test_index_requires_name(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.api.get_imagery_image(
                item_id="S2_AFTER_20250717", lat=LAT, lon=LON, side_km=3.0,
                kind="index", index=None, compare_id=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_montiferru_story_has_dnbr(self):
        import copy
        from src.stories import load_stories

        stories = copy.deepcopy(load_stories())
        items = {
            "B": self.before.item("S2_B_20210710", "2021-07-10"),
            "A": self.after.item("S2_A_20210821", "2021-08-21"),
        }
        for story in stories:
            story.pop("before_item_id", None)
            story.pop("after_item_id", None)

        def fake_find(bbox, start, end, target, max_candidates=6, min_valid=95.0):
            item = items["B"] if target.month == 7 else items["A"]
            return (item, 99.0), 1, 1

        with mock.patch.object(self.api, "load_stories", lambda: stories), \
                mock.patch.object(self.api, "find_clear_scene", fake_find):
            result = self.api.get_story("montiferru-2021")

        self.assertIn("dnbr", [layer["key"] for layer in result["layers"]])
        self.assertIn("kind=dnbr", result["after"]["images"]["dnbr"])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestNewIndices(unittest.TestCase):
    """NDRE, NDSI, NDCI, NDTI e superficie dell'acqua."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.lake = SyntheticScene(cls.tmp / "lake", water_patch=True)
        cls.grid = Grid(LAT, LON, 3.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_ndre_on_land(self):
        values, valid = index_on_grid(self.lake.item(), self.grid, "ndre")
        b05 = (500 + 3000) // 2
        self.assertAlmostEqual(float(np.nanmedian(values[valid])), (3000 - b05) / (3000 + b05), places=3)
        self.assertFalse(valid[150, 150])        # il lago al centro è escluso

    def test_water_quality_indices_only_on_water(self):
        for key in ("ndci", "ndti"):
            with self.subTest(index=key):
                _, valid = index_on_grid(self.lake.item(), self.grid, key)
                self.assertTrue(valid[150, 150])     # lago
                self.assertFalse(valid[40, 250])     # terraferma

    def test_ndsi_keeps_snow(self):
        from src import indices
        scl = np.full((4, 4), indices.SCL_SNOW, dtype=np.uint8)
        with mock.patch.object(indices, "read_on_grid", return_value=scl), \
                mock.patch.object(indices, "read_band",
                                  side_effect=lambda item, band, grid: np.full(
                                      (4, 4), 4000 if band == "B03" else 500, np.uint16)), \
                mock.patch.object(indices, "effective_offset", return_value=0):
            fake = mock.Mock()
            fake.assets = {"scl": mock.Mock(href="scl.tif")}
            values, valid = index_on_grid(fake, None, "ndsi")
        self.assertTrue(valid.all())
        self.assertAlmostEqual(float(values[0, 0]), 3500 / 4500, places=4)

    def test_water_area_counts_the_lake(self):
        from src.indices import water_area
        result = water_area(self.lake.item(), self.grid)
        self.assertAlmostEqual(result["water_ha"], 16.0, delta=2.0)   # 400 × 400 m = 16 ha
        self.assertAlmostEqual(result["area_ha"], 900.0, delta=1.0)

    def test_new_layers_listed(self):
        for key in ("ndre", "ndsi", "ndci", "ndti"):
            self.assertIn(key, DEFAULT_LAYERS)
            self.assertTrue(LAYERS[key]["color_stops"])
        self.assertEqual(LAYERS["ndwi"].get("stat"), "water")


class TestIndexStatEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.scene = SyntheticScene(cls.tmp / "s", water_patch=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_index_stat_median_over_area(self):
        from api import main
        item = self.scene.item()
        with mock.patch.object(main, "get_item_by_id", return_value=item):
            main._INDEX_STAT_CACHE.clear()
            ndvi = main.get_index_stat(item_id="S2A_TEST", lat=LAT, lon=LON,
                                       side_km=3.0, index="ndvi")
            ndci = main.get_index_stat(item_id="S2A_TEST", lat=LAT, lon=LON,
                                       side_km=3.0, index="ndci")
        self.assertAlmostEqual(ndvi["median"], (3000 - 500) / 3500, places=2)
        self.assertIsNotNone(ndci["median"])                 # c'è il lago
        self.assertLess(ndci["valid_percentage"], 10)        # solo l'acqua conta
