import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  reactStrictMode: true,
  experimental: {
    serverActions: {
      bodySizeLimit: "205mb",
    },
  },
};

export default nextConfig;
