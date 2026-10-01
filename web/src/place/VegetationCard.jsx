import { getJson, placeParams } from '../api.js'
import { ErrorBox, Loading, formatDate, formatNumber, useApi } from './common.jsx'

// Colore e frase per ogni esito del confronto con gli anni precedenti
const OUTCOMES = {
  'marcatamente sotto la baseline': ['bad', 'Molto meno verde del solito'],
  'sotto la baseline': ['bad', 'Meno verde del solito'],
  'leggermente sotto la baseline': ['warn', 'Un po\' meno verde del solito'],
  'vicino alla baseline': ['ok', 'Come negli anni scorsi'],
  'sopra la baseline': ['good', 'Più verde del solito'],
}

function ndviWords(ndvi) {
  if (ndvi < 0.1) return 'acqua, roccia, costruito o suolo nudo'
  if (ndvi < 0.3) return 'vegetazione rada o secca'
  if (ndvi < 0.5) return 'vegetazione moderata'
  if (ndvi < 0.7) return 'vegetazione rigogliosa'
  return 'vegetazione molto densa'
}

/** Stato della vegetazione: ultima osservazione Sentinel-2 e confronto con gli anni scorsi. */
export default function VegetationCard({ place }) {
  const result = useApi(
    (signal) => getJson('/api/v1/ndvi/analysis', placeParams(place, 1.0), { signal }),
    [place.lat, place.lon],
  )

  if (result.status === 'loading' || result.status === 'idle') {
    return (
      <Loading
        text="Analisi della vegetazione…"
        hint="Cerchiamo l'immagine Sentinel-2 valida più recente e le stesse settimane degli anni precedenti. Di solito 20-40 secondi."
      />
    )
  }
  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />

  const a = result.data
  const latest = a.latest_observation
  const baseline = a.baseline || {}
  const comparison = a.comparison || {}
  const [tone, headline] = OUTCOMES[comparison.classification]
    || ['neutral', comparison.classification ? capitalize(comparison.classification) : 'Confronto non disponibile']
  const years = baseline.years || []

  return (
    <div className="vegetation">
      {latest ? (
        <>
          <div className={`outcome ${tone}`}>
            <span className="outcome-dot" />
            <div>
              <strong>{headline}</strong>
              {comparison.anomaly_percent != null && comparison.percent_meaningful && (
                <span className="muted small">
                  {' '}({comparison.anomaly_percent > 0 ? '+' : ''}{formatNumber(comparison.anomaly_percent, 0)}%)
                </span>
              )}
            </div>
          </div>
          <dl className="facts">
            <div><dt>NDVI ora</dt><dd>{formatNumber(latest.ndvi_mean)} · {ndviWords(latest.ndvi_mean)}</dd></div>
            <div><dt>Immagine del</dt><dd>{formatDate(latest.date)}{!latest.is_recent && ' (non recente)'}</dd></div>
            {baseline.ndvi_median != null && (
              <div>
                <dt>Di solito{years.length > 0 && ` (${years[0]}–${years[years.length - 1]})`}</dt>
                <dd>{formatNumber(baseline.ndvi_median)}</dd>
              </div>
            )}
            {latest.valid_percentage != null && (
              <div><dt>Area senza nuvole</dt><dd>{formatNumber(latest.valid_percentage, 0)}%</dd></div>
            )}
          </dl>
        </>
      ) : (
        <p>Nessuna immagine abbastanza nitida nelle ultime settimane per quest'area.</p>
      )}
      {(a.messages || []).map((m) => <p key={m} className="note">⚠ {m}</p>)}
      <p className="muted small">
        Area di 1 × 1 km intorno al punto · Sentinel-2 L2A, 10 m. {a.warning}
      </p>
    </div>
  )
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
