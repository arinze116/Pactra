import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const frontendPort = process.env.E2E_FRONTEND_PORT ?? "5173";
const apiPort = process.env.E2E_API_PORT ?? "8000";
const localVirtualenvPython = fileURLToPath(new URL(process.platform === "win32" ? "../.venv/Scripts/python.exe" : "../.venv/bin/python", import.meta.url));
const pythonCommand = process.env.E2E_PYTHON ?? (!process.env.CI && existsSync(localVirtualenvPython) ? localVirtualenvPython : "python");
const pythonShellCommand = `"${pythonCommand.replace(/"/g, '\\"')}"`;
const baseURL = `http://127.0.0.1:${frontendPort}`;
const apiURL = `http://127.0.0.1:${apiPort}`;
const reuseExistingServer = process.env.E2E_REUSE_SERVER === "true";
const localDatabasePath = join(tmpdir(), `pactra-e2e-${process.pid}-${Date.now()}.db`).replace(/\\/g, "/");
const databaseURL = process.env.CI
  ? process.env.DATABASE_URL
  : process.env.E2E_DATABASE_URL ?? `sqlite:///${localDatabasePath}`;

if (!databaseURL) {
  throw new Error("CI E2E requires DATABASE_URL to point to the isolated pactra_e2e database");
}

const backendEnv = {
  APP_ENV: "test",
  SECRET_KEY: "pactra-e2e-only-secret-key-32-bytes-minimum",
  DATABASE_URL: databaseURL,
  FRONTEND_URL: baseURL,
  BACKEND_URL: apiURL,
  CORS_ORIGINS: baseURL,
  AI_ENABLED: "false",
  GEMINI_API_KEY: "",
  PAYPAL_PAYOUTS_ENABLED: "false",
  PAYPAL_MOCK_MODE: "false",
  PAYPAL_CLIENT_ID: "",
  PAYPAL_CLIENT_SECRET: "",
  PAYPAL_TEST_RECIPIENT_EMAIL: "",
  PAYPAL_BASE_URL: "https://api-m.sandbox.paypal.com",
  SESSION_COOKIE_SECURE: "false",
  SEED_DEMO_ACCOUNT: "false",
};

process.env.E2E_RESOLVED_DATABASE_URL = databaseURL;
process.env.E2E_RESOLVED_PYTHON = pythonCommand;

export default defineConfig({
  testDir: "./tests/e2e",
  globalSetup: "./tests/e2e/global-setup.ts",
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
      command: `${pythonShellCommand} -m alembic upgrade head && ${pythonShellCommand} -m uvicorn backend.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "..",
      env: backendEnv,
      url: `${apiURL}/api/ready`,
      reuseExistingServer,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: ".",
      env: { VITE_API_URL: apiURL },
      url: baseURL,
      reuseExistingServer,
      timeout: 120_000,
    },
  ],
});
