import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A Node server (dynamic mode): the runtime config route reads MOCK_TEST_API / API_BASE_URL per request.
  output: "standalone",
  eslint: {
    ignoreDuringBuilds: true,
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
