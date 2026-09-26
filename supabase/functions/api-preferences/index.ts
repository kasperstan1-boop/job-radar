import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const { email } = await req.json()
    if (!email || !email.includes('@')) {
      return new Response(JSON.stringify({ error: "Podaj prawidłowy adres e-mail." }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Generujemy bezpieczny token (32 bajty losowości)
    const randomBytes = new Uint8Array(24)
    crypto.getRandomValues(randomBytes)
    const token = "sec_" + Array.from(randomBytes).map(b => b.toString(16).padStart(2, '0')).join('')

    // Hashujemy token do bazy (SHA-256)
    const encoder = new TextEncoder()
    const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(token))
    const tokenHash = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('')

    // Domyślne preferencje zgodne z sekcją 5.2 dokumentacji
    const defaultPreferences = {
      roles: {
        selected: ["ai_model_trainer", "python_scraper", "async_chat_support"],
        custom_tags: [],
        match_mode: "any"
      },
      strict_no_phone: true,
      async_first_no_spyware: true,
      organization_type: ["any"],
      experience_level: ["any"],
      ignore_degree_requirement: true,
      salary: {
        enabled: false,
        min_annual_usd: null,
        min_hourly_usd: null,
        require_disclosed: false
      },
      freshness_hours: 24,
      geo: {
        remote_worldwide_only: true,
        excluded_regions: []
      },
      language: {
        offer_languages: ["en"],
        require_english_ok: true
      },
      blocklist: {
        companies: [],
        keywords: []
      },
      allowlist: {
        companies: []
      },
      notifications: {
        digest_hour_utc: 7,
        max_jobs_per_digest: 25,
        format: "html",
        email_enabled: true,
        teams_webhook_url: null,
        slack_webhook_url: null
      }
    }

    const cleanEmail = email.trim().toLowerCase()

    // Sprawdzamy, czy profil istnieje
    const { data: existingUser } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('email', cleanEmail)
      .maybeSingle()

    if (existingUser) {
      await supabase
        .from('user_profiles')
        .update({
          config_token_hash: tokenHash,
          updated_at: new Date().toISOString()
        })
        .eq('id', existingUser.id)
    } else {
      await supabase
        .from('user_profiles')
        .insert({
          email: cleanEmail,
          config_token_hash: tokenHash,
          email_verified: true,
          preferences: defaultPreferences
        })
    }

    const loginUrl = `https://kasperstan1-boop.github.io/job-radar/index.html#token=${token}`
    const resendApiKey = Deno.env.get('RESEND_API_KEY')
    let emailSent = false

    if (resendApiKey) {
      try {
        await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${resendApiKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            from: 'Job Radar <onboarding@resend.dev>',
            to: [cleanEmail],
            subject: 'Twój klucz dostępu do Job Radar',
            html: `<h2>Witaj w Job Radar!</h2><p>Twój link do panelu sterowania:</p><p><a href="${loginUrl}">Kliknij tutaj, aby otworzyć panel</a></p><p>Twój klucz: <code>${token}</code></p>`
          })
        })
        emailSent = true
      } catch (_) {
        // Fallback w razie braku aktywnej wysyłki
      }
    }

    return new Response(JSON.stringify({
      success: true,
      token: token,
      email_sent: emailSent,
      login_url: loginUrl,
      message: "Profil został skonfigurowany. Możesz przejść do panelu lub pobrać plik klucza."
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})