"""
Pagamenti con Paddle Billing (Merchant of Record: Paddle incassa e versa l'IVA UE).

PREDISPOSTO MA SPENTO: senza PADDLE_WEBHOOK_SECRET il webhook risponde 503 e il
sito mostra "pagamenti in arrivo". Per attivarlo (dopo Partita IVA e verifica
dell'account Paddle):
- PADDLE_WEBHOOK_SECRET: segreto della destinazione webhook (pdl_ntfset_…);
- PADDLE_PRICE_PRO, PADDLE_PRICE_INSTITUTIONAL: ID dei prezzi (pri_…);
- nel sito: VITE_PADDLE_CLIENT_TOKEN e VITE_PADDLE_ENV (sandbox | production).

Il checkout passa l'ID dell'utente Supabase in custom_data.user_id: così il
webhook sa a chi assegnare il piano. Firma: header Paddle-Signature "ts=…;h1=…",
HMAC-SHA256 di "ts:corpo" con il segreto; scarto oltre 5 minuti di differenza.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

SUBSCRIPTION_EVENTS = {
    "subscription.created", "subscription.activated", "subscription.updated", "subscription.canceled",
    "subscription.past_due", "subscription.paused", "subscription.resumed", "subscription.trialing",
}
MAX_SKEW_SECONDS = 300


class BillingDisabled(Exception):
    pass


class InvalidSignature(Exception):
    pass


def enabled() -> bool:
    return bool(os.environ.get("PADDLE_WEBHOOK_SECRET"))


def verify_signature(raw_body: bytes, header: str, secret: str, now: float | None = None) -> None:
    parts = dict(item.split("=", 1) for item in header.split(";") if "=" in item)
    ts, signature = parts.get("ts"), parts.get("h1")
    if not ts or not signature:
        raise InvalidSignature("Firma mancante")
    if abs((now or time.time()) - int(ts)) > MAX_SKEW_SECONDS:
        raise InvalidSignature("Firma scaduta")
    expected = hmac.new(secret.encode(), f"{ts}:".encode() + raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise InvalidSignature("Firma non valida")


def plan_for_price(price_id: str | None) -> str | None:
    if price_id and price_id == os.environ.get("PADDLE_PRICE_PRO"):
        return "pro"
    if price_id and price_id == os.environ.get("PADDLE_PRICE_INSTITUTIONAL"):
        return "institutional"
    return None


def subscription_update(event: dict) -> dict | None:
    """Evento Paddle -> riga per la tabella subscriptions (None se non riguarda gli abbonamenti)."""
    if event.get("event_type") not in SUBSCRIPTION_EVENTS:
        return None
    data = event.get("data") or {}
    user_id = (data.get("custom_data") or {}).get("user_id")
    items = data.get("items") or []
    price_id = ((items[0] if items else {}).get("price") or {}).get("id")
    plan = plan_for_price(price_id)
    if not user_id or not plan:
        return None
    period = data.get("current_billing_period") or {}
    return {
        "user_id": user_id, "plan": plan, "status": data.get("status", "active"),
        "current_period_end": period.get("ends_at"), "paddle_subscription_id": data.get("id"),
        "event_id": event.get("event_id"), "occurred_at": event.get("occurred_at"),
    }


def save(update: dict) -> None:
    """Scrive l'abbonamento su Supabase; ignora gli eventi più vecchi di quello già salvato."""
    from src.accounts import PostgresStore
    with PostgresStore()._conn() as conn:
        conn.execute(
            """insert into subscriptions (user_id, plan, status, current_period_end, paddle_subscription_id,
                                          last_event_id, last_event_at, updated_at)
               values (%(user_id)s, %(plan)s, %(status)s, %(current_period_end)s, %(paddle_subscription_id)s,
                       %(event_id)s, %(occurred_at)s, now())
               on conflict (user_id) do update set plan = excluded.plan, status = excluded.status,
                 current_period_end = excluded.current_period_end,
                 paddle_subscription_id = excluded.paddle_subscription_id,
                 last_event_id = excluded.last_event_id, last_event_at = excluded.last_event_at, updated_at = now()
               where subscriptions.last_event_at is null or subscriptions.last_event_at <= excluded.last_event_at""",
            update)


def handle(raw_body: bytes, signature_header: str) -> dict:
    if not enabled():
        raise BillingDisabled("Pagamenti non ancora attivi.")
    verify_signature(raw_body, signature_header or "", os.environ["PADDLE_WEBHOOK_SECRET"])
    event = json.loads(raw_body)
    update = subscription_update(event)
    if update:
        save(update)
    return {"received": True, "applied": bool(update)}
