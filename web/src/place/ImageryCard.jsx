import { useEffect, useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { getScenes } from './scenesCache.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, formatNumber, useApi } from './common.jsx'

const SIDE_OPTIONS = [1, 2, 3]
const INDEX_LAYERS = new Set(['ndvi', 'ndwi', 'ndmi', 'ndbi', 'ndre', 'ndsi', 'ndci', 'ndti'])

/** Valore medio di un indice (o ettari d'acqua) per una o due date. */
function StatLine({ layer, after, before }) {
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
function customPair(timeline, beforeId, afterId) {
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
function DatePicker({ place, sideKm, value, onChange, onClose }) {
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

/** Immagini "dall'alto" di Sentinel-2: colori reali e indici, prima e dopo. */
export default function ImageryCard({ place, layerOrder, tips }) {
  const [sideKm, setSideKm] = useState(3)
  const [layerKey, setLayerKey] = useState(null)
  const [picking, setPicking] = useState(false)
  const [custom, setCustom] = useState(null)
  const result = useApi(
    () => getScenes(place, sideKm),
    [place.lat, place.lon, sideKm],
  )

  const sizes = (
    <div className="chips">
      <span className="muted small">Area:</span>
      {SIDE_OPTIONS.map((km) => (
        <button key={km} className={km === sideKm ? 'chip on' : 'chip'} onClick={() => { setSideKm(km); setCustom(null) }}>
          {km} × {km} km
        </button>
      ))}
    </div>
  )

  if (result.status !== 'ok') {
    return (
      <>
        {sizes}
        {result.status === 'error'
          ? <ErrorBox message={result.error} onRetry={result.retry} />
          : <Loading text="Ricerca delle immagini più nitide…" hint="Una recente e una dello stesso periodo dell'anno scorso." />}
      </>
    )
  }

  const data = result.data
  const chosen = picking && custom ? customPair(custom.timeline, custom.beforeId, custom.afterId) : null
  const after = chosen?.after ?? data.after
  const before = chosen?.before ?? data.before
  const attribution = chosen?.attribution ?? data.attribution
  const pairKey = `${before?.item_id}-${after?.item_id}`
  // Ordine dei livelli scelto dalla categoria di lavoro (se c'è)
  let layers = data.layers.filter((l) => after?.images[l.key] || l.key === 'rgb')
  if (layerOrder?.length) {
    layers = layerOrder.map((k) => layers.find((l) => l.key === k)).filter(Boolean)
  }
  const layer = layers.find((l) => l.key === layerKey) || layers[0]

  if (!after) {
    return (
      <>
        {sizes}
        {data.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      </>
    )
  }

  const single = layer.mode === 'single'
  return (
    <div>
      {sizes}
      {layers.length > 1 && <div className="chips layers">
        {layers.map((l) => (
          <button key={l.key} className={l.key === layer.key ? 'chip on' : 'chip'} onClick={() => setLayerKey(l.key)}>
            {l.label}
          </button>
        ))}
      </div>}
      <div className="dates-bar">
        {!picking
          ? <button className="chip" onClick={() => setPicking(true)}>📅 Scegli le date</button>
          : <DatePicker place={place} sideKm={sideKm} value={custom} onChange={setCustom}
              onClose={() => { setPicking(false); setCustom(null) }} />}
      </div>
      <CompareImages
        key={`${layer.key}-${sideKm}-${pairKey}`}
        after={after.images[layer.key]}
        before={single ? null : before?.images[layer.key]}
        beforeLabel={before && formatDate(before.date)}
        afterLabel={single ? `${formatDate(before?.date)} → ${formatDate(after.date)}` : formatDate(after.date)}
        alt={layer.label}
      />
      {!single && before && <p className="muted small hint">Trascina il cursore per confrontare le due date.</p>}
      <Legend stops={layer.color_stops} labels={layer.legend_labels} />
      <StatLine key={`stat-${layer.key}-${sideKm}-${pairKey}`} layer={layer} after={after} before={single ? null : before} />
      {tips?.[layer.key] && <p className="tip">💡 {tips[layer.key]}</p>}
      <p className="small">{layer.caption}</p>
      {layer.formula && <p className="formula">{layer.formula}</p>}
      {!chosen && data.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      <p className="credit">{attribution}</p>
    </div>
  )
}
