import { useEffect, useState } from 'react'
import * as Astronomy from 'astronomy-engine'
import { apiUrl, getJson } from '../api.js'
import { useApi } from '../place/common.jsx'

/** Il Sole dal vivo: l'immagine più recente del Solar Dynamics Observatory (NASA). */
export function useSun(active) {
  const [product, setProduct] = useState('0193')
  const [observed, setObserved] = useState(null)
  const [status, setStatus] = useState('loading')
  const [image, setImage] = useState(null)
  const products = useApi((signal) => getJson('/api/v1/space/sun/products', null, { signal }), [], active)

  useEffect(() => {
    if (!active) return undefined
    let url = null
    let cancelled = false
    setStatus('loading')
    fetch(apiUrl(`/api/v1/space/sun?product=${product}`))
      .then((response) => {
        if (!response.ok) throw new Error(`Errore ${response.status}`)
        setObserved(response.headers.get('X-Observed'))
        return response.blob()
      })
      .then((blob) => {
        if (cancelled) return
        url = URL.createObjectURL(blob)
        setImage(url)
        setStatus('ok')
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true; if (url) URL.revokeObjectURL(url) }
  }, [product, active])

  return { product, setProduct, observed, status, image, products: products.status === 'ok' ? products.data : null }
}

export function SunStage({ sun }) {
  return (
    <div className="sun-stage">
      {sun.image && <img src={sun.image} alt="Il Sole ripreso dal Solar Dynamics Observatory" className={sun.status === 'loading' ? 'dim' : ''} />}
      {sun.status === 'loading' && <p className="space-status"><span className="spinner" /> Scarico l'ultima immagine dal satellite SDO…</p>}
      {sun.status === 'error' && <p className="space-status error">Immagine del Sole non disponibile in questo momento.</p>}
    </div>
  )
}

export function SunPanel({ sun }) {
  const info = sun.products?.products.find((p) => p.key === sun.product)
  const distanceKm = Astronomy.HelioVector(Astronomy.Body.Earth, new Date()).Length() * Astronomy.KM_PER_AU
  return (
    <div>
      <h2>Il Sole</h2>
      <p className="muted">La nostra stella, ripresa pochi minuti fa dal Solar Dynamics Observatory della NASA.</p>
      <div className="live">
        <span className="live-dot" /> Adesso il Sole è a <strong>{(distanceKm / 1e6).toLocaleString('it-IT', { maximumFractionDigits: 2 })} milioni di km</strong>:
        la sua luce impiega {(distanceKm / 299792.458 / 60).toLocaleString('it-IT', { maximumFractionDigits: 1 })} minuti ad arrivare.
        {sun.observed && (
          <> Immagine ricevuta il {new Date(sun.observed).toLocaleString('it-IT', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })}.</>
        )}
      </div>
      <p className="eyebrow spaced">Cosa guardare</p>
      <div className="chips">
        {(sun.products?.products || []).map((p) => (
          <button key={p.key} className={p.key === sun.product ? 'chip on' : 'chip'} onClick={() => sun.setProduct(p.key)}>{p.label}</button>
        ))}
      </div>
      {info && <p className="small">{info.text}</p>}
      <dl className="facts">
        <div><dt>Diametro</dt><dd>1,39 milioni di km (109 volte la Terra)</dd></div>
        <div><dt>Temperatura</dt><dd>circa 5500 °C in superficie, oltre un milione di °C nella corona</dd></div>
        <div><dt>Età</dt><dd>circa 4,6 miliardi di anni</dd></div>
        <div><dt>Una rotazione</dt><dd>circa 25 giorni all'equatore, più lenta ai poli</dd></div>
      </dl>
      <div className="box">
        <p className="eyebrow">Come leggere l'immagine</p>
        <ul className="missions">
          <li>Le immagini in ultravioletto (171, 193, 304 Å) sono in falsi colori: ogni filtro mostra gas a una temperatura diversa.</li>
          <li>È l'ultima immagine pubblicata dal satellite, aggiornata dal nostro server al massimo ogni 10 minuti. L'orario è quello di pubblicazione del file.</li>
          <li>SDO osserva il Sole senza interruzioni da un'orbita geosincrona dal 2010.</li>
        </ul>
      </div>
      <p className="credit">{sun.products?.attribution || 'Courtesy of NASA/SDO and the AIA, EVE, and HMI science teams.'}</p>
    </div>
  )
}
