import { API_URL } from './config.js'
import { accessToken } from './account/supabase.js'

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
  // Limiti del piano e login: il messaggio del server è già una frase completa
  if ((status === 503 || status === 429 || status === 401) && detail) return detail
  const prefix = {
    400: 'Richiesta non valida', 422: 'Richiesta non valida', 404: 'Dati non trovati',
    401: 'Accesso richiesto', 429: 'Limite del piano raggiunto',
    502: 'Servizio satellitare non raggiungibile', 503: 'Servizio temporaneamente non disponibile',
  }[status] || `Errore del server (${status})`
  return detail ? `${prefix}: ${detail}` : prefix
}

/** GET JSON dal backend; gli errori diventano messaggi in italiano. */
export async function getJson(path, params, { signal } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : ''
  let response
  try {
    response = await fetch(apiUrl(path) + query, { signal, headers: await authHeaders() })
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

/** Intestazione con il token dell'utente, se ha fatto il login (per piani e limiti). */
export async function authHeaders() {
  const token = await accessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** Scarica un file dal backend (GET o POST JSON) e lo salva con il nome indicato. */
export async function downloadFile(path, filename, { body } = {}) {
  const response = await fetch(apiUrl(path), {
    method: body ? 'POST' : 'GET',
    headers: { ...(await authHeaders()), ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) throw new Error(describeError(response.status, await response.text()))
  saveBlob(await response.blob(), filename)
}

/** Salva un Blob come file sul computer dell'utente. */
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Righe -> file CSV (separatore ";" e virgola decimale, come lo apre Excel in italiano). */
export function downloadCsv(rows, columns, filename) {
  const cell = (v) => {
    if (v == null) return ''
    const text = typeof v === 'number' ? String(v).replace('.', ',') : String(v)
    return /[;"\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
  }
  const lines = [columns.map(([, label]) => cell(label)).join(';'),
    ...rows.map((r) => columns.map(([key]) => cell(r[key])).join(';'))]
  saveBlob(new Blob(['\ufeff' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }), filename)
}
