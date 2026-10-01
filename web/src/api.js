import { API_URL } from './config.js'

/** Indirizzo completo di un percorso del backend (es. "/api/v1/heat/image?..."). */
export function apiUrl(path) {
  return path.startsWith('http') ? path : `${API_URL}${path}`
}

/** Messaggio comprensibile da una risposta di errore di FastAPI. */
function describeError(status, body) {
  let detail = null
  try {
    const d = JSON.parse(body).detail
    if (typeof d === 'string') detail = d
    else if (Array.isArray(d)) detail = d[0]?.msg
    else if (d && typeof d === 'object') detail = d.message || JSON.stringify(d)
  } catch { /* corpo non JSON */ }
  if (status === 503 && detail) return detail
  const prefix = {
    400: 'Richiesta non valida', 422: 'Richiesta non valida', 404: 'Dati non trovati',
    502: 'Servizio satellitare non raggiungibile', 503: 'Servizio temporaneamente non disponibile',
  }[status] || `Errore del server (${status})`
  return detail ? `${prefix}: ${detail}` : prefix
}

/** GET JSON dal backend; gli errori diventano messaggi in italiano. */
export async function getJson(path, params, { signal } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : ''
  let response
  try {
    response = await fetch(apiUrl(path) + query, { signal })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Impossibile contattare il server EarthPulse. Controlla la connessione e riprova.')
  }
  const text = await response.text()
  if (!response.ok) throw new Error(describeError(response.status, text))
  return JSON.parse(text)
}

/** Coordinate arrotondate come le usa l'app (stesse chiavi di cache sul server). */
export function placeParams(place, sideKm, digits = 6) {
  return {
    lat: place.lat.toFixed(digits),
    lon: place.lon.toFixed(digits),
    ...(sideKm != null ? { side_km: String(sideKm) } : {}),
  }
}
