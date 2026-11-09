import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";

const backend = (process.env.SMARTOFFICE_API_URL ?? "http://127.0.0.1:5000").replace(/\/$/, "");
if (!/^https?:\/\//.test(backend)) throw new Error("SMARTOFFICE_API_URL harus berupa URL HTTP(S).");

const config: NextConfig = {
  devIndicators: false,
  outputFileTracingRoot: fileURLToPath(new URL(".", import.meta.url)),
  poweredByHeader: false,
  async rewrites() {
    return ["/api/:path*", "/video_feed", "/snapshots/:path*", "/training_data/:path*"].map(source => ({
      source, destination: `${backend}${source}`,
    }));
  },
};
export default config;
