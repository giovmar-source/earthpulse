import { useEffect, useMemo, useRef, useState } from 'react'
import { getJson } from '../api.js'
import { useApi } from '../place/common.jsx'
import { AU_KM, PLANETS, distance, helio, keplerOrbit, keplerPosition, orbitPath, upcomingEvents } from './solar.js'

// Due zoom con distanze in scala reale: raggio della vista in UA
const ZOOMS = {
  inner: { label: 'Pianeti interni e asteroidi', radius: 3.6, ruler: 1, step: 2 },
  outer: { label: 'Tutto il Sistema solare', radius: 50, ruler: 10, step: 40 },
}
const VIEW = 500                     // viewBox da −500 a 500
const SCREEN = 470                   // raggio utile in unità SVG
const OPENABLE = { mercury: 'mercury', venus: 'venus', mars: 'mars', jupiter: 'jupiter', ceres: 'ceres', vesta: 'vesta' }
const MIN_YEAR = 1800
const MAX_YEAR = 2200

function jd(date) {
  return date.getTime() / 86400000 + 2440587.5
}

/** Posizione di una sonda alla data, interpolando i punti di Horizons (null se fuori dall'intervallo). */
function craftPosition(track, date) {
  const t = jd(date)
  if (!track.length || t < track[0][0] || t > track[track.length - 1][0]) return null
  let k = 1
  while (k < track.length && track[k][0] < t) k += 1
  const a = track[k - 1]
  const b = track[Math.min(k, track.length - 1)]
  const f = b[0] === a[0] ? 0 : (t - a[0]) / (b[0] - a[0])
  return [a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2]), a[3] + f * (b[3] - a[3])]
}

function formatDay(date) {
  return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })
}
function au(v) {
  return v.toLocaleString('it-IT', { maximumFractionDigits: v < 10 ? 2 : 1 })
}
function millionKm(v) {
  return (v * AU_KM / 1e6).toLocaleString('it-IT', { maximumFractionDigits: v < 3 ? 1 : 0 })
}

/** Stato condiviso tra la mappa (a sinistra) e il pannello (a destra). */
export function useSolarSystem() {
  const [date, setDate] = useState(() => new Date())
  const [zoom, setZoom] = useState('inner')
  const [selected, setSelected] = useState(null)
  const [playing, setPlaying] = useState(false)
  const small = useApi((signal) => getJson('/api/v1/space/small-bodies', null, { signal }), [])
  const craft = useApi((signal) => getJson('/api/v1/space/spacecraft', null, { signal }), [])

  useEffect(() => {
    if (!playing) return undefined
    const timer = setInterval(() => {
      setDate((d) => {
        const next = new Date(d.getTime() + ZOOMS[zoom].step * 86400000)
        return next.getUTCFullYear() > MAX_YEAR ? d : next
      })
    }, 60)
    return () => clearInterval(timer)
  }, [playing, zoom])

  return {
    date, setDate, zoom, setZoom, selected, setSelected, playing, setPlaying,
    small: small.status === 'ok' ? small.data : null,
    smallStatus: small.status,
    craft: craft.status === 'ok' ? craft.data : null,
    craftStatus: craft.status,
  }
}

/** Tutti gli oggetti alla data: pianeti, Cerere e Vesta, sonde. */
function useObjects(state) {
  const { date, small, craft } = state
  return useMemo(() => {
    const items = PLANETS.map((p) => ({ ...p, kind: 'planet', pos: helio(p.body, date) }))
    for (const b of small?.bodies || []) {
      items.push({ key: b.key, name: b.name, kind: 'small', color: '#a7a7a7', size: 3, pos: keplerPosition(b.elements, date), elements: b.elements, info: b })
    }
    for (const c of craft?.spacecraft || []) {
      const pos = craftPosition(c.track, date)
      if (pos) items.push({ key: c.key, name: c.name, kind: 'craft', color: '#7ef0c6', size: 2.5, pos, info: c })
    }
    return items
  }, [date, small, craft])
}

export function SolarSystemStage({ state }) {
  const { date, zoom, selected, setSelected } = state
  const objects = useObjects(state)
  const R = ZOOMS[zoom].radius
  const s = SCREEN / R
  const x = (p) => p[0] * s
  const y = (p) => -p[1] * s
  // Orbite ricalcolate al cambio di mese (cambiano molto lentamente)
  const monthKey = `${date.getUTCFullYear()}-${date.getUTCMonth()}`
  const orbits = useMemo(() => {
    const start = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1))
    return PLANETS.map((p) => ({ key: p.key, points: orbitPath(p, start, p.key === 'pluto' || p.key === 'neptune' ? 360 : 240) }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monthKey])
  const smallOrbits = useMemo(
    () => (state.small?.bodies || []).map((b) => ({ key: b.key, points: keplerOrbit(b.elements) })),
    [state.small],
  )
  const path = (points) => points.map((p, i) => `${i ? 'L' : 'M'}${x(p).toFixed(1)},${y(p).toFixed(1)}`).join('') + 'Z'
  const visible = (p) => Math.hypot(p[0], p[1]) <= R * 1.02

  return (
    <svg className="solar-map" viewBox={`${-VIEW} ${-VIEW} ${VIEW * 2} ${VIEW * 2}`} role="img"
      aria-label={`Sistema solare il ${formatDay(date)}`} onClick={() => setSelected(null)}>
      {/* Fascia principale degli asteroidi (indicativa) */}
      <circle r={2.7 * s} className="belt" strokeWidth={1.0 * s} />
      {orbits.map((o) => <path key={o.key} d={path(o.points)} className={o.key === 'earth' ? 'orbit earth' : 'orbit'} />)}
      {smallOrbits.map((o) => <path key={o.key} d={path(o.points)} className="orbit small" />)}
      {/* Direzione dell'equinozio di primavera, riferimento delle longitudini */}
      <g className="equinox">
        <line x1={14} y1={0} x2={SCREEN} y2={0} />
        <text x={SCREEN - 4} y={16} textAnchor="end">♈ direzione dell'equinozio</text>
      </g>
      <circle r={zoom === 'inner' ? 9 : 6} className="sun" />
      {objects.map((o) => {
        const far = !visible(o.pos)
        // Fuori dalla vista: solo le sonde lontane nella vista completa, segnate sul bordo
        if (far && (o.kind !== 'craft' || zoom === 'inner')) return null
        const r = Math.hypot(o.pos[0], o.pos[1])
        const p = far ? [o.pos[0] / r * R * 0.97, o.pos[1] / r * R * 0.97] : o.pos
        const on = selected === o.key
        return (
          <g key={o.key} className={`obj ${o.kind}${on ? ' on' : ''}`}
            onClick={(e) => { e.stopPropagation(); setSelected(o.key) }}>
            <circle cx={x(p)} cy={y(p)} r={Math.max(12, o.size + 6)} fill="transparent" />
            {o.kind === 'craft'
              ? <rect x={x(p) - o.size} y={y(p) - o.size} width={o.size * 2} height={o.size * 2} transform={`rotate(45 ${x(p)} ${y(p)})`} fill={o.color} />
              : <circle cx={x(p)} cy={y(p)} r={o.size} fill={o.color} />}
            {on && <circle cx={x(p)} cy={y(p)} r={o.size + 5} className="ring" />}
            {/* Etichette: nella vista completa niente nomi per i corpi vicini al Sole (si sovrappongono) */}
            {(on || far || (o.kind !== 'craft' && !(zoom === 'outer' && r < 4))) && (
              <text x={x(p) > 260 ? x(p) - o.size - 4 : x(p) + o.size + 4} y={y(p) - o.size - 2}
                textAnchor={x(p) > 260 ? 'end' : 'start'} className="label">
                {o.name}{far ? ` · ${au(r)} UA` : ''}
              </text>
            )}
          </g>
        )
      })}
      {/* Righello */}
      <g className="ruler" transform={`translate(${-SCREEN} ${SCREEN - 6})`}>
        <line x1={0} x2={ZOOMS[zoom].ruler * s} y1={0} y2={0} />
        <line x1={0} x2={0} y1={-5} y2={5} />
        <line x1={ZOOMS[zoom].ruler * s} x2={ZOOMS[zoom].ruler * s} y1={-5} y2={5} />
        <text x={0} y={-10}>{ZOOMS[zoom].ruler} UA = {millionKm(ZOOMS[zoom].ruler)} milioni di km</text>
      </g>
      <text x={SCREEN} y={SCREEN - 4} textAnchor="end" className="scale-note">Distanze in scala · dimensioni NON in scala</text>
    </svg>
  )
}

function Controls({ state }) {
  const { date, setDate, playing, setPlaying } = state
  const shift = (days, months = 0) => {
    const d = new Date(date)
    if (months) d.setUTCMonth(d.getUTCMonth() + months)
    d.setTime(d.getTime() + days * 86400000)
    if (d.getUTCFullYear() >= MIN_YEAR && d.getUTCFullYear() <= MAX_YEAR) setDate(d)
  }
  return (
    <div className="time-controls">
      <div className="time-row">
        <strong>{formatDay(date)}</strong>
        <input type="date" value={date.toISOString().slice(0, 10)} min={`${MIN_YEAR}-01-01`} max={`${MAX_YEAR}-12-31`}
          onChange={(e) => { if (e.target.value) setDate(new Date(`${e.target.value}T12:00:00Z`)) }} />
      </div>
      <div className="chips">
        <button className="chip" onClick={() => shift(0, -12)}>−1 anno</button>
        <button className="chip" onClick={() => shift(0, -1)}>−1 mese</button>
        <button className="chip" onClick={() => shift(-1)}>−1 g</button>
        <button className="chip" onClick={() => { setPlaying(false); setDate(new Date()) }}>Adesso</button>
        <button className="chip" onClick={() => shift(1)}>+1 g</button>
        <button className="chip" onClick={() => shift(0, 1)}>+1 mese</button>
        <button className="chip" onClick={() => shift(0, 12)}>+1 anno</button>
        <button className={playing ? 'chip on' : 'chip'} onClick={() => setPlaying(!playing)}>{playing ? '⏸ Ferma' : '▶ Avvia'}</button>
      </div>
    </div>
  )
}

function Details({ state, objects, onOpen, onExit }) {
  const o = objects.find((item) => item.key === state.selected)
  if (!o) return <p className="muted small">Tocca un pianeta, un asteroide o una sonda per i dettagli.</p>
  const earth = objects.find((item) => item.key === 'earth')
  const fromSun = Math.hypot(...o.pos)
  const fromEarth = o.key === 'earth' ? 0 : distance(o.pos, earth.pos)
  return (
    <div className="point-box">
      <div><strong>{o.name}</strong>{o.info?.agency && <span className="muted small"> · {o.info.agency}</span>}</div>
      {o.info?.note && <p className="small">{o.info.note}</p>}
      <dl className="facts">
        <div><dt>Dal Sole</dt><dd>{au(fromSun)} UA · {millionKm(fromSun)} milioni di km</dd></div>
        {o.key !== 'earth' && <div><dt>Dalla Terra</dt><dd>{au(fromEarth)} UA · {millionKm(fromEarth)} milioni di km</dd></div>}
        {o.key !== 'earth' && (
          <div><dt>La luce impiega</dt><dd>{Math.round(fromEarth * AU_KM / 299792.458 / 60).toLocaleString('it-IT')} minuti dalla Terra</dd></div>
        )}
      </dl>
      {OPENABLE[o.key] && <button className="chip on" onClick={() => onOpen(OPENABLE[o.key])}>Apri la scheda di {o.name} →</button>}
      {o.key === 'earth' && <button className="chip on" onClick={onExit}>Torna alla Terra →</button>}
      {o.kind === 'small' && (
        <p className="muted small">Orbita kepleriana dagli elementi del JPL (epoca {new Date(o.info.epoch_date).toLocaleDateString('it-IT')}): {o.info.source}.</p>
      )}
    </div>
  )
}

export function SolarSystemPanel({ state, onOpen, onExit }) {
  const objects = useObjects(state)
  const dayKey = state.date.toISOString().slice(0, 10)
  const events = useMemo(() => upcomingEvents(new Date(`${dayKey}T00:00:00Z`)).slice(0, 7), [dayKey])
  const craftCount = state.craft?.spacecraft?.length
  const inRange = objects.filter((o) => o.kind === 'craft').length
  const scroll = useRef(null)
  return (
    <div ref={scroll}>
      <h2>Il Sistema solare</h2>
      <p className="muted">Dove si trovano davvero, oggi o in qualsiasi data, i pianeti, Cerere, Vesta e le sonde nello spazio.</p>
      <Controls state={state} />
      <div className="chips">
        {Object.entries(ZOOMS).map(([key, z]) => (
          <button key={key} className={state.zoom === key ? 'chip on' : 'chip'} onClick={() => state.setZoom(key)}>{z.label}</button>
        ))}
      </div>
      <Details state={state} objects={objects} onOpen={onOpen} onExit={onExit} />
      <p className="eyebrow spaced">Prossimi eventi visibili dalla Terra</p>
      <ul className="events-list">
        {events.map((e) => (
          <li key={`${e.kind}-${e.body}-${e.date.toISOString()}`}>
            <strong>{formatDay(e.date)}</strong> · {e.title}
            <span className="muted small"> {e.text}</span>
          </li>
        ))}
      </ul>
      <p className="eyebrow spaced">Sonde nello spazio</p>
      {state.craftStatus === 'loading' && <p className="muted small"><span className="spinner" /> Carico le traiettorie dal JPL… la prima volta può servire un minuto.</p>}
      {state.craftStatus === 'error' && <p className="muted small">Traiettorie non disponibili in questo momento.</p>}
      {craftCount != null && (
        <p className="small">
          {craftCount} sonde, posizioni disponibili da un anno prima a un anno dopo oggi
          {inRange < craftCount && <> ({inRange} visibili alla data scelta)</>}. Le sonde oltre il bordo della vista sono
          segnate sul bordo, nella loro direzione, con la distanza.
        </p>
      )}
      <div className="box">
        <p className="eyebrow">Come leggere la mappa</p>
        <ul className="missions">
          <li>Vista dall'alto del piano dell'orbita terrestre (eclittica J2000): i pianeti girano in senso antiorario.</li>
          <li><strong>Distanze in scala reale</strong> in ciascuno zoom; <strong>dimensioni dei pianeti non in scala</strong>: in scala la Terra sarebbe più piccola di un pixel.</li>
          <li>Pianeti e Plutone: posizioni calcolate con astronomy-engine (modelli VSOP87), precisione di circa un minuto d'arco. Le orbite sono le traiettorie calcolate, non cerchi.</li>
          <li>Cerere e Vesta: orbite kepleriane dagli elementi del JPL Small-Body Database; l'errore cresce lontano dall'epoca degli elementi, ma resta piccolo alla scala della mappa.</li>
          <li>Sonde: JPL Horizons, un punto ogni 5 giorni, interpolato.</li>
          <li>La fascia degli asteroidi è disegnata come zona indicativa tra 2,2 e 3,2 UA.</li>
          <li>Eventi: opposizioni (pianeta opposto al Sole, visibile tutta la notte) e massime elongazioni di Mercurio e Venere, calcolati con astronomy-engine.</li>
        </ul>
      </div>
      <p className="credit">Posizioni: astronomy-engine (MIT). {state.small?.attribution || 'Orbite: NASA/JPL Solar System Dynamics'}.</p>
    </div>
  )
}
