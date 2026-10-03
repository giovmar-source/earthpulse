// Calcoli per la mappa del Sistema solare, tutti nel browser.
// Pianeti e Plutone: astronomy-engine (VSOP87 e modello di Plutone), coordinate
// eliocentriche riportate sull'eclittica J2000 (vista dal polo nord dell'eclittica).
// Cerere e Vesta: orbita kepleriana dagli elementi osculanti del JPL (forniti dal server).
import * as Astronomy from 'astronomy-engine'

export const AU_KM = Astronomy.KM_PER_AU
const ROT = Astronomy.Rotation_EQJ_ECL()
const DEG = Math.PI / 180

// Periodi orbitali siderei in giorni (per disegnare un'orbita completa)
export const PLANETS = [
  { key: 'mercury', body: 'Mercury', name: 'Mercurio', period: 87.969, color: '#b9b1a6', size: 4 },
  { key: 'venus', body: 'Venus', name: 'Venere', period: 224.701, color: '#e9d08e', size: 5.5 },
  { key: 'earth', body: 'Earth', name: 'Terra', period: 365.256, color: '#4f93e6', size: 5.5 },
  { key: 'mars', body: 'Mars', name: 'Marte', period: 686.98, color: '#d9704a', size: 4.5 },
  { key: 'jupiter', body: 'Jupiter', name: 'Giove', period: 4332.59, color: '#d9b68c', size: 8 },
  { key: 'saturn', body: 'Saturn', name: 'Saturno', period: 10759.22, color: '#e6d39c', size: 7 },
  { key: 'uranus', body: 'Uranus', name: 'Urano', period: 30688.5, color: '#a2dbe3', size: 6 },
  { key: 'neptune', body: 'Neptune', name: 'Nettuno', period: 60182, color: '#5a7fe6', size: 6 },
  { key: 'pluto', body: 'Pluto', name: 'Plutone', period: 90560, color: '#cbb79c', size: 3, dwarf: true },
]

/** Posizione eliocentrica [x, y, z] in UA sull'eclittica J2000. */
export function helio(bodyName, date) {
  const v = Astronomy.HelioVector(Astronomy.Body[bodyName], date)
  const e = Astronomy.RotateVector(ROT, v)
  return [e.x, e.y, e.z]
}

/** Punti di un'orbita completa a partire dalla data (traiettoria calcolata, non un cerchio). */
export function orbitPath(planet, date, steps = 240) {
  const points = []
  const start = date.getTime()
  for (let i = 0; i <= steps; i += 1) {
    points.push(helio(planet.body, new Date(start + (i / steps) * planet.period * 86400000)))
  }
  return points
}

function julianDay(date) {
  return date.getTime() / 86400000 + 2440587.5
}

function solveKepler(M, e) {
  let E = e < 0.8 ? M : Math.PI
  for (let k = 0; k < 30; k += 1) {
    const d = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E))
    E -= d
    if (Math.abs(d) < 1e-12) break
  }
  return E
}

function fromOrbitalPlane(el, xp, yp) {
  const O = el.om * DEG
  const w = el.w * DEG
  const i = el.i * DEG
  const [cO, sO, cw, sw, ci, si] = [Math.cos(O), Math.sin(O), Math.cos(w), Math.sin(w), Math.cos(i), Math.sin(i)]
  return [
    (cO * cw - sO * sw * ci) * xp + (-cO * sw - sO * cw * ci) * yp,
    (sO * cw + cO * sw * ci) * xp + (-sO * sw + cO * cw * ci) * yp,
    (sw * si) * xp + (cw * si) * yp,
  ]
}

/** Posizione di un corpo minore da elementi osculanti (UA, eclittica J2000). */
export function keplerPosition(el, date) {
  const M = ((el.ma + el.n * (julianDay(date) - el.epoch)) % 360) * DEG
  const E = solveKepler(M, el.e)
  return fromOrbitalPlane(el, el.a * (Math.cos(E) - el.e), el.a * Math.sqrt(1 - el.e * el.e) * Math.sin(E))
}

export function keplerOrbit(el, steps = 240) {
  const points = []
  for (let k = 0; k <= steps; k += 1) {
    const E = (k / steps) * 2 * Math.PI
    points.push(fromOrbitalPlane(el, el.a * (Math.cos(E) - el.e), el.a * Math.sqrt(1 - el.e * el.e) * Math.sin(E)))
  }
  return points
}

export function distance(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2])
}

const OPPOSITION = { Mars: 'Marte', Jupiter: 'Giove', Saturn: 'Saturno', Uranus: 'Urano', Neptune: 'Nettuno' }

/**
 * Prossimi eventi osservabili dalla Terra, calcolati con astronomy-engine:
 * opposizioni dei pianeti esterni e massime elongazioni di Mercurio e Venere.
 */
export function upcomingEvents(date, horizonDays = 730) {
  const events = []
  const limit = date.getTime() + horizonDays * 86400000
  for (const [body, name] of Object.entries(OPPOSITION)) {
    try {
      const t = Astronomy.SearchRelativeLongitude(Astronomy.Body[body], 0, date)
      if (t.date.getTime() <= limit) {
        events.push({
          date: t.date, kind: 'opposition', body, title: `Opposizione di ${name}`,
          text: `${name} è dalla parte opposta del Sole rispetto a noi: visibile tutta la notte, alla minima distanza dell'anno.`,
        })
      }
    } catch { /* evento oltre i limiti di calcolo */ }
  }
  for (const [body, name] of [['Mercury', 'Mercurio'], ['Venus', 'Venere']]) {
    let from = date
    for (let k = 0; k < 4; k += 1) {
      try {
        const ev = Astronomy.SearchMaxElongation(Astronomy.Body[body], from)
        if (ev.time.date.getTime() > limit) break
        const evening = ev.visibility === 'evening'
        events.push({
          date: ev.time.date, kind: 'elongation', body,
          title: `Massima elongazione ${evening ? 'serale' : 'mattutina'} di ${name}`,
          text: `${name} si allontana di ${Math.round(ev.elongation)}° dal Sole: il momento migliore per vederlo ${evening ? 'dopo il tramonto' : "prima dell'alba"}.`,
        })
        from = new Date(ev.time.date.getTime() + 5 * 86400000)
        if (body === 'Venus') break        // per Venere basta la prossima
      } catch { break }
    }
  }
  return events.sort((a, b) => a.date - b.date)
}
