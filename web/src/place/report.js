import { createContext, useContext, useEffect, useMemo } from 'react'

// Raccolta delle sezioni per la "scheda del luogo" in PDF: ogni scheda con dati sullo
// schermo registra titolo, numeri principali, note e fonte. Niente nuovi calcoli.
export const ReportContext = createContext(null)

export function useReportSection(key, section) {
  const ctx = useContext(ReportContext)
  const serialized = section ? JSON.stringify(section) : null
  useEffect(() => {
    if (!ctx) return undefined
    if (serialized) ctx.set(key, JSON.parse(serialized))
    else ctx.remove(key)
    return () => ctx.remove(key)
  }, [ctx, key, serialized])
}

/** Registro stabile delle sezioni (una Map in memoria, aggiornata dalle schede). */
export function useReportRegistry() {
  return useMemo(() => {
    const sections = new Map()
    return {
      set: (key, section) => sections.set(key, section),
      remove: (key) => sections.delete(key),
      list: (order) => order.filter((k) => sections.has(k)).map((k) => sections.get(k))
        .concat([...sections.keys()].filter((k) => !order.includes(k)).map((k) => sections.get(k))),
      size: () => sections.size,
    }
  }, [])
}
