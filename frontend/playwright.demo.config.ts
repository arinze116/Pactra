import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendPort = process.env.DEMO_FRONTEND_PORT ?? "5193";
const apiPort = process.env.DEMO_API_PORT ?? "8023";
const localVirtualenvPython = fileURLToPath(
  new URL(
    process.platform === "win32"
      ? "../.venv/Scripts/python.exe"
      : "../.venv/bin/python",
    import.meta.url,
  ),
);
const pythonCommand = process.env.DEMO_PYTHON
  ?? (!process.env.CI && existsSync(localVirtualenvPython)
    ? localVirtualenvPython
    : "python");
const pythonShellCommand = `"${pythonCommand.replace(/"/g, '\\"')}"`;
const baseURL = `http://127.0.0.1:${frontendPort}`;
const apiURL = `http://127.0.0.1:${apiPort}`;
const databasePath = process.env.DEMO_DATABASE_PATH
  ?? join(tmpdir(), `pactra-demo-playwright-${process.pid}-${Date.now()}.db`);
const databaseURL = `sqlite:///${databasePath.replace(/\\/g, "/")}`;

const backendEnv = {
  APP_ENV: "demo",
  SECRET_KEY: "pactra-demo-only-secret-key-32-bytes",
  DATABASE_URL: databaseURL,
  FRONTEND_URL: baseURL,
  BACKEND_URL: apiURL,
  CORS_ORIGINS: baseURL,
  AI_ENABLED: "false",
  GEMINI_API_KEY: "",
  GEMINI_MODEL: "gemini-3.5-flash-lite",
  GEMINI_REQUEST_ATTEMPTS: "2",
  PAYPAL_PAYOUTS_ENABLED: "false",
  PAYPAL_MOCK_MODE: "false",
  PAYPAL_CLIENT_ID: "",
  PAYPAL_CLIENT_SECRET: "",
  PAYPAL_TEST_RECIPIENT_EMAIL: "",
  PAYPAL_BASE_URL: "https://api-m.sandbox.paypal.com",
  SESSION_COOKIE_SECURE: "false",
  AUTH_REGISTRATION_RATE_LIMIT_PER_HOUR: "100",
  AUTH_LOGIN_GLOBAL_RATE_LIMIT_PER_MINUTE: "100",
  SEED_DEMO_ACCOUNT: "false",
};

export default defineConfig({
  testDir: "./tests/demo",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${pythonShellCommand} -m scripts.demo_environment reset --confirm RESET_PACTRA_DEMO && ${pythonShellCommand} -m uvicorn backend.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "..",
      env: backendEnv,
      url: `${apiURL}/api/ready`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      env: { VITE_API_URL: apiURL },
      url: baseURL,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
