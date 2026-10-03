import { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import Globe from './Globe.jsx'
import PlacePanel from './place/PlacePanel.jsx'
import SearchBox from './SearchBox.jsx'
import MethodologyPanel from './MethodologyPanel.jsx'
import CreditsPanel from './CreditsPanel.jsx'
import AccountPanel from './account/AccountPanel.jsx'
import { useAccount } from './account/useAccount.js'
import { APP_NAME, TAGLINE } from './brand.js'
import BigEvents from './events/BigEvents.jsx'
import { getJson } from './api.js'

// three.js serve solo qui: si scarica quando apri "Oltre la Terra"
const SpaceView = lazy(() => import('./space/SpaceView.jsx'))
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
          {' '}a {Math.round(live.heightKm).toLocaleString('it-IT')} km di quota.{' '}
          {periodMinutes(sat) > 1000
            ? 'Gira alla stessa velocità della Terra: per questo resta sempre sopra lo stesso punto.'
            : `Un giro della Terra dura ${Math.round(periodMinutes(sat))} minuti.`}
        </div>
      )}

      <p>{card.intro}</p>
      <SatelliteParts key={sat.card} cardKey={sat.card} title={card.title} />
      <p className="eyebrow spaced">In sintesi</p>
      <dl className="facts">
        {card.facts.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
      <div className="box">
        <p className="eyebrow">In {APP_NAME}</p>
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

function WelcomePanel({ satellites, error, onSelect }) {
  return (
    <aside className="panel">
      <p className="eyebrow">{APP_NAME}</p>
      <h2>{TAGLINE}</h2>
      <p>
        Il globo mostra in tempo reale i satelliti che usiamo per analizzare la Terra.
        Tocca un satellite per scoprire com'è fatto. Per analizzare un luogo, toccalo sul
        globo oppure cercalo per nome.
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
  const [showMethod, setShowMethod] = useState(false)
  const [showCredits, setShowCredits] = useState(false)
  const [showAccount, setShowAccount] = useState(false)
  const account = useAccount()
  const [showSpace, setShowSpace] = useState(false)
  // Big Events: pannello, evento scelto e punti sul globo
  const [showEvents, setShowEvents] = useState(false)
  const [eventId, setEventId] = useState(null)
  const [eventList, setEventList] = useState([])
  useEffect(() => {
    if (!showEvents || eventList.length) return
    getJson('/api/v1/stories').then((d) => setEventList(d.stories)).catch(() => {})
  }, [showEvents, eventList.length])
  const selectedEvent = eventList.find((e) => e.id === eventId) || null

  function openEvents() {
    setShowMethod(false)
    setShowEvents(true)
  }
  function selectEvent(id) {
    setShowEvents(true)
    setEventId(id)
    const e = eventList.find((x) => x.id === id)
    if (e) setFlyTarget({ lat: e.latitude, lon: e.longitude, zoom: e.side_km >= 10 ? 10.5 : 12, marker: false })
  }
  function closeEvents() {
    setShowEvents(false)
    setEventId(null)
  }

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
    if (p) setFlyTarget({ lat: p.lat, lon: p.lon, zoom: 1.8, marker: false })
  }

  function selectPlace(p) {
    setShowEvents(false)
    setEventId(null)
    setSelectedNorad(null)
    setPlace(p)
    setFlyTarget({ ...p, marker: true, zoom: 13 })
    // Punto scelto sul globo: cerchiamo il nome del comune o della località
    if (!p.name) {
      getJson('/api/v1/reverse-geocode', { lat: p.lat.toFixed(5), lon: p.lon.toFixed(5) })
        .then((r) => {
          if (!r.name) return
          setPlace((current) => (current && current.lat === p.lat && current.lon === p.lon
            ? { ...current, name: r.name, context: r.context } : current))
        })
        .catch(() => { /* senza nome restano le coordinate */ })
    }
  }

  function closePlace() {
    setPlace(null)
    setFlyTarget({ lat: place.lat, lon: place.lon, zoom: 1.6, marker: false })
  }

  return (
    <div className="app">
      <Globe
        satellites={satellites}
        selectedNorad={selectedNorad}
        onSelectSatellite={selectSatellite}
        onSelectPlace={selectPlace}
        flyTarget={flyTarget}
        area={showEvents
          ? (selectedEvent ? { lat: selectedEvent.latitude, lon: selectedEvent.longitude, sideKm: selectedEvent.side_km } : null)
          : (!selected && place ? { lat: place.lat, lon: place.lon, sideKm: 1 } : null)}
        wide={showEvents || (!selected && !!place)}
        events={showEvents ? eventList : []}
        onSelectEvent={selectEvent}
      />
      <header className="topbar">
        <div className="brand"><span className="logo">◉</span> {APP_NAME}</div>
        <SearchBox onSelect={selectPlace} />
        <button className="topbar-btn" onClick={openEvents} title="Big Events">⚡<span> Big Events</span></button>
        <button className="topbar-btn" onClick={() => setShowSpace(true)} title="Oltre la Terra">🪐<span> Oltre la Terra</span></button>
        <button className="topbar-btn" onClick={() => setShowMethod(true)} title="Metodologia">ⓘ<span> Metodologia</span></button>
        <button className="topbar-btn" onClick={() => setShowAccount(true)} title="Account e piani">
          👤<span> {account.user ? 'Il mio account' : 'Account'}</span>
        </button>
      </header>
      {showSpace && (
        <Suspense fallback={<div className="space"><p className="space-hint">Caricamento…</p></div>}>
          <SpaceView onClose={() => setShowSpace(false)} />
        </Suspense>
      )}
      {showEvents && !showMethod && !showCredits && !showAccount && (
        <BigEvents onClose={closeEvents} selectedId={eventId} onSelect={(id) => (id ? selectEvent(id) : setEventId(null))} />
      )}
      {showMethod && !showCredits && (
        <MethodologyPanel onClose={() => setShowMethod(false)} onCredits={() => setShowCredits(true)} />
      )}
      {showCredits && <CreditsPanel onClose={() => setShowCredits(false)} />}
      {showAccount && !showMethod && !showCredits && (
        <AccountPanel account={account} onClose={() => setShowAccount(false)}
          onOpenPlace={(p) => { setShowAccount(false); selectPlace({ lat: p.lat, lon: p.lon, name: p.name }) }} />
      )}
      {/* Con la metodologia aperta gli altri pannelli restano caricati ma nascosti */}
      <div hidden={showMethod || showEvents || showCredits || showAccount}>
      {selected && <SatellitePanel sat={selected} onClose={() => setSelectedNorad(null)} />}
      {!selected && place && <PlacePanel place={place} onClose={closePlace} onMethodology={() => setShowMethod(true)} account={account} />}
      {!selected && !place && (
        <WelcomePanel satellites={satellites} error={error} onSelect={selectSatellite} />
      )}
      </div>
    </div>
  )
}
