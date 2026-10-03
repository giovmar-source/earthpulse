import { getJson } from './api.js'
import { ErrorBox, Loading, useApi } from './place/common.jsx'
import { APP_NAME } from './brand.js'

/** Crediti e licenze: ogni fonte di dati e servizio, con licenza e testo di attribuzione. */
export default function CreditsPanel({ onClose }) {
  const result = useApi((signal) => getJson('/api/v1/credits', null, { signal }), [])
  const groups = {}
  for (const s of result.status === 'ok' ? result.data.sources : []) {
    (groups[s.group] = groups[s.group] || []).push(s)
  }
  return (
    <aside className="panel wide method">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Trasparenza</p>
      <h2>Crediti e licenze</h2>
      <p className="muted">
        {APP_NAME} è costruito su dati pubblici di agenzie spaziali e servizi europei e internazionali.
        Per ogni fonte: chi la fornisce, a cosa serve qui, la licenza e come va citata. Nessuna di
        queste organizzazioni approva o sponsorizza {APP_NAME}.
      </p>
      {result.status === 'error' && <ErrorBox message={result.error} onRetry={result.retry} />}
      {result.status === 'loading' && <Loading text="Caricamento delle fonti…" />}
      {Object.entries(groups).map(([group, items]) => (
        <section key={group} className="method-section">
          <h3>{group}</h3>
          {items.map((s) => (
            <div key={s.key} className="credit-item">
              <p><strong>{s.name}</strong> · <span className="muted">{s.provider}</span></p>
              <p className="small">{s.used_for}</p>
              <p className="small">Licenza: <a href={s.licence_url} target="_blank" rel="noreferrer">{s.licence}</a></p>
              <p className="credit">{s.attribution}</p>
            </div>
          ))}
        </section>
      ))}
      <p className="muted small">
        Le fonti di ogni evento di Big Events e i dettagli dei metodi sono nella Metodologia.
      </p>
    </aside>
  )
}
