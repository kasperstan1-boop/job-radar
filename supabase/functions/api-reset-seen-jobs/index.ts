import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })
  if (req.method !== 'DELETE') return new Response("Method not allowed", { status: 405 })

  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader?.startsWith('Bearer ')) throw new Error("Unauthorized")
    const sessionToken = authHeader.replace('Bearer ', '')

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const encoder = new TextEncoder()
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(sessionToken))
    const sessionTokenHash = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('')

    const { data: session } = await supabase.from('user_sessions').select('user_id').eq('session_token_hash', sessionTokenHash).single()
    if (!session) throw new Error("Unauthorized")

    // Pobieramy powiązany token_hash użytkownika z profilu
    const { data: profile } = await supabase.from('user_profiles').select('config_token_hash').eq('id', session.user_id).single()

    if (profile) {
      // Usuwamy historię seen_jobs dla tego profilu
      await supabase.from('seen_jobs').delete().eq('token_hash', profile.config_token_hash)
    }

    return new Response(JSON.stringify({ success: true, message: "Reset zakończony" }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})