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
}

export default function PersonalizedContent({ data, error }: PersonalizedContentProps) {
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

  return (
    <div className="space-y-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      {(data.first_name || data.company || data.title) && (
        <div className="border-b border-gray-100 pb-4">
          <h2 className="text-lg font-semibold text-gray-900">Your Profile</h2>
          <div className="mt-2 space-y-1 text-sm text-gray-600">
            {data.first_name && <p>Name: {data.first_name}</p>}
            {data.company && <p>Company: {data.company}</p>}
            {data.title && <p>Title: {data.title}</p>}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-md font-medium text-gray-900">Personalized Introduction</h3>
        <p className="mt-2 text-gray-700">{data.intro_hook}</p>
      </div>

      <div className="rounded-md bg-blue-50 p-4">
        <p className="font-medium text-blue-800">{data.cta}</p>
      </div>
    </div>
  );
}
