'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useState, useCallback } from 'react';
import EmailConsentForm from '@/components/EmailConsentForm';
import LoadingSpinner from '@/components/LoadingSpinner';
import PersonalizedContent from '@/components/PersonalizedContent';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
}

interface JobStatus {
  job_id: number;
  email: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  personalization?: {
    intro_hook: string;
    cta: string;
    normalized_data?: Record<string, unknown>;
  };
}

const POLL_INTERVAL = 2000; // 2 seconds
const MAX_POLL_ATTEMPTS = 30; // 60 seconds max

function HomeContent() {
  const searchParams = useSearchParams();
  const cta = searchParams.get('cta');

  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Personalizing your content...');
  const [personalizationData, setPersonalizationData] = useState<PersonalizationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get API URLs from environment
  const getSupabaseUrl = () => {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    return url ? `${url}/functions/v1` : null;
  };

  const getApiUrl = () => {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  };

  // Poll for job completion
  const pollJobStatus = useCallback(async (jobId: number, email: string): Promise<PersonalizationData | null> => {
    const supabaseUrl = getSupabaseUrl();
    const apiUrl = getApiUrl();

    for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
      await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL));

      try {
        // Try Supabase Edge Function first
        if (supabaseUrl) {
          const response = await fetch(
            `${supabaseUrl}/get-job-status?job_id=${jobId}`,
            {
              headers: {
                'Content-Type': 'application/json',
                'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
              },
            }
          );

          if (response.ok) {
            const status: JobStatus = await response.json();

            if (status.status === 'completed' && status.personalization) {
              const normalizedData = status.personalization.normalized_data as Record<string, string> | undefined;
              return {
                intro_hook: status.personalization.intro_hook,
                cta: status.personalization.cta,
                first_name: normalizedData?.first_name,
                company: normalizedData?.company_name || normalizedData?.company,
                title: normalizedData?.title,
              };
            }

            if (status.status === 'failed') {
              throw new Error(status.error_message || 'Personalization failed');
            }

            // Update loading message based on status
            if (status.status === 'processing') {
              setLoadingMessage('Enriching your profile...');
            }

            continue;
          }
        }

        // Fallback: Poll Railway backend directly
        const profileResponse = await fetch(`${apiUrl}/rad/profile/${encodeURIComponent(email)}`);

        if (profileResponse.ok) {
          const profileData = await profileResponse.json();
          if (profileData.personalization) {
            return {
              intro_hook: profileData.personalization.intro_hook || 'Welcome!',
              cta: profileData.personalization.cta || 'Get started today',
              first_name: profileData.normalized_profile?.first_name,
              company: profileData.normalized_profile?.company,
              title: profileData.normalized_profile?.title,
            };
          }
        }
      } catch (err) {
        console.error('Poll error:', err);
        // Continue polling unless it's a definitive failure
        if (err instanceof Error && err.message.includes('failed')) {
          throw err;
        }
      }
    }

    throw new Error('Personalization timed out. Please try again.');
  }, []);

  const handleSubmit = async (email: string) => {
    setIsLoading(true);
    setError(null);
    setLoadingMessage('Submitting your request...');

    try {
      const supabaseUrl = getSupabaseUrl();
      const apiUrl = getApiUrl();

      let jobId: number | null = null;

      // Try Supabase Edge Function first
      if (supabaseUrl) {
        try {
          const response = await fetch(`${supabaseUrl}/submit-form`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'apikey': process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
            },
            body: JSON.stringify({
              email,
              cta: cta || 'default',
              consent: true,
            }),
          });

          if (response.ok) {
            const data = await response.json();
            jobId = data.job_id;
            setLoadingMessage('Personalizing your content...');
          }
        } catch (err) {
          console.warn('Supabase Edge Function unavailable, falling back to direct API');
        }
      }

      // Fallback: Call Railway backend directly
      if (!jobId) {
        const response = await fetch(`${apiUrl}/rad/enrich`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, cta: cta || 'default' }),
        });

        if (!response.ok) {
          throw new Error('Failed to start personalization');
        }

        // Direct API call - profile should be ready immediately
        setLoadingMessage('Fetching your personalized content...');

        const profileResponse = await fetch(`${apiUrl}/rad/profile/${encodeURIComponent(email)}`);

        if (!profileResponse.ok) {
          throw new Error('Failed to fetch profile');
        }

        const profileData = await profileResponse.json();
        setPersonalizationData({
          intro_hook: profileData.personalization?.intro_hook || 'Welcome!',
          cta: profileData.personalization?.cta || 'Get started today',
          first_name: profileData.normalized_profile?.first_name,
          company: profileData.normalized_profile?.company,
          title: profileData.normalized_profile?.title,
        });
        return;
      }

      // Poll for completion
      const result = await pollJobStatus(jobId, email);
      if (result) {
        setPersonalizationData(result);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            Welcome to Your Personalized Experience
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            {cta ? `Call to Action: ${cta}` : 'Default CTA Message'}
          </p>
        </div>

        {!personalizationData && !isLoading && (
          <EmailConsentForm onSubmit={handleSubmit} isLoading={isLoading} />
        )}

        {isLoading && (
          <LoadingSpinner message={loadingMessage} />
        )}

        {personalizationData && (
          <PersonalizedContent data={personalizationData} error={error} />
        )}

        {error && !personalizationData && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<LoadingSpinner message="Loading..." />}>
      <HomeContent />
    </Suspense>
  );
}
