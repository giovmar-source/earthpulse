import { useState } from 'react'
import { getJson } from './api.js'

/** Ricerca di un luogo per nome (backend → OpenStreetMap). Una richiesta per ricerca. */
export default function SearchBox({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [status, setStatus] = useState('idle')

  async function search(event) {
    event.preventDefault()
    if (query.trim().length < 2) return
    setStatus('loading')
    try {
      const data = await getJson('/api/v1/geocode', { q: query.trim(), limit: '5' })
      setResults(data.results || [])
      setStatus('ok')
    } catch (e) {
      setResults([])
      setStatus(e.message)
    }
  }

  function choose(r) {
    setResults(null)
    setQuery(r.name || '')
    onSelect({ lat: r.latitude, lon: r.longitude, name: r.name || r.display_name })
  }

  return (
    <form className="search" onSubmit={search}>
      <input
        type="search" value={query} placeholder="Cerca un luogo…"
        onChange={(e) => { setQuery(e.target.value); if (!e.target.value) setResults(null) }}
        aria-label="Cerca un luogo"
      />
      <button type="submit" aria-label="Cerca">{status === 'loading' ? '…' : '⌕'}</button>
      {results && (
        <ul className="search-results">
          {results.length === 0 && (
            <li className="muted small">{status === 'ok' ? 'Nessun risultato.' : status}</li>
          )}
          {results.map((r) => (
            <li key={`${r.latitude},${r.longitude}`}>
              <button type="button" onClick={() => choose(r)}>
                <strong>{r.name}</strong>
                <span className="muted small">{r.display_name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  )
}
