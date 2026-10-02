import { useState } from 'react'
import { getScenes } from './scenesCache.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate } from './common.jsx'
import { DatePicker, StatLine, customPair } from './DatePicker.jsx'

const SIDE_OPTIONS = [1, 2, 3]
/** Immagini "dall'alto" di Sentinel-2: colori reali e indici, prima e dopo. */
export default function ImageryCard({ place, layerOrder, tips }) {
  const [sideKm, setSideKm] = useState(3)
  const [layerKey, setLayerKey] = useState(null)
  const [picking, setPicking] = useState(false)
  const [custom, setCustom] = useState(null)
  const result = useApi(
    () => getScenes(place, sideKm),
    [place.lat, place.lon, sideKm],
  )

  const sizes = (
    <div className="chips">
      <span className="muted small">Area:</span>
      {SIDE_OPTIONS.map((km) => (
        <button key={km} className={km === sideKm ? 'chip on' : 'chip'} onClick={() => { setSideKm(km); setCustom(null) }}>
          {km} × {km} km
        </button>
      ))}
    </div>
  )

  if (result.status !== 'ok') {
    return (
      <>
        {sizes}
        {result.status === 'error'
          ? <ErrorBox message={result.error} onRetry={result.retry} />
          : <Loading text="Ricerca delle immagini più nitide…" hint="Una recente e una dello stesso periodo dell'anno scorso." />}
      </>
    )
  }

  const data = result.data
  const chosen = picking && custom ? customPair(custom.timeline, custom.beforeId, custom.afterId) : null
  const after = chosen?.after ?? data.after
  const before = chosen?.before ?? data.before
  const attribution = chosen?.attribution ?? data.attribution
  const pairKey = `${before?.item_id}-${after?.item_id}`
  // Ordine dei livelli scelto dalla categoria di lavoro (se c'è)
  let layers = data.layers.filter((l) => after?.images[l.key] || l.key === 'rgb')
  if (layerOrder?.length) {
    layers = layerOrder.map((k) => layers.find((l) => l.key === k)).filter(Boolean)
  }
  const layer = layers.find((l) => l.key === layerKey) || layers[0]

  if (!after) {
    return (
      <>
        {sizes}
        {data.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      </>
    )
  }

  const single = layer.mode === 'single'
  return (
    <div>
      {sizes}
      {layers.length > 1 && <div className="chips layers">
        {layers.map((l) => (
          <button key={l.key} className={l.key === layer.key ? 'chip on' : 'chip'} onClick={() => setLayerKey(l.key)}>
            {l.label}
          </button>
        ))}
      </div>}
      <div className="dates-bar">
        {!picking
          ? <button className="chip" onClick={() => setPicking(true)}>📅 Scegli le date</button>
          : <DatePicker place={place} sideKm={sideKm} value={custom} onChange={setCustom}
              onClose={() => { setPicking(false); setCustom(null) }} />}
      </div>
      <CompareImages
        key={`${layer.key}-${sideKm}-${pairKey}`}
        after={after.images[layer.key]}
        before={single ? null : before?.images[layer.key]}
        beforeLabel={before && formatDate(before.date)}
        afterLabel={single ? `${formatDate(before?.date)} → ${formatDate(after.date)}` : formatDate(after.date)}
        alt={layer.label}
      />
      {!single && before && <p className="muted small hint">Trascina il cursore per confrontare le due date.</p>}
      <Legend stops={layer.color_stops} labels={layer.legend_labels} />
      <StatLine key={`stat-${layer.key}-${sideKm}-${pairKey}`} layer={layer} after={after} before={single ? null : before} />
      {tips?.[layer.key] && <p className="tip">💡 {tips[layer.key]}</p>}
      <p className="small">{layer.caption}</p>
      {layer.formula && <p className="formula">{layer.formula}</p>}
      {!chosen && data.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      <p className="credit">{attribution}</p>
    </div>
  )
}
