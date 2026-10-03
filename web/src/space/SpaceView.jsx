import { useEffect, useMemo, useState } from 'react'
import { apiUrl, getJson } from '../api.js'
import { useApi } from '../place/common.jsx'
import Sphere3D from './Sphere3D.jsx'
import { BODIES } from './bodies.js'
import { jupiterMoonsNow, moonNow, planetNow } from './live.js'
import { SolarSystemPanel, SolarSystemStage, useSolarSystem } from './SolarSystem.jsx'
import { SunPanel, SunStage, useSun } from './SunView.jsx'

// Viste speciali (non sono sfere 3D)
const SPECIAL = { system: 'Mappa del Sistema solare', sun: 'Sole' }
// Corpi con i nomi ufficiali IAU (mappe con longitudini verificate)
const NAMED = ['moon', 'mars', 'mercury', 'venus', 'ceres', 'vesta', 'phobos', 'enceladus']
// Tipi del Gazetteer IAU in italiano (prima parola del tipo)
const FEATURE_TYPES = {
  Crater: 'cratere', Mare: 'mare', Mons: 'monte', Montes: 'catena montuosa', Vallis: 'valle',
  Valles: 'valli', Planitia: 'pianura', Planum: 'altopiano', Chasma: 'canyon', Chasmata: 'canyon',
  Rupes: 'scarpata', Dorsum: 'dorsale', Dorsa: 'dorsali', Fossa: 'fossa', Fossae: 'fosse', Lacus: 'lago',
  Palus: 'palude', Oceanus: 'oceano', Sinus: 'baia', Terra: 'regione', Patera: 'caldera',
  Tholus: 'collina vulcanica', Tholi: 'colline vulcaniche', Regio: 'regione', Rima: 'solco', Rimae: 'solchi',
  Catena: 'catena di crateri', Labes: 'frana', Linea: 'linea', Lineae: 'linee', Fluctus: 'colata',
  Corona: 'corona', Undae: 'campo di dune', Mensa: 'mesa', Mensae: 'mese', Colles: 'colline',
  Promontorium: 'promontorio', Satellite: 'cratere satellite', Landing: 'sito di atterraggio',
  Facula: 'macchia chiara', Faculae: 'macchie chiare', Sulcus: 'solco', Sulci: 'solchi',
}

function featureType(type) {
  const first = (type || '').split(/[ ,]/)[0]
  return FEATURE_TYPES[first] || (type ? type.split(',')[0].toLowerCase() : '')
}

const GROUPS = [
  { title: 'Il Sistema solare', keys: ['system', 'sun'] },
  { title: 'Vicino a noi', keys: ['moon', 'mars', 'phobos'] },
  { title: 'Pianeti interni', keys: ['mercury', 'venus'] },
  { title: 'Fascia degli asteroidi', keys: ['ceres', 'vesta'] },
  { title: 'Giove e le sue lune', keys: ['jupiter', 'io', 'europa', 'ganymede', 'callisto'] },
  { title: 'Saturno e le sue lune', keys: ['saturn', 'enceladus', 'titan'] },
  { title: 'Oltre Saturno', keys: ['uranus', 'neptune', 'pluto'] },
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
    if (!body.live) return null
    if (body.live.type === 'moon') return { moon: moonNow(now) }
    if (body.live.type === 'planet') return { planet: planetNow(body.live.target, now), label: body.live.label }
    return { jupiter: jupiterMoonsNow(now) }
  }, [body.live, now])

  if (!live) return null
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
        <span className="live-dot" /> Adesso {live.label} è a <strong>{millionKm(live.planet.distanceKm)}</strong> dalla
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

// Corpi con mappe preparate dal server (gli altri hanno solo la mappa nel sito)
const SERVER_BODIES = ['moon', 'mars', 'phobos', 'mercury', 'venus', 'ceres', 'vesta', 'enceladus', 'titan']

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
          // Con molte soglie scriviamo una etichetta sì e una no (sempre la prima e l'ultima)
          (legend.labels.length <= 7 || i % 2 === 0 || i === legend.labels.length - 1) && (
            <span key={l} style={{ left: `${legend.positions[i] * 100}%` }}>{l}</span>
          )
        ))}
      </div>
    </div>
  )
}

function formatValue(value, digits) {
  return value.toLocaleString('it-IT', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** Punto toccato sul globo: coordinate e valori delle mappe numeriche. */
function PointBox({ body, point, layers, onClear }) {
  const result = useApi(
    (signal) => getJson('/api/v1/space/point',
      { body, lat: point.lat.toFixed(3), lon: point.lon.toFixed(3), layers: layers.join(',') }, { signal }),
    [body, point.lat, point.lon, layers.join(',')],
  )
  const values = result.status === 'ok' ? result.data.values : []
  const place = result.status === 'ok' ? result.data.place : null
  const landing = result.status === 'ok' ? result.data.landing : null
  return (
    <div className="point-box">
      <div>
        <strong>{formatLat(point.lat)}, {formatLon(point.lon)}</strong>
        <button className="link" onClick={onClear}>Togli il punto</button>
      </div>
      {place && (
        <p className="small place-name">
          {place.inside ? 'Dentro: ' : 'Vicino a: '}<strong>{place.name}</strong>
          <span className="muted"> ({featureType(place.type)}{place.diameter_km ? `, ${Math.round(place.diameter_km).toLocaleString('it-IT')} km` : ''})
            {!place.inside && ` a ${Math.round(place.distance_km).toLocaleString('it-IT')} km dal centro`}</span>
          {place.origin && <span className="muted small"> · {place.origin}</span>}
        </p>
      )}
      {landing && (
        <p className="small">🚩 A {landing.distance_km.toLocaleString('it-IT')} km dal sito di atterraggio di <strong>{landing.name}</strong>
          <span className="muted"> ({landing.agency}, {new Date(landing.date).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })})</span></p>
      )}
      {result.status === 'error' && <p className="muted small">Valori non disponibili: {result.error}</p>}
      {result.status === 'loading' && <p className="muted small">Lettura dei valori…</p>}
      {values.length > 0 && (
        <dl className="facts point-values">
          {values.map((v) => (
            <div key={v.key}>
              <dt>{v.label}</dt>
              <dd>
                {v.value == null
                  ? <span className="muted">nessun dato qui</span>
                  : <><strong>{v.key === 'elevation' && v.value > 0 ? '+' : ''}{formatValue(v.value, v.digits)} {v.unit}</strong>
                    {v.reference && <span className="muted small"> {v.reference}</span>}
                    <span className="muted small"> · pixel di {v.pixel_km.toLocaleString('it-IT')} km</span></>}
              </dd>
            </div>
          ))}
        </dl>
      )}
      {values.length > 0 && <p className="muted small">Ogni valore è quello del pixel della mappa che contiene il punto.</p>}
      {result.data?.names_attribution && <p className="credit">{result.data.names_attribution}</p>}
    </div>
  )
}

/** Siti di atterraggio del corpo: elenco con fonte e precisione; un tocco porta il punto lì. */
function LandingSites({ data, onPick }) {
  const [open, setOpen] = useState(false)
  if (!data?.sites?.length) return null
  return (
    <div className="sites">
      <button className="link" onClick={() => setOpen(!open)}>
        🚩 Siti di atterraggio ({data.sites.length}) {open ? '▲' : '▼'}
      </button>
      {open && (
        <ul className="sites-list">
          {data.sites.map((site) => (
            <li key={site.name}>
              <button className="link" onClick={() => onPick(site)} disabled={!data.markers}>
                {site.name}</button>
              <span className="muted small"> · {site.agency}, {site.date.slice(0, 4)} · precisione: {site.precision}</span>
              {site.note && <span className="small"> · {site.note}</span>}
            </li>
          ))}
        </ul>
      )}
      {open && <p className="credit">Coordinate: NASA NSSDCA, LROC, Mars24 ed elenchi pubblici (fonte di ogni sito nel file dei dati).</p>}
    </div>
  )
}

/** Legenda di una mappa: dal catalogo o, per le scale calcolate sui dati, dal server. */
function LayerLegend({ body, layer }) {
  const needsServer = layer.numeric && !layer.legend
  const result = useApi(
    (signal) => getJson('/api/v1/space/legend', { body, layer: layer.key }, { signal }),
    [body, layer.key],
    needsServer,
  )
  const legend = layer.legend || (result.status === 'ok' ? result.data : null)
  if (!legend) return needsServer && result.status === 'loading' ? <p className="muted small">Preparazione della legenda…</p> : null
  return (
    <>
      <SpaceLegend legend={legend} />
      {legend.no_data && (
        <p className="muted small"><span className="swatch inline" style={{ background: legend.no_data }} /> Nessun dato</p>
      )}
    </>
  )
}

/** "Oltre la Terra": Luna, pianeti, asteroidi e lune in 3D, con le mappe del telerilevamento. */
export default function SpaceView({ onClose }) {
  const [key, setKey] = useState('system')
  const [mapKey, setMapKey] = useState('photo')
  const [point, setPoint] = useState(null)
  const [textureState, setTextureState] = useState('ok')
  const special = SPECIAL[key] ? key : null
  const body = BODIES.find((b) => b.key === key) || BODIES[0]
  const fromServer = !special && SERVER_BODIES.includes(key)
  const now = useNow()
  const system = useSolarSystem()
  const sun = useSun(key === 'sun')
  const sites = useApi(
    (signal) => getJson('/api/v1/space/sites', { body: key }, { signal }),
    [key],
    fromServer,
  )
  const siteData = fromServer && sites.status === 'ok' ? sites.data : null
  const catalog = useApi(
    (signal) => getJson('/api/v1/space/layers', { body: key }, { signal }),
    [key],
    fromServer,
  )
  const all = fromServer && catalog.status === 'ok' ? catalog.data.layers : []
  const photo = all.find((l) => l.key === 'photo')
  const extra = all.filter((l) => l.key !== 'photo')
  const layer = extra.find((l) => l.key === mapKey) || null
  const numeric = all.filter((l) => l.numeric)
  // Valori nel punto: altitudine (se c'è) e la mappa numerica mostrata
  const pointLayers = [...new Set([
    ...numeric.filter((l) => l.key === 'elevation').map((l) => l.key),
    ...(layer?.numeric ? [layer.key] : []),
  ])]
  const pickable = !special && (numeric.length > 0 || NAMED.includes(key))
  let texture = body.texture
  if (layer) texture = apiUrl(layer.image)
  else if (!body.texture && photo) texture = apiUrl(photo.image)
  const credit = body.credit || photo?.attribution

  function choose(k) {
    setKey(k)
    setMapKey('photo')
    setPoint(null)
  }

  return (
    <div className="space">
      <div className="space-stage">
        {key === 'system' && <SolarSystemStage state={system} />}
        {key === 'sun' && <SunStage sun={sun} />}
        {!special && texture && (
          <Sphere3D texture={texture} flattening={body.flattening ?? (key === 'jupiter' ? 0.065 : 0)}
            rings={body.rings || null} distance={body.distance || 4.2}
            onTextureState={setTextureState} onPick={pickable ? setPoint : undefined}
            onPickSite={pickable ? (site) => setPoint({ lat: site.lat, lon: site.lon }) : undefined} marker={point}
            sites={siteData?.markers ? siteData.sites : null} />
        )}
        {!special && (textureState === 'loading' || !texture) && fromServer && catalog.status !== 'error' && (
          <p className="space-status"><span className="spinner" /> Preparazione della mappa… la prima volta può servire un minuto.</p>
        )}
        {!special && textureState === 'error' && (
          <p className="space-status error">Mappa non disponibile in questo momento. Riprova più tardi.</p>
        )}
        {catalog.status === 'error' && !body.texture && (
          <p className="space-status error">Mappa non disponibile: {catalog.error}</p>
        )}
        {!special && <p className="space-hint">
          Trascina per girare · rotella o due dita per avvicinarti{pickable && ' · tocca un punto per leggerne i valori'}
        </p>}
      </div>
      <aside className="panel wide space-panel">
        <button className="close" onClick={onClose} aria-label="Torna alla Terra">×</button>
        <p className="eyebrow">Oltre la Terra</p>
        {GROUPS.map((g) => (
          <div key={g.title} className="nav-row">
            <p className="group-title">{g.title}</p>
            <div className="chips">
              {g.keys.map((k) => (
                <button key={k} className={k === key ? 'chip on' : 'chip'} onClick={() => choose(k)}>
                  {SPECIAL[k] || BODIES.find((b) => b.key === k).name}
                </button>
              ))}
            </div>
          </div>
        ))}
        {key === 'system' && <SolarSystemPanel state={system} onOpen={choose} onExit={onClose} />}
        {key === 'sun' && <SunPanel sun={sun} />}
        {!special && (
          <>
          <h2>{body.name}</h2>
          <p className="muted">{body.tagline}</p>
          <LiveBox body={body} now={now} />
          {extra.length > 0 && (
            <div className="space-maps">
              <p className="eyebrow spaced">Mappe dal telerilevamento</p>
              <div className="chips">
                <button className={!layer ? 'chip on' : 'chip'} onClick={() => setMapKey('photo')}>
                  {photo?.label || 'Immagine'}
                </button>
                {extra.map((l) => (
                  <button key={l.key} className={layer?.key === l.key ? 'chip on' : 'chip'} onClick={() => setMapKey(l.key)}>
                    {l.label}
                  </button>
                ))}
              </div>
              {layer && (
                <>
                  <LayerLegend key={layer.key} body={key} layer={layer} />
                  {layer.caption && <p className="small">{layer.caption}</p>}
                  <p className="credit">{layer.attribution}</p>
                </>
              )}
            </div>
          )}
          {fromServer && catalog.status === 'loading' && <p className="muted small">Carico le mappe disponibili…</p>}
          {pickable && (point
            ? <PointBox body={key} point={point} layers={pointLayers} onClear={() => setPoint(null)} />
            : <p className="muted small">Tocca un punto del globo per leggerne le coordinate, il nome del luogo e i valori misurati.</p>)}
          <LandingSites data={siteData} onPick={(site) => setPoint({ lat: site.lat, lon: site.lon })} />
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
          {credit && <p className="credit">{credit}. Posizioni calcolate nel browser con astronomy-engine.</p>}
          </>
        )}
      </aside>
    </div>
  )
}
