import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "https://kasperstan1-boop.github.io",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders });
  }

  try {
    // ── 1. Wyciągnij session_token z Authorization ──
    const authHeader = req.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
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
    const sessionHash = Array.from(new Uint8Array(hashBuffer), (b) =>
      b.toString(16).padStart(2, "0")
    ).join("");

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const { data: session, error: sessionError } = await supabase
      .from("user_sessions")
      .select("user_id, expires_at")
      .eq("session_token_hash", sessionHash)
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

    const userId = session.user_id;

    // ── 3. GET → zwróć preferencje ──
    if (req.method === "GET") {
      const { data: profile } = await supabase
        .from("user_profiles")
        .select("preferences")
        .eq("id", userId)
        .maybeSingle();

      return Response.json(
        { preferences: profile?.preferences || {} },
        { headers: corsHeaders }
      );
    }

    // ── 4. PUT → zapisz preferencje ──
    if (req.method === "PUT") {
      let body: { preferences?: unknown };
      try {
        body = await req.json();
      } catch {
        return Response.json(
          { error: "Nieprawidłowy JSON" },
          { status: 400, headers: corsHeaders }
        );
      }

      const preferences = body.preferences;
      if (!preferences || typeof preferences !== "object") {
        return Response.json(
          { error: "Brak pola preferences" },
          { status: 400, headers: corsHeaders }
        );
      }

      const { error: updateError } = await supabase
        .from("user_profiles")
        .update({
          preferences,
          updated_at: new Date().toISOString(),
        })
        .eq("id", userId);

      if (updateError) {
        return Response.json(
          { error: updateError.message },
          { status: 500, headers: corsHeaders }
        );
      }

      return Response.json({ success: true }, { headers: corsHeaders });
    }

    return Response.json(
      { error: "Method not allowed" },
      { status: 405, headers: corsHeaders }
    );
  } catch (e) {
    return Response.json(
      { error: (e as Error).message },
      { status: 500, headers: corsHeaders }
    );
  }
});