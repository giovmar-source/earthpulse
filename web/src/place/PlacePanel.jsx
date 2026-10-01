import { useState } from 'react'
import { Section } from './common.jsx'
import VegetationCard from './VegetationCard.jsx'
import ImageryCard from './ImageryCard.jsx'
import HeatCard from './HeatCard.jsx'
import NightCard from './NightCard.jsx'
import ArchiveCard from './ArchiveCard.jsx'

function formatCoord(value, positive, negative) {
  return `${Math.abs(value).toFixed(4)}° ${value >= 0 ? positive : negative}`
}

// Sezioni della Superficie. Ognuna chiede i dati al server solo quando la apri:
// il server gratuito ha poca memoria e così non riceve tutto insieme.
const SURFACE_SECTIONS = [
  { key: 'vegetation', icon: '🌿', title: 'Stato della vegetazione', subtitle: 'Sentinel-2 · confronto con gli anni scorsi', Card: VegetationCard },
  { key: 'imagery', icon: '🛰️', title: "Dall'alto", subtitle: 'Colori reali e indici · Sentinel-2, 10 m', Card: ImageryCard },
  { key: 'heat', icon: '🌡️', title: 'Isole di calore', subtitle: "Temperatura delle superfici d'estate · Landsat", Card: HeatCard },
  { key: 'night', icon: '🌃', title: 'Luci notturne', subtitle: 'Dal 2012 · Suomi NPP', Card: NightCard },
  { key: 'archive', icon: '🕰️', title: "Com'era dal 1984", subtitle: 'Archivio Landsat', Card: ArchiveCard },
]

function AtmosphereTab() {
  return (
    <div className="coming">
      <p>
        Qui arriverà quello che c'è <strong>sopra</strong> il luogo, dai satelliti che osservano
        l'atmosfera:
      </p>
      <ul>
        <li><strong>Qualità dell'aria</strong> (Sentinel-5P): biossido di azoto, ozono, monossido di carbonio, aerosol.</li>
        <li><strong>Gas serra</strong> (Sentinel-5P): metano.</li>
        <li><strong>Nuvole in diretta</strong> (Meteosat di terza generazione, strumento FCI): un'immagine ogni 10 minuti.</li>
      </ul>
      <p className="muted small">
        Sono dati con pixel di chilometri, non di metri: descrivono l'aria di una città o di una
        regione, non di una singola strada.
      </p>
    </div>
  )
}

/** Analisi del luogo scelto sul globo, divisa tra Superficie e Atmosfera. */
export default function PlacePanel({ place, onClose }) {
  const [tab, setTab] = useState('surface')
  const [open, setOpen] = useState({ vegetation: true })
  const toggle = (key) => setOpen((o) => ({ ...o, [key]: !o[key] }))

  return (
    <aside className="panel wide">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Analisi del luogo</p>
      <h2>{place.name || `${formatCoord(place.lat, 'N', 'S')}, ${formatCoord(place.lon, 'E', 'O')}`}</h2>
      {place.name && (
        <p className="muted small">{formatCoord(place.lat, 'N', 'S')}, {formatCoord(place.lon, 'E', 'O')}</p>
      )}

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
        {SURFACE_SECTIONS.map(({ key, icon, title, subtitle, Card }) => (
          <Section key={key} icon={icon} title={title} subtitle={subtitle} open={!!open[key]} onToggle={() => toggle(key)}>
            <Card place={place} />
          </Section>
        ))}
        <p className="muted small">
          Ogni sezione si carica quando la apri. Le immagini si calcolano al momento sul
          server: la prima volta può servire fino a un minuto.
        </p>
      </div>
      {tab === 'atmosphere' && <AtmosphereTab />}
    </aside>
  )
}
