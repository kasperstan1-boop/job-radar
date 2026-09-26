import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

serve(async (req) => {
  const corsHeaders = {
    "Access-Control-Allow-Origin": "https://kasperstan1-boop.github.io",
    "Access-Control-Allow-Headers":
      "authorization, apikey, content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  };
  const respond = (body: unknown, status = 200) =>
    Response.json(body, { status, headers: corsHeaders });

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!supabaseUrl || !serviceRoleKey) {
    return respond({ success: false }, 500);
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
  );

  let email: unknown;
  try {
    ({ email } = await req.json());
  } catch {
    return respond({ success: false }, 400);
  }

  if (
    typeof email !== "string" ||
    !email.includes("@") ||
    email.length < 5
  ) {
    return respond({ success: false }, 400);
  }

  const normalizedEmail = email.trim().toLowerCase();
  const { data: existingUser, error: lookupError } = await supabase
    .from("user_profiles")
    .select("id")
    .eq("email", normalizedEmail)
    .maybeSingle();

  if (lookupError) return respond({ success: false }, 500);
  if (existingUser) return respond({ success: true });

  const defaultPreferences = {
    roles: {
      selected: ["ai_model_trainer", "python_scraper"],
      custom_tags: [],
      match_mode: "any",
    },
    strict_no_phone: true,
    async_first_no_spyware: true,
    ignore_degree_requirement: true,
    salary: {
      enabled: false,
      min_annual_usd: null,
      min_hourly_usd: null,
      require_disclosed: false,
    },
    freshness_hours: 24,
    geo: {
      remote_worldwide_only: true,
      excluded_regions: [],
    },
    language: {
      offer_languages: ["en"],
      require_english_ok: true,
    },
    blocklist: { companies: [], keywords: [] },
    allowlist: { companies: [] },
    notifications: {
      digest_hour_utc: 7,
      max_jobs_per_digest: 25,
      format: "html",
      email_enabled: true,
      teams_webhook_url: null,
      slack_webhook_url: null,
    },
  };

  const randomBytes = crypto.getRandomValues(new Uint8Array(32));
  const token = `sec_${
    Array.from(randomBytes, (byte) => byte.toString(16).padStart(2, "0")).join(
      "",
    )
  }`;
  const hashBuffer = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(token),
  );
  const tokenHash = Array.from(
    new Uint8Array(hashBuffer),
    (byte) => byte.toString(16).padStart(2, "0"),
  ).join("");

  const { error: insertError } = await supabase.from("user_profiles").insert({
    email: normalizedEmail,
    config_token_hash: tokenHash,
    email_verified: false,
    preferences: defaultPreferences,
  });

  if (insertError?.code === "23505") return respond({ success: true });
  if (insertError) return respond({ success: false }, 500);

  const resendApiKey = Deno.env.get("RESEND_API_KEY");
  if (!resendApiKey) {
    await supabase
      .from("user_profiles")
      .delete()
      .eq("email", normalizedEmail)
      .eq("config_token_hash", tokenHash);
    return respond({ success: false }, 500);
  }

  const configUrl =
    `https://kasperstan1-boop.github.io/job-radar/config.html#token=${token}`;

  let resendOk = false;
  try {
    const resendResponse = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${resendApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: "Job Radar <onboarding@resend.dev>",
        to: [normalizedEmail],
        subject: "Zweryfikuj swój adres e-mail",
        html: `<p><a href="${configUrl}">Skonfiguruj profil</a></p>`,
        text: `Skonfiguruj profil: ${configUrl}`,
      }),
    });
    resendOk = resendResponse.ok;
  } catch {
    // Obsłuż poniżej jako nieudaną wysyłkę.
  }

  if (!resendOk) {
    await supabase
      .from("user_profiles")
      .delete()
      .eq("email", normalizedEmail)
      .eq("config_token_hash", tokenHash);
    return respond({ success: false }, 502);
  }

  return respond({ success: true });
});