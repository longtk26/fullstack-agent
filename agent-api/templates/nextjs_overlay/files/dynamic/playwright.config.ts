import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.E2E_PORT ?? 3100);

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30_000,
  retries: 0,
  reporter: [["list"], ["junit", { outputFile: "test-results/e2e-junit.xml" }]],
  use: { baseURL: `http://127.0.0.1:${port}` },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `pnpm exec next start -p ${port} -H 127.0.0.1`,
    url: `http://127.0.0.1:${port}/api/runtime-config`,
    env: { MOCK_TEST_API: "true", API_BASE_URL: "" },
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
