import { useState } from 'react'
import { formatDate, formatNumber } from './common.jsx'

const W = 440
const H = 190
const PAD = { l: 42, r: 12, t: 14, b: 26 }

function dayOfYear(iso) {
  const d = new Date(`${iso.slice(0, 10)}T12:00:00Z`)
  return Math.floor((d - Date.UTC(d.getUTCFullYear(), 0, 1)) / 86400000)
}

/**
 * "Stesso periodo, anni diversi": un punto per ogni immagine valida della
 * stessa finestra stagionale negli anni passati, la fascia minimo–massimo,
 * la mediana (valore di riferimento) e il valore attuale evidenziato.
 */
export default function SeasonChart({ observations, baseline, latest, digits = 2, unit = '' }) {
  const [hover, setHover] = useState(null)
  const points = observations.map((o) => ({ ...o, year: Number(o.date.slice(0, 4)), current: false }))
  if (latest) points.push({ date: latest.date, value: latest.value, year: Number(latest.date.slice(0, 4)), current: true })
  if (points.length < 2) return null

  const years = [...new Set(points.map((p) => p.year))].sort()
  const values = points.map((p) => p.value)
  if (baseline) values.push(baseline.min, baseline.max)
  let lo = Math.min(...values)
  let hi = Math.max(...values)
  const pad = Math.max((hi - lo) * 0.15, 0.02)
  lo -= pad
  hi += pad

  const colW = (W - PAD.l - PAD.r) / years.length
  const refDoy = latest ? dayOfYear(latest.date) : dayOfYear(points[0].date)
  const x = (p) => {
    const center = PAD.l + colW * (years.indexOf(p.year) + 0.5)
    // Posizione nella finestra di ±15 giorni attorno alla stessa data
    const shift = Math.max(-1, Math.min(1, (dayOfYear(p.date) - refDoy) / 20))
    return center + shift * colW * 0.3
  }
  const y = (v) => H - PAD.b - ((v - lo) / (hi - lo)) * (H - PAD.t - PAD.b)
  const ticks = [lo + pad, (lo + hi) / 2, hi - pad]

  return (
    <div className="chart season-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label="Valori dello stesso periodo negli anni precedenti e valore attuale">
        {baseline && (
          <>
            <rect x={PAD.l} width={W - PAD.l - PAD.r} y={y(baseline.max)} height={Math.max(1, y(baseline.min) - y(baseline.max))}
              className="range-band" />
            <line x1={PAD.l} x2={W - PAD.r} y1={y(baseline.median)} y2={y(baseline.median)} className="median-line" />
            <text x={W - PAD.r - 2} y={y(baseline.median) - 5} textAnchor="end" className="axis strong">riferimento</text>
          </>
        )}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={PAD.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{formatNumber(v, digits)}</text>
          </g>
        ))}
        {years.map((yr, i) => (
          <text key={yr} x={PAD.l + colW * (i + 0.5)} y={H - 8} textAnchor="middle" className="axis">{yr}</text>
        ))}
        {points.map((p, i) => (
          <g key={`${p.date}-${i}`} onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
            <circle cx={x(p)} cy={y(p.value)} r="12" fill="transparent" />
            <circle cx={x(p)} cy={y(p.value)} r={p.current ? 6.5 : 4.5}
              className={p.current ? 'pt current' : 'pt'} />
          </g>
        ))}
      </svg>
      <p className="chart-readout small">
        {hover != null
          ? <>{points[hover].current ? 'Ora' : 'Anni precedenti'} · {formatDate(points[hover].date)}: <strong>{formatNumber(points[hover].value, digits)}{unit}</strong></>
          : <span className="muted">
              Punti grigi: immagini dello stesso periodo (±15 giorni) negli anni precedenti. Fascia: intervallo
              osservato. Linea: valore di riferimento (mediana). Punto arancione: valore attuale.
            </span>}
      </p>
    </div>
  )
}
