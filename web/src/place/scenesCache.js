import { getJson, placeParams } from '../api.js'

// Le due scene "prima/dopo" servono a più sezioni (ogni indice mostra la sua mappa):
// una sola richiesta al server per luogo e dimensione dell'area.
const cache = new Map()

export function getScenes(place, sideKm = 3) {
  const key = `${place.lat.toFixed(6)},${place.lon.toFixed(6)},${sideKm}`
  if (!cache.has(key)) {
    const promise = getJson('/api/v1/imagery/scenes', placeParams(place, sideKm.toFixed(1)))
      .catch((error) => { cache.delete(key); throw error })
    cache.set(key, promise)
  }
  return cache.get(key)
}
