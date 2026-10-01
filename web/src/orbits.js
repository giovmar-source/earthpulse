// Calcolo delle posizioni dei satelliti a partire dagli elementi orbitali (TLE).
// satellite.js implementa il modello SGP4, lo stesso usato da NORAD/CelesTrak.
import * as satellite from 'satellite.js'
import { API_URL } from './config.js'

// Colore di ogni famiglia di satelliti sul globo
export const CARD_COLORS = {
  'sentinel-2': '#3FD68F',
  landsat: '#F2B33D',
  'suomi-npp': '#B48CFF',
}

/** Scarica gli elementi orbitali dal backend e prepara i "satrec" per SGP4. */
export async function loadSatellites() {
  const response = await fetch(`${API_URL}/api/v1/tle`)
  if (!response.ok) throw new Error(`Dati orbitali non disponibili (HTTP ${response.status})`)
  const data = await response.json()
  return data.satellites.map((s) => ({
    ...s,
    color: CARD_COLORS[s.card] || '#FFFFFF',
    satrec: satellite.twoline2satrec(s.line1, s.line2),
  }))
}

/** Posizione sotto il satellite (lat, lon in gradi) e quota (km) in un istante. */
export function positionAt(sat, date) {
  const pv = satellite.propagate(sat.satrec, date)
  if (!pv || !pv.position || typeof pv.position === 'boolean') return null
  const gmst = satellite.gstime(date)
  const geo = satellite.eciToGeodetic(pv.position, gmst)
  return {
    lon: satellite.degreesLong(geo.longitude),
    lat: satellite.degreesLat(geo.latitude),
    heightKm: geo.height,
  }
}

/** Periodo orbitale in minuti (dal moto medio, giri al giorno). */
export function periodMinutes(sat) {
  // satrec.no è in radianti al minuto
  return (2 * Math.PI) / sat.satrec.no
}

/**
 * Traccia a terra tra "da" e "a" minuti rispetto ad ora.
 * Restituisce una lista di linee: si spezza al cambio di data (±180°),
 * altrimenti la mappa disegnerebbe una riga attraverso tutto il globo.
 */
export function groundTrack(sat, now, fromMin, toMin, stepSec = 30) {
  const lines = []
  let current = []
  let previousLon = null
  for (let t = fromMin * 60; t <= toMin * 60; t += stepSec) {
    const p = positionAt(sat, new Date(now.getTime() + t * 1000))
    if (!p) continue
    if (previousLon !== null && Math.abs(p.lon - previousLon) > 180) {
      if (current.length > 1) lines.push(current)
      current = []
    }
    current.push([p.lon, p.lat])
    previousLon = p.lon
  }
  if (current.length > 1) lines.push(current)
  return lines
}
