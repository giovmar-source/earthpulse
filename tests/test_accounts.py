"""Account (token Supabase), limiti dei piani e webhook dei pagamenti (Paddle)."""
import hashlib
import hmac
import json
import time
from unittest import mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import api.main as main
from src import accounts, billing


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    for name in ("SUPABASE_URL", "SUPABASE_DB_URL", "PLANS_ENFORCED", "PADDLE_WEBHOOK_SECRET"):
        monkeypatch.delenv(name, raising=False)
    accounts.memory.events.clear()
    accounts._jwks_client = None
    yield
    accounts._jwks_client = None


KEY = ec.generate_private_key(ec.SECP256R1())


def token(sub="11111111-2222-3333-4444-555555555555", exp_in=3600, aud="authenticated"):
    return jwt.encode({"sub": sub, "email": "prof@uni.it", "aud": aud, "role": "authenticated",
                       "exp": int(time.time()) + exp_in}, KEY, algorithm="ES256")


def fake_jwks(monkeypatch):
    signing = mock.Mock(key=KEY.public_key())
    client = mock.Mock(get_signing_key_from_jwt=mock.Mock(return_value=signing))
    monkeypatch.setattr(accounts, "_jwks", lambda: client)


def test_everything_off_by_default():
    client = TestClient(main.app)
    me = client.get("/api/v1/me").json()
    assert me["accounts_enabled"] is False and me["enforced"] is False and me["plan"] == "anonymous"
    plans = client.get("/api/v1/plans").json()
    assert [p["key"] for p in plans["plans"]] == ["free", "pro", "institutional"]
    assert plans["payments_enabled"] is False


def test_valid_and_invalid_tokens(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    fake_jwks(monkeypatch)
    client = TestClient(main.app)
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token()}"}).json()
    assert me["user"]["email"] == "prof@uni.it" and me["plan"] == "free" and me["limits"]["saved_places"] == 3
    expired = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token(exp_in=-10)}"})
    wrong_aud = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token(aud='anon')}"})
    assert expired.status_code == 401 and wrong_aud.status_code == 401


def test_anonymous_limit_counts_distinct_places(monkeypatch):
    monkeypatch.setenv("PLANS_ENFORCED", "true")
    monkeypatch.setattr(main.sea, "analyse", lambda lat, lon: {"status": "land"})
    client = TestClient(main.app)
    for k in range(5):
        assert client.get("/api/v1/sea", params={"lat": 40 + k, "lon": 10}).status_code == 200
    again = client.get("/api/v1/sea", params={"lat": 40, "lon": 10})          # stesso luogo: non conta
    blocked = client.get("/api/v1/sea", params={"lat": 50, "lon": 10})
    assert again.status_code == 200 and blocked.status_code == 429
    assert "luoghi" in blocked.json()["detail"] and blocked.headers["access-control-allow-origin"] == "*"
    assert client.get("/api/v1/me").json()["usage_today"] == {"place": 5}


def test_limits_off_means_no_counting(monkeypatch):
    monkeypatch.setattr(main.sea, "analyse", lambda lat, lon: {"status": "land"})
    client = TestClient(main.app)
    for k in range(8):
        assert client.get("/api/v1/sea", params={"lat": 30 + k, "lon": 10}).status_code == 200
    assert accounts.memory.events == {}


def test_export_needs_account_when_enforced(monkeypatch):
    monkeypatch.setenv("PLANS_ENFORCED", "true")
    request = mock.Mock(headers={}, client=mock.Mock(host="1.2.3.4"))
    with pytest.raises(accounts.HTTPException) as err:
        accounts.check(request, "export", "x")
    assert err.value.status_code == 401


# ------------------------------------------------------------------ Paddle

def signed(body: dict, secret="pdl_ntfset_test", ts=None):
    raw = json.dumps(body).encode()
    ts = str(ts or int(time.time()))
    h1 = hmac.new(secret.encode(), f"{ts}:".encode() + raw, hashlib.sha256).hexdigest()
    return raw, f"ts={ts};h1={h1}"


EVENT = {"event_id": "evt_1", "event_type": "subscription.activated", "occurred_at": "2026-10-03T10:00:00Z",
         "data": {"id": "sub_1", "status": "active", "custom_data": {"user_id": "u-1"},
                  "items": [{"price": {"id": "pri_pro"}}],
                  "current_billing_period": {"ends_at": "2026-11-03T10:00:00Z"}}}


def test_signature_checks():
    raw, header = signed(EVENT)
    billing.verify_signature(raw, header, "pdl_ntfset_test")
    with pytest.raises(billing.InvalidSignature):
        billing.verify_signature(raw + b" ", header, "pdl_ntfset_test")
    old_raw, old_header = signed(EVENT, ts=int(time.time()) - 3600)
    with pytest.raises(billing.InvalidSignature):
        billing.verify_signature(old_raw, old_header, "pdl_ntfset_test")


def test_subscription_update_maps_price_to_plan(monkeypatch):
    monkeypatch.setenv("PADDLE_PRICE_PRO", "pri_pro")
    update = billing.subscription_update(EVENT)
    assert update["plan"] == "pro" and update["user_id"] == "u-1" and update["status"] == "active"
    assert billing.subscription_update({**EVENT, "event_type": "transaction.completed"}) is None


def test_webhook_endpoint(monkeypatch):
    client = TestClient(main.app)
    raw, header = signed(EVENT)
    assert client.post("/api/v1/billing/paddle-webhook", content=raw, headers={"Paddle-Signature": header}).status_code == 503
    monkeypatch.setenv("PADDLE_WEBHOOK_SECRET", "pdl_ntfset_test")
    monkeypatch.setenv("PADDLE_PRICE_PRO", "pri_pro")
    saved = []
    monkeypatch.setattr(billing, "save", saved.append)
    ok = client.post("/api/v1/billing/paddle-webhook", content=raw, headers={"Paddle-Signature": header})
    assert ok.status_code == 200 and ok.json()["applied"] and saved[0]["plan"] == "pro"
    bad = client.post("/api/v1/billing/paddle-webhook", content=raw, headers={"Paddle-Signature": "ts=1;h1=x"})
    assert bad.status_code == 401


# ------------------------------------------------------------------ esportazioni

def test_pdf_report_handles_unicode_and_sections():
    from src import exports
    payload = {"place": {"name": "Agadez", "context": "Niger", "lat": 16.97, "lon": 7.99},
               "sections": [{"title": "Gas · NO₂", "facts": [["Media", "35 µmol/m²"], ["Variazione", "−12%"], ["Vuoto", ""]],
                             "notes": ["Nota con <simboli> & 🔥"], "attribution": "Contiene dati Copernicus"}]}
    pdf = exports.place_report(payload)
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1500
    assert exports.safe("NO₂ −3 → ok 🔥") == "NO2 -3 -> ok "


def test_pdf_endpoint_and_export_limits(monkeypatch):
    client = TestClient(main.app)
    body = {"place": {"lat": 1, "lon": 2}, "sections": []}
    assert client.post("/api/v1/export/pdf", json=body).headers["content-type"] == "application/pdf"
    monkeypatch.setenv("PLANS_ENFORCED", "true")
    assert client.post("/api/v1/export/pdf", json=body).status_code == 401      # serve un account


def test_geotiff_is_georeferenced():
    import numpy as np
    from rasterio.io import MemoryFile
    from src import exports
    from src.imagery import Grid
    grid = Grid(45.0, 9.0, 1.0)
    values = np.full((grid.height, grid.width), 0.5, np.float32)
    valid = np.ones_like(values, bool)
    valid[0, 0] = False
    data = exports.index_geotiff(values, valid, grid, {"index": "NDVI"})
    with MemoryFile(data) as m, m.open() as ds:
        assert ds.crs.to_epsg() == 32632 and ds.tags()["index"] == "NDVI"
        band = ds.read(1)
        assert np.isnan(band[0, 0]) and band[5, 5] == 0.5
