import { useEffect, useMemo, useState } from 'react'
import Globe from './Globe.jsx'
import { SATELLITE_CARDS } from './satelliteCards.js'
import SatelliteParts from './SatelliteParts.jsx'
import { loadSatellites, periodMinutes, positionAt } from './orbits.js'

function formatCoord(value, positive, negative) {
  return `${Math.abs(value).toFixed(2)}° ${value >= 0 ? positive : negative}`
}

/** Posizione e quota del satellite, aggiornate ogni secondo. */
function useLivePosition(sat) {
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])
  return sat ? positionAt(sat, now) : null
}

function SatellitePanel({ sat, onClose }) {
  const card = SATELLITE_CARDS[sat.card]
  const live = useLivePosition(sat)
  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow" style={{ color: sat.color }}>● {sat.name}</p>
      <h2>{card.title}</h2>
      <p className="muted">{card.agency}</p>
      {live && (
        <div className="live">
          <span className="live-dot" /> In questo momento {sat.name} è sopra{' '}
          <strong>{formatCoord(live.lat, 'N', 'S')}, {formatCoord(live.lon, 'E', 'O')}</strong>,
          {' '}a {Math.round(live.heightKm)} km di quota. Un giro della Terra dura{' '}
          {Math.round(periodMinutes(sat))} minuti.
        </div>
      )}

      <p>{card.intro}</p>
      <SatelliteParts key={sat.card} cardKey={sat.card} title={card.title} />
      <p className="eyebrow section">In sintesi</p>
      <dl className="facts">
        {card.facts.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
      <div className="box">
        <p className="eyebrow">In EarthPulse</p>
        <p>{card.inEarthPulse}</p>
      </div>
      {card.note && <p className="muted small">{card.note}</p>}
      <p className="muted small">
        La linea tratteggiata è la <strong>traccia a terra</strong> del prossimo giro: i punti
        della Terra sopra cui passerà. Quella più tenue è il percorso degli ultimi minuti.
      </p>
    </aside>
  )
}

function PlacePanel({ place, onClose }) {
  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Luogo scelto</p>
      <h2>{formatCoord(place.lat, 'N', 'S')}, {formatCoord(place.lon, 'E', 'O')}</h2>
      <p>
        Qui arriverà l'analisi del luogo: vegetazione, acqua, calore, luci notturne e
        archivio dal 1984, divisi tra <strong>Superficie</strong> e <strong>Atmosfera</strong>.
      </p>
      <p className="muted small">Prossimo passo: collegare questo pannello al backend di EarthPulse.</p>
    </aside>
  )
}

function WelcomePanel({ satellites, error, onSelect }) {
  return (
    <aside className="panel">
      <p className="eyebrow">EarthPulse</p>
      <h2>Cosa vedono i satelliti, spiegato</h2>
      <p>
        Il globo mostra in tempo reale i satelliti che usiamo per analizzare la Terra.
        Tocca un satellite per scoprire com'è fatto, oppure un punto della Terra per sceglierlo.
      </p>
      {error && <p className="error">{error}</p>}
      {!error && satellites.length === 0 && <p className="muted">Calcolo delle orbite…</p>}
      <ul className="sat-list">
        {satellites.map((sat) => (
          <li key={sat.norad}>
            <button onClick={() => onSelect(sat.norad)}>
              <span className="swatch" style={{ background: sat.color }} />
              {sat.name}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}

export default function App() {
  const [satellites, setSatellites] = useState([])
  const [error, setError] = useState(null)
  const [selectedNorad, setSelectedNorad] = useState(null)
  const [place, setPlace] = useState(null)
  const [flyTarget, setFlyTarget] = useState(null)

  useEffect(() => {
    loadSatellites()
      .then(setSatellites)
      .catch((e) => setError(
        `${e.message}. Se il server si stava risvegliando, ricarica la pagina tra un minuto.`,
      ))
  }, [])

  const selected = useMemo(
    () => satellites.find((s) => s.norad === selectedNorad) || null,
    [satellites, selectedNorad],
  )

  function selectSatellite(norad) {
    setPlace(null)
    setSelectedNorad(norad)
    const sat = satellites.find((s) => s.norad === norad)
    const p = sat && positionAt(sat, new Date())
    if (p) setFlyTarget({ lat: p.lat, lon: p.lon, zoom: 1.8 })
  }

  function selectPlace(p) {
    setSelectedNorad(null)
    setPlace(p)
    setFlyTarget({ ...p, marker: true })
  }

  return (
    <div className="app">
      <Globe
        satellites={satellites}
        selectedNorad={selectedNorad}
        onSelectSatellite={selectSatellite}
        onSelectPlace={selectPlace}
        flyTarget={flyTarget}
      />
      <header className="brand">
        <span className="logo">◉</span> EarthPulse
      </header>
      {selected && <SatellitePanel sat={selected} onClose={() => setSelectedNorad(null)} />}
      {!selected && place && <PlacePanel place={place} onClose={() => setPlace(null)} />}
      {!selected && !place && (
        <WelcomePanel satellites={satellites} error={error} onSelect={selectSatellite} />
      )}
    </div>
  )
}
