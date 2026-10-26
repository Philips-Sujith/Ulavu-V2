/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/backend-api/:path*',
        destination: `${(process.env.NEXT_PUBLIC_API_URL || 'https://ulavu-v2-backend.onrender.com').replace(/\/+$/, '')}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
