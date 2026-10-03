import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_alerts", Path(__file__).resolve().parent.parent / "scripts" / "run_alerts.py")
run_alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_alerts)

ALERT = {"kind": "fires", "radius_km": 25, "threshold": None, "place_name": "Bosco", "lat": 40.0, "lon": 15.0}


def test_fire_alert_found_and_quiet():
    hit = lambda lat, lon, r, d: {"count": 2, "nearest_km": 4.2, "points": [
        {"date": "2026-10-03", "time_utc": "01:10", "confidence": "nominale"}]}
    found = run_alerts.evaluate(ALERT, fire_check=hit)
    assert found["fingerprint"] == "fires:2026-10-03:01:10" and "2 punti di calore" in found["subject"]
    quiet = lambda lat, lon, r, d: {"count": 0, "nearest_km": None, "points": []}
    assert run_alerts.evaluate(ALERT, fire_check=quiet) is None


def test_water_alert_uses_threshold():
    alert = {**ALERT, "kind": "new_water", "threshold": 10}
    small = lambda lat, lon, ref: {"status": "ok", "stats": {"new": 6.0}, "acquired": {"now": "2026-10-02T05:00:00Z"}}
    big = lambda lat, lon, ref: {"status": "ok", "stats": {"new": 42.0}, "acquired": {"now": "2026-10-02T05:00:00Z"}}
    assert run_alerts.evaluate(alert, water_check=small) is None
    assert run_alerts.evaluate(alert, water_check=big)["fingerprint"] == "water:2026-10-02T05:00:00Z"


def test_main_does_nothing_without_configuration(monkeypatch, capsys):
    for name in ("SUPABASE_DB_URL", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_FROM"):
        monkeypatch.delenv(name, raising=False)
    assert run_alerts.main() == 0 and "non attivi" in capsys.readouterr().out
