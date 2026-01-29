// Supabase Edge Function: get-job-status
// Returns the status of a personalization job
// Frontend polls this to check completion

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers":
    "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  // Only accept GET
  if (req.method !== "GET") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    // Get job_id from URL params
    const url = new URL(req.url);
    const jobId = url.searchParams.get("job_id");
    const email = url.searchParams.get("email");

    if (!jobId && !email) {
      return new Response(
        JSON.stringify({ error: "job_id or email is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Query job status
    let query = supabase.from("personalization_jobs").select("*");

    if (jobId) {
      query = query.eq("id", parseInt(jobId));
    } else if (email) {
      query = query.eq("email", email.toLowerCase()).order("created_at", { ascending: false });
    }

    const { data: jobs, error: queryError } = await query.limit(1);

    if (queryError) {
      console.error("Error querying job:", queryError);
      return new Response(
        JSON.stringify({ error: "Failed to query job status" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (!jobs || jobs.length === 0) {
      return new Response(
        JSON.stringify({ error: "Job not found" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const job = jobs[0];

    // If job is completed, also fetch the output
    let personalization = null;
    if (job.status === "completed") {
      // Get from finalize_data
      const { data: finalData } = await supabase
        .from("finalize_data")
        .select("*")
        .eq("email", job.email)
        .order("resolved_at", { ascending: false })
        .limit(1);

      if (finalData && finalData.length > 0) {
        personalization = {
          intro_hook: finalData[0].personalization_intro,
          cta: finalData[0].personalization_cta,
          normalized_data: finalData[0].normalized_data,
        };
      }
    }

    return new Response(
      JSON.stringify({
        job_id: job.id,
        email: job.email,
        status: job.status,
        created_at: job.created_at,
        completed_at: job.completed_at,
        error_message: job.error_message,
        personalization,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error getting job status:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
