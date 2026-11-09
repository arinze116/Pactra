# Pactra Release-Candidate Acceptance Evidence

Recorded: 2026-11-09, Africa/Lagos

Release-candidate commit: `8c8798a0dd89608c22b4c986428af9d815219771`

Branch: `codex/prd-gap-closure-20261107`

Production URL (unchanged and not tested as this release candidate):
`https://pactra-nine.vercel.app`

## Release-candidate identity

**Verified.** Immediately before the release-candidate rerun and again after all
test commands completed:

```text
git rev-parse HEAD
8c8798a0dd89608c22b4c986428af9d815219771

git status --porcelain=v1
<no output>
```

Every result in this report was rerun while that exact commit was checked out
and the tracked working tree was clean. The two requested QA documentation
edits were made only after the rerun completed, so they are the expected local
changes after this evidence was recorded.

## CI association

**Verified: no valid CI run exists for this release-candidate SHA.**

- GitHub's commit API returns `No commit found` for the exact SHA.
- The Actions API returns `total_count: 0` for the exact SHA.
- The feature branch has no remote/upstream branch.
- Therefore there is no CI run ID, job log or GitHub check that can be
  associated with this release candidate.

The newest repository CI run is `42262019828`, associated with unrelated commit
`1067e611f1405995736bab5221b2af5765db1d3d`. Its overall result is `success`,
but it is not evidence for this release candidate and is not used below.

| Gate | Valid CI run ID | Exact commit association | Actual CI result | Exact-commit fallback evidence |
|---|---:|---|---|---|
| Backend / SQLite | None | None | NOT RUN in CI | PASS — 87 passed, 9 PostgreSQL-only skipped |
| PostgreSQL backend | None | None | NOT RUN in CI | PASS — migration to `0005`; 96 passed on PostgreSQL 16 |
| Frontend | None | None | NOT RUN in CI | PASS — `npm ci`, lint and Vite 8.3.6 production build |
| E2E | None | None | NOT RUN in CI | PASS — 13 PostgreSQL Playwright journeys |
| WCAG | None | None | NOT RUN in CI | PASS — one automated suite scanned 14 public/authenticated surfaces |
| Dependency audits | None | None | NOT RUN in CI | PASS — both npm audits, `pip check` and `pip-audit` |

The workflow at `.github/workflows/ci.yml` contains PostgreSQL backend,
frontend, E2E/WCAG, dependency-audit and homepage Lighthouse steps, but the
workflow definition has not executed on this commit.

## Exact-commit rerun results

| Gate | Result |
|---|---|
| SQLite backend | PASS — 87 passed, 9 PostgreSQL-only skipped, 1 deprecation warning |
| PostgreSQL backend | PASS — 96 passed, 1 deprecation warning |
| PostgreSQL clean migration | PASS — clean upgrade through `20261107_0005` |
| Frontend install/lint/build | PASS — 328 packages installed; lint clean; Vite 8.3.6 build complete |
| PostgreSQL Playwright journeys | PASS — 13 passed in 1.4 minutes |
| WCAG 2.1 AA automated suite | PASS — 1 test in 26.4 seconds across 14 surfaces |
| Lighthouse | PASS — homepage only: performance 0.97, accessibility 1.00, best practices 0.96 |
| Python dependency consistency/audit | PASS — no broken requirements; no known vulnerabilities |
| npm production/full audits | PASS — 0 vulnerabilities in both audits |
| Live Gemini | BLOCKED — no approved credential/configuration; no provider call made |
| Live PayPal Sandbox | BLOCKED — no approved credentials/capability/recipient/test authorization; no provider call made |

The FastAPI TestClient emitted one `StarletteDeprecationWarning`. `npm ci` also
reported that ESLint 9.39.5 is no longer supported. Neither warning failed its
gate, but both are maintenance follow-ups.

## Commands executed at the exact SHA

```bash
APP_ENV=test \
DATABASE_URL=sqlite:////tmp/pactra-rc-8c8798a-backend-20261109-r2.db \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: `87 passed, 9 skipped, 1 warning` in 62.34 seconds. The skipped tests
are explicitly PostgreSQL-only and passed in the PostgreSQL run.

```bash
APP_ENV=test \
DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_backend_20261109_r2 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m alembic upgrade head

APP_ENV=test \
DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_backend_20261109_r2 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m pytest -o addopts='' -q
```

Result: clean migration through `0005`; `96 passed, 1 warning` in 62.45
seconds.

```bash
cd frontend
npm ci
npm run lint
npm run build
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
../.venv-linux/bin/python -m pip check
../.venv-linux/bin/python -m pip_audit -r ../requirements.txt
```

Result: all passed; both npm audits reported `found 0 vulnerabilities`, Python
reported `No broken requirements found` and `No known vulnerabilities found`.

```bash
cd frontend
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python \
E2E_DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_e2e_20261109 \
npm run test:e2e
```

Result: 13 journey tests passed in 1.4 minutes; the separate automated WCAG
suite passed in 26.4 seconds. The WCAG suite scanned the landing, sign-in,
sign-up, public not-found, overview, wallet, policy, new-payment, approvals,
transactions, assistant, settings, PayPal integration and authenticated
not-found surfaces.

## Lighthouse scope

**Verified scope: homepage only.**

```bash
CHROME_PATH=/home/ubuntu/.cache/ms-playwright/chromium-1194/chrome-linux/chrome \
npx lighthouse http://127.0.0.1:4173/ \
  --chrome-flags='--headless --no-sandbox' \
  --only-categories=performance,accessibility,best-practices \
  --output=json \
  --output-path=/tmp/pactra-lighthouse-8c8798a-20261109.json \
  --quiet
npm run test:lighthouse:assert -- \
  /tmp/pactra-lighthouse-8c8798a-20261109.json
```

Result: performance `0.97`, accessibility `1.00`, best practices `0.96`.
No authenticated route, secondary public route or route-wide Lighthouse crawl
was run. Route-wide accessibility evidence comes from Axe/Playwright, not
Lighthouse.

## Migration `20261107_0005`

### Existing production compatibility

**Verified by read-only production inspection and an isolated live-data clone.**

- Production is PostgreSQL 16.15 at migration `20261107_0004`.
- Production has 15 public base tables and no existing
  `rate_limit_buckets` table or `ix_rate_limit_buckets_expires` index.
- A separate database was populated from the live database without writing to
  production, then upgraded from `0004` to `0005` successfully.
- After upgrade, the new table and index existed and the table was empty.
- No user, wallet, policy, transaction, audit or ledger table is altered or
  rewritten by the migration.

### Upgrade safety and locking

**Verified/strongly supported.** The migration uses PostgreSQL transactional
DDL to create one new table and one ordinary index on that new empty table. It
does not acquire a table-rewrite lock on an existing application relation.

On the production-data clone, an `ACCESS SHARE` lock was held on the existing
`transactions` table while the migration ran with `lock_timeout=2s`. Upgrade
completed in 0.88 seconds and the concurrent reader completed normally. Short
catalog/namespace locks and locks on the newly created relation still occur,
so the controlled service-restart window remains appropriate. Concurrent
schema DDL should not be scheduled during the release.

### Downgrade behaviour

**Verified on the isolated clone.** Downgrade to `20261107_0004` drops the
expiry index and the entire `rate_limit_buckets` table. A seeded test bucket
was destroyed, and re-upgrade recreated an empty table. Downgrade therefore
discards active rate-limit window state.

The safe application rollback is to return to the prior application release
while leaving additive migration `0005` in place; the prior application ignores
the new table. Do not run the downgrade while the new application is serving
traffic. If downgrade is ever required, stop the new application first and
explicitly accept loss of the stored limiter state.

## Original 14-row backlog traceability

All 14 rows from `QA/FINAL-PRD-GAP-REVIEW.md` are mapped below. `PASS` means
implementation and non-provider acceptance evidence passed. `BLOCKED` means
the implementation exists but the PRD requires a genuine external-provider
acceptance result that was not attempted.

| # | Original backlog row | Implementation mapping | Acceptance evidence | Status |
|---:|---|---|---|---|
| 1 | AI-006 / INT-005 live Gemini | `backend/services/assistant.py`, `backend/config.py` retain the exact-model governed tool path | `test_assistant.py` fake-client function/failure tests pass; no live call | BLOCKED |
| 2 | PAY-010 / INT-002 / INT-003 PayPal | `backend/services/paypal.py`, `backend/paypal_client.py`, `backend/worker.py` implement submission/reconciliation | `test_paypal_payouts.py` fake-client state tests pass; no real item result | BLOCKED |
| 3 | PLT-006 PayPal guided scenario | `OverviewPage.tsx` requires completed PayPal rail plus persisted provider `SUCCESS`; `PaymentPages.tsx` gates the rail on configuration | Source assertion and internal browser no-`SUCCESS` assertion; provider prerequisite absent | BLOCKED |
| 4 | PAY-003 blocked HTTP contract | `backend/main.py` and `frontend/src/api.ts` preserve exact 422/402 replay-safe outcomes | `test_policy_update_changes_decision_and_blocked_transaction_is_persisted`; `test_insufficient_funds_returns_persisted_402_without_ledger_movement` | PASS |
| 5 | PLT-006 insufficient-funds + analytics | `backend/services/judge.py`, `backend/services/sandbox.py`, `OverviewPage.tsx`, `PaymentPages.tsx` | `test_guided_analytics_events_are_unique_per_generation`; guided insufficient-funds E2E | PASS |
| 6 | PAY-005 / BUG-007 approval context | `backend/schemas.py`, `backend/services/transactions.py`, `TransactionPages.tsx` add requester, policy/checks, balance, time and age | `test_pending_approval_and_rejection_flows`; approval-context browser assertions | PASS |
| 7 | Reset/retry/reversal acceptance | `backend/services/transactions.py`, `backend/services/sandbox.py`, `scripts/seed_e2e_failed_transaction.py` | backend reset/retry tests plus browser reversal and idempotent retry journeys | PASS for internal/state-fixture scope; live provider remains row 2 |
| 8 | POL-007 policy preview | `backend/services/policies.py`, `backend/main.py`, `PaymentPages.tsx` use the production evaluator without mutation | `test_policy_preview_is_authoritative_and_side_effect_free`; browser likely-decision assertions | PASS |
| 9 | PLT-004 recovery states | `OverviewPage.tsx` and `ControlPages.tsx` split loaders and targeted retries | `overview and wallet sections recover independently` | PASS |
| 10 | REC-003 lifecycle context | `backend/services/transactions.py` and `TransactionPages.tsx` expose actor labels and allow-listed summaries | receipt API assertions for actor, summary, ordering and secret redaction | PASS |
| 11 | REC-004 ledger labels | `backend/services/transactions.py` and `TransactionPages.tsx` expose safe labels and debit/credit totals | receipt API assertions for labels and balanced amounts; browser reversal totals | PASS |
| 12 | AUTH-008 password reveal | `PublicPages.tsx` adds independent accessible sign-up/sign-in reveal controls | desktop/mobile keyboard and successful auth E2E | PASS |
| 13 | INF-005 dependencies/CI | `frontend/package*.json`, `requirements-dev.txt`, `.github/workflows/ci.yml`, `assert-lighthouse.mjs` | Local audits/build pass; no exact-commit CI execution exists | PARTIAL — CI evidence blocker |
| 14 | SEC-005 distributed limiter | `backend/auth.py`, `backend/models.py`, migration `0005` add atomic hashed database buckets and `Retry-After` | PostgreSQL 10-way independent-state concurrency test; migration/clone checks | PASS |

## Provider-evidence boundary

**Verified: no provider success is inferred from mocks or fixtures.**

- Gemini tests inject `FakeGeminiClient`; their results prove orchestration,
  validation and fallback behaviour only.
- PayPal tests inject `FakePayPalClient`; synthetic `SUCCESS` values prove
  state-machine and exactly-once ledger behaviour only.
- Legacy PayPal mock-mode tests explicitly require a failed outcome and no
  provider identifier.
- Playwright runs with `AI_ENABLED=false`, `PAYPAL_PAYOUTS_ENABLED=false`,
  `PAYPAL_MOCK_MODE=false` and blank provider credentials.
- The internal retry fixture is restricted to `APP_ENV=test`, uses the
  `internal_sandbox` rail and contains no provider success.
- The browser core journey explicitly asserts that an internal receipt does
  not display provider `SUCCESS`.

No Gemini request and no PayPal request was sent during this verification.

## Release-candidate blockers

- No GitHub CI run or run ID is associated with the exact release-candidate
  commit.
- No deployed live Gemini function call has been verified.
- No real PayPal Sandbox payout item has reached verified `SUCCESS` and
  exactly-once Pactra reconciliation.
- The separately tracked PayPal guided scenario remains blocked by that same
  real provider prerequisite.
- No public release-candidate smoke test ran because deployment was correctly
  withheld.
