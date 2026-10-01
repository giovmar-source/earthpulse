import { useEffect, useRef, useState } from 'react'
import { apiUrl } from '../api.js'

/**
 * Carica dati dal backend quando `enabled` è vero; ricarica se cambiano le
 * dipendenze o con retry(). Conta i secondi di attesa (il server gratuito
 * può impiegare 20-60 s, di più se si stava risvegliando).
 */
export function useApi(load, deps, enabled = true) {
  const [state, setState] = useState({ status: 'idle' })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!enabled) return undefined
    const controller = new AbortController()
    setState({ status: 'loading' })
    load(controller.signal)
      .then((data) => setState({ status: 'ok', data }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ status: 'error', error: error.message })
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled, attempt])
  return { ...state, retry: () => setAttempt((a) => a + 1) }
}

function useSeconds(running) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    if (!running) return undefined
    setSeconds(0)
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [running])
  return seconds
}

export function Loading({ text, hint }) {
  const seconds = useSeconds(true)
  return (
    <div className="loading">
      <span className="spinner" />
      <div>
        <strong>{text} {seconds > 0 && `${seconds} s`}</strong>
        {hint && <p className="muted small">{hint}</p>}
        {seconds >= 45 && (
          <p className="muted small">
            Ci vuole più del solito: il server gratuito potrebbe essersi appena risvegliato.
          </p>
        )}
      </div>
    </div>
  )
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="error-box">
      <p>{message}</p>
      {onRetry && <button className="btn" onClick={onRetry}>Riprova</button>}
    </div>
  )
}

/** Riquadro richiudibile: il contenuto (e la richiesta al server) parte solo all'apertura. */
export function Section({ icon, title, subtitle, open, onToggle, children }) {
  return (
    <section className={open ? 'section open' : 'section'}>
      <button className="section-head" onClick={onToggle} aria-expanded={open}>
        <span className="section-icon">{icon}</span>
        <span className="section-titles">
          <strong>{title}</strong>
          {subtitle && <span className="muted small">{subtitle}</span>}
        </span>
        <span className="chevron">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="section-body">{children}</div>}
    </section>
  )
}

/** Barra dei colori con le etichette (sinistra, centro, destra). */
export function Legend({ stops, labels }) {
  if (!stops || stops.length < 2) return null
  const min = stops[0][0]
  const max = stops[stops.length - 1][0]
  const gradient = stops
    .map(([value, color]) => `${color} ${(((value - min) / (max - min)) * 100).toFixed(1)}%`)
    .join(', ')
  return (
    <div className="legend">
      <div className="legend-bar" style={{ background: `linear-gradient(90deg, ${gradient})` }} />
      {labels && labels.some(Boolean) && (
        <div className="legend-labels">
          {labels.map((label, i) => <span key={i}>{label}</span>)}
        </div>
      )}
    </div>
  )
}

/** Immagine del backend con attesa e "riprova" (le immagini si calcolano al momento). */
function RemoteImage({ src, alt, onState }) {
  const [status, setStatus] = useState('loading')
  const [attempt, setAttempt] = useState(0)
  const notify = useRef(onState)
  notify.current = onState
  useEffect(() => { setStatus('loading') }, [src])
  useEffect(() => { notify.current?.(status) }, [status])
  const url = src ? apiUrl(src) + (attempt ? `&retry=${attempt}` : '') : null
  return (
    <>
      {url && (
        <img
          src={url} alt={alt} draggable={false}
          onLoad={() => setStatus('ok')} onError={() => setStatus('error')}
          style={{ visibility: status === 'ok' ? 'visible' : 'hidden' }}
        />
      )}
      {status === 'error' && (
        <div className="image-overlay">
          <span>Immagine non disponibile.</span>
          <button className="btn small" onClick={() => setAttempt((a) => a + 1)}>Riprova</button>
        </div>
      )}
    </>
  )
}

/**
 * Due immagini sovrapposte con un cursore: a sinistra "prima", a destra "dopo".
 * Con una sola immagine mostra solo quella.
 */
export function CompareImages({ before, after, beforeLabel, afterLabel, alt }) {
  const [position, setPosition] = useState(50)
  const [loaded, setLoaded] = useState({})
  const frame = useRef(null)
  const dragging = useRef(false)
  const waiting = (after && loaded.after !== 'ok' && loaded.after !== 'error')
    || (before && loaded.before !== 'ok' && loaded.before !== 'error')

  function move(clientX) {
    const rect = frame.current.getBoundingClientRect()
    setPosition(Math.min(100, Math.max(0, ((clientX - rect.left) / rect.width) * 100)))
  }

  return (
    <div
      ref={frame}
      className="compare"
      onPointerDown={(e) => { if (before) { dragging.current = true; move(e.clientX); e.currentTarget.setPointerCapture(e.pointerId) } }}
      onPointerMove={(e) => { if (dragging.current) move(e.clientX) }}
      onPointerUp={() => { dragging.current = false }}
    >
      <div className="layer">
        <RemoteImage src={after} alt={alt} onState={(s) => setLoaded((l) => ({ ...l, after: s }))} />
      </div>
      {before && (
        <div className="layer" style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }}>
          <RemoteImage src={before} alt={alt} onState={(s) => setLoaded((l) => ({ ...l, before: s }))} />
        </div>
      )}
      {before && <div className="divider" style={{ left: `${position}%` }}><span>⇆</span></div>}
      {before && beforeLabel && <span className="tag left">{beforeLabel}</span>}
      {afterLabel && <span className="tag right">{afterLabel}</span>}
      {waiting && (
        <div className="image-overlay">
          <span className="spinner" /> <span>Calcolo dell'immagine…</span>
        </div>
      )}
    </div>
  )
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(`${iso.slice(0, 10)}T12:00:00Z`)
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function formatNumber(value, digits = 2) {
  return value == null ? '—' : value.toLocaleString('it-IT', {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  })
}
