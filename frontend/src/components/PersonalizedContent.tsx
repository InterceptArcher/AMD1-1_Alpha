interface PersonalizationData {
  intro_hook: string;
  cta: string;
  first_name?: string;
  company?: string;
  title?: string;
}

interface PersonalizedContentProps {
  data: PersonalizationData | null;
  error?: string | null;
  onReset?: () => void;
}

export default function PersonalizedContent({ data, error, onReset }: PersonalizedContentProps) {
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-red-700">{error}</p>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const greeting = data.first_name
    ? `Hi ${data.first_name}!`
    : 'Welcome!';

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-8 text-white">
        <p className="text-sm font-medium uppercase tracking-wider opacity-80">Your Personalized Ebook</p>
        <h2 className="mt-2 text-2xl font-bold">{greeting}</h2>
        {data.company && (
          <p className="mt-1 text-blue-100">
            Tailored insights for {data.title ? `${data.title} at ` : ''}{data.company}
          </p>
        )}
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Intro Hook */}
        <div className="prose prose-gray">
          <p className="text-lg leading-relaxed text-gray-700">{data.intro_hook}</p>
        </div>

        {/* Divider */}
        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-gray-200"></div>
          <span className="text-xs font-medium uppercase tracking-wider text-gray-400">What's Inside</span>
          <div className="h-px flex-1 bg-gray-200"></div>
        </div>

        {/* Preview bullets */}
        <ul className="space-y-3 text-gray-600">
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Industry-specific strategies and best practices</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Real-world case studies from leading companies</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">✓</span>
            <span>Actionable frameworks you can implement today</span>
          </li>
        </ul>

        {/* CTA Box */}
        <div className="rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 p-5 border border-blue-100">
          <p className="font-semibold text-gray-900">{data.cta}</p>
        </div>

        {/* Download Button */}
        <button
          className="w-full rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white shadow-md transition hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          onClick={() => alert('PDF download coming soon!')}
        >
          Download Your Free Ebook
        </button>

        <p className="text-center text-xs text-gray-400">
          Your personalized ebook will be delivered instantly
        </p>

        {onReset && (
          <button
            onClick={onReset}
            className="w-full text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Try with a different email
          </button>
        )}
      </div>
    </div>
  );
}
