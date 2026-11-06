import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PUBLIC_BASE_URL?.trim().replace(/\/$/, "");

if (!baseURL?.startsWith("https://")) {
  throw new Error("PUBLIC_BASE_URL must be the deployed HTTPS Pactra origin");
}

export default defineConfig({
  testDir: "./tests/public",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 180_000,
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
