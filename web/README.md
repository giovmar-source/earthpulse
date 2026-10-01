# EarthPulse Web

Il sito di EarthPulse: globo 3D con i satelliti in tempo reale e, nei prossimi passi,
l'analisi di qualsiasi luogo. Usa lo stesso backend FastAPI dell'app Android.

## Avviarlo sul PC

1. Installa **Node.js LTS** da <https://nodejs.org> (una volta sola).
2. Dalla cartella `web/`:

   ```
   npm install
   npm run dev
   ```

3. Apri <http://localhost:5173>.

Di default il sito usa il backend su Render. Per usare quello sul PC copia
`.env.example` in `.env.local` e imposta `VITE_API_URL=http://127.0.0.1:8000`.

## Tecnologie

React 19 · Vite · MapLibre GL JS 5 (proiezione a globo) · satellite.js (modello SGP4)

## Dati

- Orbite: elementi TLE di CelesTrak, forniti dal backend (`/api/v1/tle`).
- Mappa: OpenFreeMap e OpenMapTiles, © OpenStreetMap contributors.
- Immagini dei satelliti: ESA/ATG medialab (Licenza standard ESA), NASA (pubblico dominio).
