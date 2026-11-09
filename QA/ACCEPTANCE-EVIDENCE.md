# Pactra Acceptance Evidence

Updated: 2026-11-09, Africa/Lagos

This report separates verified engineering/deployment evidence from external
provider acceptance. `PASS` never means more than the evidence stated.

## Release and GitHub association

| Item | Evidence | Status |
|---|---|---|
| PR #7 | Merge `506108663ea6a535e54b3f834f95beaffee83ff6` | PASS |
| PR #8 | Merge `2f97cf07e27d572d9f7ad3efdd49d2c485bae347` | PASS |
| PR #9 | Merge `9b4bc77cf65b5ac85be616f6c6afc4a7481de22b` | PASS |
| PR #10 | Merge `c599f5ca0603c1cc66b25684358c3336227dd8c3` | PASS |
| PR #11 | Merge `4534d136766a094aeeac4489a9e694111b9257ae` | PASS |
| Exact-main CI | [42656025377](https://github.com/arinze116/Pactra/actions/runs/42656025377), four jobs, exact SHA `4534d136...` | PASS |
| Local/main agreement | Local `main`, `origin/main` and release source agreed before staging | PASS |

The four CI jobs were Backend SQLite, Backend PostgreSQL, Frontend
lint/build/audits, and E2E journeys/WCAG/homepage Lighthouse.

## Engineering verification

| Gate | Result | Status |
|---|---|---|
| SQLite | 118 passed, 10 PostgreSQL-only skipped | PASS |
| PostgreSQL | 128 passed, including payment, worker, auth, policy, migration and concurrency coverage | PASS |
| Frontend lint/type/build | ESLint, TypeScript and Vite build completed | PASS |
| Browser journeys | 16 configured E2E journeys | PASS |
| Automated WCAG | Axe passed configured public and authenticated surfaces | PASS |
| Python dependency consistency | `pip check` | PASS |
| Python vulnerability audit | `pip-audit -r requirements.txt` | PASS |
| npm production audit | zero vulnerabilities | PASS |
| npm full audit | zero vulnerabilities | PASS |
| Artifact imports | FastAPI, Alembic, SQLAlchemy, Psycopg, Gemini SDK and application modules | PASS |

Representative commands:

```bash
python -m pytest -q
python -m pip check
python -m pip_audit -r requirements.txt
cd frontend
npm run lint
npm run build
npm run test:e2e
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
```

## Payment and security invariants

- No active API route submits a PayPal payout. The API validates, evaluates
  policy, reserves and queues only.
- The worker is the only non-test caller of payout creation and holds a
  PostgreSQL advisory lease.
- Transaction/attempt claims use row locks and conditional state transitions;
  concurrent workers have one winner.
- Sender batch ID, sender item ID and local request ID remain stable for the
  same attempt.
- Timeout, connection failure, HTTP 408/425/429/5xx and malformed accepted
  responses become `unknown`; the reservation remains active.
- Automatic scans exclude unknown submissions without a trustworthy batch ID.
- Batch acceptance never captures. Only payout-item `SUCCESS` captures once.
- Terminal failure releases once. Returned, reversed and refunded states
  compensate at most once.
- Authentication, tenant ownership, approval authorisation, CSRF, secure
  cookies, policy checks, validation and database-backed rate limits passed.
- Production uses `SECRET_KEY_FILE=/etc/pactra/secret-key`; the file is mode
  `0600`, non-default and at least 32 characters. Configured CORS includes the
  exact frontend origin.
- Frontend and logs exposed no credentials. The PayPal page displayed only a
  masked recipient.

These are deterministic implementation results, not proof of provider payout
success.

## Gemini evidence

| Check | Result | Status |
|---|---|---|
| Production model/key presence | `gemini-3.8-flash`; key present | PASS |
| Old production key | `400 INVALID_ARGUMENT` / `API_KEY_INVALID` | FAIL |
| Replacement key model lookup | Model metadata returned | PASS |
| Production/project key alignment | Keys compare equal without printing either value | PASS |
| Genuine Pactra function call | Provider `503` and bounded timeout; no function-call response | BLOCKED |
| Function name/arguments validation | No genuine call returned to validate | NOT TESTED |
| Deterministic fallback | Governed internal $20 payment completed once | PASS |
| Error containment | Quota/timeout/provider failures left the UI and policy/ledger path operational | PASS |

The production environment file was backed up before the targeted key change:

`/opt/pactra/backups/pactra.env-pre-gemini-key-fix-20261109T160057Z`

SHA-256:
`41786f0daecc906dac785bb45d8ef38c25775151e358fcf488f8f188724cf86a`.

No additional generation retry is justified until provider capacity changes.

## PayPal Sandbox evidence and checkpoint

Configuration inspection, without printing credentials, verified:

- host `https://api-m.sandbox.paypal.com`;
- payouts enabled;
- mock mode disabled;
- client ID, client secret and configured recipient present;
- OAuth succeeded in 737 ms and the token included Payouts scope;
- the worker acquired its database lease after deployment.

The sender email is not exposed by the client-credentials API and was not
independently verified. OAuth is not payout success.

Prepared transaction:

| Field | Value |
|---|---|
| Transaction | `bfe1e158-863b-4ddf-93a0-e31146e7cbcb` |
| Test account | `pactra-paypal-approval-20261109160306@example.com` |
| Amount | `$25.00 USD` |
| Recipient | `sb-4fqlt53808662@personal.example.com` |
| Rail | `paypal_sandbox_payouts` |
| Category/reason | `freelance` / `PayPal Sandbox payout test` |
| Policy | version `2`; approval threshold `$1.00` |
| State | `pending_approval` |
| Posted/reserved/available | `$1,000.00` / `$25.00` / `$975.00` |
| Attempts/provider IDs/ledger journals | `0` / none / `0` |

The transaction remained unchanged through worker scans and deployment. The
approval endpoint was not called. Payout item success and provider-backed
capture are **BLOCKED** pending separate explicit authorisation.

## Artifact integrity

| Check | Evidence | Status |
|---|---|---|
| Release directory | `/opt/pactra/releases/4534d13` | PASS |
| Embedded SHA | `4534d136766a094aeeac4489a9e694111b9257ae` | PASS |
| Source archive | Preserved inside `.release-metadata` | PASS |
| Archive SHA-256 | `7b54f3923994af46e7aed7da3e3f60f2d19220d50a2ab0757613d8d1002d8610` | PASS |
| Tracked contents | 139 archive members compared byte-for-byte, zero mismatches | PASS |
| Permissions | `root:pactra`, read-only; no group/world writable files or directories | PASS |
| Python | 3.12.3, resolved manifest, `pip check`, required imports | PASS |
| Frontend | Actual `dist` plus per-file SHA-256 manifest | PASS |
| Capacity | 86 GiB filesystem free and 9.7 GiB memory available at preflight | PASS |

## Backup, migration and rollback

Backup:

- path:
  `/opt/pactra/backups/pactra-pre-4534d136766a094aeeac4489a9e694111b9257ae-20261109T163956Z.dump`;
- SHA-256:
  `e7c1ce7bac3891586d19c0165be42eda0dde21c3da93b2e1fa4178c1c50b7f1e`;
- mode/owner: `0600`, `pactra:pactra`;
- `pg_restore --list`: PASS.

Restore database: `pactra_restore_4534d13_20261109163956`.

The restored clone was at `20261107_0005` with 16 base tables and preserved
the prepared PayPal transaction/reservation. The exact artifact then passed:

1. an inserted rate-limit row;
2. downgrade `0005 → 0004`;
3. verification that `rate_limit_buckets` was absent;
4. unchanged counts for users (53), transactions (106), reservations (86),
   ledger entries (308), and audit events (861);
5. readiness of legacy release `0e3e905` against the downgraded clone;
6. re-upgrade `0004 → 0005` and recreation of the table/index.

The downgrade intentionally deletes every rate-limit bucket. Immediate
rollback to `9b4bc77` is schema-compatible and requires no downgrade. Rollback
to `0e3e905` requires both services stopped and the candidate code used to
downgrade first.

## Production deployment

Deployment started `2026-11-09T16:41:01Z`.

| Check | Result | Status |
|---|---|---|
| Active symlink | `/opt/pactra/releases/4534d13` | PASS |
| Embedded SHA | `4534d136...` | PASS |
| Alembic revision | `20261107_0005` | PASS |
| Rate-limit table/index | Present | PASS |
| API | Active/running, zero restarts | PASS |
| Worker | Active/running, zero restarts, lease acquired | PASS |
| Local health/readiness | 200 | PASS |
| Public health/readiness | 200 | PASS |
| Startup logs | No unexpected error; Alembic pre-start was a no-op at head | PASS |
| PayPal checkpoint after deployment | Still pending; zero attempts/provider IDs/journals | PASS |

No rollback trigger occurred. No unrelated service, Docker workload, Nginx
site, certificate, domain, firewall or Tailscale configuration was changed.

## Public post-deployment verification

The original production acceptance tests used a five-second assistant
assertion while the bounded provider path takes about 38 seconds. The server
subsequently persisted both deterministic fallback responses. PR #11 corrected
the public crawl wait to 60 seconds without weakening the required response.

A recovery test signed back into the same synthetic accounts and sent no new
Gemini or PayPal request. It passed before and after deployment (32.4 and 32.8
seconds respectively), covering:

- homepage, sign-in, sign-up and not-found routes;
- registration/login, secure cookies, sign-out and unauthenticated access;
- dashboard, wallet funding simulation and persisted balances;
- policy save/versioning;
- completed manual payment and receipt/ledger evidence;
- approval-required rejection and policy-blocked transaction;
- persisted AI deterministic fallback and verified receipt;
- approvals, transactions, policy, wallet, assistant and settings reloads;
- PayPal integration page with masked recipient;
- tenant isolation returning 404 for another user's receipt;
- Axe checks and no browser console/page errors;
- 1440×1000, 1024×768 and 390×844 layouts with no horizontal overflow.

Production Lighthouse (`--preset=desktop`) passed on `/`, `/sign-in` and
`/sign-up` with 1.00 in performance, accessibility and best practices.

Security headers verified: CSP, HSTS, `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff`, strict referrer policy and a restricted
permissions policy.

## Final acceptance matrix

| Requirement | Status |
|---|---|
| GitHub integration and exact-main CI | PASS |
| Engineering suites and audits | PASS |
| Worker-only PayPal architecture and financial invariants | PASS |
| Immutable release and dependency integrity | PASS |
| Backup, migration, downgrade and rollback readiness | PASS |
| Production deployment and service health | PASS |
| Public functional, responsive and accessibility acceptance | PASS |
| Genuine Gemini function-call response | BLOCKED |
| Exact $25 PayPal payout submission | BLOCKED pending separate approval |
| PayPal item-level `SUCCESS` and exactly-once provider capture | NOT TESTED |
| Overall product acceptance | BLOCKED |
