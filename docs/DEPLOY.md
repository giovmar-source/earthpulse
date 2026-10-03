# Messa in produzione: cosa accendere e in che ordine

Tutto il codice della Fase 3 è già nel progetto ma **spento**: finché non imposti le
variabili qui sotto, il sito funziona come la beta gratuita (nessun login, nessun limite,
nessun pagamento). Ogni passo si può fare da solo, quando serve.

Le chiavi segrete vanno **solo** nel pannello di Render (Environment) o di Cloudflare,
mai nel repository.

---

## 0. Subito, gratis: chiave per gli incendi

1. Chiedi una chiave gratuita su https://firms.modaps.eosdis.nasa.gov/api/map_key
   (arriva per email).
2. Render → servizio `earthpulse-api` → Environment → aggiungi `FIRMS_MAP_KEY`.

La sezione "Incendi attivi" si attiva da sola.

---

## 1. Account (Supabase)

1. Crea un progetto su https://supabase.com, regione **Frankfurt (eu-central-1)**.
2. Editor SQL → incolla ed esegui tutto `supabase/schema.sql`.
3. Authentication → Sign In / Providers: lascia attivo **Email** (link magico).
   URL configuration → Site URL = indirizzo del sito; aggiungi anche
   `http://localhost:5173` tra i Redirect URL per le prove.
4. Prima del lancio: Authentication → Emails → imposta un **SMTP tuo** (il servizio
   email incluso in Supabase ha limiti molto bassi).
5. Project Settings → API Keys: copia la chiave **publishable** (`sb_publishable_…`).
   Project Settings → Database → Connection string → **Session pooler** (porta 5432).
6. Render (backend): `SUPABASE_URL` = `https://<progetto>.supabase.co`,
   `SUPABASE_DB_URL` = stringa del pooler (con la password del database).
7. Sito: `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY` (vedi `web/.env.example`).

Da qui compaiono login, luoghi salvati e avvisi. I limiti restano spenti.

## 2. Limiti dei piani

Render: `PLANS_ENFORCED=true`. Limiti e testi dei piani: `src/plans.py` (e, per luoghi
salvati e avvisi, la funzione `plan_limit` in `supabase/schema.sql`: tenerli uguali).

## 3. Pagamenti (Paddle Billing) — dopo la Partita IVA

1. Account Paddle → prima in **sandbox** (https://sandbox-vendors.paddle.com).
2. Crea i prodotti Pro (mensile) e, se serve, Istituzionale; copia gli ID dei prezzi (`pri_…`).
3. Developer tools → Notifications → nuova destinazione:
   `https://<backend>/api/v1/billing/paddle-webhook`, eventi `subscription.*`;
   copia il segreto (`pdl_ntfset_…`).
4. Render: `PADDLE_WEBHOOK_SECRET`, `PADDLE_PRICE_PRO`, `PADDLE_PRICE_INSTITUTIONAL`.
5. Sito: `VITE_PADDLE_CLIENT_TOKEN`, `VITE_PADDLE_ENV=sandbox`.
6. Per il passaggio a "live" Paddle verifica dominio, attività e identità: il sito deve
   avere prezzi, termini di servizio, privacy e politica di rimborso raggiungibili dal menu.

## 4. Fonti in versione commerciale (prima di incassare)

Dettaglio fonte per fonte in `docs/LICENZE.md`.

| Cosa | Variabile | Dove si ottiene |
|---|---|---|
| Qualità dell'aria (Open-Meteo commerciale) | `OPENMETEO_API_KEY` | https://open-meteo.com/en/pricing |
| Ricerca dei luoghi (Geoapify, server UE) | `GEOCODER=geoapify`, `GEOAPIFY_KEY` | https://www.geoapify.com/pricing/ |
| Meteosat con 1 ora di ritardo | backend `EUMETSAT_DELAY_MINUTES=60`, sito `VITE_IMAGERY_DELAY_MINUTES=60` | — |
| Budget Copernicus | `CDSE_MONTHLY_BUDGET` (predefinito 9000) | quota CDSE o piano CREODIAS |
| Immagini ESA dei satelliti | sostituire i file in `web/public/img` | immagini CC BY-SA 3.0 IGO o permesso ESA |

Consumo del mese: `GET /api/v1/status/usage`.

## 5. Hosting di produzione

**Sito → Cloudflare Pages** (gratis):
1. Cloudflare → Workers & Pages → Create → Pages → collega il repository GitHub.
2. Preset **React (Vite)**, cartella principale `web`, comando `npm run build`, output `dist`.
3. Variabili `VITE_*` come in `web/.env.example`.
4. Dominio personalizzato quando c'è il nome definitivo. `web/public/_headers` aggiunge
   le intestazioni di sicurezza. Poi si può spegnere GitHub Pages.

**Backend → Render a pagamento**: usa `render.production.yaml` (piano Standard,
Frankfurt, 2 processi, tutte le variabili elencate) al posto di `render.yaml`.
Il file definisce anche il cron job degli avvisi (`scripts/run_alerts.py`, ogni giorno
alle 6:00 UTC), che richiede un servizio email SMTP (`SMTP_*`, `ALERT_FROM`).

Alternative più economiche in UE (si gestisce di più da soli): Hetzner CX23 (circa 5,5 €/mese),
Fly.io Frankfurt.

## Controllo finale prima del lancio

- [ ] Nessuna riga 🔴 in `docs/LICENZE.md`
- [ ] `PLANS_ENFORCED=true` e piani provati con un account di prova
- [ ] Webhook Paddle provato in sandbox (abbonamento → piano Pro nel pannello Account)
- [ ] Pagine legali (privacy, cookie, termini, recesso) e nome definitivo (Fase 5)
