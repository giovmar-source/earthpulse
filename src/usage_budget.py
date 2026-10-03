"""
Contatore mensile delle richieste ai servizi con quota (Copernicus Data Space).

Quota gratuita CDSE: 10 000 richieste al mese. Il server conta le richieste e
si ferma a CDSE_MONTHLY_BUDGET (predefinito 9 000, un margine del 10%) con un
messaggio chiaro, invece di ricevere errori dal servizio. Il conteggio è salvato
su disco (si azzera a ogni mese; su Render gratuito anche al riavvio).
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(os.environ.get("USAGE_FILE", "/tmp/earthpulse-usage.json"))
_lock = threading.Lock()


class BudgetExceeded(Exception):
    pass


def month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def budget(service: str) -> int:
    try:
        return int(os.environ.get(f"{service.upper()}_MONTHLY_BUDGET", "9000"))
    except ValueError:
        return 9000


def _load() -> dict:
    try:
        data = json.loads(PATH.read_text())
    except (OSError, ValueError):
        data = {}
    return data if data.get("month") == month() else {"month": month(), "counts": {}}


def spend(service: str, amount: int = 1) -> int:
    """Registra `amount` richieste; BudgetExceeded se si supera il budget del mese."""
    with _lock:
        data = _load()
        used = data["counts"].get(service, 0)
        if used + amount > budget(service):
            raise BudgetExceeded(
                "Raggiunto il limite mensile di elaborazioni satellitari di questo servizio: "
                "i dati torneranno disponibili il mese prossimo.")
        data["counts"][service] = used + amount
        try:
            PATH.write_text(json.dumps(data))
        except OSError:
            pass
        return used + amount


def report() -> dict:
    with _lock:
        data = _load()
    return {"month": data["month"],
            "services": {k: {"used": v, "budget": budget(k)} for k, v in data["counts"].items()}}
