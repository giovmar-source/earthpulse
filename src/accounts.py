"""
Account utenti (Supabase Auth) e limiti dei piani.

Tutto è predisposto ma SPENTO finché non si configura:
- SUPABASE_URL: per verificare i token degli utenti (chiavi pubbliche JWKS,
  firma asimmetrica ES256/RS256, come raccomanda Supabase dal 2025);
- SUPABASE_DB_URL: connessione Postgres (pooler "session", porta 5432) per piani
  e contatori; tabelle in supabase/schema.sql;
- PLANS_ENFORCED=true: solo allora i limiti bloccano davvero le richieste.

Senza queste variabili il sito funziona come oggi: nessun login, nessun limite.

Conteggio: un'"analisi" è un luogo diverso al giorno (coordinate arrotondate a
circa 100 m); un'esportazione è ogni PDF o GeoTIFF generato.
"""

from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from src.plans import PLANS, limits

_jwks_client = None
_pool = None
_lock = threading.Lock()


def accounts_enabled() -> bool:
    return bool(os.environ.get("SUPABASE_URL"))


def database_enabled() -> bool:
    return bool(os.environ.get("SUPABASE_DB_URL"))


def enforced() -> bool:
    return os.environ.get("PLANS_ENFORCED", "").lower() in ("1", "true", "yes")


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ------------------------------------------------------------------
# Verifica del token di Supabase
# ------------------------------------------------------------------

def _jwks():
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient
        base = os.environ["SUPABASE_URL"].rstrip("/")
        _jwks_client = PyJWKClient(f"{base}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=600)
    return _jwks_client


def verify_token(token: str) -> dict:
    """Token di accesso di Supabase -> {"id", "email"}; HTTPException 401 se non valido."""
    import jwt
    try:
        key = _jwks().get_signing_key_from_jwt(token)
        claims = jwt.decode(token, getattr(key, "key", key), algorithms=["ES256", "RS256"], audience="authenticated",
                            options={"require": ["exp", "sub"]})
    except Exception as exc:                     # firma, scadenza, formato
        raise HTTPException(status_code=401, detail="Sessione scaduta o non valida: accedi di nuovo.") from exc
    if claims.get("role") not in (None, "authenticated"):
        raise HTTPException(status_code=401, detail="Sessione non valida.")
    return {"id": claims["sub"], "email": claims.get("email")}


def current_user(request: Request) -> dict | None:
    """Utente dal token "Authorization: Bearer", oppure None (visitatore senza account)."""
    header = request.headers.get("authorization", "")
    if not accounts_enabled() or not header.lower().startswith("bearer "):
        return None
    return verify_token(header[7:].strip())


# ------------------------------------------------------------------
# Archivio dei piani e dei contatori
# ------------------------------------------------------------------

class MemoryStore:
    """Contatori in memoria: visitatori senza account, test, server senza database."""

    def __init__(self):
        self.events: dict = {}           # (soggetto, giorno, tipo) -> set di elementi
        self.plans: dict = {}

    def plan(self, user_id: str) -> str:
        return self.plans.get(user_id, "free")

    def record(self, subject: str, kind: str, item: str, limit: int) -> tuple:
        key = (subject, today(), kind)
        with _lock:
            seen = self.events.setdefault(key, set())
            if item in seen:
                return True, len(seen)
            if len(seen) >= limit:
                return False, len(seen)
            seen.add(item)
            if len(self.events) > 50000:            # pulizia dei giorni passati
                for k in [k for k in self.events if k[1] != today()]:
                    del self.events[k]
            return True, len(seen)

    def usage(self, subject: str) -> dict:
        return {kind: len(items) for (s, day, kind), items in self.events.items() if s == subject and day == today()}


class PostgresStore:
    """Piani e contatori su Supabase Postgres (tabelle in supabase/schema.sql)."""

    def _conn(self):
        global _pool
        if _pool is None:
            from psycopg_pool import ConnectionPool
            _pool = ConnectionPool(os.environ["SUPABASE_DB_URL"], min_size=1, max_size=4, open=True)
        return _pool.connection()

    def plan(self, user_id: str) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "select plan from subscriptions where user_id = %s and status in ('active', 'trialing') "
                "and (current_period_end is null or current_period_end > now())", (user_id,)).fetchone()
        return row[0] if row else "free"

    def record(self, subject: str, kind: str, item: str, limit: int) -> tuple:
        with self._conn() as conn:
            with conn.transaction():
                exists = conn.execute(
                    "select 1 from usage_events where user_id = %s and day = current_date and kind = %s and item = %s",
                    (subject, kind, item)).fetchone()
                count = conn.execute(
                    "select count(*) from usage_events where user_id = %s and day = current_date and kind = %s",
                    (subject, kind)).fetchone()[0]
                if exists:
                    return True, count
                if count >= limit:
                    return False, count
                conn.execute("insert into usage_events (user_id, kind, item) values (%s, %s, %s) on conflict do nothing",
                             (subject, kind, item))
                return True, count + 1

    def usage(self, subject: str) -> dict:
        with self._conn() as conn:
            rows = conn.execute("select kind, count(*) from usage_events where user_id = %s and day = current_date "
                                "group by kind", (subject,)).fetchall()
        return {kind: count for kind, count in rows}


memory = MemoryStore()


def store_for(user: dict | None):
    return PostgresStore() if user and database_enabled() else memory


def subject_of(user: dict | None, request: Request) -> str:
    if user:
        return user["id"]
    ip = request.client.host if request.client else "?"
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return "anon:" + hashlib.sha256((forwarded or ip).encode()).hexdigest()[:16]   # niente IP in chiaro


def plan_of(user: dict | None) -> str:
    if not user:
        return "anonymous"
    return store_for(user).plan(user["id"])


# ------------------------------------------------------------------
# Dipendenze per gli endpoint
# ------------------------------------------------------------------

LIMIT_KEYS = {"place": "places_per_day", "export": "exports_per_day"}
MESSAGES = {
    "place": "Hai raggiunto il numero di luoghi analizzabili oggi con il tuo piano ({limit}). "
             "Riprova domani o passa a un piano superiore.",
    "export": "Hai raggiunto le esportazioni di oggi del tuo piano ({limit}).",
}


def check(request: Request, kind: str, item: str) -> None:
    """Conta l'uso e blocca (429) oltre il limite del piano, solo se PLANS_ENFORCED è attivo."""
    if not enforced():
        return
    user = current_user(request)
    plan = plan_of(user)
    limit = limits(plan)[LIMIT_KEYS[kind]]
    if kind == "export" and not user:
        raise HTTPException(status_code=401, detail="Per esportare serve un account gratuito: accedi o registrati.")
    allowed, _ = store_for(user).record(subject_of(user, request), kind, item, limit)
    if not allowed:
        raise HTTPException(status_code=429, detail=MESSAGES[kind].format(limit=limit))


def meter_place(request: Request, lat: float, lon: float) -> None:
    check(request, "place", f"{round(lat, 3)},{round(lon, 3)}")


def me(request: Request) -> dict:
    user = current_user(request)
    plan = plan_of(user)
    store = store_for(user)
    return {
        "accounts_enabled": accounts_enabled(), "enforced": enforced(),
        "user": user, "plan": plan, "plan_label": PLANS[plan]["label"],
        "limits": limits(plan),
        "usage_today": store.usage(subject_of(user, request)) if (user or enforced()) else {},
    }
