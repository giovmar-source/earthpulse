import { useEffect, useMemo, useState } from 'react'
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

/** "Oltre la Terra": Luna, Marte, Giove e le sue lune in 3D. */
export default function SpaceView({ onClose }) {
  const [key, setKey] = useState('moon')
  const body = BODIES.find((b) => b.key === key)
  const now = useNow()
  return (
    <div className="space">
      <div className="space-stage">
        <Sphere3D texture={body.texture} flattening={key === 'jupiter' ? 0.065 : 0} />
        <p className="space-hint">Trascina per girare · rotella o due dita per avvicinarti</p>
      </div>
      <aside className="panel wide space-panel">
        <button className="close" onClick={onClose} aria-label="Torna alla Terra">×</button>
        <p className="eyebrow">Oltre la Terra</p>
        {GROUPS.map((g) => (
          <div key={g.title}>
            <p className="group-title">{g.title}</p>
            <div className="chips">
              {g.keys.map((k) => (
                <button key={k} className={k === key ? 'chip on' : 'chip'} onClick={() => setKey(k)}>
                  {BODIES.find((b) => b.key === k).name}
                </button>
              ))}
            </div>
          </div>
        ))}
        <h2>{body.name}</h2>
        <p className="muted">{body.tagline}</p>
        <LiveBox body={body} now={now} />
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
