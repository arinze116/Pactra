import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repoRoot = fileURLToPath(new URL("../../../", import.meta.url));

export default function globalSetup() {
  const databaseURL = process.env.E2E_RESOLVED_DATABASE_URL;
  const pythonCommand = process.env.E2E_RESOLVED_PYTHON ?? "python";
  if (!databaseURL) throw new Error("E2E database isolation was not configured");

  const result = spawnSync(pythonCommand, ["-m", "alembic", "upgrade", "head"], {
    cwd: repoRoot,
    encoding: "utf8",
    env: {
      ...process.env,
      APP_ENV: "test",
      SECRET_KEY: "pactra-e2e-only-secret-key-32-bytes-minimum",
      DATABASE_URL: databaseURL,
      FRONTEND_URL: "http://127.0.0.1:5173",
      BACKEND_URL: "http://127.0.0.1:8000",
      CORS_ORIGINS: "http://127.0.0.1:5173",
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
    },
  });

  if (result.status !== 0) {
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
    throw new Error(`E2E database migration failed${output ? `:\n${output}` : ""}`);
  }
}
