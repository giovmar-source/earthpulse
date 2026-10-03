import { METHODOLOGY } from './methodology.js'

/** Come funziona EarthPulse: dati, indici, controlli di qualità e limiti. */
export default function MethodologyPanel({ onClose, onCredits }) {
  return (
    <aside className="panel wide method">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Come funziona</p>
      <h2>Metodologia</h2>
      <p className="muted">
        Il satellite è l'ingrediente, non il prodotto: ecco come trasformiamo le immagini in
        un'informazione leggibile.
      </p>
      {onCredits && <button className="method-link" onClick={onCredits}>📜 Crediti e licenze di tutte le fonti →</button>}
      <nav className="method-index" aria-label="Indice">
        {METHODOLOGY.map((s, i) => (
          <a key={s.title} href={`#metodo-${i}`}>{s.title}</a>
        ))}
      </nav>
      {METHODOLOGY.map((s, i) => (
        <section key={s.title} id={`metodo-${i}`} className="method-section">
          <h3>{s.title}</h3>
          {s.items.map(([kind, text], k) => {
            if (kind === 'f') return <p key={k} className="method-formula">{text}</p>
            if (kind === 'b') return <p key={k} className="method-bullet">{text}</p>
            return <p key={k}>{text}</p>
          })}
        </section>
      ))}
    </aside>
  )
}
