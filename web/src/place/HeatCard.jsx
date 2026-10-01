import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, formatNumber, useApi } from './common.jsx'

const SIDE_OPTIONS = [4, 8, 12]

/** Isole di calore: temperatura delle superfici d'estate (Landsat 8-9). */
export default function HeatCard({ place }) {
  const [sideKm, setSideKm] = useState(8)
  const [view, setView] = useState('anomaly')
  const result = useApi(
    (signal) => getJson('/api/v1/heat', placeParams(place, sideKm.toFixed(1), 5), { signal }),
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
          : <Loading text="Lettura delle giornate estive Landsat…" hint="Più giornate limpide degli ultimi anni: può servire un minuto." />}
      </>
    )
  }

  const h = result.data
  const legend = h.legend || {}
  const views = [
    ['anomaly', 'Più caldo / più fresco'],
    ['temperature', 'Temperatura'],
    ...(h.images.rgb ? [['rgb', 'Colori reali']] : []),
  ]
  const current = views.find(([k]) => k === view) ? view : 'anomaly'
  const legendFor = current === 'rgb' ? null : legend[current]

  return (
    <div>
      {sizes}
      <div className="chips layers">
        {views.map(([k, label]) => (
          <button key={k} className={k === current ? 'chip on' : 'chip'} onClick={() => setView(k)}>{label}</button>
        ))}
      </div>
      <CompareImages
        key={`${current}-${sideKm}`}
        after={h.images[current]}
        afterLabel={current === 'rgb' ? formatDate(h.rgb_date) : `Estati fino al ${formatDate(h.latest_date)}`}
        alt="Isole di calore"
      />
      {legendFor && <Legend stops={legendFor.color_stops} labels={legendFor.labels} />}
      {legend.water_color && current !== 'rgb' && (
        <p className="muted small"><span className="swatch inline" style={{ background: legend.water_color }} /> Mare e laghi (esclusi)</p>
      )}
      {h.message && <p className="highlight">{h.message}</p>}
      <p className="small">{h.caption}</p>
      <p className="note">⚠ {h.caveat}</p>
      {h.days?.length > 0 && (
        <details className="days">
          <summary>Giornate usate ({h.days.length})</summary>
          <ul>
            {h.days.map((d) => (
              <li key={d.date}>{formatDate(d.date)} · {d.platform} · terraferma {formatNumber(d.land_median_c, 1)} °C</li>
            ))}
          </ul>
        </details>
      )}
      <p className="credit">{h.attribution}</p>
    </div>
  )
}
