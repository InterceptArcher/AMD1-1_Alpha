import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmailConsentForm from '../src/components/EmailConsentForm';

describe('EmailConsentForm', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders email input field', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/email/i)).toBeInTheDocument();
  });

  it('renders consent checkbox', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByLabelText(/consent|agree/i)).toBeInTheDocument();
  });

  it('renders submit button', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    expect(screen.getByRole('button', { name: /submit|get|personalize/i })).toBeInTheDocument();
  });

  it('submit button is disabled when form is empty', () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const submitButton = screen.getByRole('button', { name: /submit|get|personalize/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is disabled when only email is filled', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/email/i);
    await userEvent.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /submit|get|personalize/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is disabled when only consent is checked', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);

    const submitButton = screen.getByRole('button', { name: /submit|get|personalize/i });
    expect(submitButton).toBeDisabled();
  });

  it('submit button is enabled when email is valid and consent is checked', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/email/i);
    const checkbox = screen.getByRole('checkbox');

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.click(checkbox);

    const submitButton = screen.getByRole('button', { name: /submit|get|personalize/i });
    expect(submitButton).toBeEnabled();
  });

  it('shows error for invalid email format', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/email/i);

    await userEvent.type(emailInput, 'invalid-email');
    fireEvent.blur(emailInput);

    await waitFor(() => {
      expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    });
  });

  it('calls onSubmit with email when form is valid and submitted', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} />);
    const emailInput = screen.getByLabelText(/email/i);
    const checkbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', { name: /submit|get|personalize/i });

    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.click(checkbox);
    await userEvent.click(submitButton);

    expect(mockOnSubmit).toHaveBeenCalledWith('test@example.com');
  });

  it('disables form during submission', async () => {
    render(<EmailConsentForm onSubmit={mockOnSubmit} isLoading={true} />);

    const emailInput = screen.getByLabelText(/email/i);
    const checkbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', { name: /processing/i });

    expect(emailInput).toBeDisabled();
    expect(checkbox).toBeDisabled();
    expect(submitButton).toBeDisabled();
  });
});
