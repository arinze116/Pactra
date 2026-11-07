# Pactra Release-Candidate Acceptance Evidence

Recorded: 2026-11-07, Africa/Lagos

Production URL (unchanged): `https://pactra-nine.vercel.app`

Isolated PostgreSQL databases: `pactra_gap_baseline_20261107`, `pactra_gap_e2e_baseline_20261107`

## Results

| Gate | Result |
|---|---|
| SQLite backend | PASS — 87 passed, 9 PostgreSQL-only skipped |
| PostgreSQL backend | PASS — 96 passed |
| Migration | PASS — clean upgrade through `20261107_0005` on SQLite and PostgreSQL |
| Frontend lint/build | PASS — Vite 8.3.6 production build |
| PostgreSQL Playwright journeys | PASS — 13 passed |
| WCAG 2.1 AA automated suite | PASS — public and authenticated routes |
| Lighthouse | PASS — performance 0.99, accessibility 1.00, best practices 0.96 |
| Python consistency/audit | PASS — no broken requirements; no known vulnerabilities |
| npm production/full audits | PASS — 0 vulnerabilities |
| Live Gemini | BLOCKED — no approved credential/configuration |
| Live PayPal Sandbox | BLOCKED — no approved credentials/capability/recipient/test authorization |

## Exact commands

```bash
APP_ENV=test DATABASE_URL=sqlite:////tmp/pactra-gap-final-sqlite.db \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: `87 passed, 9 skipped` in 19.73 seconds. The skips are explicitly
PostgreSQL-only; every skipped case passed in the PostgreSQL run.

```bash
psql -d pactra_gap_baseline_20261107 -c 'DROP SCHEMA public CASCADE' \
  -c 'CREATE SCHEMA public'
APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_gap_baseline_20261107 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m alembic upgrade head
APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_gap_baseline_20261107 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: clean migration through `0005`; `96 passed` in 24.17 seconds.

```bash
cd frontend
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
```

Result: all passed; both audits reported `found 0 vulnerabilities`.

```bash
.venv-linux/bin/python -m pip check
.venv-linux/bin/python -m pip_audit -r requirements.txt
```

Result: `No broken requirements found`; `No known vulnerabilities found`.

```bash
cd frontend
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python \
E2E_DATABASE_URL=postgresql+psycopg:///pactra_gap_e2e_baseline_20261107 \
npm run test:e2e
```

Result: 13 journey tests passed in 1.4 minutes; the WCAG suite passed in 27.6
seconds. The isolated database was reset and migrated before the run.

```bash
CHROME_PATH=<Playwright Chromium> npx lighthouse http://127.0.0.1:4173/ \
  --chrome-flags='--headless --no-sandbox' \
  --only-categories=performance,accessibility,best-practices \
  --output=json --output-path=/tmp/pactra-lighthouse-rc.json --quiet
npm run test:lighthouse:assert -- /tmp/pactra-lighthouse-rc.json
```

Result: performance `0.99`, accessibility `1.00`, best practices `0.96`.

## Key new acceptance tests

- `test_policy_update_changes_decision_and_blocked_transaction_is_persisted`
- `test_insufficient_funds_returns_persisted_402_without_ledger_movement`
- `test_policy_preview_is_authoritative_and_side_effect_free`
- `test_guided_analytics_events_are_unique_per_generation`
- `test_shared_rate_limit_is_atomic_across_independent_process_state`
- `test_reset_waits_for_unresolved_provider_outcome`
- Playwright: `password reveal remains accessible through sign-up and sign-in`
- Playwright: `overview and wallet sections recover independently`
- Playwright: `guided insufficient-funds outcome and internal reversal remain auditable`
- Playwright: `failed internal retry is idempotent through the browser path`

## Skips and blocked tests

- SQLite skipped nine PostgreSQL-only tests; the PostgreSQL run passed all 96.
- No public smoke test ran because this release candidate was not deployed.
- No Gemini call ran because an approved server-side key/configuration was absent.
- No PayPal call ran because Sandbox capability, credentials, recipient and
  explicit authorization for a specific test payout were absent.
