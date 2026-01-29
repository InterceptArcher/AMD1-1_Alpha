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

  const handleReset = () => {
    setPersonalizationData(null);
    setError(null);
  };

  // Get API URLs from environment
  const getSupabaseUrl = () => {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    return url ? `${url}/functions/v1` : null;
  };

  const getApiUrl = () => {
    // Use relative URL to leverage Next.js proxy (avoids CORS/port issues in Codespaces)
    return '/api';
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
      const apiUrl = getApiUrl();
      console.log('Using API URL:', apiUrl);

      // Call backend directly
      setLoadingMessage('Enriching your profile...');
      const response = await fetch(`${apiUrl}/rad/enrich`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, cta: cta || 'default' }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Enrich failed:', response.status, errorText);
        throw new Error(`Failed to start personalization: ${response.status}`);
      }

      // Profile should be ready immediately
      setLoadingMessage('Fetching your personalized content...');

      const profileResponse = await fetch(`${apiUrl}/rad/profile/${encodeURIComponent(email)}`);

      if (!profileResponse.ok) {
        const errorText = await profileResponse.text();
        console.error('Profile fetch failed:', profileResponse.status, errorText);
        throw new Error(`Failed to fetch profile: ${profileResponse.status}`);
      }

      const profileData = await profileResponse.json();
      console.log('Profile data:', profileData);

      setPersonalizationData({
        intro_hook: profileData.personalization?.intro_hook || 'Welcome!',
        cta: profileData.personalization?.cta || 'Get started today',
        first_name: profileData.normalized_profile?.first_name,
        company: profileData.normalized_profile?.company,
        title: profileData.normalized_profile?.title,
      });
    } catch (err) {
      console.error('Submit error:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-gray-50 to-white p-8">
      <div className="w-full max-w-md space-y-8">
        {!personalizationData && (
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
              <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              Get Your Free Ebook
            </h1>
            <p className="mt-3 text-gray-600">
              {cta ? cta : 'Personalized insights tailored just for you'}
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Enter your email to receive your customized content
            </p>
          </div>
        )}

        {!personalizationData && !isLoading && (
          <EmailConsentForm onSubmit={handleSubmit} isLoading={isLoading} />
        )}

        {isLoading && (
          <LoadingSpinner message={loadingMessage} />
        )}

        {personalizationData && (
          <PersonalizedContent data={personalizationData} error={error} onReset={handleReset} />
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
