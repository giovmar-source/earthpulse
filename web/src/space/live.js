// Dati "in questo momento" calcolati nel browser con astronomy-engine
// (modelli VSOP87 e lunari, nessun servizio esterno).
import * as Astronomy from 'astronomy-engine'

const JUPITER_RADIUS_KM = 71492

/** Fase della Luna in parole, dall'angolo di fase (0 = nuova, 180 = piena). */
function phaseName(angle) {
  if (angle < 22.5 || angle >= 337.5) return 'Luna nuova'
  if (angle < 67.5) return 'Falce crescente'
  if (angle < 112.5) return 'Primo quarto'
  if (angle < 157.5) return 'Gibbosa crescente'
  if (angle < 202.5) return 'Luna piena'
  if (angle < 247.5) return 'Gibbosa calante'
  if (angle < 292.5) return 'Ultimo quarto'
  return 'Falce calante'
}

const QUARTERS = ['Luna nuova', 'Primo quarto', 'Luna piena', 'Ultimo quarto']

export function moonNow(date = new Date()) {
  const angle = Astronomy.MoonPhase(date)
  const illumination = Astronomy.Illumination(Astronomy.Body.Moon, date)
  const distanceKm = Astronomy.GeoVector(Astronomy.Body.Moon, date, true).Length() * Astronomy.KM_PER_AU
  const next = Astronomy.SearchMoonQuarter(date)
  return {
    angle,
    phase: phaseName(angle),
    illuminated: illumination.phase_fraction,
    distanceKm,
    next: { name: QUARTERS[next.quarter], date: next.time.date },
  }
}

/** Distanza dalla Terra e luce che impiega ad arrivare. */
export function planetNow(bodyName, date = new Date()) {
  const body = Astronomy.Body[bodyName]
  const au = Astronomy.GeoVector(body, date, true).Length()
  const km = au * Astronomy.KM_PER_AU
  return { distanceKm: km, lightMinutes: km / 299792.458 / 60 }
}

/**
 * Posizione delle lune di Giove come le vedremmo con un binocolo dalla Terra:
 * spostamento a est (+) o ovest (−) del pianeta, in raggi di Giove.
 */
export function jupiterMoonsNow(date = new Date()) {
  const toJupiter = Astronomy.GeoVector(Astronomy.Body.Jupiter, date, true)
  const los = [toJupiter.x, toJupiter.y, toJupiter.z]
  const norm = Math.hypot(...los)
  const d = los.map((v) => v / norm)
  // Est sul cielo: perpendicolare alla linea di vista e al polo nord celeste
  const east = [-d[1], d[0], 0]
  const eastNorm = Math.hypot(...east)
  const e = east.map((v) => v / eastNorm)
  const north = [d[1] * e[2] - d[2] * e[1], d[2] * e[0] - d[0] * e[2], d[0] * e[1] - d[1] * e[0]]
  const moons = Astronomy.JupiterMoons(date)
  const result = {}
  for (const key of ['io', 'europa', 'ganymede', 'callisto']) {
    const m = moons[key]
    const v = [m.x, m.y, m.z].map((c) => c * Astronomy.KM_PER_AU)
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    result[key] = {
      east: dot(v, e) / JUPITER_RADIUS_KM,
      north: dot(v, north) / JUPITER_RADIUS_KM,
      behind: dot(v, d) > 0,           // più lontana di Giove: può essere nascosta
    }
  }
  return { moons: result, ...planetNow('Jupiter', date) }
}
