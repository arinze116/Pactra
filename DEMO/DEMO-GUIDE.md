# Pactra Demo Guide

Pactra's demo runs in an isolated local SQLite database with fictional data,
Gemini optional, and PayPal disabled. It never connects to production or moves
real money.

## Fast verification

From `frontend/`:

```bash
DEMO_PYTHON=/absolute/path/to/pactra/.venv/bin/python npm run test:demo
```

The Playwright configuration creates a uniquely named database under the OS
temporary directory, migrates it, seeds it, starts API/frontend servers,
executes the three product stories, and captures screenshots. On this node use
`.venv-linux/bin/python` for `DEMO_PYTHON`.

## Interactive demo setup

Prerequisites:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cd frontend && npm ci && npx playwright install chromium && cd ..
```

Choose a deliberate temporary database:

```bash
export APP_ENV=demo
export SECRET_KEY=pactra-demo-only-secret-key-32-bytes
export DATABASE_URL=sqlite:////tmp/pactra-demo-live.db
export FRONTEND_URL=http://127.0.0.1:5193
export BACKEND_URL=http://127.0.0.1:8023
export CORS_ORIGINS=http://127.0.0.1:5193
export AI_ENABLED=false
export GEMINI_API_KEY=
export GEMINI_MODEL=gemini-3.5-flash-lite
export GEMINI_REQUEST_ATTEMPTS=2
export PAYPAL_PAYOUTS_ENABLED=false
export PAYPAL_MOCK_MODE=false
export PAYPAL_CLIENT_ID=
export PAYPAL_CLIENT_SECRET=
export PAYPAL_TEST_RECIPIENT_EMAIL=
export PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
export SESSION_COOKIE_SECURE=false
export SEED_DEMO_ACCOUNT=false

python -m scripts.demo_environment reset --confirm RESET_PACTRA_DEMO
```

Start the API:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8023
```

In a second terminal with the same frontend URL:

```bash
cd frontend
VITE_API_URL=http://127.0.0.1:8023 \
  npm run dev -- --host 127.0.0.1 --port 5193
```

Open `http://127.0.0.1:5193/sign-in`.

Demo-only credentials:

- email: `demo@pactra-demo.example.com`
- password: `PactraDemo2026!`

These credentials are fictional and valid only in the isolated seeded
database. Never reuse them for staging, production, or another service.

## Safety properties

The demo tool refuses to run unless:

- `APP_ENV=demo`;
- the database is a file-backed SQLite URL;
- the absolute filename begins `pactra-demo-` and ends `.db`;
- the path is outside `/etc/pactra`, `/opt/pactra`, and the default development
  database;
- reset receives the exact confirmation phrase;
- no non-demo user exists in an existing target database.

The dataset is idempotent, uses the normal policy/transaction/ledger services,
and cannot create a provider payout.

## Recommended flow

Follow `DEMO/DEMO-SCRIPT.md`. Keep `DEMO/DEMO-FAILURE-RECOVERY.md` open in a
second window. Reset immediately before the presentation, sign in, and confirm
the dashboard shows `$951.00` posted, `$125.00` reserved, `$826.00` available,
and one pending approval.
