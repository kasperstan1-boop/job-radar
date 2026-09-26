import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const { token } = await req.json()
    if (!token) throw new Error("Brak tokenu")

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Hashujemy token przed porównaniem z bazą (SHA-256)
    const encoder = new TextEncoder()
    const data = encoder.encode(token)
    const hashBuffer = await crypto.subtle.digest('SHA-256', data)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    const tokenHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')

    // Szukamy profilu
    const { data: profile, error } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('config_token_hash', tokenHash)
      .single()

    if (error || !profile) {
      return new Response(JSON.stringify({ error: "Nieprawidłowy token" }), {
        status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // Generujemy session_token
    const sessionToken = crypto.randomUUID() + crypto.randomUUID()
    const sessionEncoder = new TextEncoder()
    const sessionData = sessionEncoder.encode(sessionToken)
    const sessionHashBuffer = await crypto.subtle.digest('SHA-256', sessionData)
    const sessionHashArray = Array.from(new Uint8Array(sessionHashBuffer))
    const sessionTokenHash = sessionHashArray.map(b => b.toString(16).padStart(2, '0')).join('')

    // Zapisujemy sesję na 30 dni
    const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
    await supabase.from('user_sessions').insert({
      session_token_hash: sessionTokenHash,
      user_id: profile.id,
      expires_at: expiresAt
    })

    return new Response(JSON.stringify({ session_token: sessionToken }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})