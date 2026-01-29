interface LoadingSpinnerProps {
  message?: string;
}

export default function LoadingSpinner({ message = 'Loading...' }: LoadingSpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className="flex flex-col items-center justify-center space-y-4 py-8"
    >
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
      <p className="text-sm text-gray-600">{message}</p>
    </div>
  );
}
