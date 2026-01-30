'use client';

import { useState, useEffect } from 'react';

interface UserContext {
  firstName?: string;
  company?: string;
  industry?: string;
  persona?: string;
  goal?: string;
}

interface LoadingSpinnerProps {
  message?: string;
  userContext?: UserContext;
}

// Industry-specific loading messages
const INDUSTRY_MESSAGES: Record<string, string[]> = {
  technology: [
    'Analyzing tech industry trends...',
    'Finding relevant SaaS case studies...',
    'Tailoring content for software leaders...',
  ],
  financial_services: [
    'Reviewing financial services benchmarks...',
    'Adding compliance considerations...',
    'Customizing for banking & insurance...',
  ],
  healthcare: [
    'Incorporating healthcare regulations...',
    'Finding life sciences case studies...',
    'Tailoring for patient data requirements...',
  ],
  retail_ecommerce: [
    'Analyzing retail transformation trends...',
    'Adding e-commerce scalability insights...',
    'Customizing for customer experience...',
  ],
  manufacturing: [
    'Reviewing industrial automation trends...',
    'Adding supply chain considerations...',
    'Tailoring for operational efficiency...',
  ],
  telecommunications: [
    'Analyzing network infrastructure trends...',
    'Adding media delivery insights...',
    'Customizing for 5G readiness...',
  ],
  energy_utilities: [
    'Reviewing grid modernization trends...',
    'Adding sustainability considerations...',
    'Tailoring for energy efficiency...',
  ],
  government: [
    'Incorporating compliance requirements...',
    'Adding security frameworks...',
    'Customizing for public sector needs...',
  ],
  education: [
    'Analyzing education technology trends...',
    'Adding research computing insights...',
    'Tailoring for academic institutions...',
  ],
  professional_services: [
    'Reviewing consulting best practices...',
    'Adding client delivery insights...',
    'Customizing for service organizations...',
  ],
};

// Role-specific messages
const PERSONA_MESSAGES: Record<string, string> = {
  c_suite: 'Preparing executive-level insights...',
  vp_director: 'Curating strategic recommendations...',
  it_infrastructure: 'Adding technical architecture details...',
  engineering: 'Including implementation patterns...',
  data_ai: 'Incorporating ML/AI workload specifics...',
  security: 'Adding security & compliance frameworks...',
  procurement: 'Including vendor evaluation criteria...',
};

// Buying stage messages
const GOAL_MESSAGES: Record<string, string> = {
  awareness: 'Building your foundational guide...',
  consideration: 'Preparing comparison frameworks...',
  decision: 'Finalizing your decision toolkit...',
  implementation: 'Creating your implementation roadmap...',
};

export default function LoadingSpinner({ message, userContext }: LoadingSpinnerProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [displayMessage, setDisplayMessage] = useState(message || 'Personalizing your content...');

  // Generate personalized loading steps
  const getLoadingSteps = (): string[] => {
    const steps: string[] = [];

    if (userContext?.firstName && userContext?.company) {
      steps.push(`Hi ${userContext.firstName}, preparing your personalized guide for ${userContext.company}...`);
    } else if (userContext?.firstName) {
      steps.push(`Hi ${userContext.firstName}, creating your personalized ebook...`);
    } else {
      steps.push('Creating your personalized ebook...');
    }

    // Add industry-specific messages
    if (userContext?.industry && INDUSTRY_MESSAGES[userContext.industry]) {
      steps.push(...INDUSTRY_MESSAGES[userContext.industry]);
    }

    // Add persona-specific message
    if (userContext?.persona && PERSONA_MESSAGES[userContext.persona]) {
      steps.push(PERSONA_MESSAGES[userContext.persona]);
    }

    // Add goal-specific message
    if (userContext?.goal && GOAL_MESSAGES[userContext.goal]) {
      steps.push(GOAL_MESSAGES[userContext.goal]);
    }

    steps.push('Finalizing your personalized content...');

    return steps;
  };

  const steps = getLoadingSteps();

  useEffect(() => {
    if (!userContext) {
      setDisplayMessage(message || 'Loading...');
      return;
    }

    // Cycle through personalized messages
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        const next = (prev + 1) % steps.length;
        setDisplayMessage(steps[next]);
        return next;
      });
    }, 2500);

    // Set initial message
    setDisplayMessage(steps[0]);

    return () => clearInterval(interval);
  }, [userContext, steps.length]);

  // Calculate progress percentage
  const progress = Math.min(((currentStep + 1) / steps.length) * 100, 95);

  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-col items-center justify-center space-y-6 py-8"
    >
      {/* Personalized Header */}
      {userContext?.firstName && (
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">
            Almost there, {userContext.firstName}!
          </h2>
          {userContext.company && (
            <p className="text-sm text-gray-500 mt-1">
              Customizing insights for {userContext.company}
            </p>
          )}
        </div>
      )}

      {/* Animated dots */}
      <div className="flex space-x-2">
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.3s]" />
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600 [animation-delay:-0.15s]" />
        <div className="h-3 w-3 animate-bounce rounded-full bg-blue-600" />
      </div>

      {/* Progress card */}
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 animate-pulse rounded-full bg-blue-100 flex items-center justify-center">
              <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900 transition-all duration-300">{displayMessage}</p>
              <p className="text-sm text-gray-500">This usually takes 10-15 seconds</p>
            </div>
          </div>

          {/* Progress bar */}
          <div className="h-2 overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* What we're doing */}
          {userContext && (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs text-gray-400 text-center">
                Personalizing for {userContext.industry?.replace('_', ' ')} • {userContext.persona?.replace('_', ' ')} • {userContext.goal?.replace('_', ' ')} stage
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Preview of what's coming */}
      {userContext && (
        <div className="w-full max-w-md space-y-2">
          <p className="text-xs font-medium text-gray-500 text-center">Your ebook will include:</p>
          <div className="flex flex-wrap justify-center gap-2">
            <span className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
              {userContext.industry?.replace('_', ' ')} insights
            </span>
            <span className="inline-flex items-center rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
              {userContext.persona?.replace('_', ' ')} focus
            </span>
            <span className="inline-flex items-center rounded-full bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700">
              Relevant case studies
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
