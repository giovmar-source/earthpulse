import { getJson, placeParams } from '../api.js'
import { ErrorBox, Loading, formatDate, formatNumber, useApi } from './common.jsx'
import IndexMap from './IndexMap.jsx'
import SeasonChart from './SeasonChart.jsx'
import { useReportSection } from './report.js'

// Come leggere ogni indice: frasi per l'andamento e per il valore attuale
export const INDEX_SECTIONS = {
  ndre: {
    icon: '🍃', title: 'Clorofilla', subtitle: 'NDRE · nutrimento delle piante',
    up: 'Più clorofilla del solito', down: 'Meno clorofilla del solito',
    words: (v) => (v < 0.2 ? 'poca clorofilla o vegetazione rada' : v < 0.4 ? 'clorofilla moderata' : 'molta clorofilla'),
  },
  ndmi: {
    icon: '💧', title: 'Umidità della vegetazione', subtitle: 'NDMI · stress idrico',
    up: 'Vegetazione più umida del solito', down: 'Vegetazione più secca del solito',
    words: (v) => (v < 0 ? 'secco' : v < 0.2 ? 'umidità medio-bassa' : v < 0.4 ? 'buona umidità' : 'molto umido'),
  },
  ndwi: {
    icon: '🌊', title: 'Acqua', subtitle: "NDWI · laghi, fiumi, allagamenti",
    up: 'Più acqua del solito', down: 'Meno acqua del solito',
    words: (v) => (v > 0 ? "prevalenza d'acqua" : v > -0.3 ? 'terreno umido o vegetazione' : 'terra asciutta'),
  },
  ndbi: {
    icon: '🏙️', title: 'Costruito', subtitle: 'NDBI · edifici, strade, suolo nudo',
    up: 'Più superfici costruite o suolo nudo', down: 'Meno superfici costruite, più verde',
    words: (v) => (v > 0.1 ? 'molto costruito o suolo nudo' : v > 0 ? 'misto' : 'prevalenza di vegetazione'),
  },
  ndsi: {
    icon: '❄️', title: 'Neve', subtitle: 'NDSI · neve e ghiaccio',
    up: 'Più neve del solito', down: 'Meno neve del solito',
    words: (v) => (v > 0.4 ? 'neve o ghiaccio' : v > 0 ? 'neve sporadica o acqua' : 'senza neve'),
  },
  ndci: {
    icon: '🦠', title: 'Alghe', subtitle: "NDCI · solo sull'acqua",
    up: 'Più alghe del solito', down: 'Meno alghe del solito',
    words: (v) => (v < 0 ? 'acqua limpida' : v < 0.1 ? "un po' di alghe" : 'molte alghe (possibile fioritura)'),
  },
  ndti: {
    icon: '🟤', title: 'Torbidità', subtitle: "NDTI · solo sull'acqua",
    up: 'Acqua più torbida del solito', down: 'Acqua più limpida del solito',
    words: (v) => (v < 0 ? 'acqua limpida' : v < 0.1 ? "un po' torbida" : 'torbida (fango, sedimenti)'),
  },
}

function headline(info, comparison) {
  if (comparison.trend === 'same') return ['ok', 'Come negli anni scorsi']
  if (comparison.trend === 'up' || comparison.trend === 'down') {
    const text = comparison.trend === 'up' ? info.up : info.down
    return comparison.strength === 'clear' ? ['warn strong', text] : ['warn', `${text}, di poco`]
  }
  return ['neutral', 'Confronto non disponibile']
}

function signed(value, digits = 2) {
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${formatNumber(Math.abs(value), digits)}`
}

/** Un indice: valore attuale, confronto con la stessa stagione degli anni scorsi e mappa. */
export default function IndexCard({ place, indexKey }) {
  const info = INDEX_SECTIONS[indexKey]
  const result = useApi(
    (signal) => getJson('/api/v1/index/analysis', { index: indexKey, ...placeParams(place, 1.0) }, { signal }),
    [place.lat, place.lon, indexKey],
  )
  const r = result.status === 'ok' && result.data.status !== 'no_water' ? result.data : null
  useReportSection(indexKey, r?.latest ? {
    title: `${info.title} (${indexKey.toUpperCase()})`,
    facts: [
      ['Valore ora', `${formatNumber(r.latest.median)} · ${info.words(r.latest.median)}`],
      ['Immagine del', formatDate(r.latest.date)],
      r.baseline && ['Di solito', `${formatNumber(r.baseline.median)} (da ${formatNumber(r.baseline.min)} a ${formatNumber(r.baseline.max)})`],
      ['Confronto', headline(info, r.comparison)[1]],
    ].filter(Boolean),
    notes: ['Area di 1 × 1 km intorno al punto · Sentinel-2 L2A, 10 m.'],
    attribution: 'Contiene dati Copernicus Sentinel modificati',
  } : null)
  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />
  if (result.status !== 'ok') {
    return <Loading text={`Analisi: ${info.title.toLowerCase()}…`}
      hint="Immagine recente più nitida e stesse settimane dei 3 anni precedenti. Di solito 20-40 secondi." />
  }

  const a = result.data
  if (a.status === 'no_water') {
    return (
      <>
        {a.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
        <p className="small muted">{a.caption}</p>
      </>
    )
  }
  const { latest, baseline, comparison } = a
  const [tone, text] = headline(info, comparison)
  const years = baseline?.years || []

  return (
    <div>
      {latest && (
        <div className={`outcome ${tone}`}>
          <span className="outcome-dot" />
          <div>
            <strong>{text}</strong>
            {comparison.delta != null && <span className="muted small"> ({signed(comparison.delta)})</span>}
          </div>
        </div>
      )}
      <dl className="facts">
        {latest && (
          <div><dt>Valore ora</dt><dd>{formatNumber(latest.median)} · {info.words(latest.median)}</dd></div>
        )}
        {latest?.water_ha != null && (
          <div><dt>Acqua libera ora</dt><dd>{formatNumber(latest.water_ha, 1)} ha</dd></div>
        )}
        {latest?.snow_percentage != null && (
          <div><dt>Area innevata ora</dt><dd>{formatNumber(latest.snow_percentage, 0)}%</dd></div>
        )}
        {latest && <div><dt>Immagine del</dt><dd>{formatDate(latest.date)}{!latest.is_recent && ' (non recente)'}</dd></div>}
        {baseline && (
          <div>
            <dt>Di solito ({years[0]}–{years[years.length - 1]})</dt>
            <dd>
              {formatNumber(baseline.median)}
              {baseline.water_ha != null && ` · ${formatNumber(baseline.water_ha, 1)} ha`}
              {baseline.snow_percentage != null && ` · ${formatNumber(baseline.snow_percentage, 0)}% innevato`}
            </dd>
          </div>
        )}
        {baseline && (
          <div><dt>Negli anni scorsi</dt><dd>da {formatNumber(baseline.min)} a {formatNumber(baseline.max)} ({baseline.samples} immagini)</dd></div>
        )}
        {latest && <div><dt>Zona senza nuvole</dt><dd>{formatNumber(latest.clear_percentage, 0)}%</dd></div>}
      </dl>
      {(baseline?.observations?.length > 0 || latest) && (
        <>
          <p className="eyebrow spaced">Stesso periodo, anni diversi</p>
          <SeasonChart
            observations={(baseline?.observations || []).map((o) => ({ date: o.date, value: o.median }))}
            baseline={baseline}
            latest={latest && { date: latest.date, value: latest.median }}
          />
        </>
      )}
      {a.messages.map((m) => <p key={m} className="note">⚠ {m}</p>)}
      {a.formula && <p className="formula">{a.formula}</p>}
      <IndexMap place={place} layerKey={indexKey} />
    </div>
  )
}
