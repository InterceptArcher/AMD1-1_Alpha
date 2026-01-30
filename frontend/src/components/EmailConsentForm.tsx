'use client';

import { useState, FormEvent, ChangeEvent } from 'react';

export interface UserInputs {
  email: string;
  firstName: string;
  lastName: string;
  company: string;
  goal: string;
  persona: string;
  industry: string;
}

interface EmailConsentFormProps {
  onSubmit: (inputs: UserInputs) => void;
  isLoading?: boolean;
}

// Buying stage - helps LLM tailor urgency and depth of content
const GOAL_OPTIONS = [
  { value: '', label: 'Select your current stage...' },
  { value: 'awareness', label: 'Just starting to research' },
  { value: 'consideration', label: 'Actively evaluating options' },
  { value: 'decision', label: 'Ready to make a decision' },
  { value: 'implementation', label: 'Already implementing, need guidance' },
];

// Role/Persona - helps LLM customize technical depth and focus areas
const PERSONA_OPTIONS = [
  { value: '', label: 'Select your role...' },
  { value: 'c_suite', label: 'C-Suite / Executive (CEO, CTO, CIO, CFO)' },
  { value: 'vp_director', label: 'VP / Director' },
  { value: 'it_infrastructure', label: 'IT / Infrastructure Manager' },
  { value: 'engineering', label: 'Engineering / DevOps' },
  { value: 'data_ai', label: 'Data Science / AI / ML' },
  { value: 'security', label: 'Security / Compliance' },
  { value: 'procurement', label: 'Procurement / Vendor Management' },
  { value: 'other', label: 'Other' },
];

// Industry - maps to case studies and specific pain points
const INDUSTRY_OPTIONS = [
  { value: '', label: 'Select your industry...' },
  { value: 'technology', label: 'Technology / Software / SaaS' },
  { value: 'financial_services', label: 'Financial Services / Banking / Insurance' },
  { value: 'healthcare', label: 'Healthcare / Life Sciences / Pharma' },
  { value: 'retail_ecommerce', label: 'Retail / E-commerce' },
  { value: 'manufacturing', label: 'Manufacturing / Industrial' },
  { value: 'telecommunications', label: 'Telecommunications / Media' },
  { value: 'energy_utilities', label: 'Energy / Utilities' },
  { value: 'government', label: 'Government / Public Sector' },
  { value: 'education', label: 'Education / Research' },
  { value: 'professional_services', label: 'Professional Services / Consulting' },
  { value: 'other', label: 'Other' },
];

export default function EmailConsentForm({ onSubmit, isLoading = false }: EmailConsentFormProps) {
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [company, setCompany] = useState('');
  const [goal, setGoal] = useState('');
  const [persona, setPersona] = useState('');
  const [industry, setIndustry] = useState('');
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
      onSubmit({ email, firstName, lastName, company, goal, persona, industry });
    }
  };

  const isEmailValid = email.length > 0 && validateEmail(email);
  const isNameValid = firstName.length > 0 && lastName.length > 0;
  const isCompanyValid = company.length > 0;
  const isFormValid = isEmailValid && isNameValid && isCompanyValid && consent && goal && persona && industry;

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Name Inputs */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="firstName"
            className="block text-sm font-medium text-gray-700"
          >
            First Name
          </label>
          <input
            type="text"
            id="firstName"
            name="firstName"
            placeholder="John"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            disabled={isLoading}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
        <div>
          <label
            htmlFor="lastName"
            className="block text-sm font-medium text-gray-700"
          >
            Last Name
          </label>
          <input
            type="text"
            id="lastName"
            name="lastName"
            placeholder="Smith"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            disabled={isLoading}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>
      </div>

      {/* Company Input */}
      <div>
        <label
          htmlFor="company"
          className="block text-sm font-medium text-gray-700"
        >
          Company
        </label>
        <input
          type="text"
          id="company"
          name="company"
          placeholder="Acme Corp"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
      </div>

      {/* Email Input */}
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-700"
        >
          Work Email
        </label>
        <input
          type="email"
          id="email"
          name="email"
          placeholder="you@company.com"
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

      {/* Industry Dropdown */}
      <div>
        <label
          htmlFor="industry"
          className="block text-sm font-medium text-gray-700"
        >
          Industry
        </label>
        <select
          id="industry"
          name="industry"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {INDUSTRY_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Persona/Role Dropdown */}
      <div>
        <label
          htmlFor="persona"
          className="block text-sm font-medium text-gray-700"
        >
          Your Role
        </label>
        <select
          id="persona"
          name="persona"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {PERSONA_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Buying Stage Dropdown */}
      <div>
        <label
          htmlFor="goal"
          className="block text-sm font-medium text-gray-700"
        >
          Where are you in your journey?
        </label>
        <select
          id="goal"
          name="goal"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          disabled={isLoading}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
        >
          {GOAL_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {/* Consent Checkbox */}
      <div className="flex items-start">
        <input
          type="checkbox"
          id="consent"
          name="consent"
          checked={consent}
          onChange={handleConsentChange}
          disabled={isLoading}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed mt-0.5"
        />
        <label
          htmlFor="consent"
          className="ml-2 block text-sm text-gray-600"
        >
          I agree to receive my personalized ebook and relevant updates
        </label>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={!isFormValid || isLoading}
        className="w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
            Creating Your Personalized Ebook...
          </span>
        ) : (
          'Get My Free Ebook'
        )}
      </button>

      <p className="text-center text-xs text-gray-400">
        Your ebook will be personalized for {company || 'your company'} in {
          INDUSTRY_OPTIONS.find(i => i.value === industry)?.label.split(' /')[0] || 'your industry'
        }
      </p>
    </form>
  );
}
