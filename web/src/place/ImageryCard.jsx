import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, formatNumber, useApi } from './common.jsx'

const SIDE_OPTIONS = [1, 2, 3]
const INDEX_LAYERS = new Set(['ndvi', 'ndwi', 'ndmi', 'ndbi', 'ndre', 'ndsi', 'ndci', 'ndti'])

/** Valore medio di un indice (o ettari d'acqua) per una o due date. */
function StatLine({ layer, after, before }) {
  const isIndex = INDEX_LAYERS.has(layer.key)
  const isWater = layer.stat === 'water'
  const make = (scene) => {
    if (!scene) return null
    if (isWater) return scene.images.stat_water
    if (isIndex) return scene.images.stat_index?.replace('{index}', layer.key)
    return null
  }
  const afterPath = make(after)
  const beforePath = make(before)
  const enabled = Boolean(afterPath)
  const stats = useApi(
    (signal) => Promise.all([
      getJson(afterPath, null, { signal }),
      beforePath ? getJson(beforePath, null, { signal }) : Promise.resolve(null),
    ]),
    [afterPath, beforePath],
    enabled,
  )
  if (!enabled) return null
  if (stats.status === 'loading' || stats.status === 'idle') {
    return <p className="muted small">Calcolo del valore nell'area…</p>
  }
  if (stats.status === 'error') return <p className="muted small">Valore non disponibile: {stats.error}</p>

  const [a, b] = stats.data
  if (isWater) {
    return (
      <div className="stat">
        <span>Acqua libera nell'area</span>
        <strong>
          {b && `${formatNumber(b.water_ha, 1)} ha → `}{formatNumber(a.water_ha, 1)} ha
        </strong>
      </div>
    )
  }
  return (
    <div className="stat">
      <span>{layer.label}: valore tipico nel km² centrale</span>
      <strong>
        {b && `${formatNumber(b.median)} → `}{formatNumber(a.median)}
      </strong>
    </div>
  )
}

/** Immagini "dall'alto" di Sentinel-2: colori reali e indici, prima e dopo. */
export default function ImageryCard({ place, layerOrder, tips }) {
  const [sideKm, setSideKm] = useState(3)
  const [layerKey, setLayerKey] = useState(null)
  const result = useApi(
    (signal) => getJson('/api/v1/imagery/scenes', placeParams(place, sideKm.toFixed(1)), { signal }),
    [place.lat, place.lon, sideKm],
  )

  const sizes = (
    <div className="chips">
      <span className="muted small">Area:</span>
      {SIDE_OPTIONS.map((km) => (
        <button key={km} className={km === sideKm ? 'chip on' : 'chip'} onClick={() => setSideKm(km)}>
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
  const { after, before } = data
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
      <div className="chips layers">
        {layers.map((l) => (
          <button key={l.key} className={l.key === layer.key ? 'chip on' : 'chip'} onClick={() => setLayerKey(l.key)}>
            {l.label}
          </button>
        ))}
      </div>
      <CompareImages
        key={`${layer.key}-${sideKm}`}
        after={after.images[layer.key]}
        before={single ? null : before?.images[layer.key]}
        beforeLabel={before && formatDate(before.date)}
        afterLabel={single ? `${formatDate(before?.date)} → ${formatDate(after.date)}` : formatDate(after.date)}
        alt={layer.label}
      />
      {!single && before && <p className="muted small hint">Trascina il cursore per confrontare le due date.</p>}
      <Legend stops={layer.color_stops} labels={layer.legend_labels} />
      <StatLine key={`stat-${layer.key}-${sideKm}`} layer={layer} after={after} before={single ? null : before} />
      {tips?.[layer.key] && <p className="tip">💡 {tips[layer.key]}</p>}
      <p className="small">{layer.caption}</p>
      {layer.formula && <p className="formula">{layer.formula}</p>}
      {data.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      <p className="credit">{data.attribution}</p>
    </div>
  )
}
