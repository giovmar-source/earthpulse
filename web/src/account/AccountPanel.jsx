import { useEffect, useState } from 'react'
import { getJson } from '../api.js'
import { ErrorBox, useApi } from '../place/common.jsx'
import { APP_NAME } from '../brand.js'
import { supabase } from './supabase.js'

const LIMIT_LABELS = {
  places_per_day: 'Luoghi al giorno', exports_per_day: 'Esportazioni al giorno',
  saved_places: 'Luoghi salvati', alerts: 'Avvisi automatici',
}
const ALERT_KINDS = { fires: 'Incendi entro il raggio', new_water: 'Acqua nuova (possibile allagamento)' }

/** Piani: Gratis, Pro, Istituzionale (pagamenti predisposti ma non ancora attivi). */
function Plans({ current }) {
  const result = useApi((signal) => getJson('/api/v1/plans', null, { signal }), [])
  if (result.status !== 'ok') return null
  const { plans, payments_enabled: payments } = result.data
  return (
    <div className="plans">
      {plans.map((p) => (
        <div key={p.key} className={p.key === current ? 'plan on' : 'plan'}>
          <p className="plan-name">{p.label}</p>
          <p className="plan-price">{p.price}</p>
          <ul>{(p.features || []).map((f) => <li key={f}>{f}</li>)}</ul>
          {p.key === current
            ? <span className="muted small">Il tuo piano</span>
            : p.key === 'institutional'
              ? <span className="muted small">Scrivici per un preventivo</span>
              : p.key === 'free'
                ? <span className="muted small">Basta un account gratuito</span>
              : <button className="chip" disabled={!payments}>{payments ? 'Passa a Pro' : 'Pagamenti in arrivo'}</button>}
        </div>
      ))}
    </div>
  )
}

function SignIn() {
  const [email, setEmail] = useState('')
  const [state, setState] = useState(null)
  async function send(e) {
    e.preventDefault()
    setState('sending')
    const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: window.location.href } })
    setState(error ? `Errore: ${error.message}` : 'sent')
  }
  if (state === 'sent') return <p className="highlight">Ti abbiamo inviato un'email: apri il link per entrare. Puoi chiudere questa pagina.</p>
  return (
    <form className="signin" onSubmit={send}>
      <label className="small" htmlFor="email">Entra o registrati con la tua email (nessuna password: ricevi un link)</label>
      <div className="signin-row">
        <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nome@università.it" />
        <button className="chip on" disabled={state === 'sending'}>{state === 'sending' ? 'Invio…' : 'Invia il link'}</button>
      </div>
      {state && state !== 'sending' && <p className="note">{state}</p>}
    </form>
  )
}

/** Luoghi salvati (tabella saved_places, ognuno vede solo i propri) e avvisi. */
function SavedPlaces({ onOpenPlace, plan, limits }) {
  const [places, setPlaces] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [error, setError] = useState(null)
  async function load() {
    const p = await supabase.from('saved_places').select('*').order('created_at', { ascending: false })
    const a = await supabase.from('alerts').select('*')
    if (p.error) setError(p.error.message)
    setPlaces(p.data || [])
    setAlerts(a.data || [])
  }
  useEffect(() => { load() }, [])
  async function remove(id) {
    await supabase.from('saved_places').delete().eq('id', id)
    load()
  }
  async function addAlert(placeId, kind) {
    const { error: e } = await supabase.from('alerts').insert({ place_id: placeId, kind, radius_km: 25 })
    if (e) setError(e.message)
    load()
  }
  async function removeAlert(id) {
    await supabase.from('alerts').delete().eq('id', id)
    load()
  }
  if (error) return <ErrorBox message={error} onRetry={() => { setError(null); load() }} />
  if (!places) return <p className="muted small">Caricamento dei luoghi salvati…</p>
  return (
    <div>
      <p className="eyebrow spaced">Luoghi salvati ({places.length} su {limits.saved_places})</p>
      {!places.length && <p className="muted small">Nessun luogo salvato: apri un luogo e premi "☆ Salva".</p>}
      <ul className="saved-list">
        {places.map((p) => (
          <li key={p.id}>
            <button className="link" onClick={() => onOpenPlace(p)}>{p.name}</button>
            <span className="muted small"> · {p.lat.toFixed(3)}, {p.lon.toFixed(3)}</span>
            <button className="link danger" onClick={() => remove(p.id)} aria-label={`Elimina ${p.name}`}>Elimina</button>
            <div className="alerts-row">
              {Object.entries(ALERT_KINDS).map(([kind, label]) => {
                const alert = alerts.find((a) => a.place_id === p.id && a.kind === kind)
                return alert
                  ? <button key={kind} className="chip on" onClick={() => removeAlert(alert.id)}>🔔 {label}</button>
                  : <button key={kind} className="chip" disabled={!limits.alerts} onClick={() => addAlert(p.id, kind)}
                      title={limits.alerts ? '' : 'Disponibile nei piani Pro e Istituzionale'}>🔕 {label}</button>
              })}
            </div>
          </li>
        ))}
      </ul>
      {!limits.alerts && <p className="muted small">Gli avvisi automatici via email sono inclusi nei piani Pro e Istituzionale.</p>}
    </div>
  )
}

/** Account: accesso, piano, uso di oggi, luoghi salvati, avvisi. */
export default function AccountPanel({ account, onClose, onOpenPlace }) {
  const { me, user } = account
  const plan = me?.plan || 'anonymous'
  return (
    <aside className="panel wide method">
      <button className="close" onClick={onClose} aria-label="Chiudi">×</button>
      <p className="eyebrow">Il tuo spazio</p>
      <h2>Account e piani</h2>
      {!account.enabled && (
        <p className="note">
          Gli account saranno attivati al lancio di {APP_NAME}. Per ora tutte le funzioni sono libere, senza
          registrazione. Qui sotto i piani previsti.
        </p>
      )}
      {account.enabled && !user && <SignIn />}
      {user && (
        <div className="box">
          <p><strong>{user.email}</strong> · piano <strong>{me?.plan_label || '…'}</strong></p>
          {me && (
            <dl className="facts">
              {Object.entries(me.limits).map(([k, v]) => (
                <div key={k}><dt>{LIMIT_LABELS[k]}</dt>
                  <dd>{k === 'places_per_day' ? `${me.usage_today?.place || 0} usati su ${v}` : k === 'exports_per_day' ? `${me.usage_today?.export || 0} usate su ${v}` : v}</dd></div>
              ))}
            </dl>
          )}
          {!me?.enforced && <p className="muted small">I limiti non sono ancora attivi: durante la beta tutto è libero.</p>}
          <button className="link" onClick={() => supabase.auth.signOut()}>Esci</button>
        </div>
      )}
      {user && me && <SavedPlaces onOpenPlace={onOpenPlace} plan={plan} limits={me.limits} />}
      <p className="eyebrow spaced">Piani</p>
      <Plans current={user ? plan : null} />
      <p className="muted small">
        I limiti riguardano il numero di luoghi analizzati al giorno, le esportazioni, i luoghi salvati e gli
        avvisi; tutte le analisi e i dati sono disponibili in ogni piano. Prezzi in definizione.
      </p>
    </aside>
  )
}
