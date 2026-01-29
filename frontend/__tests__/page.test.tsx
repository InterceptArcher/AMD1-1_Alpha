import { render, screen } from '@testing-library/react';
import Home from '../src/app/page';

// Mock useSearchParams
const mockSearchParams = new Map<string, string>();
jest.mock('next/navigation', () => ({
  useSearchParams: () => ({
    get: (key: string) => mockSearchParams.get(key) || null,
  }),
}));

describe('Home Page', () => {
  beforeEach(() => {
    mockSearchParams.clear();
  });

  it('renders the landing page with ebook heading', () => {
    render(<Home />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/get your free ebook/i);
  });

  it('displays default message when no cta parameter provided', () => {
    render(<Home />);
    expect(screen.getByText(/personalized insights/i)).toBeInTheDocument();
  });

  it('displays the cta value from query string when provided', () => {
    mockSearchParams.set('cta', 'Compare solutions for your team');
    render(<Home />);
    expect(screen.getByText(/compare solutions/i)).toBeInTheDocument();
  });

  it('renders email form', () => {
    render(<Home />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('renders consent checkbox', () => {
    render(<Home />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('renders submit button', () => {
    render(<Home />);
    expect(screen.getByRole('button', { name: /get personalized content/i })).toBeInTheDocument();
  });
});
