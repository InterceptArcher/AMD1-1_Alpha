'use client';

import { useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';
import EmailConsentForm, { UserInputs } from '@/components/EmailConsentForm';
import LoadingSpinner from '@/components/LoadingSpinner';
import PersonalizedContent from '@/components/PersonalizedContent';

interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
  email?: string;
}

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
  goal?: string;
}

function HomeContent() {
  const searchParams = useSearchParams();
  const cta = searchParams.get('cta');

  const [isLoading, setIsLoading] = useState(false);
  const [userContext, setUserContext] = useState<UserContext | null>(null);
  const [personalizationData, setPersonalizationData] = useState<PersonalizationData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleReset = () => {
    setPersonalizationData(null);
    setUserContext(null);
    setError(null);
  };

  const getApiUrl = () => {
    // Use relative URL to leverage Next.js proxy (avoids CORS/port issues)
    return '/api';
  };

  const handleSubmit = async (inputs: UserInputs) => {
    setIsLoading(true);
    setError(null);

    // Set user context immediately for personalized loading
    setUserContext({
      firstName: inputs.firstName,
      company: inputs.company,
      industry: inputs.industry,
      persona: inputs.persona,
      goal: inputs.goal,
    });

    try {
      const apiUrl = getApiUrl();
      console.log('Submitting to API:', apiUrl);

      // Call backend with all user inputs
      const response = await fetch(`${apiUrl}/rad/enrich`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: inputs.email,
          firstName: inputs.firstName,
          lastName: inputs.lastName,
          company: inputs.company,
          goal: inputs.goal,
          persona: inputs.persona,
          industry: inputs.industry,
          cta: cta || 'default',
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Enrich failed:', response.status, errorText);
        throw new Error(`Failed to start personalization: ${response.status}`);
      }

      // Profile should be ready - fetch it
      const profileResponse = await fetch(`${apiUrl}/rad/profile/${encodeURIComponent(inputs.email)}`);

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
        first_name: inputs.firstName || profileData.normalized_profile?.first_name,
        company: inputs.company || profileData.normalized_profile?.company,
        title: profileData.normalized_profile?.title,
        email: inputs.email,
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
        {!personalizationData && !isLoading && (
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
              {cta ? cta : 'Personalized insights tailored to your role and industry'}
            </p>
            <p className="mt-1 text-sm text-gray-400">
              Answer a few questions to customize your content
            </p>
          </div>
        )}

        {!personalizationData && !isLoading && (
          <EmailConsentForm onSubmit={handleSubmit} isLoading={isLoading} />
        )}

        {isLoading && (
          <LoadingSpinner userContext={userContext || undefined} />
        )}

        {personalizationData && (
          <PersonalizedContent data={personalizationData} error={error} onReset={handleReset} />
        )}

        {error && !personalizationData && !isLoading && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-700">{error}</p>
            <button
              onClick={handleReset}
              className="mt-2 text-sm text-red-600 underline hover:text-red-800"
            >
              Try again
            </button>
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
