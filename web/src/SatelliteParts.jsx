import { useState } from 'react'
import { SATELLITE_PARTS } from './satelliteParts.js'

/**
 * Immagine del satellite con i punti numerati delle parti (come nell'app):
 * tocca un numero o un'etichetta per leggere com'è fatta quella parte.
 */
export default function SatelliteParts({ cardKey, title }) {
  const info = SATELLITE_PARTS[cardKey]
  const [view, setView] = useState(0)
  const [selected, setSelected] = useState(null)
  if (!info) return null

  const image = info.images[Math.min(view, info.images.length - 1)]
  const part = info.parts.find((p) => p.number === selected) || null

  function choose(p) {
    if (selected === p.number) { setSelected(null); return }
    setSelected(p.number)
    // Se la parte si vede solo nell'altra vista, passiamo a quella
    if (!p.spots[view]) {
      const other = info.images.findIndex((_, i) => p.spots[i])
      if (other >= 0) setView(other)
    }
  }

  return (
    <section className="parts">
      <p className="eyebrow spaced">Com'è fatto</p>
      {info.images.length > 1 && (
        <div className="chips">
          {info.images.map((img, i) => (
            <button key={img.label} className={i === view ? 'chip on' : 'chip'} onClick={() => setView(i)}>
              {img.label}
            </button>
          ))}
        </div>
      )}

      <div className="sat-frame">
        <img src={image.src} alt={`${title}, ${image.label.toLowerCase()}`} />
        {info.parts.map((p) => {
          const spot = p.spots[view]
          if (!spot) return null
          return (
            <button
              key={p.number}
              className={p.number === selected ? 'spot on' : 'spot'}
              style={{ left: `${spot[0] * 100}%`, top: `${spot[1] * 100}%` }}
              onClick={() => choose(p)}
              aria-label={`${p.number}. ${p.name}`}
            >
              {p.number}
            </button>
          )
        })}
      </div>
      <p className="credit">{image.caption}</p>
      <p className="credit">{image.credit}</p>

      <div className="chips parts-list">
        {info.parts.map((p) => (
          <button key={p.number} className={p.number === selected ? 'chip on' : 'chip'} onClick={() => choose(p)}>
            <span className="swatch" style={{ background: p.color }} /> {p.number} · {p.name}
          </button>
        ))}
      </div>

      {part ? (
        <div className="part-card">
          <h3><span className="swatch" style={{ background: part.color }} /> {part.number} · {part.name}</h3>
          <p className="role">{part.role}</p>
          <p>{part.description}</p>
          {part.facts.length > 0 && (
            <dl className="facts">
              {part.facts.map(([label, value]) => (
                <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
              ))}
            </dl>
          )}
          <div className="info-box">
            <p className="eyebrow">Info</p>
            <p>{part.info}</p>
          </div>
          {part.inEarthPulse && (
            <div className="box">
              <p className="eyebrow">In EarthPulse</p>
              <p>{part.inEarthPulse}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="part-card">
          <h3>Visione d'insieme</h3>
          <p>{info.overview}</p>
        </div>
      )}
      <p className="muted small">{info.sources}</p>
    </section>
  )
}
