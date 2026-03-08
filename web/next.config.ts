import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow large response bodies for MP3 streaming
  experimental: {
    serverActions: {
      bodySizeLimit: "50mb",
    },
  },
};

export default nextConfig;
