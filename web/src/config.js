// Indirizzo del backend FastAPI. Si può cambiare con il file .env.local
// (vedi .env.example), per esempio per usare il backend sul proprio PC.
export const API_URL =
  import.meta.env.VITE_API_URL || 'https://earthpulse-api-tk6r.onrender.com'

// Stile della mappa: OpenFreeMap (vettoriale, gratuito, senza chiave)
export const MAP_STYLE =
  import.meta.env.VITE_MAP_STYLE || 'https://tiles.openfreemap.org/styles/liberty'
