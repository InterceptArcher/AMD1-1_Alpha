import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../src/components/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders loading spinner', () => {
    render(<LoadingSpinner />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('displays loading message', () => {
    render(<LoadingSpinner message="Personalizing your content..." />);
    expect(screen.getByText(/personalizing/i)).toBeInTheDocument();
  });

  it('has accessible label for screen readers', () => {
    render(<LoadingSpinner />);
    expect(screen.getByLabelText(/loading/i)).toBeInTheDocument();
  });
});
