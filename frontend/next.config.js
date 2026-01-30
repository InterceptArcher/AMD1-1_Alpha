/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use env var if set, otherwise use Render backend URL
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'https://amd1-1-backend.onrender.com';
    console.log('Backend URL for rewrites:', backendUrl);
    return [
      {
        source: '/api/rad/:path*',
        destination: `${backendUrl}/rad/:path*`,
      },
    ];
  },
}

module.exports = nextConfig
