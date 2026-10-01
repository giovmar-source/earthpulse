import { useState } from 'react'
import { CompareImages, ErrorBox, Legend, formatDate, useApi } from './common.jsx'
import { getScenes } from './scenesCache.js'

const MAP_SIDE_KM = 3
const ANALYSIS_SIDE_KM = 1

/**
 * Mappa di un indice sull'area di 3 km: oggi e un anno fa con il cursore.
 * Il riquadro tratteggiato è l'area di 1 km su cui sono calcolati i numeri.
 * Con withChange mostra anche la mappa della variazione (solo NDVI).
 */
export default function IndexMap({ place, layerKey, withChange = false }) {
  const [view, setView] = useState('pair')
  const result = useApi(() => getScenes(place, MAP_SIDE_KM), [place.lat, place.lon])
  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />
  if (result.status !== 'ok') return <p className="muted small"><span className="spinner" /> Ricerca delle immagini più nitide…</p>

  const { after, before, layers } = result.data
  if (!after) return <p className="note">⚠ Nessuna immagine abbastanza nitida per la mappa.</p>
  const showChange = withChange && view === 'change' && after.images.diff
  const layer = layers.find((l) => l.key === (showChange ? 'diff' : layerKey))
  if (!layer) return null

  return (
    <div className="index-map">
      <p className="eyebrow spaced">Mappa · {MAP_SIDE_KM} × {MAP_SIDE_KM} km</p>
      {withChange && after.images.diff && (
        <div className="chips">
          <button className={view === 'pair' ? 'chip on' : 'chip'} onClick={() => setView('pair')}>Due date</button>
          <button className={view === 'change' ? 'chip on' : 'chip'} onClick={() => setView('change')}>Variazione</button>
        </div>
      )}
      <div className="framed">
        <CompareImages
          key={layer.key}
          after={after.images[layer.key]}
          before={showChange ? null : before?.images[layer.key]}
          beforeLabel={before && formatDate(before.date)}
          afterLabel={showChange ? `${formatDate(before?.date)} → ${formatDate(after.date)}` : formatDate(after.date)}
          alt={layer.label}
        />
        <span className="analysis-box" style={{ width: `${(100 * ANALYSIS_SIDE_KM) / MAP_SIDE_KM}%` }} />
      </div>
      <Legend stops={layer.color_stops} labels={layer.legend_labels} />
      <p className="small muted">
        {showChange ? layer.caption : `${layer.caption} Il riquadro tratteggiato è l'area di 1 km dei numeri qui sopra.`}
      </p>
    </div>
  )
}
