# Pactra Coverage Report

Audit date: 2026-11-07  
Release: `0e3e905`

## Executive summary

- Unique automated executions/checks counted in the final evidence set: **201**.
- Passed/clean: **200**.
- Functional test failures: **0**.
- Checks with findings: **1** (full npm development-tool audit).
- Live-provider tests blocked: **2** (Gemini success and PayPal Sandbox payout-item success).
- SQLite skips: **8 PostgreSQL-only cases**; all corresponding PostgreSQL coverage ran in the 91-test PostgreSQL suite.

No statement of line/branch percentage is made because the repository does not currently configure a coverage instrument such as `coverage.py`/Istanbul. This report records behavioural and environment coverage, not an invented percentage.

## Existing automated coverage

| Area | Main files | Coverage highlights |
|---|---|---|
| Authentication/config | `test_auth.py`, `test_config.py` | Registration, login, cookies, expiry/revocation, CSRF, rate limits, password change, unsafe production config refusal |
| Ledger/wallet | `test_ledger.py`, `test_auth.py` | Issuance, top-up, balance, reservation, capture/release, reversal, cursors, audit evidence |
| Policy | `test_policy_engine.py`, `test_transactions.py` | Rule precedence, limits/budgets/vendor/category, approval threshold, version changes |
| Transactions | `test_transactions.py`, `test_transaction_api.py` | Manual/AI source, idempotency, approvals/rejection, retry/reversal, ownership, receipts, filters |
| PostgreSQL/runtime | `test_postgres_runtime.py` | UUID binding, version races, over-reservation, approval races, worker lease, ledger/audit immutability |
| AI | `test_assistant.py`, `test_agent_handlers.py` | Conversation persistence, fallback parsing, tool validation, prompt injection, provider-failure audit |
| PayPal | `test_paypal_payouts.py` | Stable IDs, provider states, unknown outcomes, reconciliation and ledger capture rules |
| Migrations | `test_migrations.py` | Clean SQLite schema/head, required tables/indexes/types |
| Frontend journeys | `judge-flow.spec.ts` | Core payment/approval/reset, policy/block/reject, isolation, recovery, idempotency, conversations, mobile |
| Accessibility | `accessibility.spec.ts` | Automated WCAG 2.1 AA scans across public/authenticated surfaces |
| Production | `route-crawl.spec.ts`, `submission-journey.spec.ts` | All route reloads, console/layout, cookies/CSRF, persistence, tenant isolation and receipt evidence |

## Tests added during this audit

1. `test_approval_revalidation_block_is_audited_and_releases_hold`
   - Proves the hold is released.
   - Proves the transaction is blocked.
   - Proves `transaction.state_changed` records `pending_approval → blocked`.
   - Proves `payment.blocked` records reason and policy versions.
2. `test_audit_events_are_immutable`
   - Proves PostgreSQL rejects audit-event update and delete.
3. Local/PG core journey recipient assertions
   - Proves payout recipient renders on pending and approved receipts.
4. Production submission journey recipient assertions
   - Proves the deployed frontend/API path renders the recipient before and after approval.
5. The previously added production route crawl remains part of the audited branch.

## Final commands and results

### Backend — SQLite

```bash
APP_ENV=test DATABASE_URL=sqlite:// PAYPAL_MOCK_MODE=true \
SESSION_COOKIE_SECURE=false .venv-linux/bin/python -m pytest -q
```

Result: **91 collected; 83 passed; 8 PostgreSQL-only skipped**. One Starlette/httpx deprecation warning.

### Backend — isolated PostgreSQL

Database: `pactra_audit_backend_20261107_r2`

```bash
APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_audit_backend_20261107_r2 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m alembic upgrade head

APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_audit_backend_20261107_r2 \
PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
.venv-linux/bin/python -m pytest -q
```

Result: migration to `20261107_0004`; **91 passed**. One deprecation warning.

### Frontend static checks

```bash
cd frontend
npm run lint
npm run build
```

Result: both PASS. Build output:

```text
1,618 modules transformed
initial JS: 253.13 kB / 78.33 kB gzip
AG Grid lazy JS: 1,107.31 kB / 288.16 kB gzip
AG Grid lazy CSS: 294.70 kB / 41.27 kB gzip
```

The initial gzip payload is within the 200 kB project budget. AG Grid is route-lazy but remains a large optional chunk.

### Local SQLite E2E

```bash
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:e2e
```

Result: **9 journeys passed; 1 WCAG test passed**.

### Isolated PostgreSQL E2E

Database: `pactra_audit_e2e_20261107`

```bash
E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python \
E2E_DATABASE_URL=postgresql+psycopg:///pactra_audit_e2e_20261107 \
npm run test:e2e
```

Result: migration `0003 → 0004`; **9 journeys passed; 1 WCAG test passed**.

### Production E2E

```bash
PUBLIC_BASE_URL=https://pactra-nine.vercel.app npm run test:e2e:public
```

Result: **2 passed** after deployment.

After adding the explicit recipient assertion, the submission test was rerun:

```bash
PUBLIC_BASE_URL=https://pactra-nine.vercel.app npx playwright test \
  --config playwright.public.config.ts tests/public/submission-journey.spec.ts
```

Result: **1 passed**. This is a rerun of one of the two public cases and is not double-counted in the 201 total.

### Dependencies

```bash
.venv-linux/bin/python -m pip check
.venv-linux/bin/python -m pip_audit -r requirements.txt
cd frontend && npm audit --omit=dev --audit-level=high
cd frontend && npm audit --audit-level=high
```

Results:

- Python environment consistency: PASS.
- Python known vulnerabilities: zero.
- Production npm dependencies: zero vulnerabilities.
- Full npm tree: 9 development-tool findings (8 moderate, 1 high), primarily Vite/esbuild and lint/minimatch chains. Suggested fixes require breaking-major changes.

### Lighthouse

Public landing result:

```json
{
  "performance": 0.99,
  "accessibility": 1.0,
  "bestPractices": 1.0,
  "LCP": "1.5 s",
  "CLS": "0",
  "TTI": "1.6 s",
  "TBT": "80 ms",
  "transfer": "149 KiB"
}
```

## Database verification

After production deployment and sandbox smoke tests:

```text
users=44
transactions=85
audit_events=681
status.blocked=16
status.completed=54
status.pending_approval=1
status.rejected=14
unbalanced_journals=0
journals_not_two_entries=0
duplicate_captures=0
completed_internal_without_capture=0
pending_or_executing_without_hold=0
active_hold_invalid_status=0
```

The one active reservation corresponds to the one pending approval and is consistent.

## Coverage gaps

- Live Gemini success/timeout/malformed-response against the real provider.
- Live PayPal Sandbox authentication, payout-item success and reconciliation.
- Manual screen-reader verification.
- Browser E2E for password change, reversal and retry controls.
- Large-history browser pagination/performance beyond the first wallet ledger page.
- Shared/distributed rate-limiter behaviour because production intentionally uses one API worker.
