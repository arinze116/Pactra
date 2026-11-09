# Pactra Final Regression Test Report

Test date: 2026-11-09

Branch: `release/final-pre-demo-readiness`

## Results

| Suite | Result | Evidence |
|---|---|---|
| Backend SQLite | PASS | 138 passed, 10 PostgreSQL-only skipped |
| Backend PostgreSQL | PASS | 148 passed |
| Frontend lint | PASS | ESLint, zero errors |
| TypeScript + production build | PASS | Vite build completed |
| Existing E2E journeys | PASS | 16 passed |
| Automated WCAG | PASS | 1 comprehensive Axe test passed |
| Isolated demo rehearsal | PASS | 1 Playwright scenario passed |
| Lighthouse | PASS | performance 0.97, accessibility 1.00, best practices 0.96 |
| Python dependency consistency | PASS | `pip check` |
| Python vulnerabilities | PASS | `pip-audit`: no known vulnerabilities |
| npm production audit | PASS | zero vulnerabilities |
| npm full audit | PASS | zero vulnerabilities |
| Production public monitor | PASS | `/`, health, readiness all 200 within budget |
| Production financial invariants | PASS | 10/10 checks; zero violations; read-only |
| Accepted backup verification | PASS | checksum match and archive list valid |

## Exact commands

Backend SQLite:

```bash
APP_ENV=test \
DATABASE_URL=sqlite:////tmp/pactra-final-pre-demo-sqlite.db \
AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=true \
.venv-linux/bin/pytest -q -o addopts=""
```

Backend PostgreSQL used the isolated local `pactra_test` database through peer
authentication as its test owner, with AI and provider credentials explicitly
empty:

```bash
APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_test \
AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=false \
.venv-linux/bin/python -m pytest -q -o addopts=""
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:e2e:journeys
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:e2e:accessibility
DEMO_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:demo
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
```

Python dependencies:

```bash
.venv-linux/bin/python -m pip check
.venv-linux/bin/python -m pip_audit -r requirements.txt
```

Diagnostics:

```bash
python -m scripts.check_public_health \
  --base-url https://pactra-nine.vercel.app --json
python -m scripts.check_financial_invariants --json
python -m scripts.verify_backup <archive> \
  --sha256 <expected> --require-checksum --json
```

## Coverage highlights

Authentication covers registration, login, logout, expiry, revocation,
password change, CSRF, rate limiting, and tenant ownership. Payments cover
manual/assistant creation, invalid and missing data, policy blocks, approvals,
rejections, idempotency, concurrency, receipts, audit history, reversal, and
provider-safe unknown outcomes.

Gemini regressions cover genuine function parts through fixtures, response
round trips, timeout, 503, quota, empty/malformed output, strict arguments,
post-tool failure, and deterministic fallback. No live Gemini request ran.

PayPal regressions cover request construction, worker-only authority, stable
IDs, batch/item parsing, unknown outcomes, terminal failure, success capture,
reconciliation, duplicate protection, reservation rules, and compensation. No
live Sandbox payout ran.

## Test-environment corrections

Three PostgreSQL attempts failed before a valid suite result because the first
used the CI placeholder password, the second inherited the wrong OS peer role
and production provider variables, and the third reached `pactra_test` through
the service role but lacked test-table ownership. These were environment setup
errors, not ignored failures. The final run used the isolated database's local
test owner and passed all 148 tests.

Two final browser-suite invocations stopped before producing valid product
results because this node has no global `python` alias; the successful runs
used the documented `E2E_PYTHON` and `DEMO_PYTHON` overrides. One deliberately
parallel Playwright run also invalidated its own trace output because both
suites share Playwright's default `test-results` directory. A concurrent ESLint
run observed that same directory while Playwright removed it. The normal
sequential commands were rerun: journeys passed 16/16, the demo rehearsal
passed 1/1, accessibility passed 1/1, and lint passed with zero errors.

## Skips and warnings

- The 10 SQLite skips are the explicit PostgreSQL locking, trigger,
  immutability, shared rate-limit, and concurrency tests; all ran and passed in
  the PostgreSQL suite.
- FastAPI TestClient emitted one Starlette deprecation warning about future
  `httpx2` adoption. It does not affect current results and is a P3 dependency
  maintenance item.

No existing test was deleted, weakened, or marked successful after failure.
