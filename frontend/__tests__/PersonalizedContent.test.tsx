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
  it('renders personalized greeting with name', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/hi john/i)).toBeInTheDocument();
  });

  it('renders personalized intro hook', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/welcome back, john/i)).toBeInTheDocument();
  });

  it('renders personalized CTA', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/download your personalized guide/i)).toBeInTheDocument();
  });

  it('renders company and title context', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByText(/tailored insights for/i)).toBeInTheDocument();
  });

  it('renders download button', () => {
    render(<PersonalizedContent data={mockPersonalizationData} />);
    expect(screen.getByRole('button', { name: /download your free ebook/i })).toBeInTheDocument();
  });

  it('handles missing optional fields gracefully', () => {
    const partialData = {
      intro_hook: 'Discover powerful insights in this ebook!',
      cta: 'Get started today',
    };
    render(<PersonalizedContent data={partialData} />);
    expect(screen.getByText(/discover powerful insights/i)).toBeInTheDocument();
    expect(screen.getByText(/get started today/i)).toBeInTheDocument();
  });

  it('shows generic greeting when no name provided', () => {
    const partialData = {
      intro_hook: 'Generic intro',
      cta: 'CTA text',
    };
    render(<PersonalizedContent data={partialData} />);
    expect(screen.getByText('Welcome!')).toBeInTheDocument();
  });

  it('displays error state when error prop is passed', () => {
    render(<PersonalizedContent data={null} error="Failed to load personalization" />);
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it('renders nothing when data is null and no error', () => {
    const { container } = render(<PersonalizedContent data={null} />);
    expect(container.firstChild).toBeNull();
  });
});
