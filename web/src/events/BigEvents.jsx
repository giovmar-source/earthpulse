import { useMemo, useState } from 'react'
import { getJson } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, useApi } from '../place/common.jsx'

const CATEGORY_ICONS = {
  Alluvione: '🌊', Incendio: '🔥', Vulcano: '🌋', Siccità: '🏜️', Terremoto: '🌍',
  'Terremoto e tsunami': '🌊', Città: '🏙️', Ghiacciaio: '🧊',
}
const icon = (category) => CATEGORY_ICONS[category] || '🛰️'
// Livelli proposti nelle storie, nell'ordine in cui conviene guardarli
const LAYER_ORDER = ['rgb', 'diff', 'dnbr', 'ndwi', 'ndvi', 'ndmi', 'ndbi']

function eventDate(e) {
  return e.event_label || formatDate(e.event_date)
}

function EventDetail({ summary, onBack }) {
  const [layerKey, setLayerKey] = useState(null)
  const result = useApi(
    (signal) => getJson(`/api/v1/stories/${encodeURIComponent(summary.id)}`, null, { signal }),
    [summary.id],
  )
  const d = result.status === 'ok' ? result.data : null
  const layers = useMemo(() => {
    if (!d) return []
    const available = d.layers.filter((l) => d.after?.images?.[l.key])
    return LAYER_ORDER.map((k) => available.find((l) => l.key === k)).filter(Boolean)
  }, [d])
  const layer = layers.find((l) => l.key === layerKey) || layers[0]
  const single = layer?.mode === 'single'

  return (
    <div>
      <button className="link" onClick={onBack}>← Tutti gli eventi</button>
      <p className="eyebrow spaced">{icon(summary.category)} {summary.category} · {eventDate(summary)}</p>
      <h2>{summary.title}</h2>
      <p className="muted">{summary.place}, {summary.country}</p>
      <p>{summary.summary}</p>

      {result.status === 'error' && <ErrorBox message={result.error} onRetry={result.retry} />}
      {(result.status === 'loading' || result.status === 'idle') && (
        <Loading text="Preparazione delle immagini prima e dopo…"
          hint={summary.source === 'landsat' ? 'Archivio Landsat: può servire un minuto.' : 'Di solito 20-40 secondi.'} />
      )}
      {d && layer && (
        <>
          <div className="chips layers">
            {layers.map((l) => (
              <button key={l.key} className={l.key === layer.key ? 'chip on' : 'chip'} onClick={() => setLayerKey(l.key)}>{l.label}</button>
            ))}
          </div>
          <CompareImages
            key={layer.key}
            after={d.after.images[layer.key]}
            before={single ? null : d.before?.images?.[layer.key]}
            beforeLabel={d.before && formatDate(d.before.date)}
            afterLabel={single ? `${formatDate(d.before?.date)} → ${formatDate(d.after.date)}` : formatDate(d.after.date)}
            alt={layer.label}
          />
          {!single && d.before && <p className="muted small hint">Trascina il cursore: a sinistra prima, a destra dopo.</p>}
          <Legend stops={layer.color_stops} labels={layer.legend_labels} />
          <p className="small muted">{layer.caption}</p>
          <div className="box">
            <p className="eyebrow">Cosa osservare</p>
            <p>{d.what_to_look}</p>
          </div>
          {layer.key === 'diff' && d.diff_note && <p className="small">{d.diff_note}</p>}
          <dl className="facts">
            {d.facts.map((f) => {
              const [label, ...rest] = f.split(': ')
              return rest.length
                ? <div key={f}><dt>{label}</dt><dd>{rest.join(': ')}</dd></div>
                : <div key={f}><dd style={{ textAlign: 'left' }}>{f}</dd></div>
            })}
          </dl>
          <p className="note">⚠ {d.caveat}</p>
          {d.messages?.map((m) => <p key={m} className="note">⚠ {m}</p>)}
          <p className="eyebrow spaced">Fonti</p>
          <ul className="sources">
            {d.sources.map((s) => <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a></li>)}
          </ul>
          <p className="credit">{d.attribution}</p>
        </>
      )}
    </div>
  )
}

/** Big Events: grandi eventi visti dal satellite, prima e dopo. */
export default function BigEvents({ onClose, selectedId, onSelect }) {
  const [category, setCategory] = useState('Tutti')
  const list = useApi((signal) => getJson('/api/v1/stories', null, { signal }), [])
  const events = list.status === 'ok' ? list.data.stories : []
  const selected = events.find((e) => e.id === selectedId)
  const categories = ['Tutti', ...new Set(events.map((e) => e.category))]
  const shown = events
    .filter((e) => category === 'Tutti' || e.category === category)
    .sort((a, b) => b.event_date.localeCompare(a.event_date))

  return (
    <aside className="panel wide events">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      {selected ? (
        <EventDetail key={selected.id} summary={selected} onBack={() => onSelect(null)} />
      ) : (
        <>
          <p className="eyebrow">Big Events</p>
          <h2>I grandi eventi visti dallo spazio</h2>
          <p className="muted">
            Alluvioni, incendi, eruzioni, siccità e città che crescono: per ognuno le immagini
            satellitari di prima e dopo, cosa osservare e le fonti. Sono segnati anche sul globo.
          </p>
          {list.status === 'error' && <ErrorBox message={list.error} onRetry={list.retry} />}
          {list.status === 'loading' && <Loading text="Caricamento degli eventi…" />}
          <div className="chips">
            {categories.map((c) => (
              <button key={c} className={c === category ? 'chip on' : 'chip'} onClick={() => setCategory(c)}>
                {c === 'Tutti' ? c : `${icon(c)} ${c}`}
              </button>
            ))}
          </div>
          <ul className="event-list">
            {shown.map((e) => (
              <li key={e.id}>
                <button onClick={() => onSelect(e.id)}>
                  <span className="event-icon">{icon(e.category)}</span>
                  <span className="event-text">
                    <strong>{e.title}</strong>
                    <span className="muted small">{e.place}, {e.country} · {eventDate(e)}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  )
}
