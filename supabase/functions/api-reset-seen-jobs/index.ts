import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "https://kasperstan1-boop.github.io",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
};

serve(async (req) => {
  // Preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  if (req.method !== "DELETE") {
    return Response.json(
      { error: "Method not allowed" },
      { status: 405, headers: corsHeaders }
    );
  }

  try {
    // ── 1. Wyciągnij session_token ──
    const authHeader = req.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return Response.json(
        { error: "Brak autoryzacji" },
        { status: 401, headers: corsHeaders }
      );
    }
    const sessionToken = authHeader.substring(7);

    // ── 2. Hashuj i znajdź sesję ──
    const encoder = new TextEncoder();
    const hashBuffer = await crypto.subtle.digest(
      "SHA-256",
      encoder.encode(sessionToken)
    );
    const sessionTokenHash = Array.from(new Uint8Array(hashBuffer), (b) =>
      b.toString(16).padStart(2, "0")
    ).join("");

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const { data: session, error: sessionError } = await supabase
      .from("user_sessions")
      .select("user_id, expires_at")
      .eq("session_token_hash", sessionTokenHash)
      .maybeSingle();

    if (sessionError || !session) {
      return Response.json(
        { error: "Nieprawidłowa sesja" },
        { status: 401, headers: corsHeaders }
      );
    }

    if (new Date(session.expires_at) < new Date()) {
      return Response.json(
        { error: "Sesja wygasła" },
        { status: 401, headers: corsHeaders }
      );
    }

    // ── 3. Pobierz config_token_hash użytkownika ──
    const { data: profile, error: profileError } = await supabase
      .from("user_profiles")
      .select("config_token_hash")
      .eq("id", session.user_id)
      .maybeSingle();

    if (profileError || !profile) {
      return Response.json(
        { error: "Nie znaleziono profilu" },
        { status: 404, headers: corsHeaders }
      );
    }

    // ── 4. Usuń historię seen_jobs dla tego użytkownika ──
    const { error: deleteError } = await supabase
      .from("seen_jobs")
      .delete()
      .eq("token_hash", profile.config_token_hash);

    if (deleteError) {
      return Response.json(
        { error: deleteError.message },
        { status: 500, headers: corsHeaders }
      );
    }

    return Response.json(
      { success: true, message: "Reset zakończony" },
      { headers: corsHeaders }
    );
  } catch (e) {
    return Response.json(
      { error: (e as Error).message },
      { status: 500, headers: corsHeaders }
    );
  }
});