import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import { MAP_STYLE } from './config.js'
import { groundTrack, periodMinutes, positionAt } from './orbits.js'

// Ogni quanto aggiornare posizioni (1 s) e tracce a terra (30 s)
const POSITION_MS = 1000
const TRACK_MS = 30000
const PAST_MINUTES = 25

/** Etichette della mappa in italiano, poi inglese, poi nome locale. */
function localizeLabels(map) {
  for (const layer of map.getStyle().layers) {
    if (layer.type === 'symbol' && map.getLayoutProperty(layer.id, 'text-field')) {
      map.setLayoutProperty(layer.id, 'text-field', [
        'coalesce', ['get', 'name:it'], ['get', 'name:en'], ['get', 'name:latin'], ['get', 'name'],
      ])
    }
  }
}

function emptyCollection() {
  return { type: 'FeatureCollection', features: [] }
}

function satellitePoints(satellites, now) {
  return {
    type: 'FeatureCollection',
    features: satellites.flatMap((sat) => {
      const p = positionAt(sat, now)
      if (!p) return []
      return [{
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
        properties: { norad: sat.norad, name: sat.name, color: sat.color },
      }]
    }),
  }
}

function satelliteTracks(satellites, now) {
  const features = []
  for (const sat of satellites) {
    const future = groundTrack(sat, now, 0, periodMinutes(sat))
    const past = groundTrack(sat, now, -PAST_MINUTES, 0)
    for (const [kind, lines] of [['future', future], ['past', past]]) {
      for (const coordinates of lines) {
        features.push({
          type: 'Feature',
          geometry: { type: 'LineString', coordinates },
          properties: { norad: sat.norad, color: sat.color, kind },
        })
      }
    }
  }
  return { type: 'FeatureCollection', features }
}

/**
 * Globo 3D (MapLibre GL, proiezione "globe") con i satelliti in tempo reale:
 * punto sotto il satellite, traccia a terra dell'orbita (tratteggiata) e nome.
 */
export default function Globe({ satellites, selectedNorad, onSelectSatellite, onSelectPlace, flyTarget }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const readyRef = useRef(false)
  const satellitesRef = useRef(satellites)
  const markerRef = useRef(null)
  const callbacks = useRef({ onSelectSatellite, onSelectPlace })
  callbacks.current = { onSelectSatellite, onSelectPlace }
  satellitesRef.current = satellites

  // Creazione della mappa (una sola volta)
  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: [12.5, 30],
      zoom: window.innerWidth <= 700 ? 0.7 : 1.4,
      attributionControl: { compact: true },
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'bottom-left')

    // Il globo va centrato nello spazio libero: a sinistra del pannello sul PC,
    // sopra il pannello sul telefono.
    function applyPadding() {
      const mobile = window.innerWidth <= 700
      map.setPadding(mobile
        ? { top: 60, bottom: Math.round(window.innerHeight * 0.48), left: 0, right: 0 }
        : { top: 0, bottom: 0, left: 0, right: Math.min(410, window.innerWidth * 0.45) })
    }
    applyPadding()
    window.addEventListener('resize', applyPadding)

    map.on('style.load', () => {
      map.setProjection({ type: 'globe' })
      map.setSky({
        'sky-color': '#0b1a2e',
        'horizon-color': '#3a6ea5',
        'atmosphere-blend': ['interpolate', ['linear'], ['zoom'], 0, 1, 5, 1, 7, 0],
      })
      localizeLabels(map)

      map.addSource('tracks', { type: 'geojson', data: emptyCollection() })
      map.addSource('sats', { type: 'geojson', data: emptyCollection() })

      map.addLayer({
        id: 'tracks-past', type: 'line', source: 'tracks',
        filter: ['==', ['get', 'kind'], 'past'],
        paint: { 'line-color': ['get', 'color'], 'line-width': 1.5, 'line-opacity': 0.35 },
      })
      map.addLayer({
        id: 'tracks-future', type: 'line', source: 'tracks',
        filter: ['==', ['get', 'kind'], 'future'],
        paint: {
          'line-color': ['get', 'color'], 'line-width': 1.8, 'line-opacity': 0.8,
          'line-dasharray': [2, 2],
        },
      })
      map.addLayer({
        id: 'sats-halo', type: 'circle', source: 'sats',
        paint: { 'circle-radius': 13, 'circle-color': ['get', 'color'], 'circle-opacity': 0.25 },
      })
      map.addLayer({
        id: 'sats-dot', type: 'circle', source: 'sats',
        paint: {
          'circle-radius': 6, 'circle-color': '#ffffff',
          'circle-stroke-color': ['get', 'color'], 'circle-stroke-width': 3,
        },
      })
      map.addLayer({
        id: 'sats-label', type: 'symbol', source: 'sats',
        layout: {
          'text-field': ['get', 'name'], 'text-font': ['Noto Sans Regular'],
          'text-size': 12, 'text-offset': [0, 1.4], 'text-anchor': 'top',
        },
        paint: { 'text-color': '#ffffff', 'text-halo-color': '#0b1a2e', 'text-halo-width': 1.6 },
      })

      // Clic: su un satellite apre la sua scheda, altrove sceglie un luogo
      map.on('click', (event) => {
        const hit = map.queryRenderedFeatures(event.point, { layers: ['sats-dot', 'sats-halo'] })
        if (hit.length > 0) {
          callbacks.current.onSelectSatellite(hit[0].properties.norad)
        } else {
          callbacks.current.onSelectPlace({ lat: event.lngLat.lat, lon: event.lngLat.lng })
        }
      })
      map.on('mouseenter', 'sats-halo', () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', 'sats-halo', () => { map.getCanvas().style.cursor = '' })

      readyRef.current = true
      refreshTracks()
      refreshPositions()
    })

    function refreshPositions() {
      if (!readyRef.current) return
      map.getSource('sats')?.setData(satellitePoints(satellitesRef.current, new Date()))
    }
    function refreshTracks() {
      if (!readyRef.current) return
      map.getSource('tracks')?.setData(satelliteTracks(satellitesRef.current, new Date()))
    }

    const positionTimer = setInterval(refreshPositions, POSITION_MS)
    const trackTimer = setInterval(refreshTracks, TRACK_MS)
    mapRef.current.refresh = () => { refreshTracks(); refreshPositions() }

    return () => {
      window.removeEventListener('resize', applyPadding)
      clearInterval(positionTimer)
      clearInterval(trackTimer)
      map.remove()
      readyRef.current = false
    }
  }, [])

  // Nuovi satelliti caricati: ridisegna subito
  useEffect(() => {
    mapRef.current?.refresh?.()
  }, [satellites])

  // Satellite selezionato: la sua traccia in evidenza
  useEffect(() => {
    const map = mapRef.current
    if (!map || !readyRef.current) return
    const width = selectedNorad
      ? ['case', ['==', ['get', 'norad'], selectedNorad], 3.2, 1.2] : 1.8
    const opacity = selectedNorad
      ? ['case', ['==', ['get', 'norad'], selectedNorad], 1, 0.35] : 0.8
    map.setPaintProperty('tracks-future', 'line-width', width)
    map.setPaintProperty('tracks-future', 'line-opacity', opacity)
  }, [selectedNorad])

  // Volo verso un punto (satellite o luogo scelto) e segnaposto del luogo
  useEffect(() => {
    const map = mapRef.current
    if (!map || !flyTarget) return
    map.flyTo({ center: [flyTarget.lon, flyTarget.lat], zoom: flyTarget.zoom ?? map.getZoom(), duration: 1600 })
    if (flyTarget.marker) {
      markerRef.current?.remove()
      markerRef.current = new maplibregl.Marker({ color: '#F2B33D' })
        .setLngLat([flyTarget.lon, flyTarget.lat])
        .addTo(map)
    }
  }, [flyTarget])

  return <div ref={containerRef} className="globe" />
}
