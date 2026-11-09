import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: { baseURL: "http://127.0.0.1:3100", channel: "msedge", headless: true, viewport: { width: 1440, height: 1000 }, trace: "retain-on-failure" },
  webServer: [
    { command: "python tests/mock_api.py", url: "http://127.0.0.1:5051/health", reuseExistingServer: false },
    { command: "npm run dev:compat -- --port 3100", url: "http://127.0.0.1:3100", reuseExistingServer: false, timeout: 180000, env: { SMARTOFFICE_API_URL: "http://127.0.0.1:5051" } },
  ],
});
