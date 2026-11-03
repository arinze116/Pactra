import { defineConfig, devices } from "@playwright/test";

const frontendPort = process.env.E2E_FRONTEND_PORT ?? "5173";
const apiPort = process.env.E2E_API_PORT ?? "8000";
const pythonCommand = process.env.E2E_PYTHON ?? "python";
const baseURL = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${pythonCommand} -m uvicorn backend.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "..",
      env: {
        CORS_ORIGINS: baseURL,
        FRONTEND_URL: baseURL,
      },
      url: `http://127.0.0.1:${apiPort}/api/ready`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      env: { VITE_API_URL: `http://localhost:${apiPort}` },
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
