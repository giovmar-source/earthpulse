
import unittest

import requests

from src import geocoding


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._payload


class FakeSession:
    """
    Simula requests senza usare la rete.
    responses: {url: (payload, status_code)}
    """

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        payload, status = self.responses[url]
        return FakeResponse(payload, status)


NOMINATIM_PAYLOAD = [{
    "name": "Salerno",
    "display_name": "Salerno, Campania, Italia",
    "lat": "40.6803",
    "lon": "14.7594",
    "type": "city",
    "category": "place",
}]

PHOTON_PAYLOAD = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [14.7594, 40.6803]},
        "properties": {
            "name": "Salerno",
            "county": "Salerno",
            "state": "Campania",
            "country": "Italia",
            "osm_key": "place",
            "osm_value": "city",
        },
    }],
}


class TestGeocoding(unittest.TestCase):

    def setUp(self):
        geocoding._cache.clear()
        geocoding._nominatim_blocked_until[0] = 0.0
        # Nessuna attesa tra le chiamate durante i test.
        self._interval = geocoding.MIN_INTERVAL_SECONDS
        geocoding.MIN_INTERVAL_SECONDS = 0.0

    def tearDown(self):
        geocoding.MIN_INTERVAL_SECONDS = self._interval
        geocoding._nominatim_blocked_until[0] = 0.0

    def test_nominatim_results_and_user_agent(self):
        session = FakeSession({geocoding.NOMINATIM_URL: (NOMINATIM_PAYLOAD, 200)})
        results = geocoding.search_places("Salerno", session=session)

        self.assertEqual(results[0]["name"], "Salerno")
        self.assertAlmostEqual(results[0]["latitude"], 40.6803)
        self.assertIn("EarthPulse", session.calls[0]["headers"]["User-Agent"])

    def test_cache_avoids_second_request(self):
        session = FakeSession({geocoding.NOMINATIM_URL: (NOMINATIM_PAYLOAD, 200)})
        geocoding.search_places("Salerno", session=session)
        geocoding.search_places("  salerno ", session=session)

        self.assertEqual(len(session.calls), 1)

    def test_short_query_rejected(self):
        with self.assertRaises(ValueError):
            geocoding.search_places(" a ", session=FakeSession({}))

    def test_fallback_to_photon_when_nominatim_blocks(self):
        session = FakeSession({
            geocoding.NOMINATIM_URL: ({}, 429),
            geocoding.PHOTON_URL: (PHOTON_PAYLOAD, 200),
        })
        results = geocoding.search_places("Salerno", session=session)

        self.assertEqual(results[0]["name"], "Salerno")
        # GeoJSON [lon, lat] convertito correttamente
        self.assertAlmostEqual(results[0]["latitude"], 40.6803)
        self.assertAlmostEqual(results[0]["longitude"], 14.7594)
        self.assertIn("Campania", results[0]["display_name"])

        # Dopo il rifiuto, la ricerca successiva salta Nominatim.
        geocoding.search_places("Napoli", session=session)
        urls = [call["url"] for call in session.calls]
        self.assertEqual(urls.count(geocoding.NOMINATIM_URL), 1)

    def test_nominatim_prefers_italian_then_english_names(self):
        payload = [dict(NOMINATIM_PAYLOAD[0], name="بغداد", display_name="Baghdad, Iraq",
                        namedetails={"name": "بغداد", "name:en": "Baghdad"})]
        session = FakeSession({geocoding.NOMINATIM_URL: (payload, 200)})
        results = geocoding.search_places("Baghdad", session=session)

        self.assertEqual(results[0]["name"], "Baghdad")
        self.assertEqual(session.calls[0]["params"]["namedetails"], 1)
        self.assertEqual(session.calls[0]["headers"]["Accept-Language"], "it,en;q=0.8")

    def test_photon_falls_back_to_english_language(self):
        class LangSession(FakeSession):
            def get(self, url, params=None, headers=None, timeout=None):
                self.calls.append({"url": url, "params": params, "headers": headers})
                if url == geocoding.NOMINATIM_URL:
                    return FakeResponse({}, 429)
                if params.get("lang") == "it":
                    return FakeResponse({"message": "language not supported"}, 400)
                return FakeResponse(PHOTON_PAYLOAD, 200)

        session = LangSession({})
        results = geocoding.search_places("Salerno", session=session)

        self.assertEqual(results[0]["name"], "Salerno")
        photon_langs = [c["params"]["lang"] for c in session.calls
                        if c["url"] == geocoding.PHOTON_URL]
        self.assertEqual(photon_langs, ["it", "en"])

    def test_both_services_down(self):
        session = FakeSession({
            geocoding.NOMINATIM_URL: ({}, 500),
            geocoding.PHOTON_URL: ({}, 503),
        })
        with self.assertRaises(geocoding.GeocodingUnavailable):
            geocoding.search_places("Salerno", session=session)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ------------------------------------------------------------------
# Geocoding inverso
# ------------------------------------------------------------------
from unittest import mock as _mock

from src import geocoding as _geo


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _geo.requests.HTTPError(str(self.status_code))


def test_reverse_place_uses_town_and_context():
    _geo._reverse_cache.clear()
    _geo._nominatim_blocked_until[0] = 0.0
    session = _mock.Mock()
    session.get.return_value = _Resp({"address": {"town": "Cava de' Tirreni", "state": "Campania",
                                                  "country": "Italia"}, "display_name": "Cava"})
    with _mock.patch.object(_geo, "MIN_INTERVAL_SECONDS", 0):
        place = _geo.reverse_place(40.70, 14.70, session=session)
        again = _geo.reverse_place(40.7001, 14.7002, session=session)
    assert place["name"] == "Cava de' Tirreni" and place["context"] == "Campania, Italia"
    assert again == place and session.get.call_count == 1      # cache a ~100 m


def test_reverse_place_open_sea_has_no_name():
    _geo._reverse_cache.clear()
    _geo._nominatim_blocked_until[0] = 0.0
    session = _mock.Mock()
    session.get.return_value = _Resp({"error": "Unable to geocode"})
    with _mock.patch.object(_geo, "MIN_INTERVAL_SECONDS", 0):
        assert _geo.reverse_place(38.0, 13.0, session=session)["name"] is None


def test_reverse_place_falls_back_to_photon():
    _geo._reverse_cache.clear()
    _geo._nominatim_blocked_until[0] = 0.0
    session = _mock.Mock()
    session.get.side_effect = [_Resp({}, status=429),
                               _Resp({"features": [{"properties": {"city": "Salerno", "country": "Italia"}}]})]
    with _mock.patch.object(_geo, "MIN_INTERVAL_SECONDS", 0):
        place = _geo.reverse_place(40.68, 14.77, session=session)
    assert place["name"] == "Salerno"
