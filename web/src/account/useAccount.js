import { useCallback, useEffect, useState } from 'react'
import { getJson } from '../api.js'
import { supabase } from './supabase.js'

/** Sessione Supabase, piano e uso di oggi (dal nostro server). */
export function useAccount() {
  const [session, setSession] = useState(null)
  const [me, setMe] = useState(null)

  useEffect(() => {
    if (!supabase) return undefined
    supabase.auth.getSession().then(({ data }) => setSession(data.session))
    const { data } = supabase.auth.onAuthStateChange((_event, s) => setSession(s))
    return () => data.subscription.unsubscribe()
  }, [])

  const refresh = useCallback(() => {
    getJson('/api/v1/me').then(setMe).catch(() => setMe(null))
  }, [])
  useEffect(() => { refresh() }, [session, refresh])

  return { enabled: Boolean(supabase), session, user: session?.user || null, me, refresh }
}
