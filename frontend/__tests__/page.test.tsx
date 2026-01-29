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

  it('renders the landing page with welcome heading', () => {
    render(<Home />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/welcome/i);
  });

  it('displays default CTA message when no cta parameter provided', () => {
    render(<Home />);
    expect(screen.getByText(/default/i)).toBeInTheDocument();
  });

  it('displays the cta value from query string when provided', () => {
    mockSearchParams.set('cta', 'compare');
    render(<Home />);
    expect(screen.getByText(/compare/i)).toBeInTheDocument();
  });

  it('handles different cta values correctly', () => {
    mockSearchParams.set('cta', 'download');
    render(<Home />);
    expect(screen.getByText(/download/i)).toBeInTheDocument();
  });
});
