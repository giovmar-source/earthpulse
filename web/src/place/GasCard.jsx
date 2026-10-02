import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, formatNumber, useApi } from './common.jsx'

const GAS_OPTIONS = [
  { key: 'no2', label: 'NO₂ · biossido di azoto', mapDays: 7, digits: 0 },
  { key: 'ch4', label: 'CH₄ · metano', mapDays: 30, digits: 0 },
  { key: 'co', label: 'CO · monossido di carbonio', mapDays: 7, digits: 1 },
]
const RANGES = [30, 90, 365]
const DAY = 86400000

function dayIndex(iso, startIso) {
  return Math.round((Date.parse(`${iso}T12:00:00Z`) - Date.parse(`${startIso}T12:00:00Z`)) / DAY)
}

/** Media mobile su 7 giorni (solo dove ci sono almeno 3 valori nella finestra). */
function rolling(points, total) {
  const byDay = new Map(points.map((p) => [p.i, p.value]))
  const out = []
  for (let i = 0; i < total; i += 1) {
    const window = []
    for (let k = i - 3; k <= i + 3; k += 1) if (byDay.has(k)) window.push(byDay.get(k))
    out.push(window.length >= 3 ? window.reduce((a, b) => a + b, 0) / window.length : null)
  }
  return out
}

function path(values, x, y) {
  let d = ''
  let pen = false
  values.forEach((v, i) => {
    if (v == null) { pen = false; return }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
    pen = true
  })
  return d
}

/** Andamento sul luogo: valori giornalieri, media su 7 giorni e anno precedente. */
function TrendChart({ data, digits }) {
  const [hover, setHover] = useState(null)
  const W = 440
  const H = 190
  const P = { l: 40, r: 10, t: 12, b: 24 }
  const start = data.period.start
  const total = data.period.days
  const now = data.series.map((p) => ({ i: dayIndex(p.date, start), value: p.value, date: p.date }))
  const prevStart = `${Number(start.slice(0, 4)) - 1}${start.slice(4)}`
  const prev = data.previous.map((p) => ({ i: dayIndex(p.date, prevStart), value: p.value, date: p.date }))
  const nowLine = rolling(now, total)
  const prevLine = rolling(prev, total)
  const all = [...now.map((p) => p.value), ...prevLine.filter((v) => v != null)]
  if (all.length < 2) return <p className="muted small">Troppo pochi giorni con dati validi per un grafico.</p>
  const lo = Math.min(...all)
  const hi = Math.max(...all)
  const pad = (hi - lo) * 0.1 || 1
  const y = (v) => H - P.b - ((v - (lo - pad)) / (hi - lo + 2 * pad)) * (H - P.t - P.b)
  const x = (i) => P.l + (i / Math.max(1, total - 1)) * (W - P.l - P.r)
  const ticks = [lo, (lo + hi) / 2, hi]
  const months = []
  for (let i = 0; i < total; i += 1) {
    const d = new Date(Date.parse(`${start}T12:00:00Z`) + i * DAY)
    if (d.getUTCDate() === 1) months.push([i, d.toLocaleDateString('it-IT', { month: 'short' })])
  }
  const hoverNow = hover != null ? now.find((p) => p.i === hover) : null

  function onMove(e) {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = ((e.clientX - rect.left) / rect.width) * W
    const i = Math.round(((px - P.l) / (W - P.l - P.r)) * (total - 1))
    setHover(i >= 0 && i < total ? i : null)
  }

  return (
    <div className="chart">
      <div className="chart-legend small">
        <span><i className="key now" /> Media su 7 giorni, ultimi {total} giorni</span>
        <span><i className="key prev" /> Stesso periodo, anno precedente</span>
        <span><i className="key dot" /> Valore del singolo giorno</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)}
        role="img" aria-label="Andamento del gas sul luogo">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={P.l} x2={W - P.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={P.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{formatNumber(v, digits)}</text>
          </g>
        ))}
        {months.map(([i, label]) => <text key={i} x={x(i)} y={H - 6} className="axis">{label}</text>)}
        {now.map((p) => <circle key={p.i} cx={x(p.i)} cy={y(p.value)} r="2.2" className="day-dot" />)}
        <path d={path(prevLine, x, y)} className="trend-prev" />
        <path d={path(nowLine, x, y)} className="trend-now" />
        {hover != null && <line x1={x(hover)} x2={x(hover)} y1={P.t} y2={H - P.b} className="cross" />}
      </svg>
      <p className="chart-readout small">
        {hover != null ? (
          <>
            {new Date(Date.parse(`${start}T12:00:00Z`) + hover * DAY).toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })}:{' '}
            {hoverNow ? <strong>{formatNumber(hoverNow.value, digits)} {data.unit}</strong> : 'nessun dato (nuvole)'}
            {nowLine[hover] != null && <> · media 7 giorni {formatNumber(nowLine[hover], digits)}</>}
            {prevLine[hover] != null && <> · anno prima {formatNumber(prevLine[hover], digits)}</>}
          </>
        ) : <span className="muted">Passa sul grafico per leggere i singoli giorni.</span>}
      </p>
    </div>
  )
}

function signedPercent(v) {
  return v == null ? '—' : `${v > 0 ? '+' : ''}${formatNumber(v, 0)}%`
}

/** Gas dal satellite: andamento sul luogo e confronto con l'anno precedente. */
export default function GasCard({ place }) {
  const [gas, setGas] = useState(GAS_OPTIONS[0])
  const [range, setRange] = useState(90)
  const coords = placeParams(place, null, 4)
  const series = useApi(
    (signal) => getJson('/api/v1/s5p/timeseries', { gas: gas.key, ...coords, days: String(range) }, { signal }),
    [place.lat, place.lon, gas.key, range],
  )
  const map = useApi(
    (signal) => getJson('/api/v1/s5p', { gas: gas.key, ...coords, days: String(gas.mapDays) }, { signal }),
    [place.lat, place.lon, gas.key],
  )
  const s = series.status === 'ok' ? series.data : null
  const m = map.status === 'ok' ? map.data : null

  return (
    <div>
      <div className="chips">
        {GAS_OPTIONS.map((g) => (
          <button key={g.key} className={g.key === gas.key ? 'chip on' : 'chip'} onClick={() => setGas(g)}>{g.label}</button>
        ))}
      </div>

      <p className="eyebrow spaced">Sul luogo · entro 15 km dal punto</p>
      <div className="chips">
        <span className="muted small">Periodo:</span>
        {RANGES.map((n) => (
          <button key={n} className={n === range ? 'chip on' : 'chip'} onClick={() => setRange(n)}>
            {n === 365 ? '1 anno' : `${n} giorni`}
          </button>
        ))}
      </div>
      {series.status === 'error' && <ErrorBox message={series.error} onRetry={series.retry} />}
      {(series.status === 'loading' || series.status === 'idle') && <Loading text="Lettura dei valori giornalieri…" />}
      {s && (
        <>
          <dl className="facts">
            <div><dt>Media del periodo</dt><dd>{formatNumber(s.mean, gas.digits)} {s.unit}{s.level && ` · ${s.level}`}</dd></div>
            <div><dt>Rispetto all'anno precedente</dt><dd>{signedPercent(s.change_percent)}</dd></div>
            <div><dt>Giorni con dati validi</dt><dd>{s.valid_days} su {s.period.days}</dd></div>
          </dl>
          <TrendChart data={s} digits={gas.digits} />
        </>
      )}

      <p className="eyebrow spaced">Mappa · 300 × 300 km, media degli ultimi {gas.mapDays} giorni</p>
      {map.status === 'error' && <ErrorBox message={map.error} onRetry={map.retry} />}
      {(map.status === 'loading' || map.status === 'idle') && <Loading text="Preparazione delle mappe…" />}
      {m && (
        <>
          <div className="framed">
            <CompareImages
              before={m.image_previous}
              after={m.image}
              beforeLabel={m.previous && `Anno prima`}
              afterLabel="Adesso"
              alt={m.label}
            />
            <span className="place-area" style={{ width: `${(100 * 2 * m.place_radius_km) / m.side_km}%` }}>
              <span>luogo</span>
            </span>
          </div>
          <p className="muted small hint">
            Adesso: {formatDate(m.period.start)} – {formatDate(m.period.end)}
            {m.previous && <> · anno prima: {formatDate(m.previous.period.start)} – {formatDate(m.previous.period.end)}
              {m.previous.change_percent != null && <> · sul luogo {m.previous.change_percent > 0 ? '+' : ''}{formatNumber(m.previous.change_percent, 0)}%</>}</>}
            {m.image_previous && <>. Trascina il cursore per confrontare.</>}
          </p>
          <Legend stops={m.legend.color_stops} labels={m.legend.labels} />
          <p className="muted small">
            <span className="swatch inline" style={{ background: m.legend.no_data_color }} /> Nessun dato:
            nuvole o qualità insufficiente in tutti i passaggi. Il riquadro tratteggiato è l'area &quot;sul luogo&quot;.
          </p>
          {m.message && <p className="highlight">{m.message}</p>}
          <p className="small">{m.caption}</p>
          <p className="muted small">
            Sono quantità di gas nella colonna d'aria sopra il luogo, misurate dal satellite verso
            le 13:30. Non sono concentrazioni al livello della strada: per l'aria che si respira vale
            la sezione &quot;Qualità dell'aria&quot;.
          </p>
          <p className="credit">{m.attribution}</p>
        </>
      )}
    </div>
  )
}
