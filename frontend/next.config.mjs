/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The demo runs on a single machine; no image optimisation server needed.
  images: { unoptimized: true },
};

export default nextConfig;
