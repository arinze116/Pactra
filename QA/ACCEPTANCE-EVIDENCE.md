# Pactra Acceptance Evidence

Updated: 2026-11-09, Africa/Lagos

Branch: `codex/paypal-worker-single-authority`

Implementation baseline: `82e1b75a2ab59a105fee2b59c2aa481f63c738a5`

Production: release `0e3e905`, migration `20261107_0004`

This report separates deterministic implementation evidence from external
provider acceptance. The final branch SHA and exact-SHA CI run are recorded in
the pull request and final release report after the documentation commit.

## GitHub CI association

The latest completed remote run before the final documentation commit is:

- Run ID: `42569969262`
- URL: https://github.com/arinze116/Pactra/actions/runs/42569969262
- Branch: `codex/paypal-worker-single-authority`
- Exact SHA: `82e1b75a2ab59a105fee2b59c2aa481f63c738a5`
- Result: `success`

All four mandatory jobs passed: Backend SQLite, Backend PostgreSQL, Frontend
lint/build/audits, and E2E journeys/WCAG/homepage Lighthouse. This run does not
cover the subsequent documentation, recovery, recipient-masking, and keyboard
regressions; those changes require a new exact-final-SHA run before merge.

## Current local verification

All provider calls were disabled or replaced by deterministic fakes.

| Gate | Command/evidence | Result |
|---|---|---|
| SQLite | Fresh migration plus full Pytest suite | PASS — 118 passed, 10 PostgreSQL-only skipped |
| PostgreSQL | Fresh isolated database, migration plus full Pytest suite | PASS — 128 passed |
| Frontend | `npm run lint`; `npm run build` | PASS |
| Browser journeys | `npm run test:e2e:journeys` | PASS — 15 journeys |
| Automated WCAG | `npm run test:e2e:accessibility` | PASS across 14 configured public/authenticated surfaces |
| Keyboard journey | Keyboard-only registration plus application skip link | PASS |
| Python dependencies | `pip check`; `pip-audit -r requirements.txt` | PASS — no broken requirements or known vulnerabilities |
| Node dependencies | production and full `npm audit` | PASS — zero vulnerabilities |
| Lighthouse | Local preview homepage `/` only | PASS — 0.97 performance, 1.00 accessibility, 0.96 best practices; no route-wide claim |

The FastAPI suite emits one upstream Starlette/httpx deprecation warning. It
does not change the test result and remains a maintenance item.

### Commands executed

```bash
APP_ENV=test +SECRET_KEY=final-verification-secret-key-at-least-32-bytes +DATABASE_URL=sqlite:////tmp/pactra-merge-verification-20261109-r3.db +AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=true +PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com +SESSION_COOKIE_SECURE=false +.venv-linux/bin/alembic upgrade head

APP_ENV=test +SECRET_KEY=final-verification-secret-key-at-least-32-bytes +DATABASE_URL=sqlite:////tmp/pactra-merge-verification-20261109-r3.db +AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=true +PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com +SESSION_COOKIE_SECURE=false +.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: 118 passed, 10 skipped.

```bash
sudo -u postgres createdb -O ubuntu pactra_merge_verification_20261109_r2

APP_ENV=test +SECRET_KEY=final-verification-secret-key-at-least-32-bytes +DATABASE_URL=postgresql+psycopg:///pactra_merge_verification_20261109_r2 +AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=false +PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com +SESSION_COOKIE_SECURE=false +.venv-linux/bin/alembic upgrade head

APP_ENV=test +SECRET_KEY=final-verification-secret-key-at-least-32-bytes +DATABASE_URL=postgresql+psycopg:///pactra_merge_verification_20261109_r2 +AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=false +PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com +SESSION_COOKIE_SECURE=false +.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: 128 passed.

```bash
cd frontend
npm run lint
npm run build
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python +E2E_FRONTEND_PORT=5189 E2E_API_PORT=8019 +npm run test:e2e
```

Result: 15 journeys passed; one Axe suite passed across 14 configured surfaces.

```bash
.venv-linux/bin/python -m compileall -q backend
.venv-linux/bin/python -m pip check
.venv-linux/bin/python -m pip_audit -r requirements.txt
cd frontend
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
```

Result: compile and dependency consistency passed; both ecosystems reported no
known vulnerabilities.

```bash
npx lighthouse http://127.0.0.1:4174/ +  --chrome-flags="--headless --no-sandbox" +  --only-categories=performance,accessibility,best-practices +  --output=json --output-path=/tmp/pactra-final-lighthouse.json --quiet
npm run test:lighthouse:assert -- /tmp/pactra-final-lighthouse.json
```

Result: performance 0.97, accessibility 1.00, best practices 0.96. Scope was
the homepage only.

## Payment execution evidence

- No active API route calls PayPal submission.
- `backend/services/paypal.py` is the only non-test caller of
  `PayPalClient.create_payout`.
- The worker locks the transaction and attempt with PostgreSQL
  `FOR UPDATE SKIP LOCKED`, then conditionally changes `submitting` to
  `claimed`.
- Submission and reconciliation are separate commits/cycles, so a stored
  provider batch reference survives a later capture failure.
- Sender batch/request IDs are stable for transaction plus attempt number.
- Duplicate queue delivery and concurrent claims have one local winner.
- Timeout, connection reset, HTTP 408/425/429/5xx, and malformed 201 responses
  become `unknown`; the reservation remains held.
- Automatic scans exclude `unknown` attempts without a batch ID.
- Explicit authenticated recovery reuses the same attempt and identifiers.
- Batch acceptance never captures funds. Only payout-item `SUCCESS` does.
- Terminal failure releases the reservation once. Returned, reversed, and
  refunded states post at most one compensating journal.

These are deterministic implementation results. They are not proof that the
current PayPal Sandbox account can complete a payout.

## Approval and policy evidence

- A one-dollar isolated policy requires approval only when the amount is above
  the configured threshold; the exact threshold remains auto-approved.
- Pending approval cannot be claimed by the worker because no PayPal attempt is
  executable until approval changes the transaction to `executing`.
- Rejection releases the reservation and creates zero provider submissions.
- Duplicate and concurrent approval/rejection actions are conditional and
  single-use.
- Policy changes are re-evaluated before approval and are audited.
- Expired or revoked sessions cannot approve or reject.

## Migration `20261107_0005`

The migration creates only `rate_limit_buckets` and an expiry index. It has no
backfill, foreign key, default expression, or rewrite of an existing table.

Verified on an isolated PostgreSQL clone:

- A forced migration conflict rolled back transactionally and left revision
  `20261107_0004`.
- Recovery upgraded successfully to `20261107_0005`.
- Upgrade completed in approximately 905 ms while an existing-table reader
  remained active.
- Downgrade removed the table and therefore destroyed only stored rate-limit
  windows.
- Release `0e3e905` can run at `0004`, but its Alembic graph cannot recognize a
  database stamped at `0005`.

Rollback therefore requires both Pactra services stopped, candidate code used
to downgrade to `0004`, verification that the limiter table is absent, then a
symlink switch to `0e3e905`. Production was not migrated.

## Original 14-row PRD gap traceability

| # | Original gap | Implementation and acceptance evidence | Status |
|---:|---|---|---|
| 1 | AI-006 / INT-005 live Gemini | Exact model/tool path and fallback tests pass; latest live request returned `429 RESOURCE_EXHAUSTED` with no function call | BLOCKED |
| 2 | PAY-010 / INT-002 / INT-003 PayPal | Worker-only state machine, idempotency, failure and reconciliation tests pass; no payout item `SUCCESS` exists | BLOCKED |
| 3 | PLT-006 PayPal guided scenario | Checklist requires persisted provider `SUCCESS`; mocks cannot complete it | BLOCKED |
| 4 | PAY-003 blocked HTTP contract | Persisted 422/402 outcomes and idempotent replay tests | PASS |
| 5 | PLT-006 insufficient funds and analytics | Persisted insufficient-funds scenario and generation-scoped events | PASS |
| 6 | PAY-005 / BUG-007 approval context | Requester, policy checks, balance, age, and action evidence in API/UI tests | PASS |
| 7 | Reset/retry/reversal | Internal reversal, retry idempotency, reset preservation, unresolved-provider safeguards | PASS for deterministic scope |
| 8 | POL-007 policy preview | Server evaluator with no mutation plus API/browser assertions | PASS |
| 9 | PLT-004 recovery states | Independent overview/wallet loaders and targeted retry journeys | PASS |
| 10 | REC-003 lifecycle context | Owned audit actors and allow-listed event summaries | PASS |
| 11 | REC-004 ledger labels | Safe account labels and balanced debit/credit receipt totals | PASS |
| 12 | AUTH-008 password reveal | Accessible controls plus desktop/mobile and keyboard browser coverage | PASS |
| 13 | INF-005 dependencies/CI | Required audits and quality jobs exist; final exact-SHA run remains the merge gate | PASS locally / CI pending final SHA |
| 14 | SEC-005 distributed limiter | PostgreSQL atomic bucket tests and migration drill | PASS candidate; not deployed |

The separately tracked PayPal guided scenario remains row 3 and is not hidden
inside another backlog item.

## Provider evidence boundary

Production readiness currently reports Gemini and PayPal configured/enabled.
That is configuration evidence only.

- Gemini: the latest recorded live generation returned
  `429 RESOURCE_EXHAUSTED`; no live tool call was produced.
- PayPal: Sandbox OAuth succeeded in the prior authorized verification. One
  prior authorized payout ended `DENIED`/`FAILED` with PayPal reporting that
  the recipient could not accept the payment. Credentials and recipient were
  subsequently changed, but no payout after that change was authorized in this
  mandate.
- Fake Gemini/PayPal clients and synthetic provider statuses prove only local
  orchestration and financial invariants.
- An OAuth token, HTTP 201, batch creation, deterministic fallback, fixture, or
  mock `SUCCESS` is never counted as provider success.

## Remaining release blockers

1. Genuine `gemini-3.8-flash` function calling remains unverified because of
   provider quota/entitlement.
2. No real PayPal Sandbox payout item has reached `SUCCESS` and reconciled
   through this candidate.
3. The PayPal guided scenario is therefore incomplete.
4. The candidate is not deployed; production remains at `0e3e905`/`0004`.
5. Public post-deployment acceptance has not run.

Production configuration, services, database, and provider accounts were not
changed during this verification. No payout was submitted.
