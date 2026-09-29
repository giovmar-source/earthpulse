
import unittest

from src import geocoding


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeSession:
    """Simula requests: registra le chiamate senza usare la rete."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return FakeResponse(self.payload)


PAYLOAD = [{
    "name": "Salerno",
    "display_name": "Salerno, Campania, Italia",
    "lat": "40.6803",
    "lon": "14.7594",
    "type": "city",
    "category": "place",
}]


class TestGeocoding(unittest.TestCase):

    def setUp(self):
        geocoding._cache.clear()
        # Nessuna attesa tra le chiamate durante i test.
        self._interval = geocoding.MIN_INTERVAL_SECONDS
        geocoding.MIN_INTERVAL_SECONDS = 0.0

    def tearDown(self):
        geocoding.MIN_INTERVAL_SECONDS = self._interval

    def test_parses_results_and_sends_user_agent(self):
        session = FakeSession(PAYLOAD)
        results = geocoding.search_places("Salerno", session=session)

        self.assertEqual(results[0]["name"], "Salerno")
        self.assertAlmostEqual(results[0]["latitude"], 40.6803)
        self.assertIn("EarthPulse", session.calls[0]["headers"]["User-Agent"])

    def test_cache_avoids_second_request(self):
        session = FakeSession(PAYLOAD)
        geocoding.search_places("Salerno", session=session)
        geocoding.search_places("  salerno ", session=session)

        self.assertEqual(len(session.calls), 1)

    def test_short_query_rejected(self):
        with self.assertRaises(ValueError):
            geocoding.search_places(" a ", session=FakeSession([]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
