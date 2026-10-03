import { useEffect, useState } from 'react'
import { downloadFile } from '../api.js'
import { supabase } from '../account/supabase.js'
import { ReportContext, useReportRegistry } from './report.js'
import { Section } from './common.jsx'
import VegetationCard from './VegetationCard.jsx'
import ImageryCard from './ImageryCard.jsx'
import HeatCard from './HeatCard.jsx'
import NightCard from './NightCard.jsx'
import ArchiveCard from './ArchiveCard.jsx'
import IndexCard, { INDEX_SECTIONS } from './IndexCard.jsx'
import AtmosphereTab from './AtmosphereTab.jsx'
import { FiresCard, RainCard, SealedCard, SeaCard, WaterCard } from './EarthToolsCards.jsx'

function formatCoord(value, positive, negative) {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`
}

// Sezioni della Superficie, in tre gruppi. Ognuna chiede i dati al server solo
// quando la apri: il server gratuito ha poca memoria e così non riceve tutto insieme.
const SURFACE_GROUPS = [
  {
    title: null,
    sections: [
      { key: 'imagery', icon: '🛰️', title: "Dall'alto", subtitle: 'Colori reali · Sentinel-2, 10 m',
        render: (place) => <ImageryCard place={place} layerOrder={['rgb']} /> },
    ],
  },
  {
    title: 'Indici · area di 1 km, confronto con gli anni scorsi',
    sections: [
      { key: 'vegetation', icon: '🌿', title: 'Vegetazione', subtitle: 'NDVI · vigore delle piante',
        render: (place) => <VegetationCard place={place} /> },
      ...Object.entries(INDEX_SECTIONS).map(([key, info]) => ({
        key, icon: info.icon, title: info.title, subtitle: info.subtitle,
        render: (place) => <IndexCard place={place} indexKey={key} />,
      })),
    ],
  },
  {
    title: 'Acqua, fuoco e suolo',
    sections: [
      { key: 'water', icon: '🌊', title: 'Acqua e allagamenti', subtitle: 'Radar Sentinel-1 · anche con le nuvole',
        render: (place) => <WaterCard place={place} /> },
      { key: 'rain', icon: '🌧️', title: 'Pioggia e umidità del suolo', subtitle: 'NASA POWER · rispetto alla norma',
        render: (place) => <RainCard place={place} /> },
      { key: 'fires', icon: '🔥', title: 'Incendi attivi', subtitle: 'NASA FIRMS · ultimi 5 giorni',
        render: (place) => <FiresCard place={place} /> },
      { key: 'sea', icon: '🐟', title: 'Mare', subtitle: 'Temperatura e clorofilla · NOAA',
        render: (place) => <SeaCard place={place} /> },
      { key: 'sealed', icon: '🏙️', title: 'Suolo impermeabilizzato', subtitle: 'Cemento e asfalto · Copernicus, Europa',
        render: (place) => <SealedCard place={place} /> },
    ],
  },
  {
    title: 'Altri dati',
    sections: [
      { key: 'heat', icon: '🌡️', title: 'Isole di calore', subtitle: "Temperatura delle superfici d'estate · Landsat",
        render: (place) => <HeatCard place={place} /> },
      { key: 'night', icon: '🌃', title: 'Luci notturne', subtitle: 'Dal 2012 · Suomi NPP',
        render: (place) => <NightCard place={place} /> },
      { key: 'archive', icon: '🕰️', title: "Com'era dal 1984", subtitle: 'Archivio Landsat',
        render: (place) => <ArchiveCard place={place} /> },
    ],
  },
]

// Ordine delle sezioni nella scheda PDF
const REPORT_ORDER = ['vegetation', ...Object.keys(INDEX_SECTIONS), 'water', 'rain', 'fires', 'sea', 'sealed', 'air', 'gas']

/** Analisi del luogo scelto sul globo, divisa tra Superficie e Atmosfera. */
export default function PlacePanel({ place, onClose, onMethodology, account }) {
  const [tab, setTab] = useState('surface')
  const [atmosphereSeen, setAtmosphereSeen] = useState(false)
  useEffect(() => { if (tab === 'atmosphere') setAtmosphereSeen(true) }, [tab])
  const [open, setOpen] = useState({ imagery: true })
  const toggle = (key) => setOpen((o) => ({ ...o, [key]: !o[key] }))
  const report = useReportRegistry()
  const [action, setAction] = useState(null)
  useEffect(() => setAction(null), [place.lat, place.lon])
  const user = account?.user

  async function downloadReport() {
    const sections = report.list(REPORT_ORDER)
    if (!sections.length) {
      setAction('Apri almeno una sezione con dati: la scheda contiene ciò che vedi nel pannello.')
      return
    }
    setAction('Preparazione del PDF…')
    try {
      await downloadFile('/api/v1/export/pdf', `scheda-${(place.name || 'luogo').replace(/[^\w-]+/g, '_')}.pdf`, {
        body: { place: { name: place.name, context: place.context, lat: place.lat, lon: place.lon }, sections },
      })
      setAction(`Scheda PDF scaricata (${sections.length} sezioni).`)
    } catch (e) {
      setAction(e.message)
    }
  }

  async function savePlace() {
    const name = place.name || `${place.lat.toFixed(3)}, ${place.lon.toFixed(3)}`
    const { error } = await supabase.from('saved_places').insert({ name, lat: place.lat, lon: place.lon })
    setAction(error ? error.message : `"${name}" salvato nei tuoi luoghi.`)
  }

  return (
    <ReportContext.Provider value={report}>
    <aside className="panel wide">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Analisi del luogo</p>
      <h2>{place.name || `${formatCoord(place.lat, 'N', 'S')}, ${formatCoord(place.lon, 'E', 'O')}`}</h2>
      {place.name && (
        <p className="muted small">
          {place.context && <>{place.context} · </>}
          {formatCoord(place.lat, 'N', 'S')}, {formatCoord(place.lon, 'E', 'O')}
        </p>
      )}

      <div className="place-actions">
        <button className="chip" onClick={downloadReport}>📄 Scarica la scheda PDF</button>
        {user && <button className="chip" onClick={savePlace}>☆ Salva luogo</button>}
      </div>
      {action && <p className="muted small">{action}</p>}

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'surface'} className={tab === 'surface' ? 'on' : ''} onClick={() => setTab('surface')}>
          Superficie
        </button>
        <button role="tab" aria-selected={tab === 'atmosphere'} className={tab === 'atmosphere' ? 'on' : ''} onClick={() => setTab('atmosphere')}>
          Atmosfera
        </button>
      </div>

      {/* Le sezioni restano montate quando passi ad Atmosfera: niente nuove richieste al ritorno */}
      <div key={`${place.lat},${place.lon}`} hidden={tab !== 'surface'}>
        {SURFACE_GROUPS.map((group) => (
          <div key={group.title || 'top'}>
            {group.title && <p className="group-title">{group.title}</p>}
            {group.sections.map(({ key, icon, title, subtitle, render }) => (
              <Section key={key} icon={icon} title={title} subtitle={subtitle} open={!!open[key]} onToggle={() => toggle(key)}>
                {render(place)}
              </Section>
            ))}
          </div>
        ))}
        <p className="muted small">
          Ogni sezione si carica quando la apri. Le immagini si calcolano al momento sul
          server: la prima volta può servire fino a un minuto.
        </p>
      </div>
      {/* Atmosfera: caricata la prima volta che apri la scheda, poi resta montata */}
      {(tab === 'atmosphere' || atmosphereSeen) && (
        <div key={`atmo-${place.lat},${place.lon}`} hidden={tab !== 'atmosphere'}>
          <AtmosphereTab place={place} />
        </div>
      )}
      <button className="method-link" onClick={onMethodology}>📘 Metodologia completa e limiti →</button>
    </aside>
    </ReportContext.Provider>
  )
}
