import { useEffect, useMemo, useState } from 'react'
import { apiUrl, getJson } from '../api.js'
import { useApi } from '../place/common.jsx'
import Sphere3D from './Sphere3D.jsx'
import { BODIES } from './bodies.js'
import { jupiterMoonsNow, moonNow, planetNow } from './live.js'

const GROUPS = [
  { title: 'Vicino a noi', keys: ['moon', 'mars'] },
  { title: 'Giove e le sue lune', keys: ['jupiter', 'io', 'europa', 'ganymede', 'callisto'] },
]
const GALILEAN = ['io', 'europa', 'ganymede', 'callisto']
const MOON_LABEL = { io: 'Io', europa: 'Europa', ganymede: 'Ganimede', callisto: 'Callisto' }

function km(value) {
  return `${Math.round(value).toLocaleString('it-IT')} km`
}
function millionKm(value) {
  return `${(value / 1e6).toLocaleString('it-IT', { maximumFractionDigits: 1 })} milioni di km`
}

/** Aggiorna "adesso" ogni minuto. */
function useNow() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60000)
    return () => clearInterval(timer)
  }, [])
  return now
}

/** Lune di Giove come in un binocolo: Giove al centro, est a sinistra. */
function JupiterSky({ data: raw, highlight }) {
  let data = raw
  const W = 440
  const H = 90
  // Le lune stanno sul piano dell'equatore di Giove, inclinato rispetto all'est-ovest
  // del cielo: ruotiamo il disegno perché la loro linea sia orizzontale.
  const sxy = GALILEAN.reduce((s, k) => s + data.moons[k].east * data.moons[k].north, 0)
  const sxx = GALILEAN.reduce((s, k) => s + data.moons[k].east ** 2, 0) || 1
  const tilt = Math.atan2(sxy, sxx)
  const rotated = Object.fromEntries(GALILEAN.map((k) => {
    const { east, north, behind } = data.moons[k]
    return [k, { east: east * Math.cos(tilt) + north * Math.sin(tilt), north: -east * Math.sin(tilt) + north * Math.cos(tilt), behind }]
  }))
  data = { ...data, moons: rotated }
  const maxEast = Math.max(30, ...GALILEAN.map((k) => Math.abs(data.moons[k].east))) * 1.08
  const x = (east) => W / 2 - (east / maxEast) * (W / 2 - 14)
  const r = Math.max(3, (W / 2 - 14) / maxEast)
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="jupiter-sky" role="img" aria-label="Posizione delle lune di Giove">
      <line x1="10" x2={W - 10} y1={H / 2} y2={H / 2} className="axis-line" />
      <circle cx={W / 2} cy={H / 2} r={r} className="jupiter-dot" />
      {GALILEAN.map((key) => {
        const m = data.moons[key]
        const hidden = m.behind && Math.abs(m.east) < 1
        const cx = x(m.east)
        const cy = H / 2 - Math.max(-30, Math.min(30, (m.north / maxEast) * (W / 2 - 14)))
        return (
          <g key={key} opacity={hidden ? 0.3 : 1}>
            <circle cx={cx} cy={cy} r={key === highlight ? 5.5 : 4} className={key === highlight ? 'moon-dot on' : 'moon-dot'} />
            <text x={cx} y={key === 'io' || key === 'ganymede' ? cy - 10 : cy + 18} textAnchor="middle" className="moon-label">
              {MOON_LABEL[key]}
            </text>
          </g>
        )
      })}
      <text x="10" y="12" className="moon-label">Est</text>
      <text x={W - 10} y="12" textAnchor="end" className="moon-label">Ovest</text>
    </svg>
  )
}

function LiveBox({ body, now }) {
  const live = useMemo(() => {
    if (body.key === 'moon') return { moon: moonNow(now) }
    if (body.key === 'mars') return { planet: planetNow('Mars', now) }
    return { jupiter: jupiterMoonsNow(now) }
  }, [body.key, now])

  if (live.moon) {
    const m = live.moon
    return (
      <div className="live">
        <span className="live-dot" /> Adesso: <strong>{m.phase}</strong>, illuminata al{' '}
        {Math.round(m.illuminated * 100)}%. È a {km(m.distanceKm)} da noi. Prossima fase:{' '}
        {m.next.name.toLowerCase()} il {m.next.date.toLocaleDateString('it-IT', { day: 'numeric', month: 'long' })}.
      </div>
    )
  }
  if (live.planet) {
    return (
      <div className="live">
        <span className="live-dot" /> Adesso Marte è a <strong>{millionKm(live.planet.distanceKm)}</strong> dalla
        Terra: la sua luce impiega {Math.round(live.planet.lightMinutes)} minuti ad arrivare fino a noi.
      </div>
    )
  }
  const j = live.jupiter
  const isMoon = GALILEAN.includes(body.key)
  const sel = isMoon ? j.moons[body.key] : null
  return (
    <div className="live">
      <span className="live-dot" /> Adesso Giove è a <strong>{millionKm(j.distanceKm)}</strong>: la sua luce
      impiega {Math.round(j.lightMinutes)} minuti ad arrivare.
      {sel && (
        <> {body.name} si trova {Math.abs(sel.east) < 1
          ? (sel.behind ? 'dietro a Giove, nascosta' : 'davanti a Giove')
          : `a ${Math.round(Math.abs(sel.east))} ${Math.round(Math.abs(sel.east)) === 1 ? 'raggio' : 'raggi'} di Giove (${km(Math.abs(sel.east) * 71492)}) verso ${sel.east > 0 ? 'est' : 'ovest'}, come la vediamo dalla Terra`}.</>
      )}
      <JupiterSky data={j} highlight={isMoon ? body.key : null} />
      <p className="muted small">Come le vedresti con un binocolo: le quattro lune scoperte da Galileo nel 1610.</p>
    </div>
  )
}

// Corpi con mappe tematiche e altitudine calcolate dal server
const MAPPED = ['moon', 'mars']

function formatLat(lat) {
  return `${Math.abs(lat).toLocaleString('it-IT', { maximumFractionDigits: 1 })}° ${lat >= 0 ? 'N' : 'S'}`
}
function formatLon(lon) {
  return `${Math.abs(lon).toLocaleString('it-IT', { maximumFractionDigits: 1 })}° ${lon >= 0 ? 'E' : 'O'}`
}

/** Legenda di una mappa tematica: colori con le soglie al loro posto. */
function SpaceLegend({ legend }) {
  if (legend.gradient) {
    return (
      <div className="legend">
        <div className="legend-bar" style={{ background: `linear-gradient(90deg, ${legend.gradient.join(', ')})` }} />
        <div className="legend-labels">{legend.labels.map((l) => <span key={l}>{l}</span>)}</div>
      </div>
    )
  }
  const gradient = legend.color_stops.map((c, i) => `${c} ${(legend.positions[i] * 100).toFixed(1)}%`).join(', ')
  return (
    <div className="legend">
      <div className="legend-bar" style={{ background: `linear-gradient(90deg, ${gradient})` }} />
      <div className="legend-ticks">
        {legend.labels.map((l, i) => (
          <span key={l} style={{ left: `${legend.positions[i] * 100}%` }}>{l}</span>
        ))}
      </div>
    </div>
  )
}

/** Punto toccato sul globo: coordinate e altitudine. */
function PointBox({ body, point, onClear }) {
  const result = useApi(
    (signal) => getJson('/api/v1/space/elevation',
      { body, lat: point.lat.toFixed(3), lon: point.lon.toFixed(3) }, { signal }),
    [body, point.lat, point.lon],
  )
  const e = result.status === 'ok' ? result.data : null
  return (
    <div className="point-box">
      <div>
        <strong>{formatLat(point.lat)}, {formatLon(point.lon)}</strong>
        <button className="link" onClick={onClear}>Togli il punto</button>
      </div>
      {result.status === 'error' && <p className="muted small">Altitudine non disponibile: {result.error}</p>}
      {(result.status === 'loading' || result.status === 'idle') && <p className="muted small">Lettura dell'altitudine…</p>}
      {e && (
        <p className="small">
          Altitudine <strong>{e.elevation_m > 0 ? '+' : ''}{e.elevation_m.toLocaleString('it-IT')} m</strong>{' '}
          <span className="muted">rispetto al {e.reference}; media su un pixel di circa {e.pixel_km.toLocaleString('it-IT')} km.</span>
        </p>
      )}
    </div>
  )
}

/** "Oltre la Terra": Luna, Marte, Giove e le sue lune in 3D. */
export default function SpaceView({ onClose }) {
  const [key, setKey] = useState('moon')
  const [mapKey, setMapKey] = useState('photo')
  const [point, setPoint] = useState(null)
  const [textureState, setTextureState] = useState('ok')
  const body = BODIES.find((b) => b.key === key)
  const mapped = MAPPED.includes(key)
  const now = useNow()
  const layers = useApi(
    (signal) => getJson('/api/v1/space/layers', { body: key }, { signal }),
    [key],
    mapped,
  )
  const available = mapped && layers.status === 'ok' ? layers.data.layers : []
  const layer = available.find((l) => l.key === mapKey) || null
  const texture = layer ? apiUrl(layer.image) : body.texture

  function choose(k) {
    setKey(k)
    setMapKey('photo')
    setPoint(null)
  }

  return (
    <div className="space">
      <div className="space-stage">
        <Sphere3D texture={texture} flattening={key === 'jupiter' ? 0.065 : 0}
          onTextureState={setTextureState} onPick={mapped ? setPoint : undefined} marker={point} />
        {textureState === 'loading' && layer && (
          <p className="space-status"><span className="spinner" /> Preparazione della mappa… la prima volta può servire un minuto.</p>
        )}
        {textureState === 'error' && layer && (
          <p className="space-status error">Mappa non disponibile in questo momento. Riprova più tardi.</p>
        )}
        <p className="space-hint">
          Trascina per girare · rotella o due dita per avvicinarti{mapped && ' · tocca un punto per leggerne l\'altitudine'}
        </p>
      </div>
      <aside className="panel wide space-panel">
        <button className="close" onClick={onClose} aria-label="Torna alla Terra">×</button>
        <p className="eyebrow">Oltre la Terra</p>
        {GROUPS.map((g) => (
          <div key={g.title}>
            <p className="group-title">{g.title}</p>
            <div className="chips">
              {g.keys.map((k) => (
                <button key={k} className={k === key ? 'chip on' : 'chip'} onClick={() => choose(k)}>
                  {BODIES.find((b) => b.key === k).name}
                </button>
              ))}
            </div>
          </div>
        ))}
        <h2>{body.name}</h2>
        <p className="muted">{body.tagline}</p>
        <LiveBox body={body} now={now} />
        {mapped && (
          <div className="space-maps">
            <p className="eyebrow spaced">Mappa sul globo</p>
            <div className="chips">
              <button className={!layer ? 'chip on' : 'chip'} onClick={() => setMapKey('photo')}>Immagine</button>
              {available.map((l) => (
                <button key={l.key} className={layer?.key === l.key ? 'chip on' : 'chip'} onClick={() => setMapKey(l.key)}>
                  {l.label}
                </button>
              ))}
              {layers.status === 'loading' && <span className="muted small">Carico le mappe…</span>}
            </div>
            {layers.status === 'error' && <p className="muted small">Mappe tematiche non disponibili: {layers.error}</p>}
            {layer && (
              <>
                <SpaceLegend legend={layer.legend} />
                <p className="small">{layer.caption}</p>
                <p className="credit">{layer.attribution}</p>
              </>
            )}
            {point
              ? <PointBox body={key} point={point} onClear={() => setPoint(null)} />
              : <p className="muted small">Tocca un punto del globo per leggerne coordinate e altitudine.</p>}
          </div>
        )}
        <p>{body.story}</p>
        <dl className="facts">
          {body.facts.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>
        <div className="box">
          <p className="eyebrow">Chi lo osserva</p>
          <ul className="missions">{body.missions.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
        <p className="credit">{body.credit}. Posizioni calcolate nel browser con astronomy-engine.</p>
      </aside>
    </div>
  )
}
