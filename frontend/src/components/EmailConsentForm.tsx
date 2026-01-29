'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

interface EmailConsentFormProps {
  onSubmit: (email: string) => void;
  isLoading?: boolean;
}

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const validateEmail = (value: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(value);
  };

  const handleEmailChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setEmail(value);
    if (touched && value && !validateEmail(value)) {
      setEmailError('Please enter a valid email address');
    } else {
      setEmailError(null);
    }
  };

  const handleEmailBlur = () => {
    setTouched(true);
    if (email && !validateEmail(email)) {
      setEmailError('Please enter a valid email address');
    }
  };

  const handleConsentChange = (e: ChangeEvent<HTMLInputElement>) => {
    setConsent(e.target.checked);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (isFormValid) {
      onSubmit(email);
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isFormValid = isEmailValid && consent;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-700"
        >
          Email Address
        </label>
        <input
          type="email"
          id="email"
          name="email"
          placeholder="Enter your email"
          value={email}
          onChange={handleEmailChange}
          onBlur={handleEmailBlur}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          aria-describedby={emailError ? 'email-error' : undefined}
        />
        {emailError && (
          <p id="email-error" className="mt-1 text-sm text-red-600">
            {emailError}
          </p>
        )}
      </div>

      <div className="flex items-start">
        <input
          type="checkbox"
          id="consent"
          name="consent"
          checked={consent}
          onChange={handleConsentChange}
          disabled={isLoading}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed"
        />
        <label
          htmlFor="consent"
          className="ml-2 block text-sm text-gray-700"
        >
          I consent to receive personalized content and agree to the terms of service
        </label>
      </div>

      <button
        type="submit"
        disabled={!isFormValid || isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {isLoading ? 'Processing...' : 'Get Personalized Content'}
      </button>
    </form>
  );
}
