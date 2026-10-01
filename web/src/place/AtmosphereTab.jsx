import { useEffect, useMemo, useRef, useState } from 'react'
import { ErrorBox, Loading, Section, formatNumber, useApi } from './common.jsx'

// ------------------------------------------------------------------
// QUALITÀ DELL'ARIA: Copernicus CAMS tramite Open-Meteo (gratuito, senza chiave)
// ------------------------------------------------------------------

const AIR_URL = 'https://air-quality-api.open-meteo.com/v1/air-quality'

// Classi dell'indice europeo della qualità dell'aria (EEA)
const AQI_CLASSES = [
  [20, 'Buona', '#50c8a0'],
  [40, 'Discreta', '#a6d96a'],
  [60, 'Moderata', '#f2d15c'],
  [80, 'Scadente', '#f29a4a'],
  [100, 'Molto scadente', '#e05a4f'],
  [Infinity, 'Pessima', '#9a3d7a'],
]
function aqiClass(value) {
  if (value == null) return null
  return AQI_CLASSES.find(([max]) => value <= max)
}

// Inquinanti mostrati: chiave Open-Meteo, nome, sotto-indice europeo, spiegazione
const POLLUTANTS = [
  { key: 'nitrogen_dioxide', label: 'NO₂', name: 'Biossido di azoto', aqi: 'european_aqi_nitrogen_dioxide',
    why: 'Viene soprattutto dal traffico e dalle combustioni: è il gas che Sentinel-5P misura meglio sulle città.' },
  { key: 'pm2_5', label: 'PM2.5', name: 'Polveri fini', aqi: 'european_aqi_pm2_5',
    why: 'Particelle sotto 2,5 millesimi di millimetro: entrano fino in fondo ai polmoni.' },
  { key: 'pm10', label: 'PM10', name: 'Polveri', aqi: 'european_aqi_pm10',
    why: 'Traffico, riscaldamento, ma anche sabbia del Sahara e sale marino.' },
  { key: 'ozone', label: 'O₃', name: 'Ozono', aqi: 'european_aqi_ozone',
    why: "Al suolo si forma con il sole dagli altri inquinanti: è più alto d'estate nel pomeriggio." },
  { key: 'sulphur_dioxide', label: 'SO₂', name: 'Biossido di zolfo', aqi: 'european_aqi_sulphur_dioxide',
    why: 'Industrie, navi e vulcani.' },
]
const EXTRA = [
  { key: 'carbon_monoxide', label: 'Monossido di carbonio (CO)', unit: 'µg/m³', digits: 0 },
  { key: 'methane', label: 'Metano (CH₄)', unit: 'µg/m³', digits: 0 },
  { key: 'dust', label: 'Polvere del deserto', unit: 'µg/m³', digits: 0 },
  { key: 'aerosol_optical_depth', label: 'Foschia (spessore ottico aerosol)', unit: '', digits: 2 },
  { key: 'uv_index', label: 'Indice UV', unit: '', digits: 1 },
]
const CHART_SERIES = [
  { key: 'european_aqi', label: 'Indice europeo', unit: '' },
  ...POLLUTANTS.slice(0, 4).map((p) => ({ key: p.key, label: p.label, unit: 'µg/m³' })),
]

async function loadAir(place, signal) {
  const current = [
    'european_aqi', ...POLLUTANTS.flatMap((p) => [p.key, p.aqi]), ...EXTRA.map((e) => e.key),
  ]
  const params = new URLSearchParams({
    latitude: place.lat.toFixed(4),
    longitude: place.lon.toFixed(4),
    current: current.join(','),
    hourly: CHART_SERIES.map((s) => s.key).join(','),
    past_days: '1',
    forecast_days: '2',
    timezone: 'auto',
  })
  let response
  try {
    response = await fetch(`${AIR_URL}?${params}`, { signal })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Servizio della qualità dell\'aria non raggiungibile. Riprova tra poco.')
  }
  const data = await response.json()
  if (!response.ok || data.error) throw new Error(data.reason || `Errore ${response.status}`)
  return data
}

/** Andamento orario (ieri, oggi, domani) di una grandezza, con il cursore su ogni ora. */
function HourlyChart({ times, values, unit, nowIso, colorFor }) {
  const [hover, setHover] = useState(null)
  const W = 440
  const H = 150
  const pad = { l: 34, r: 8, t: 10, b: 22 }
  const points = values.map((v, i) => [i, v]).filter(([, v]) => v != null)
  if (points.length < 2) return <p className="muted small">Andamento non disponibile.</p>
  const max = Math.max(...points.map(([, v]) => v)) * 1.1 || 1
  const x = (i) => pad.l + (i / (values.length - 1)) * (W - pad.l - pad.r)
  const y = (v) => H - pad.b - (v / max) * (H - pad.t - pad.b)
  const path = points.map(([i, v], k) => `${k ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join('')
  const nowIndex = times.findIndex((t) => t >= nowIso)
  const ticks = [0, max / 2, max].map((v) => Math.round(v))
  const days = times.map((t, i) => [t, i]).filter(([t]) => t.endsWith('T00:00'))

  function onMove(event) {
    const rect = event.currentTarget.getBoundingClientRect()
    const px = ((event.clientX - rect.left) / rect.width) * W
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (values.length - 1))
    setHover(i >= 0 && i < values.length && values[i] != null ? i : null)
  }

  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)} role="img"
        aria-label="Andamento orario">
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} className="grid" />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" className="axis">{v}</text>
          </g>
        ))}
        {days.map(([t, i]) => (
          <text key={t} x={x(i) + 3} y={H - 6} className="axis">
            {new Date(`${t}:00`).toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric' })}
          </text>
        ))}
        {nowIndex > 0 && (
          <g>
            <line x1={x(nowIndex)} x2={x(nowIndex)} y1={pad.t} y2={H - pad.b} className="now" />
            <text x={x(nowIndex) + 4} y={pad.t + 10} className="axis strong">ora</text>
          </g>
        )}
        <path d={path} className="line" />
        {hover != null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={H - pad.b} className="cross" />
            <circle cx={x(hover)} cy={y(values[hover])} r="4.5" fill={colorFor(values[hover])} className="dot" />
          </g>
        )}
      </svg>
      <p className="chart-readout small">
        {hover != null
          ? <>{new Date(`${times[hover]}:00`).toLocaleString('it-IT', { weekday: 'long', hour: '2-digit', minute: '2-digit' })}: <strong>{formatNumber(values[hover], 0)} {unit}</strong></>
          : <span className="muted">Passa sul grafico per leggere ogni ora. A destra di "ora" è la previsione.</span>}
      </p>
    </div>
  )
}

function AirCard({ place }) {
  const result = useApi((signal) => loadAir(place, signal), [place.lat, place.lon])
  const [series, setSeries] = useState('european_aqi')

  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />
  if (result.status !== 'ok') return <Loading text="Lettura dei dati sull'aria…" />

  const d = result.data
  const c = d.current
  const overall = aqiClass(c.european_aqi)
  const chosen = CHART_SERIES.find((s) => s.key === series)
  const nowIso = c.time
  // Colore del punto: per l'indice europeo segue la classe, altrimenti neutro
  const colorFor = (v) => (series === 'european_aqi' ? aqiClass(v)?.[2] : '#3fd68f') || '#3fd68f'

  return (
    <div>
      {overall && (
        <div className="aqi" style={{ '--aqi': overall[2] }}>
          <span className="aqi-value">{Math.round(c.european_aqi)}</span>
          <div>
            <strong>Aria {overall[1].toLowerCase()}</strong>
            <span className="muted small">Indice europeo della qualità dell'aria (0-100+), ora</span>
          </div>
        </div>
      )}

      <ul className="pollutants">
        {POLLUTANTS.map((p) => {
          const cls = aqiClass(c[p.aqi])
          return (
            <li key={p.key} title={p.why}>
              <span className="swatch" style={{ background: cls?.[2] || 'var(--muted)' }} />
              <span className="p-name"><strong>{p.label}</strong> <span className="muted small">{p.name}</span></span>
              <span className="p-value">{formatNumber(c[p.key], 0)} <span className="muted small">µg/m³</span></span>
              <span className="p-class small">{cls?.[1] || '—'}</span>
            </li>
          )
        })}
      </ul>

      <p className="eyebrow spaced">Ieri, oggi e domani</p>
      <div className="chips">
        {CHART_SERIES.map((s) => (
          <button key={s.key} className={s.key === series ? 'chip on' : 'chip'} onClick={() => setSeries(s.key)}>{s.label}</button>
        ))}
      </div>
      <HourlyChart
        key={series}
        times={d.hourly.time}
        values={d.hourly[series]}
        unit={chosen.unit}
        nowIso={nowIso}
        colorFor={colorFor}
      />

      <dl className="facts">
        {EXTRA.filter((e) => c[e.key] != null).map((e) => (
          <div key={e.key}><dt>{e.label}</dt><dd>{formatNumber(c[e.key], e.digits)} {e.unit}</dd></div>
        ))}
      </dl>

      <p className="small">
        Sono stime del servizio europeo <strong>Copernicus CAMS</strong>, che unisce modelli
        dell'atmosfera, stazioni a terra e misure da satellite. In Europa i pixel sono di circa
        11 km, nel resto del mondo di 45 km: descrivono l'aria della zona, non della singola strada.
      </p>
      <p className="credit">Dati: Copernicus Atmosphere Monitoring Service (CAMS) · Open-Meteo.com</p>
    </div>
  )
}

// ------------------------------------------------------------------
// NUVOLE IN DIRETTA: Meteosat di terza generazione (MTG-I1, strumento FCI)
// ------------------------------------------------------------------

const EUMETVIEW = 'https://view.eumetsat.int/geoserver/ows'
const CLOUD_VIEWS = [
  { key: 'mtg_fd:rgb_geocolour', label: 'Colori (giorno e notte)',
    caption: 'Di giorno i colori naturali, di notte le nuvole in grigio-azzurro sopra le luci delle città.' },
  { key: 'mtg_fd:rgb_cloudtype', label: 'Tipo di nubi',
    caption: 'Distingue nubi basse (acqua) da nubi alte (ghiaccio): utile per capire dove si formano i temporali. Solo di giorno.' },
  { key: 'mtg_fd:rgb_dust', label: 'Polvere',
    caption: 'La polvere del deserto appare in rosa-magenta: si vedono le nubi di sabbia del Sahara che arrivano in Europa.' },
]
const RANGES = [
  { key: 'region', label: 'Regione', halfLat: 3 },
  { key: 'wide', label: 'Area vasta', halfLat: 9 },
]
const FRAME_STEP_MIN = 10
const FRAMES = 12           // 2 ore
const DELAY_MIN = 20        // le immagini arrivano sul servizio con circa 15-20 minuti di ritardo

function frameTimes(now = new Date()) {
  const t = new Date(now.getTime() - DELAY_MIN * 60000)
  t.setUTCSeconds(0, 0)
  t.setUTCMinutes(Math.floor(t.getUTCMinutes() / FRAME_STEP_MIN) * FRAME_STEP_MIN)
  return Array.from({ length: FRAMES }, (_, k) => new Date(t.getTime() - (FRAMES - 1 - k) * FRAME_STEP_MIN * 60000))
}

function wmsUrl({ layers, bbox, size, time, png }) {
  const params = new URLSearchParams({
    service: 'WMS', version: '1.1.1', request: 'GetMap', layers, styles: '',
    srs: 'EPSG:4326', bbox: bbox.join(','), width: String(size), height: String(size),
    format: png ? 'image/png' : 'image/jpeg', ...(png ? { transparent: 'true' } : {}),
    ...(time ? { time: time.toISOString().replace('.000Z', 'Z') } : {}),
  })
  return `${EUMETVIEW}?${params}`
}

function CloudsCard({ place }) {
  const [view, setView] = useState(CLOUD_VIEWS[0])
  const [range, setRange] = useState(RANGES[0])
  const [times] = useState(() => frameTimes())
  const [status, setStatus] = useState({})      // stato di ogni fotogramma: ok / error
  const [index, setIndex] = useState(FRAMES - 1)
  const [playing, setPlaying] = useState(false)

  // Riquadro quadrato in km: in longitudine serve più ampiezza lontano dall'equatore
  const bbox = useMemo(() => {
    const halfLon = range.halfLat / Math.max(0.2, Math.cos((place.lat * Math.PI) / 180))
    return [place.lon - halfLon, place.lat - range.halfLat, place.lon + halfLon, place.lat + range.halfLat]
  }, [place.lat, place.lon, range])
  const frames = useMemo(
    () => times.map((time) => wmsUrl({ layers: view.key, bbox, size: 640, time })),
    [times, view, bbox],
  )
  const overlay = wmsUrl({
    layers: 'backgrounds:ne_10m_coastline,backgrounds:ne_boundary_lines_land', bbox, size: 640, png: true,
  })

  useEffect(() => { setStatus({}); setIndex(FRAMES - 1); setPlaying(false) }, [frames])

  const ready = frames.map((_, i) => status[i] === 'ok')
  const available = ready.map((ok, i) => (ok ? i : null)).filter((i) => i != null)
  const shown = ready[index] ? index : available[available.length - 1]

  // Animazione: passa al fotogramma disponibile successivo ogni 0,5 s
  const timer = useRef(null)
  useEffect(() => {
    if (!playing || available.length < 2) return undefined
    timer.current = setInterval(() => {
      setIndex((i) => {
        const next = available.find((k) => k > i)
        return next ?? available[0]
      })
    }, 500)
    return () => clearInterval(timer.current)
  }, [playing, available.join(',')]) // eslint-disable-line react-hooks/exhaustive-deps

  const allFailed = Object.keys(status).length === FRAMES && available.length === 0
  const loadedCount = Object.keys(status).length

  return (
    <div>
      <div className="chips">
        {RANGES.map((r) => (
          <button key={r.key} className={r.key === range.key ? 'chip on' : 'chip'} onClick={() => setRange(r)}>{r.label}</button>
        ))}
      </div>
      <div className="chips layers">
        {CLOUD_VIEWS.map((v) => (
          <button key={v.key} className={v.key === view.key ? 'chip on' : 'chip'} onClick={() => setView(v)}>{v.label}</button>
        ))}
      </div>

      <div className="compare clouds">
        {frames.map((src, i) => (
          <img
            key={src} src={src} alt="" draggable={false}
            onLoad={() => setStatus((s) => ({ ...s, [i]: 'ok' }))}
            onError={() => setStatus((s) => ({ ...s, [i]: 'error' }))}
            style={{ opacity: i === shown ? 1 : 0 }}
          />
        ))}
        <img src={overlay} alt="" className="overlay" draggable={false} onError={(e) => { e.currentTarget.style.display = 'none' }} />
        <span className="place-dot" />
        {shown != null && (
          <span className="tag right">
            {times[shown].toLocaleString('it-IT', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
        {shown == null && !allFailed && (
          <div className="image-overlay"><span className="spinner" /> <span>Immagini dal satellite… {loadedCount}/{FRAMES}</span></div>
        )}
        {allFailed && <div className="image-overlay"><span>Immagini non disponibili in questo momento.</span></div>}
      </div>

      <div className="player">
        <button className="btn small" disabled={available.length < 2} onClick={() => setPlaying((p) => !p)}>
          {playing ? '❚❚ Pausa' : '▶ Ultime 2 ore'}
        </button>
        <input
          type="range" min="0" max={FRAMES - 1} value={shown ?? FRAMES - 1}
          onChange={(e) => { setPlaying(false); setIndex(Number(e.target.value)) }}
          aria-label="Ora dell'immagine"
        />
      </div>
      <p className="small">{view.caption}</p>
      <p className="small muted">
        Meteosat-12 (MTG-I1) è fermo sopra l'equatore, a 36 000 km di quota: vede sempre la
        stessa metà del pianeta e fa un'immagine ogni 10 minuti. Il punto giallo è il luogo scelto.
      </p>
      <p className="credit">Immagini: © EUMETSAT (EUMETView) · Coste e confini: Natural Earth</p>
    </div>
  )
}

// ------------------------------------------------------------------
// SCHEDA ATMOSFERA
// ------------------------------------------------------------------

export default function AtmosphereTab({ place }) {
  const [open, setOpen] = useState({ air: true })
  const toggle = (key) => setOpen((o) => ({ ...o, [key]: !o[key] }))
  // Meteosat vede l'Europa, l'Africa e l'Atlantico (circa da 80° O a 80° E)
  const inMeteosatView = Math.abs(place.lon) <= 75 && Math.abs(place.lat) <= 75
  return (
    <div>
      <Section icon="🌫️" title="Qualità dell'aria" subtitle="Ora e prossime 48 ore · Copernicus CAMS"
        open={!!open.air} onToggle={() => toggle('air')}>
        <AirCard place={place} />
      </Section>
      <Section icon="☁️" title="Nuvole in diretta" subtitle="Ogni 10 minuti · Meteosat di terza generazione"
        open={!!open.clouds} onToggle={() => toggle('clouds')}>
        {inMeteosatView
          ? <CloudsCard place={place} />
          : <p className="note">⚠ Questo luogo è fuori dalla vista di Meteosat, che copre Europa, Africa e Atlantico.</p>}
      </Section>
      <p className="muted small">
        In arrivo: le mappe dei gas misurati direttamente da Sentinel-5P (biossido di azoto,
        metano, monossido di carbonio), con pixel di circa 5 km.
      </p>
    </div>
  )
}
