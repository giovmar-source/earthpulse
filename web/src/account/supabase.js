// Client Supabase del sito (login e dati dell'utente con Row Level Security).
// Spento finché non si impostano VITE_SUPABASE_URL e VITE_SUPABASE_PUBLISHABLE_KEY
// (chiave "publishable", pensata per stare nel browser). Senza, il sito funziona
// come prima e il pannello Account spiega che gli account arriveranno al lancio.
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

export const supabase = url && key
  ? createClient(url, key, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } })
  : null

/** Token di accesso della sessione corrente (null se nessuno ha fatto il login). */
export async function accessToken() {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token || null
}
