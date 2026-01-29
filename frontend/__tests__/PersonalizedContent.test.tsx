import { render, screen } from '@testing-library/react';
import PersonalizedContent from '../src/components/PersonalizedContent';

const mockPersonalizationData = {
  intro_hook: 'Welcome back, John! As a Product Manager at TechCorp...',
  cta: 'Download your personalized guide now',
  first_name: 'John',
  company: 'TechCorp',
  title: 'Product Manager',
};

describe('PersonalizedContent', () => {
  it('renders personalized intro hook', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/welcome back, john/i)).toBeInTheDocument();
  });

  it('renders personalized CTA', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/download your personalized guide/i)).toBeInTheDocument();
  });

  it('renders user profile information', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/name: john/i)).toBeInTheDocument();
    expect(screen.getByText(/company: techcorp/i)).toBeInTheDocument();
  });

  it('handles missing optional fields gracefully', () => {
    const partialData = {
      intro_hook: 'Welcome!',
      cta: 'Get started',
    };
    render(<PersonalizedContent data={partialData} />);
    expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    expect(screen.getByText(/get started/i)).toBeInTheDocument();
  });

  it('displays error state when data is null', () => {
    render(<PersonalizedContent data={null} error="Failed to load personalization" />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });
});
