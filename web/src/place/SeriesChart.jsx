import { useState } from 'react'
import { formatNumber } from './common.jsx'
import { downloadCsv } from '../api.js'

const W = 440
const H = 160
const P = { l: 40, r: 10, t: 12, b: 24 }

function shortDate(iso) {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

/**
 * Serie giornaliera (barre o linea) con lo stesso stile dei grafici dell'atmosfera:
 * griglia, linea di riferimento opzionale, cursore e lettura del valore.
 */
export default function SeriesChart({ series, kind = 'line', unit = '', digits = 1, color = 'var(--green)',
  reference = null, referenceLabel = '', min = null, max = null, csvName = 'serie' }) {
  const [hover, setHover] = useState(null)
  const points = series.filter((p) => p.value != null)
  if (points.length < 2) return <p className="muted small">Troppo pochi dati per un grafico.</p>
  const values = points.map((p) => p.value).concat(reference != null ? [reference] : [])
  let lo = min ?? Math.min(...values)
  let hi = max ?? Math.max(...values)
  if (kind === 'bar') lo = Math.min(0, lo)
  if (hi === lo) hi = lo + 1
  const pad = kind === 'bar' || max != null ? 0 : (hi - lo) * 0.1
  lo -= min != null ? 0 : pad
  hi += max != null ? 0 : pad
  const n = series.length
  const x = (i) => P.l + (n === 1 ? 0 : (i / (n - 1)) * (W - P.l - P.r))
  const y = (v) => H - P.b - ((v - lo) / (hi - lo)) * (H - P.t - P.b)
  const ticks = [lo, (lo + hi) / 2, hi]
  const barW = Math.max(1.5, (W - P.l - P.r) / n - 1)
  let d = ''
  let pen = false
  series.forEach((p, i) => {
    if (p.value == null) { pen = false; return }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`
    pen = true
  })
  const months = series.map((p, i) => [p.date, i]).filter(([iso], i) => i === 0 || iso.endsWith('-01'))

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    const i = Math.round(((px - P.l) / (W - P.l - P.r)) * (n - 1))
    setHover(i >= 0 && i < n ? i : null)
  }
  const h = hover != null ? series[hover] : null
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)} role="img" aria-label="Andamento giornaliero">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={P.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{formatNumber(v, digits)}</text>
          </g>
        ))}
        {months.map(([iso, i]) => <text key={iso} x={x(i)} y={H - 6} className="axis">{shortDate(iso)}</text>)}
        {reference != null && (
          <g>
            <line x1={P.l} x2={W - P.r} y1={y(reference)} y2={y(reference)} className="median-line" />
            {referenceLabel && <text x={W - P.r - 2} y={y(reference) - 4} textAnchor="end" className="axis strong">{referenceLabel}</text>}
          </g>
        )}
        {kind === 'bar'
          ? series.map((p, i) => p.value != null && p.value > 0 && (
            <rect key={p.date} x={x(i) - barW / 2} y={y(p.value)} width={barW} height={y(lo) - y(p.value)} fill={color} opacity={hover === i ? 1 : 0.8} />
          ))
          : <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} className="cross" />}
        {h?.value != null && kind !== 'bar' && <circle cx={x(hover)} cy={y(h.value)} r="4" fill={color} className="dot" />}
      </svg>
      <p className="chart-readout small">
        {h ? <>{shortDate(h.date)}: {h.value == null ? 'nessun dato' : <strong>{formatNumber(h.value, digits)} {unit}</strong>}
          {h.extra && <> · {h.extra}</>}</>
          : <span className="muted">Passa sul grafico per leggere i singoli giorni.</span>}
        {' '}<button className="link csv-link" onClick={() => downloadCsv(series, [['date', 'Data'], ['value', `Valore${unit ? ` (${unit})` : ''}`]], `${csvName}.csv`)}>⬇ CSV</button>
      </p>
    </div>
  )
}
