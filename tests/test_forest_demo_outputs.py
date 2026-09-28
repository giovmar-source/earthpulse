
import json
import unittest
from pathlib import Path


# Cartella principale del repository EarthPulse
PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ANDROID_ASSETS_DIR = (
    PROJECT_ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "assets"
)


def load_json(path):
    """Carica un JSON e restituisce il contenuto."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class TestForestDemoOutputs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.summary_path = PROCESSED_DIR / "forest_demo.json"
        cls.series_path = (
            PROCESSED_DIR / "forest_demo_timeseries.json"
        )

        if not cls.summary_path.exists():
            raise FileNotFoundError(
                f"File non trovato: {cls.summary_path}"
            )

        if not cls.series_path.exists():
            raise FileNotFoundError(
                f"File non trovato: {cls.series_path}"
            )

        cls.summary = load_json(cls.summary_path)
        cls.series = load_json(cls.series_path)

    def test_summary_has_required_fields(self):
        required = [
            "place_id",
            "place_name",
            "indicator",
            "target_date",
            "comparison_date",
            "ndvi",
            "baseline_ndvi",
            "anomaly_percent",
            "data_source",
            "methodology",
        ]

        for field in required:
            with self.subTest(field=field):
                self.assertIn(field, self.summary)

    def test_indicator_is_ndvi(self):
        self.assertEqual(self.summary["indicator"], "NDVI")

    def test_summary_ndvi_values_are_valid(self):
        for field in ["ndvi", "baseline_ndvi"]:
            value = self.summary[field]

            self.assertIsInstance(value, (int, float))
            self.assertGreaterEqual(value, -1.0)
            self.assertLessEqual(value, 1.0)

    def test_timeseries_is_not_empty(self):
        observations = self.series["observations"]

        self.assertIsInstance(observations, list)
        self.assertGreater(len(observations), 0)

    def test_timeseries_dates_are_ordered(self):
        dates = [
            observation["date"]
            for observation in self.series["observations"]
        ]

        self.assertEqual(dates, sorted(dates))

    def test_timeseries_ndvi_values_are_valid(self):
        for observation in self.series["observations"]:
            with self.subTest(date=observation["date"]):
                value = observation["ndvi"]

                self.assertIsInstance(value, (int, float))
                self.assertGreaterEqual(value, -1.0)
                self.assertLessEqual(value, 1.0)

    def test_target_date_exists_in_timeseries(self):
        dates = {
            observation["date"]
            for observation in self.series["observations"]
        }

        self.assertIn(self.summary["target_date"], dates)

    def test_android_json_matches_python_json(self):
        android_summary_path = (
            ANDROID_ASSETS_DIR / "forest_demo.json"
        )
        android_series_path = (
            ANDROID_ASSETS_DIR / "forest_demo_timeseries.json"
        )

        self.assertTrue(
            android_summary_path.exists(),
            f"JSON Android non trovato: {android_summary_path}",
        )
        self.assertTrue(
            android_series_path.exists(),
            f"Serie Android non trovata: {android_series_path}",
        )

        android_summary = load_json(android_summary_path)
        android_series = load_json(android_series_path)

        self.assertEqual(android_summary, self.summary)
        self.assertEqual(android_series, self.series)


if __name__ == "__main__":
    unittest.main(verbosity=2)