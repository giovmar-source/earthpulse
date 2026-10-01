import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, useApi } from './common.jsx'
import { YearPicker } from './NightCard.jsx'

const SIDE_OPTIONS = [3, 6, 12]

/** Archivio Landsat dal 1984: una giornata estiva limpida per ogni anno. */
export default function ArchiveCard({ place }) {
  const [sideKm, setSideKm] = useState(6)
  const [pair, setPair] = useState(null)
  const [kind, setKind] = useState('rgb')
  const result = useApi(
    (signal) => getJson('/api/v1/archive', placeParams(place, sideKm.toFixed(1), 5), { signal }),
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
          : <Loading text="Ricerca nell'archivio Landsat…" hint="Cerchiamo un'estate limpida per ogni anno dal 1984." />}
      </>
    )
  }

  const a = result.data
  const before = pair?.[0] ?? a.default_before
  const after = pair?.[1] ?? a.default_after
  const layer = a.layers.find((l) => l.key === kind) || a.layers[0]
  const image = (year) => a.image_template.replace('{year}', year).replace('{kind}', layer.key)
  const sensor = (y) => a.sensors?.[String(y)] || 'Landsat'

  return (
    <div>
      {sizes}
      <div className="chips layers">
        {a.layers.map((l) => (
          <button key={l.key} className={l.key === layer.key ? 'chip on' : 'chip'} onClick={() => setKind(l.key)}>
            {l.label}
          </button>
        ))}
      </div>
      <div className="year-row">
        <YearPicker label="Prima" years={a.years} value={before} onChange={(y) => setPair([y, after])} describe={sensor} />
        <YearPicker label="Dopo" years={a.years} value={after} onChange={(y) => setPair([before, y])} describe={sensor} />
      </div>
      <CompareImages
        before={before !== after ? image(before) : null}
        after={image(after)}
        beforeLabel={`${before} · ${sensor(before)}`}
        afterLabel={`${after} · ${sensor(after)}`}
        alt="Archivio Landsat"
      />
      <Legend stops={layer.color_stops} labels={layer.legend_labels} />
      <p className="small">{layer.caption}</p>
      <p className="small muted">{a.caption}</p>
      <p className="credit">{a.attribution}</p>
    </div>
  )
}
