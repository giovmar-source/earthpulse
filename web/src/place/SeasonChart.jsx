import { useState } from 'react'
import { formatDate, formatNumber } from './common.jsx'

const W = 440
const H = 170
const PAD = { l: 40, r: 14, t: 14, b: 24 }

function median(values) {
  const s = [...values].sort((a, b) => a - b)
  const m = Math.floor(s.length / 2)
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2
}

function shortDate(iso) {
  return new Date(`${iso.slice(0, 10)}T12:00:00Z`).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

/**
 * "Stesso periodo, anni diversi", nello stile dei grafici dell'atmosfera:
 * una colonna per anno (valore tipico delle immagini di quelle settimane),
 * l'ultima colonna è il valore di adesso. Fascia: intervallo degli anni
 * scorsi; linea tratteggiata: valore di riferimento ("di solito").
 */
export default function SeasonChart({ observations, baseline, latest, digits = 2, unit = '' }) {
  const [hover, setHover] = useState(null)

  const byYear = new Map()
  observations.forEach((o) => {
    const year = Number(o.date.slice(0, 4))
    if (!byYear.has(year)) byYear.set(year, [])
    byYear.get(year).push(o)
  })
  const columns = [...byYear.entries()].sort(([a], [b]) => a - b).map(([year, obs]) => ({
    label: String(year), value: median(obs.map((o) => o.value)), obs, current: false,
  }))
  if (latest) columns.push({ label: 'ora', value: latest.value, obs: [latest], current: true })
  if (columns.length < 2) return null

  const values = observations.map((o) => o.value).concat(columns.map((c) => c.value))
  if (baseline?.min != null) values.push(baseline.min, baseline.max)
  let lo = Math.min(...values)
  let hi = Math.max(...values)
  const span = Math.max(hi - lo, 0.04)
  lo -= span * 0.2
  hi += span * 0.2

  const step = (W - PAD.l - PAD.r) / columns.length
  const x = (i) => PAD.l + step * (i + 0.5)
  const y = (v) => H - PAD.b - ((v - lo) / (hi - lo)) * (H - PAD.t - PAD.b)
  const ticks = [lo + span * 0.2, (lo + hi) / 2, hi - span * 0.2]
  const past = columns.filter((c) => !c.current)
  const pastPath = past.map((c, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(c.value).toFixed(1)}`).join('')
  const lastPast = past.length - 1
  const ref = baseline?.median

  function onMove(event) {
    const rect = event.currentTarget.getBoundingClientRect()
    const px = ((event.clientX - rect.left) / rect.width) * W
    const i = Math.floor((px - PAD.l) / step)
    setHover(i >= 0 && i < columns.length ? i : null)
  }

  const h = hover != null ? columns[hover] : null
  return (
    <div className="chart season-chart">
      <div className="chart-legend small">
        <span><i className="key line" /> Stesse settimane, anni scorsi</span>
        <span><i className="key ref" /> Di solito</span>
        <span><i className="key band" /> Intervallo</span>
        <span><i className="key now-dot" /> Ora</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)}
        role="img" aria-label="Valore dello stesso periodo negli anni precedenti e valore attuale">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{formatNumber(v, digits)}</text>
          </g>
        ))}
        {baseline?.min != null && (
          <rect x={PAD.l} width={W - PAD.l - PAD.r} y={y(baseline.max)}
            height={Math.max(1, y(baseline.min) - y(baseline.max))} className="range-band" />
        )}
        {ref != null && <line x1={PAD.l} x2={W - PAD.r} y1={y(ref)} y2={y(ref)} className="median-line" />}
        {columns.map((c, i) => (
          <text key={c.label} x={x(i)} y={H - 7} textAnchor="middle" className={c.current ? 'axis strong' : 'axis'}>
            {c.current ? `ora · ${shortDate(latest.date)}` : c.label}
          </text>
        ))}
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={PAD.t} y2={H - PAD.b} className="cross" />}
        <path d={pastPath} className="line" />
        {latest && lastPast >= 0 && (
          <line x1={x(lastPast)} y1={y(past[lastPast].value)} x2={x(columns.length - 1)} y2={y(latest.value)}
            className="link-now" />
        )}
        {columns.map((c, i) => (
          <circle key={c.label} cx={x(i)} cy={y(c.value)} r={c.current ? 6 : hover === i ? 5 : 3.5}
            className={c.current ? 'pt current' : 'pt'} />
        ))}
      </svg>
      <p className="chart-readout small">
        {h ? (
          h.current ? (
            <>Ora ({formatDate(latest.date)}): <strong>{formatNumber(h.value, digits)}{unit}</strong>
              {ref != null && <> · di solito {formatNumber(ref, digits)}{unit}</>}</>
          ) : (
            <>{h.label}: <strong>{formatNumber(h.value, digits)}{unit}</strong>
              {' '}· {h.obs.length === 1 ? 'immagine del' : `${h.obs.length} immagini:`} {h.obs.map((o) => shortDate(o.date)).join(', ')}</>
          )
        ) : <span className="muted">Passa sul grafico per leggere ogni anno.</span>}
      </p>
    </div>
  )
}
