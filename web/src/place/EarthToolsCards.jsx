import { useState } from 'react'
import { getJson, placeParams } from '../api.js'
import { CompareImages, ErrorBox, Legend, Loading, formatDate, formatNumber, useApi } from './common.jsx'
import SeriesChart from './SeriesChart.jsx'
import { useReportSection } from './report.js'

function coords(place) {
  return placeParams(place, null, 4)
}

function signed(v, digits = 0) {
  return `${v > 0 ? '+' : ''}${formatNumber(v, digits)}`
}

// ------------------------------------------------------------------ Acqua dal radar

/** Acqua e allagamenti: radar Sentinel-1, adesso contro un periodo di riferimento. */
export function WaterCard({ place }) {
  const [reference, setReference] = useState('year')
  const result = useApi(
    (signal) => getJson('/api/v1/sar/water', { ...coords(place), reference }, { signal }),
    [place.lat, place.lon, reference],
  )
  const w = result.status === 'ok' && result.data.status === 'ok' ? result.data : null
  useReportSection('water', w ? {
    title: 'Acqua e allagamenti (radar Sentinel-1)',
    facts: [['Acqua adesso', `${formatNumber(w.stats.water_now_ha, 1)} ha`],
      [reference === 'year' ? 'Un anno fa' : 'Un mese fa', `${formatNumber(w.stats.water_ref_ha, 1)} ha`],
      ['Acqua nuova (possibile allagamento)', `${formatNumber(w.stats.new, 1)} ha`],
      ['Ultimo passaggio radar', formatDate(w.acquired.now.slice(0, 10))]],
    notes: [`Area di ${w.side_km} × ${w.side_km} km, soglia ${w.threshold_db} dB su VV. Superfici lisce possono sembrare acqua.`],
    attribution: w.attribution,
  } : null)
  const chips = (
    <div className="chips">
      <span className="muted small">Confronta con:</span>
      <button className={reference === 'year' ? 'chip on' : 'chip'} onClick={() => setReference('year')}>un anno fa</button>
      <button className={reference === 'month' ? 'chip on' : 'chip'} onClick={() => setReference('month')}>un mese fa</button>
    </div>
  )
  if (result.status === 'error') return <>{chips}<ErrorBox message={result.error} onRetry={result.retry} /></>
  if (result.status !== 'ok') return <>{chips}<Loading text="Lettura delle immagini radar…" hint="Due periodi di 12 giorni di Sentinel-1: di solito 20-40 secondi." /></>
  const d = result.data
  if (d.status !== 'ok') return <>{chips}<p className="note">⚠ {d.message}</p></>
  const s = d.stats
  const change = s.water_now_ha - s.water_ref_ha
  return (
    <div>
      {chips}
      <dl className="facts">
        <div><dt>Acqua adesso</dt><dd>{formatNumber(s.water_now_ha, 1)} ha</dd></div>
        <div><dt>{reference === 'year' ? 'Un anno fa' : 'Un mese fa'}</dt><dd>{formatNumber(s.water_ref_ha, 1)} ha ({signed(change, 1)} ha)</dd></div>
        <div><dt>Acqua nuova (possibile allagamento)</dt><dd>{formatNumber(s.new, 1)} ha</dd></div>
        <div><dt>Ultimo passaggio radar</dt><dd>{formatDate(d.acquired.now.slice(0, 10))}</dd></div>
      </dl>
      <div className="framed"><CompareImages after={d.image} alt="Acqua dal radar Sentinel-1" afterLabel="Radar di adesso" /></div>
      <p className="muted small">
        <span className="swatch inline" style={{ background: '#1f4fd1' }} /> acqua in entrambi i periodi ·{' '}
        <span className="swatch inline" style={{ background: '#ff3b30' }} /> acqua solo adesso ·{' '}
        <span className="swatch inline" style={{ background: '#ffcc00' }} /> acqua solo prima · in grigio il segnale radar
      </p>
      <p className="small">
        Il radar vede il suolo anche con le nuvole e di notte: l'acqua ferma appare scura. Un pixel è
        acqua se il segnale è sotto {d.threshold_db} dB. Area di {d.side_km} × {d.side_km} km, pixel di 20 m.
      </p>
      <p className="muted small">
        Attenzione: asfalto, sabbia asciutta e neve bagnata possono sembrare acqua; i rilievi creano
        zone d'ombra; il vento increspa l'acqua e la può nascondere. Area senza dati: {formatNumber(100 - s.valid_percent, 0)}%.
      </p>
      <p className="credit">{d.attribution}</p>
    </div>
  )
}

// ------------------------------------------------------------------ Pioggia e suolo

const RAIN_RANGES = [30, 90, 365]

/** Pioggia giornaliera e umidità del suolo (NASA POWER) rispetto alla norma. */
export function RainCard({ place }) {
  const [days, setDays] = useState(90)
  const result = useApi(
    (signal) => getJson('/api/v1/water-cycle', { ...coords(place), days: String(days) }, { signal }),
    [place.lat, place.lon, days],
  )
  const rd = result.status === 'ok' ? result.data : null
  useReportSection('rain', rd ? {
    title: `Pioggia e umidità del suolo (ultimi ${days} giorni)`,
    facts: [['Pioggia nel periodo', `${formatNumber(rd.rain.total_mm, 0)} mm in ${rd.rain.rainy_days} giorni di pioggia`],
      rd.rain.normal_mm != null && ['Di solito negli stessi giorni', `${formatNumber(rd.rain.normal_mm, 0)} mm · ${rd.rain.percent_of_normal}% della norma`],
      rd.soil.surface.latest && ['Umidità del suolo in superficie', `${formatNumber(rd.soil.surface.latest.value, 0)}% (di solito ${formatNumber(rd.soil.surface.normal, 0)}%)`],
      rd.soil.root.latest && ['Umidità nella zona delle radici', `${formatNumber(rd.soil.root.latest.value, 0)}% (di solito ${formatNumber(rd.soil.root.normal, 0)}%)`]].filter(Boolean),
    notes: ['Stime di rianalisi NASA (MERRA-2/GEOS) su celle di circa 50 km; norma 2001–2020.'],
    attribution: rd.attribution,
  } : null)
  const chips = (
    <div className="chips">
      <span className="muted small">Periodo:</span>
      {RAIN_RANGES.map((n) => (
        <button key={n} className={n === days ? 'chip on' : 'chip'} onClick={() => setDays(n)}>{n === 365 ? '1 anno' : `${n} giorni`}</button>
      ))}
    </div>
  )
  if (result.status === 'error') return <>{chips}<ErrorBox message={result.error} onRetry={result.retry} /></>
  if (result.status !== 'ok') return <>{chips}<Loading text="Lettura dei dati NASA POWER…" /></>
  const d = result.data
  const r = d.rain
  const top = d.soil.surface
  const root = d.soil.root
  return (
    <div>
      {chips}
      <dl className="facts">
        <div><dt>Pioggia nel periodo</dt><dd>{formatNumber(r.total_mm, 0)} mm in {r.rainy_days} giorni di pioggia</dd></div>
        {r.normal_mm != null && (
          <div><dt>Di solito negli stessi giorni</dt><dd>{formatNumber(r.normal_mm, 0)} mm · <strong>{r.percent_of_normal}% della norma</strong></dd></div>
        )}
        {top.latest && <div><dt>Umidità del suolo in superficie</dt><dd>{formatNumber(top.latest.value, 0)}%{top.normal != null && <> (di solito {formatNumber(top.normal, 0)}%)</>}</dd></div>}
        {root.latest && <div><dt>Umidità nella zona delle radici</dt><dd>{formatNumber(root.latest.value, 0)}%{root.normal != null && <> (di solito {formatNumber(root.normal, 0)}%)</>}</dd></div>}
        {r.last_date && <div><dt>Ultimo giorno con dati</dt><dd>{formatDate(r.last_date)}</dd></div>}
      </dl>
      <p className="eyebrow spaced">Pioggia giornaliera (mm)</p>
      <SeriesChart series={r.series} kind="bar" unit="mm" digits={1} color="#4f93e6" csvName="pioggia_giornaliera" />
      <p className="eyebrow spaced">Umidità del suolo in superficie (% della saturazione)</p>
      <SeriesChart series={top.series} unit="%" digits={0} color="#a07850" reference={top.normal}
        referenceLabel={top.normal != null ? 'di solito' : ''} min={0} max={100} csvName="umidita_suolo" />
      <p className="small">
        Stime di un modello di rianalisi della NASA (MERRA-2/GEOS) corretto con osservazioni, su celle di
        circa 50 km: descrivono la zona, non il singolo campo. "Di solito" è la media 2001–2020 dello
        stesso luogo e mese. I dati arrivano con 2–7 giorni di ritardo.
      </p>
      <p className="credit">{d.attribution}</p>
    </div>
  )
}

// ------------------------------------------------------------------ Incendi

/** Punti di calore VIIRS entro il raggio: elenco e disegno attorno al luogo. */
export function FiresCard({ place }) {
  const [radius, setRadius] = useState(50)
  const result = useApi(
    (signal) => getJson('/api/v1/fires', { ...coords(place), radius: String(radius), days: '5' }, { signal }),
    [place.lat, place.lon, radius],
  )
  const fd = result.status === 'ok' ? result.data : null
  useReportSection('fires', fd ? {
    title: `Incendi attivi entro ${radius} km (ultimi ${fd.days} giorni)`,
    facts: [['Punti di calore', String(fd.count)],
      fd.nearest_km != null && ['Il più vicino', `${formatNumber(fd.nearest_km, 1)} km`]].filter(Boolean),
    notes: ['VIIRS 375 m, dati quasi in tempo reale. Un punto di calore non è sempre un incendio di vegetazione.'],
    attribution: fd.attribution,
  } : null)
  const chips = (
    <div className="chips">
      <span className="muted small">Raggio:</span>
      {[25, 50, 100].map((r) => <button key={r} className={r === radius ? 'chip on' : 'chip'} onClick={() => setRadius(r)}>{r} km</button>)}
    </div>
  )
  if (result.status === 'error') return <>{chips}<ErrorBox message={result.error} onRetry={result.retry} /></>
  if (result.status !== 'ok') return <>{chips}<Loading text="Ricerca dei punti di calore…" /></>
  const d = result.data
  const R = 90
  return (
    <div>
      {chips}
      <div className={`outcome ${d.count ? 'bad' : 'good'}`}>
        <span className="outcome-dot" />
        <strong>{d.count ? `${d.count} punti di calore negli ultimi ${d.days} giorni` : `Nessun punto di calore negli ultimi ${d.days} giorni`}</strong>
        {d.nearest_km != null && <span className="muted small"> · il più vicino a {formatNumber(d.nearest_km, 1)} km</span>}
      </div>
      {d.count > 0 && (
        <>
          <svg viewBox={`${-R - 10} ${-R - 10} ${2 * R + 20} ${2 * R + 20}`} className="fire-rings" role="img" aria-label="Punti di calore attorno al luogo">
            {[1, 0.5].map((f) => <circle key={f} r={R * f} className="ring" />)}
            <text x={0} y={-R - 2} textAnchor="middle" className="axis">N</text>
            <text x={R * 0.5 + 2} y={-3} className="axis">{radius / 2} km</text>
            <text x={R + 2} y={-3} className="axis">{radius} km</text>
            {d.points.map((p, i) => {
              const a = (p.bearing * Math.PI) / 180
              const r = (p.distance_km / radius) * R
              return <circle key={i} cx={Math.sin(a) * r} cy={-Math.cos(a) * r} r={Math.min(6, 2.5 + (p.frp_mw || 0) / 30)} className="fire-dot" />
            })}
            <circle r="3" className="center" />
          </svg>
          <table className="mini-table">
            <thead><tr><th>Quando (UTC)</th><th>Distanza</th><th>Potenza</th><th>Affidabilità</th></tr></thead>
            <tbody>
              {d.points.slice(0, 12).map((p, i) => (
                <tr key={i}>
                  <td>{formatDate(p.date)} {p.time_utc}{p.night ? ' 🌙' : ''}</td>
                  <td>{formatNumber(p.distance_km, 1)} km</td>
                  <td>{p.frp_mw != null ? `${formatNumber(p.frp_mw, 0)} MW` : '—'}</td>
                  <td>{p.confidence}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {d.points.length > 12 && <p className="muted small">e altri {d.points.length - 12}.</p>}
        </>
      )}
      <p className="small">
        Rilevamenti dei satelliti VIIRS (Suomi NPP, NOAA-20, NOAA-21), pixel di 375 m, circa 3 ore dopo
        il passaggio. Un punto di calore non è sempre un incendio di vegetazione: anche impianti
        industriali, vulcani e roghi agricoli. La potenza (FRP, megawatt) misura l'energia irradiata.
      </p>
      <p className="credit">{d.attribution}</p>
    </div>
  )
}

// ------------------------------------------------------------------ Mare

/** Temperatura del mare e clorofilla negli ultimi 60 giorni (NOAA). */
export function SeaCard({ place }) {
  const result = useApi((signal) => getJson('/api/v1/sea', coords(place), { signal }), [place.lat, place.lon])
  const sd = result.status === 'ok' && result.data.status === 'ok' ? result.data : null
  useReportSection('sea', sd ? {
    title: 'Mare',
    facts: [['Temperatura dell\'acqua', `${formatNumber(sd.sst.summary.latest, 1)} °C (${formatDate(sd.sst.summary.latest_date)})`],
      sd.sst.anomaly && ['Rispetto alla norma', `${signed(sd.sst.anomaly.latest, 1)} °C`],
      sd.chlorophyll.summary && ['Clorofilla', `${formatNumber(sd.chlorophyll.summary.latest, 2)} mg/m³ (${formatDate(sd.chlorophyll.summary.latest_date)})`]].filter(Boolean),
    notes: ['NOAA OISST 0,25° e clorofilla da satellite circa 9 km.'],
    attribution: sd.attribution,
  } : null)
  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />
  if (result.status !== 'ok') return <Loading text="Lettura dei dati del mare…" />
  const d = result.data
  if (d.status !== 'ok') {
    return <p className="note">Il punto è sulla terraferma o troppo vicino alla costa per le celle di 25 km dei dati sul mare. Scegli un punto in mare.</p>
  }
  const t = d.sst.summary
  const a = d.sst.anomaly
  const c = d.chlorophyll.summary
  return (
    <div>
      <dl className="facts">
        <div><dt>Temperatura dell'acqua</dt><dd>{formatNumber(t.latest, 1)} °C il {formatDate(t.latest_date)}</dd></div>
        {a && <div><dt>Rispetto alla norma del periodo</dt><dd><strong>{signed(a.latest, 1)} °C</strong></dd></div>}
        <div><dt>Ultimi 60 giorni</dt><dd>da {formatNumber(t.min, 1)} a {formatNumber(t.max, 1)} °C</dd></div>
        {c && <div><dt>Clorofilla</dt><dd>{formatNumber(c.latest, 2)} mg/m³ il {formatDate(c.latest_date)}</dd></div>}
      </dl>
      <p className="eyebrow spaced">Temperatura della superficie del mare (°C)</p>
      <SeriesChart series={d.sst.series.map((p) => ({ ...p, extra: p.anomaly != null ? `${signed(p.anomaly, 1)} °C rispetto alla norma` : null }))}
        unit="°C" digits={1} color="#f29a4a" csvName="temperatura_mare" />
      {c && (
        <>
          <p className="eyebrow spaced">Clorofilla-a (mg/m³)</p>
          <SeriesChart series={d.chlorophyll.series} unit="mg/m³" digits={2} color="#3fd68f" csvName="clorofilla" />
        </>
      )}
      <p className="small">
        Temperatura: NOAA OISST, dati di satelliti, navi e boe su celle di 0,25° (circa 25 km), un valore
        al giorno; l'anomalia è rispetto alla climatologia del prodotto. Clorofilla: indicatore della
        quantità di fitoplancton, da satelliti (VIIRS, Sentinel-3 OLCI) su celle di circa 9 km, con circa
        10 giorni di ritardo. Valori alti vicino alla costa possono indicare acque torbide o ricche di nutrienti.
      </p>
      <p className="credit">{d.attribution}</p>
    </div>
  )
}

// ------------------------------------------------------------------ Suolo impermeabilizzato

/** Quota di suolo coperta da cemento, asfalto ed edifici (Copernicus HRL 2018). */
export function SealedCard({ place }) {
  const result = useApi((signal) => getJson('/api/v1/imperviousness', coords(place), { signal }), [place.lat, place.lon])
  const hd = result.status === 'ok' && result.data.status === 'ok' ? result.data : null
  useReportSection('sealed', hd ? {
    title: `Suolo impermeabilizzato (${hd.year})`,
    facts: [['Media nell\'area', `${formatNumber(hd.mean_percent, 0)}%`],
      ['Superficie impermeabile', `${formatNumber(hd.sealed_ha, 0)} ha su ${formatNumber(hd.area_ha, 0)} ha`]],
    notes: [`Area di ${hd.side_km} × ${hd.side_km} km, pixel di 10 m.`],
    attribution: hd.attribution,
  } : null)
  if (result.status === 'error') return <ErrorBox message={result.error} onRetry={result.retry} />
  if (result.status !== 'ok') return <Loading text="Lettura della mappa europea…" />
  const d = result.data
  if (d.status !== 'ok') return <p className="note">{d.message}</p>
  return (
    <div>
      <dl className="facts">
        <div><dt>Suolo impermeabile (media)</dt><dd><strong>{formatNumber(d.mean_percent, 0)}%</strong> dell'area</dd></div>
        <div><dt>Superficie impermeabile</dt><dd>{formatNumber(d.sealed_ha, 0)} ha su {formatNumber(d.area_ha, 0)} ha</dd></div>
        {d.center_percent != null && <div><dt>Nel punto scelto (100 m)</dt><dd>{formatNumber(d.center_percent, 0)}%</dd></div>}
        <div><dt>Situazione al</dt><dd>{d.year}</dd></div>
      </dl>
      <div className="framed">
        <CompareImages after={d.image} alt="Suolo impermeabilizzato" afterLabel={String(d.year)} />
        <span className="place-area" style={{ width: '5%' }} />
      </div>
      <Legend stops={d.legend.color_stops} labels={d.legend.labels} />
      <p className="small">
        Percentuale di ogni pixel di 10 m coperta da superfici impermeabili (edifici, strade, piazzali),
        in un'area di {d.side_km} × {d.side_km} km. È l'edizione 2018, l'ultima con un servizio pubblico di
        consultazione; le edizioni più recenti sono solo da scaricare. Solo paesi europei.
      </p>
      <p className="credit">{d.attribution}</p>
    </div>
  )
}
