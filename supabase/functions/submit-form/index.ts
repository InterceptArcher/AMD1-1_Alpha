// Supabase Edge Function: submit-form
// Receives form submissions from Vercel frontend
// Validates input, creates job record, and triggers enrichment

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

// CORS headers for Vercel frontend
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// Email validation regex
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface FormSubmission {
  email: string;
  cta?: string;
  consent: boolean;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}

interface JobRecord {
  email: string;
  domain: string | null;
  cta: string | null;
  status: string;
  created_at: string;
}

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  // Only accept POST
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    // Parse request body
    const body: FormSubmission = await req.json();

    // Validate required fields
    if (!body.email) {
      return new Response(
        JSON.stringify({ error: "Email is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (!body.consent) {
      return new Response(
        JSON.stringify({ error: "Consent is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Validate email format
    const email = body.email.toLowerCase().trim();
    if (!EMAIL_REGEX.test(email)) {
      return new Response(
        JSON.stringify({ error: "Invalid email format" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Extract domain from email
    const domain = email.split("@")[1];

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Create job record
    const jobData: JobRecord = {
      email,
      domain,
      cta: body.cta || null,
      status: "pending",
      created_at: new Date().toISOString(),
    };

    const { data: job, error: insertError } = await supabase
      .from("personalization_jobs")
      .insert(jobData)
      .select()
      .single();

    if (insertError) {
      console.error("Error creating job:", insertError);
      return new Response(
        JSON.stringify({ error: "Failed to create job" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Trigger enrichment (call Railway backend)
    const railwayUrl = Deno.env.get("RAILWAY_BACKEND_URL");
    if (railwayUrl) {
      // Fire and forget - don't wait for enrichment to complete
      fetch(`${railwayUrl}/rad/enrich`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, domain, job_id: job.id }),
      }).catch((err) => {
        console.error("Error triggering enrichment:", err);
      });
    }

    // Return job ID for polling
    return new Response(
      JSON.stringify({
        success: true,
        job_id: job.id,
        email,
        status: "pending",
        message: "Form submitted successfully. Personalization in progress.",
      }),
      {
        status: 201,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error processing form submission:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
