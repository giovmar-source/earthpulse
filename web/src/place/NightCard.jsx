import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, useApi } from './common.jsx'

const SIDE_OPTIONS = [30, 60, 120]

export function YearPicker({ label, years, value, onChange, describe }) {
  return (
    <label className="year-picker">
      <span className="muted small">{label}</span>
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {years.map((y) => <option key={y} value={y}>{y}{describe ? ` · ${describe(y)}` : ''}</option>)}
      </select>
    </label>
  )
}

/** Numeri del confronto tra due anni (solo dopo che le immagini sono pronte sul server). */
function NightNumbers({ path }) {
  const result = useApi((signal) => getJson(path, null, { signal }), [path])
  if (result.status === 'ok') {
    return (
      <>
        <p className="highlight">{result.data.message}</p>
        <p className="note">⚠ {result.data.caveat}</p>
      </>
    )
  }
  if (result.status === 'error') return <p className="muted small">{result.error}</p>
  return <p className="muted small">Calcolo della variazione…</p>
}

/** Luci notturne annuali (NASA Black Marble, Suomi NPP) dal 2012. */
export default function NightCard({ place }) {
  const [sideKm, setSideKm] = useState(60)
  const [pair, setPair] = useState(null)
  const result = useApi(
    (signal) => getJson('/api/v1/nightlights', placeParams(place, sideKm.toFixed(1), 5), { signal }),
    [place.lat, place.lon, sideKm],
  )

  const sizes = (
    <div className="chips">
      <span className="muted small">Area:</span>
      {SIDE_OPTIONS.map((km) => (
        <button key={km} className={km === sideKm ? 'chip on' : 'chip'} onClick={() => { setSideKm(km) }}>
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
          : <Loading text="Ricerca degli anni disponibili…" />}
      </>
    )
  }

  const n = result.data
  const before = pair?.[0] ?? n.default_before
  const after = pair?.[1] ?? n.default_after
  const image = (year) => n.image_template.replace('{year}', year)
  const compare = n.compare_template.replace('{before}', before).replace('{after}', after)

  return (
    <div>
      {sizes}
      <div className="year-row">
        <YearPicker label="Prima" years={n.years} value={before} onChange={(y) => setPair([y, after])} />
        <YearPicker label="Dopo" years={n.years} value={after} onChange={(y) => setPair([before, y])} />
      </div>
      <CompareImages
        before={before !== after ? image(before) : null}
        after={image(after)}
        beforeLabel={String(before)}
        afterLabel={String(after)}
        alt="Luci notturne"
      />
      <Legend stops={n.legend?.color_stops} labels={n.legend?.labels} />
      {before !== after && <NightNumbers key={compare} path={compare} />}
      <p className="small">{n.caption}</p>
      <p className="credit">{n.attribution}</p>
    </div>
  )
}
