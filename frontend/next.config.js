/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/rad/:path*',
        destination: `${backendUrl}/rad/:path*`,
      },
    ];
  },
}

module.exports = nextConfig
