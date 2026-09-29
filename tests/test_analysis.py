
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest import mock

from src.analysis import (
    build_analysis,
    classify_anomaly,
    compute_many,
    freshness,
    historical_support,
    pick_baseline_candidates,
    pick_recent_candidates,
    seasonal_windows,
)


def fake_item(day: str, cloud: float, item_id: str | None = None):
    """Item STAC minimo, sufficiente per la logica di selezione."""
    return SimpleNamespace(
        id=item_id or f"S2_{day}_{cloud}",
        datetime=datetime.fromisoformat(day).replace(
            hour=10, tzinfo=timezone.utc
        ),
        properties={"eo:cloud_cover": cloud},
        assets={"red": None, "nir": None, "scl": None},
    )


def fake_result(day: str, ndvi: float, valid: float = 100.0):
    """Risultato nello stesso formato di calculate_ndvi_for_item."""
    return {
        "item_id": f"S2_{day}",
        "date": f"{day}T10:00:00Z",
        "cloud_cover_percent": 5.0,
        "ndvi_mean": ndvi,
        "ndvi_median": ndvi,
        "valid_pixels": 100,
        "area_pixels": 100,
        "valid_percentage": valid,
        "spatial_resolution_m": 10,
    }


class TestSelection(unittest.TestCase):

    def test_recent_candidates_newest_first_one_per_day(self):
        items = [
            fake_item("2025-07-01", 50),
            fake_item("2025-07-10", 30),
            fake_item("2025-07-10", 5),   # stesso giorno, meno nuvole
            fake_item("2025-07-05", 10),
        ]
        selected = pick_recent_candidates(items, max_candidates=2)

        self.assertEqual(
            [i.datetime.date().isoformat() for i in selected],
            ["2025-07-10", "2025-07-05"],
        )
        self.assertEqual(selected[0].properties["eo:cloud_cover"], 5)

    def test_baseline_candidates_limited_per_year(self):
        items = [
            fake_item("2023-07-01", 40),
            fake_item("2023-07-05", 1),
            fake_item("2023-07-09", 20),
            fake_item("2024-07-03", 10),
        ]
        selected = pick_baseline_candidates(items, per_year=2)
        days = [i.datetime.date().isoformat() for i in selected]

        # Per il 2023 le due scene con meno nuvole, ordinate per data.
        self.assertEqual(days, ["2023-07-05", "2023-07-09", "2024-07-03"])

    def test_seasonal_windows_same_period_previous_years(self):
        windows = seasonal_windows(date(2025, 7, 17), years_back=2, window_days=15)

        self.assertEqual(windows[0], (2024, date(2024, 7, 2), date(2024, 8, 1)))
        self.assertEqual(windows[1], (2023, date(2023, 7, 2), date(2023, 8, 1)))

    def test_seasonal_windows_leap_day(self):
        windows = seasonal_windows(date(2024, 2, 29), years_back=1, window_days=0)
        self.assertEqual(windows[0][1], date(2023, 2, 28))


class TestComputeMany(unittest.TestCase):

    def test_errors_are_captured_and_order_preserved(self):
        def compute(x):
            if x == 2:
                raise ValueError("boom")
            return x * 10

        rows = compute_many([1, 2, 3], compute)

        self.assertEqual([r[0] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0][1], 10)
        self.assertIsNone(rows[1][1])
        self.assertEqual(rows[1][2], "boom")


class TestInterpretation(unittest.TestCase):

    def test_historical_support_thresholds(self):
        self.assertEqual(historical_support(1), "insufficiente")
        self.assertEqual(historical_support(3), "limitato")
        self.assertEqual(historical_support(5), "buono")
        self.assertEqual(historical_support(6), "forte")

    def test_classification(self):
        self.assertEqual(
            classify_anomaly(-8.5, "forte", 0.87),
            "marcatamente sotto la baseline",
        )
        self.assertEqual(
            classify_anomaly(2.0, "buono", 0.8), "vicino alla baseline"
        )
        self.assertEqual(
            classify_anomaly(-30, "insufficiente", 0.8),
            "baseline poco supportata",
        )
        self.assertIn("vegetazione scarsa", classify_anomaly(-30, "forte", 0.15))

    def test_freshness(self):
        f = freshness(date(2025, 7, 1), date(2025, 7, 10))
        self.assertEqual(f["days_since_observation"], 9)
        self.assertTrue(f["is_recent"])
        self.assertFalse(freshness(date(2025, 5, 1), date(2025, 7, 10))["is_recent"])


class TestBuildAnalysis(unittest.TestCase):

    def test_full_analysis_uses_median(self):
        baseline = [
            fake_result("2023-07-15", 0.80),
            fake_result("2024-07-16", 0.90),
            fake_result("2022-07-14", 0.86),
            fake_result("2024-07-20", 0.10),  # valore anomalo: la mediana resiste
        ]
        result = build_analysis(
            recent_result=fake_result("2025-07-17", 0.79),
            baseline_results=baseline,
            reference_date=date(2025, 7, 20),
            window_days=15,
            min_baseline_samples=3,
        )

        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["baseline"]["ndvi_median"], 0.83)
        self.assertEqual(result["baseline"]["samples"], 4)
        self.assertEqual(result["baseline"]["support"], "buono")
        self.assertEqual(result["baseline"]["years"], [2022, 2023, 2024])
        self.assertAlmostEqual(result["comparison"]["delta_ndvi"], -0.04)
        self.assertTrue(result["comparison"]["percent_meaningful"])
        self.assertTrue(result["latest_observation"]["is_recent"])
        self.assertEqual(result["latest_observation"]["date"], "2025-07-17")

    def test_stale_observation_is_flagged(self):
        result = build_analysis(
            recent_result=fake_result("2025-05-01", 0.7),
            baseline_results=[],
            reference_date=date(2025, 7, 20),
            window_days=15,
            min_baseline_samples=3,
        )
        self.assertEqual(result["status"], "no_baseline")
        self.assertFalse(result["latest_observation"]["is_recent"])
        self.assertTrue(any("attuale" in m for m in result["messages"]))

    def test_no_recent_observation(self):
        result = build_analysis(
            recent_result=None,
            baseline_results=[fake_result("2024-07-10", 0.8)] * 3,
            reference_date=date(2025, 7, 20),
            window_days=15,
            min_baseline_samples=3,
        )
        self.assertEqual(result["status"], "no_recent_observation")
        self.assertIsNone(result["latest_observation"])
        self.assertIsNone(result["comparison"]["anomaly_percent"])

    def test_low_ndvi_percent_not_meaningful(self):
        result = build_analysis(
            recent_result=fake_result("2025-07-17", 0.10),
            baseline_results=[
                fake_result("2024-07-10", 0.16),
                fake_result("2023-07-10", 0.17),
                fake_result("2022-07-10", 0.15),
            ],
            reference_date=date(2025, 7, 20),
            window_days=15,
            min_baseline_samples=3,
        )
        self.assertFalse(result["comparison"]["percent_meaningful"])


class TestAnalysisEndpoint(unittest.TestCase):
    """Endpoint completo con catalogo e calcolo NDVI simulati (offline)."""

    def test_endpoint_with_mocked_data(self):
        import api.main as api

        recent = [fake_item("2025-07-17", 5), fake_item("2025-07-12", 50)]
        historical = {
            2024: [fake_item("2024-07-15", 3)],
            2023: [fake_item("2023-07-18", 2)],
            2022: [fake_item("2022-07-16", 8)],
        }

        def fake_search(bbox, start_date, end_date, max_cloud, max_items):
            if start_date.year == 2025:
                return recent
            return historical[start_date.year]

        ndvi_by_day = {
            "2025-07-17": (0.79, 95.0),
            "2025-07-12": (0.85, 40.0),   # scartata: pochi pixel validi
            "2024-07-15": (0.88, 100.0),
            "2023-07-18": (0.86, 100.0),
            "2022-07-16": (0.87, 100.0),
        }

        def fake_calc(item, bbox):
            day = item.datetime.date().isoformat()
            ndvi, valid = ndvi_by_day[day]
            return fake_result(day, ndvi, valid)

        with mock.patch.object(api, "search_sentinel_items", fake_search), \
                mock.patch.object(api, "calculate_ndvi_for_item", fake_calc):
            response = api.get_ndvi_analysis(
                lat=40.81, lon=15.007, side_km=1.0,
                reference_date=date(2025, 7, 20),
                recent_days=45, recent_candidates=4,
                baseline_years=3, baseline_window_days=15,
                baseline_per_year=3, min_baseline_samples=3,
                max_cloud=60.0, min_valid_percentage=70.0,
            )

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["latest_observation"]["date"], "2025-07-17")
        self.assertAlmostEqual(response["baseline"]["ndvi_median"], 0.87)
        self.assertEqual(response["quality"]["recent_scenes_evaluated"], 2)
        self.assertEqual(response["quality"]["recent_scenes_rejected_quality"], 1)
        self.assertEqual(response["baseline"]["samples"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
