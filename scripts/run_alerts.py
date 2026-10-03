"""
Avvisi automatici per i luoghi salvati (piani Pro e Istituzionale).

Da eseguire a orari fissi (es. una volta al giorno) come "Cron Job" di Render:
    python scripts/run_alerts.py
Serve: SUPABASE_DB_URL (database), SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
ALERT_FROM (mittente). Senza queste variabili lo script si ferma senza fare nulla.

Controlli:
- fires: punti di calore NASA FIRMS nelle ultime 24 ore entro il raggio;
- new_water: acqua nuova dal radar Sentinel-1 rispetto a un mese prima, oltre la
  soglia in ettari (predefinita 5 ha).
Ogni avviso è inviato una sola volta (tabella alert_events, "impronta" dell'evento).
"""

from __future__ import annotations

import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import fires, sar_water  # noqa: E402
from src.exports import PRODUCT_NAME  # noqa: E402

PAID_PLANS = ("pro", "institutional")


def evaluate(alert: dict, fire_check=fires.detections, water_check=sar_water.analyse) -> dict | None:
    """Condizione dell'avviso -> {"fingerprint", "subject", "text"} se c'è qualcosa da segnalare."""
    name, lat, lon = alert["place_name"], alert["lat"], alert["lon"]
    if alert["kind"] == "fires":
        result = fire_check(lat, lon, alert["radius_km"], 1)
        if not result["count"]:
            return None
        latest = result["points"][0]
        return {
            "fingerprint": f"fires:{latest['date']}:{latest['time_utc']}",
            "subject": f"{name}: {result['count']} punti di calore entro {alert['radius_km']} km",
            "text": (f"Nelle ultime 24 ore i satelliti VIIRS hanno rilevato {result['count']} punti di calore "
                     f"entro {alert['radius_km']} km da {name}. Il più vicino è a {result['nearest_km']} km "
                     f"({latest['date']} {latest['time_utc']} UTC, affidabilità {latest['confidence']}).\n"
                     "Un punto di calore non è sempre un incendio di vegetazione.\n\nFonte: NASA FIRMS."),
        }
    if alert["kind"] == "new_water":
        result = water_check(lat, lon, "month")
        threshold = alert.get("threshold") or 5.0
        if result.get("status") != "ok" or result["stats"]["new"] < threshold:
            return None
        return {
            "fingerprint": f"water:{result['acquired']['now']}",
            "subject": f"{name}: {result['stats']['new']} ha di acqua nuova dal radar",
            "text": (f"Il radar di Sentinel-1 ({result['acquired']['now'][:10]}) vede {result['stats']['new']} ettari "
                     f"di acqua in più rispetto a un mese prima nell'area di 6 × 6 km attorno a {name}: possibile "
                     "allagamento. Superfici lisce come asfalto o sabbia asciutta possono sembrare acqua.\n\n"
                     "Fonte: dati Copernicus Sentinel-1 elaborati."),
        }
    return None


def send(to: str, subject: str, text: str) -> None:
    message = EmailMessage()
    message["From"] = os.environ["ALERT_FROM"]
    message["To"] = to
    message["Subject"] = f"[{PRODUCT_NAME}] {subject}"
    message.set_content(text + f"\n\n—\nAvviso automatico di {PRODUCT_NAME}. Gestisci gli avvisi dal tuo account.")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(message)


def main() -> int:
    needed = ("SUPABASE_DB_URL", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_FROM")
    missing = [n for n in needed if not os.environ.get(n)]
    if missing:
        print(f"Avvisi non attivi: mancano {', '.join(missing)}")
        return 0
    import psycopg
    sent = 0
    with psycopg.connect(os.environ["SUPABASE_DB_URL"]) as conn:
        rows = conn.execute("""
            select a.id, a.kind, a.radius_km, a.threshold, p.name, p.lat, p.lon, u.email,
                   coalesce(s.plan, 'free') as plan
            from alerts a join saved_places p on p.id = a.place_id join auth.users u on u.id = a.user_id
            left join subscriptions s on s.user_id = a.user_id and s.status in ('active', 'trialing')
            where a.active""").fetchall()
        for alert_id, kind, radius, threshold, name, lat, lon, email, plan in rows:
            if plan not in PAID_PLANS or not email:
                continue
            alert = {"kind": kind, "radius_km": radius, "threshold": threshold, "place_name": name, "lat": lat, "lon": lon}
            try:
                found = evaluate(alert)
            except Exception as exc:            # un servizio non risponde: si riprova al prossimo giro
                print(f"Avviso {alert_id}: controllo non riuscito ({exc})")
                continue
            if not found:
                continue
            inserted = conn.execute(
                "insert into alert_events (alert_id, fingerprint) values (%s, %s) on conflict do nothing returning 1",
                (alert_id, found["fingerprint"])).fetchone()
            if inserted:
                send(email, found["subject"], found["text"])
                conn.commit()
                sent += 1
    print(f"Avvisi inviati: {sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
