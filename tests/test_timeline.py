
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import mock


def fake_item(item_id, day, cloud):
    assets = {k: SimpleNamespace(href=f"https://example.org/{item_id}/{k}.tif")
              for k in ("visual", "scl", "green", "red", "rededge1", "nir", "swir16", "swir22")}
    return SimpleNamespace(
        id=item_id,
        datetime=datetime.fromisoformat(day).replace(hour=10, tzinfo=timezone.utc),
        properties={"eo:cloud_cover": cloud},
        assets=assets,
    )


class TestSeasonKey(unittest.TestCase):

    def test_december_belongs_to_next_winter(self):
        from api.main import season_key
        self.assertEqual(season_key(date(2023, 12, 20)), (2024, "Inverno"))
        self.assertEqual(season_key(date(2024, 2, 10)), (2024, "Inverno"))
        self.assertEqual(season_key(date(2024, 7, 1)), (2024, "Estate"))
        self.assertEqual(season_key(date(2024, 11, 30)), (2024, "Autunno"))


class TestTimelineEndpoint(unittest.TestCase):

    def setUp(self):
        import api.main as api
        self.api = api
        api._TIMELINE_CACHE.clear()
        api._ITEM_CACHE.clear()

    def test_one_clear_scene_per_season(self):
        items = [
            # Estate 2024: la meno nuvolosa è coperta sull'area, la seconda è nitida
            fake_item("S2_20240705", "2024-07-05", 1.0),
            fake_item("S2_20240720", "2024-07-20", 5.0),
            # Inverno 2025 (dicembre 2024)
            fake_item("S2_20241215", "2024-12-15", 2.0),
            # Primavera 2025: nessuna scena abbastanza nitida
            fake_item("S2_20250410", "2025-04-10", 20.0),
        ]
        validity = {"S2_20240705": 60.0, "S2_20240720": 97.0,
                    "S2_20241215": 99.0, "S2_20250410": 40.0}

        calls = []

        def fake_search(bbox, start_date, end_date, max_cloud, max_items):
            calls.append((start_date, end_date))
            return [i for i in items if start_date <= i.datetime.date() <= end_date]

        with mock.patch.object(self.api, "search_sentinel_items", fake_search), \
                mock.patch.object(self.api, "scl_valid_percentage",
                                  lambda item, bbox: validity[item.id]):
            result = self.api.get_imagery_timeline(
                lat=40.81, lon=15.007, side_km=3.0, years=3, min_valid=90.0)

        labels = [s["label"] for s in result["scenes"]]
        self.assertEqual(labels, ["Estate 2024", "Inverno 2025"])
        self.assertEqual(result["scenes"][0]["item_id"], "S2_20240720")
        self.assertIn("ndmi", result["scenes"][0]["images"])

        # Ricerca a blocchi annuali, contigui e senza sovrapposizioni
        for (s1, e1), (s2, _e2) in zip(calls, calls[1:]):
            self.assertEqual((s2 - e1).days, 1)

        templates = result["pair_templates"]
        self.assertIn("item_id={after}&compare_id={before}", templates["diff"])
        self.assertIn("kind=dnbr", templates["dnbr"])
        self.assertIn("item_id={before}&compare_id={after}", templates["rgb_before"])

        # Seconda richiesta: dalla cache, nessuna nuova ricerca
        n = len(calls)
        with mock.patch.object(self.api, "search_sentinel_items", fake_search):
            self.api.get_imagery_timeline(lat=40.81, lon=15.007, side_km=3.0,
                                          years=3, min_valid=90.0)
        self.assertEqual(len(calls), n)


if __name__ == "__main__":
    unittest.main(verbosity=2)
