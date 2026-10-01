from unittest import mock

from src import orbits

# TLE di esempio nel formato CelesTrak (Sentinel-2B, valori illustrativi)
SAMPLE = """SENTINEL-2B
1 42063U 17013A   26273.50000000  .00000100  00000-0  50000-4 0  9990
2 42063  98.5600 340.0000 0001000  90.0000 270.0000 14.30820000 99990
"""


def test_parse_tle():
    line1, line2 = orbits.parse_tle(SAMPLE)
    assert line1.startswith("1 42063U") and len(line1) == 69
    assert line2.startswith("2 42063") and len(line2) == 69
    assert orbits.parse_tle("errore") is None


def test_satellites_with_tle_uses_cache_and_keeps_old_on_failure():
    orbits._cache.update({"time": 0.0, "data": []})
    with mock.patch.object(orbits, "fetch_tle", return_value=orbits.parse_tle(SAMPLE)) as fetch, \
            mock.patch.object(orbits, "fetch_tle_backup") as backup:
        first = orbits.satellites_with_tle()
        again = orbits.satellites_with_tle()
    assert len(first) == len(orbits.SATELLITES)
    assert fetch.call_count == len(orbits.SATELLITES)     # la seconda volta usa la cache
    assert again is first
    backup.assert_not_called()

    def boom(norad):
        raise orbits.requests.ConnectionError("giù")
    with mock.patch.object(orbits, "fetch_tle", side_effect=boom), \
            mock.patch.object(orbits, "fetch_tle_backup", side_effect=boom):
        kept = orbits.satellites_with_tle(force=True)
    assert len(kept) == len(orbits.SATELLITES)             # elementi precedenti tenuti
    orbits._cache.update({"time": 0.0, "data": []})


def test_backup_source_and_saved_copy():
    orbits._cache.update({"time": 0.0, "data": []})

    def down(norad):
        raise orbits.requests.ConnectionError("rifiutato")

    # CelesTrak giù, la fonte di riserva risponde
    with mock.patch.object(orbits, "fetch_tle", side_effect=down), \
            mock.patch.object(orbits, "fetch_tle_backup", return_value=orbits.parse_tle(SAMPLE)):
        sats = orbits.satellites_with_tle(force=True)
    assert {s["source"] for s in sats} == {"TLE API"}

    # Tutte le fonti online giù e nessuna memoria: si usa la copia salvata
    orbits._cache.update({"time": 0.0, "data": []})
    with mock.patch.object(orbits, "fetch_tle", side_effect=down), \
            mock.patch.object(orbits, "fetch_tle_backup", side_effect=down):
        sats = orbits.satellites_with_tle(force=True)
    assert len(sats) == len(orbits.SATELLITES)
    assert {s["source"] for s in sats} == {"copia salvata"}
    orbits._cache.update({"time": 0.0, "data": []})


def test_epoch_age_days():
    line1 = "1 42063U 17013A   26273.94177341 -.00000063  00000+0 -74071-5 0  9997"
    from datetime import datetime, timezone
    now = datetime(2026, 10, 1, 22, 36, tzinfo=timezone.utc).timestamp()
    assert abs(orbits.epoch_age_days(line1, now) - 1.0) < 0.1
