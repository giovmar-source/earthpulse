import { useEffect } from 'react'
import { getJson, placeParams } from '../api.js'
import { ErrorBox, Loading, formatNumber, useApi } from './common.jsx'

// Scelta di due date (una scena nitida per stagione) e valore nell'area di 1 km:
// usati sia da "Dall'alto" sia dalle mappe degli indici.

const INDEX_LAYERS = new Set(['ndvi', 'ndwi', 'ndmi', 'ndbi', 'ndre', 'ndsi', 'ndci', 'ndti'])

/** Valore medio di un indice (o ettari d'acqua) per una o due date. */
export function StatLine({ layer, after, before }) {
  const isIndex = INDEX_LAYERS.has(layer.key)
  const isWater = layer.stat === 'water'
  const make = (scene) => {
    if (!scene) return null
    if (isWater) return scene.images.stat_water
    if (isIndex) return scene.images.stat_index?.replace('{index}', layer.key)
    return null
  }
  const afterPath = make(after)
  const beforePath = make(before)
  const enabled = Boolean(afterPath)
  const stats = useApi(
    (signal) => Promise.all([
      getJson(afterPath, null, { signal }),
      beforePath ? getJson(beforePath, null, { signal }) : Promise.resolve(null),
    ]),
    [afterPath, beforePath],
    enabled,
  )
  if (!enabled) return null
  if (stats.status === 'loading' || stats.status === 'idle') {
    return <p className="muted small">Calcolo del valore nell'area…</p>
  }
  if (stats.status === 'error') return <p className="muted small">Valore non disponibile: {stats.error}</p>

  const [a, b] = stats.data
  if (isWater) {
    return (
      <div className="stat">
        <span>Acqua libera nell'area</span>
        <strong>
          {b && `${formatNumber(b.water_ha, 1)} ha → `}{formatNumber(a.water_ha, 1)} ha
        </strong>
      </div>
    )
  }
  return (
    <div className="stat">
      <span>{layer.label}: valore tipico nel km² centrale</span>
      <strong>
        {b && `${formatNumber(b.median)} → `}{formatNumber(a.median)}
      </strong>
    </div>
  )
}

/**
 * Coppia di date scelta dall'utente sulla linea del tempo (una scena per stagione).
 * Restituisce null se la scelta non è valida (stessa data o ordine invertito).
 */
export function customPair(timeline, beforeId, afterId) {
  if (!timeline) return null
  const b = timeline.scenes.find((s) => s.item_id === beforeId)
  const a = timeline.scenes.find((s) => s.item_id === afterId)
  if (!a || !b || b.date >= a.date) return null
  const fill = (template) => template.replaceAll('{before}', b.item_id).replaceAll('{after}', a.item_id)
  const t = timeline.pair_templates || {}
  return {
    after: { ...a, images: { ...a.images, ...(t.diff ? { diff: fill(t.diff) } : {}) } },
    before: { ...b, images: { ...b.images, ...(t.rgb_before ? { rgb: fill(t.rgb_before) } : {}) } },
    attribution: `Contiene dati Copernicus Sentinel modificati (${[...new Set([b.date.slice(0, 4), a.date.slice(0, 4)])].join(', ')})`,
  }
}

function shortDate(iso) {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

/** "Scegli le date": due menu con una scena nitida per ogni stagione degli ultimi anni. */
export function DatePicker({ place, sideKm, value, onChange, onClose }) {
  const timeline = useApi(
    (signal) => getJson('/api/v1/imagery/timeline', placeParams(place, sideKm.toFixed(2)), { signal }),
    [place.lat, place.lon, sideKm],
  )
  // Appena arriva la linea del tempo: confronto tra la prima e l'ultima stagione
  const loaded = timeline.status === 'ok' ? timeline.data : null
  useEffect(() => {
    if (loaded && !value && loaded.scenes.length >= 2) {
      onChange({ beforeId: loaded.scenes[0].item_id, afterId: loaded.scenes[loaded.scenes.length - 1].item_id, timeline: loaded })
    }
  }, [loaded, value, onChange])
  if (timeline.status === 'error') return <ErrorBox message={timeline.error} onRetry={timeline.retry} />
  if (timeline.status !== 'ok') {
    return <Loading text="Ricerca di una scena nitida per ogni stagione…" hint="Ultimi 5 anni: può servire un minuto." />
  }
  const scenes = timeline.data.scenes
  if (scenes.length < 2) return <p className="note">⚠ Troppo poche scene senza nuvole per scegliere le date.</p>
  const beforeId = value?.beforeId ?? scenes[0].item_id
  const afterId = value?.afterId ?? scenes[scenes.length - 1].item_id
  const set = (patch) => onChange({ beforeId, afterId, ...patch, timeline: timeline.data })
  const valid = customPair(timeline.data, beforeId, afterId)
  const option = (s) => <option key={s.item_id} value={s.item_id}>{s.label} · {shortDate(s.date)}</option>
  return (
    <div className="date-picker">
      <div className="year-row">
        <label className="year-picker">
          <span className="muted small">Prima</span>
          <select value={beforeId} onChange={(e) => set({ beforeId: e.target.value })}>{scenes.map(option)}</select>
        </label>
        <label className="year-picker">
          <span className="muted small">Dopo</span>
          <select value={afterId} onChange={(e) => set({ afterId: e.target.value })}>{scenes.map(option)}</select>
        </label>
      </div>
      <p className="muted small">Una scena senza nuvole per ogni stagione degli ultimi anni: il confronto si aggiorna subito.</p>
      {value && !valid && <p className="note">⚠ La data "Prima" deve essere precedente a "Dopo".</p>}
      <button className="link" onClick={onClose}>Torna alle date proposte</button>
    </div>
  )
}

