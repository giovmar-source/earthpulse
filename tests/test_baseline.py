
import unittest

from src.baseline import add_seasonal_baseline


class TestSeasonalBaseline(unittest.TestCase):

    def test_baseline_uses_other_years(self):
        observations = [
            {"date": "2023-07-10", "ndvi_mean": 0.70},
            {"date": "2024-07-12", "ndvi_mean": 0.80},
            {"date": "2025-07-11", "ndvi_mean": 0.60},
            {"date": "2025-07-10", "ndvi_mean": 0.90},
        ]

        result = add_seasonal_baseline(
            observations,
            window_days=30,
            min_samples=2,
        )

        target = next(
            item for item in result
            if item["date"] == "2025-07-11"
        )

        # La baseline usa 2023 e 2024, non il 2025.
        self.assertAlmostEqual(
            target["baseline_ndvi"], 0.75
        )
        self.assertEqual(
            target["historical_observations"], 2
        )
        self.assertAlmostEqual(
            target["anomaly_percent"], -20.0
        )

    def test_insufficient_history_returns_no_baseline(self):
        observations = [
            {"date": "2024-07-10", "ndvi_mean": 0.80},
            {"date": "2025-07-10", "ndvi_mean": 0.60},
        ]

        result = add_seasonal_baseline(
            observations,
            min_samples=3,
        )

        target = next(
            item for item in result
            if item["date"] == "2025-07-10"
        )

        self.assertIsNone(target["baseline_ndvi"])
        self.assertIsNone(target["anomaly_percent"])
        self.assertEqual(
            target["historical_support"], "insufficiente"
        )

    def test_same_year_is_excluded(self):
        observations = [
            {"date": "2025-07-09", "ndvi_mean": 0.90},
            {"date": "2025-07-10", "ndvi_mean": 0.60},
        ]

        result = add_seasonal_baseline(
            observations,
            min_samples=1,
        )

        target = next(
            item for item in result
            if item["date"] == "2025-07-10"
        )

        self.assertIsNone(target["baseline_ndvi"])
        self.assertEqual(
            target["historical_observations"], 0
        )


if __name__ == "__main__":
    unittest.main()