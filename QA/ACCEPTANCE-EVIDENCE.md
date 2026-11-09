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
| PR #12 | Merge `73fdfb692f6daea69ba5f44bc37d9afa1814419a` | PASS |
| Exact-main CI | [42659603721](https://github.com/arinze116/Pactra/actions/runs/42659603721), four jobs, exact SHA `73fdfb69...` | PASS |
| Local/main agreement | Local `main`, `origin/main` and release source agreed before staging | PASS |

The four CI jobs were Backend SQLite, Backend PostgreSQL, Frontend
lint/build/audits, and E2E journeys/WCAG/homepage Lighthouse.

## Engineering verification

| Gate | Result | Status |
|---|---|---|
| SQLite | 121 passed, 10 PostgreSQL-only skipped on the Gemini candidate | PASS |
| PostgreSQL | 131 passed after an isolated concurrency rerun and second full-suite pass | PASS |
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

These deterministic implementation results are supplemented below by the
separately authorised live Sandbox payout and item-level provider evidence.

## Gemini evidence

| Check | Result | Status |
|---|---|---|
| Production model/key presence | `gemini-3.8-flash`; key present | PASS |
| Production/project key alignment | Keys compare equal without printing either value | PASS |
| Actual account discovery | Eight relevant Flash identifiers returned with `generateContent` | PASS |
| Current model baseline | HTTP 503 at 6,312 ms, then timeout at 12,011 ms | FAIL |
| `gemini-3.6-flash` | Two bounded 12-second timeouts | FAIL |
| `gemini-3.1-flash-lite` | Two bounded 12-second timeouts | FAIL |
| `gemini-3.5-flash` | Two bounded 12-second timeouts | FAIL |
| `gemini-3.5-flash-lite` basic calls | Two genuine `create_payment_request` calls with validated arguments | PASS |
| Function-response round trip | Two calls and final text replies; `STOP` finish reasons | PASS |
| Full isolated Pactra workflow | Extraction, policy, approval, fallback boundary, receipt and audit checks | PASS |
| Deterministic fallback | Timeout, 503 and malformed/empty response regressions | PASS |
| Production candidate deployment | Current runtime is unchanged | NOT TESTED |

The production environment file was backed up before the targeted key change:

`/opt/pactra/backups/pactra.env-pre-gemini-key-fix-20261109T160057Z`

SHA-256:
`41786f0daecc906dac785bb45d8ef38c25775151e358fcf488f8f188724cf86a`.

The selected model is `gemini-3.5-flash-lite`; `gemini-3.8-flash` remains the
documented configuration rollback. Google documents the selected identifier as
stable, function-calling capable and free-tier eligible. No billing, API key or
Google project change was made.

The complete workflow exposed and corrected two request-contract defects. A
function response had been sent with role `tool`, which the API rejected with
HTTP 400; the SDK contract uses role `user`. The tool declaration also failed
to identify `recipient` as a payout-only email, causing intermittent invalid
vendor-payment arguments. The corrected contract passed two exact final
round trips at 539–972 ms for the call and 652–671 ms for the final response.

The final isolated workflow used PayPal-disabled in-memory data. It completed
one $49 internal payout with a balanced two-entry receipt, retained one $120
request at `pending_approval` with one active reservation and zero attempts,
and created no transaction for a missing-amount request. Full evidence and
commands are in `QA/GEMINI-MODEL-COMPATIBILITY.md`.

## PayPal Sandbox execution evidence

Configuration inspection, without printing credentials, verified:

- host `https://api-m.sandbox.paypal.com`;
- payouts enabled;
- mock mode disabled;
- client ID, client secret and configured recipient present;
- OAuth succeeded in 737 ms and the token included Payouts scope;
- the worker acquired its database lease after deployment.

The sender email is not exposed by the client-credentials API and was not
independently verified. OAuth alone was not treated as payout success.

Executed transaction:

| Field | Value |
|---|---|
| Transaction | `bfe1e158-863b-4ddf-93a0-e31146e7cbcb` |
| Test account | `pactra-paypal-approval-20261109160306@example.com` |
| Amount | `$25.00 USD` |
| Recipient | `sb-4fqlt53808662@personal.example.com` |
| Rail | `paypal_sandbox_payouts` |
| Category/reason | `freelance` / `PayPal Sandbox payout test` |
| Policy | version `2`; approval threshold `$1.00` |
| Pre-approval state | `pending_approval`; active $25.00 reservation; zero attempts, provider IDs and journals |
| Approval | One API approval at `2026-11-09 18:23:44 WAT`, policy version `2` |
| Worker submission | One payout POST, HTTP `201`, at `2026-11-09 18:23:47 WAT` |
| Provider reconciliation | Persisted batch `ZMQQ…3Q8U`; one item `E5KZ…KTYA`; item-level `SUCCESS` |
| Final state | `completed` at `2026-11-09 18:24:08 WAT`; failure code absent |
| Final posted/reserved/available | `$975.00` / `$0.00` / `$975.00` |
| Ledger | One `payment_capture` journal; one $25.00 wallet debit and one $25.00 clearing credit |

The user separately authorised this exact transaction, amount, currency and
recipient. Immediately before approval, the live database still showed the
prepared values above, one active reservation, no approval action, no attempt,
no provider identifiers and no journal. The approval endpoint was called once
with one idempotency key through a short-lived operator session scoped to the
isolated account; that session was revoked immediately after the response. The
endpoint changed the transaction to `executing` and created one `submitting`
attempt; it did not contact PayPal.

The existing worker claimed that attempt, issued the only payout-creation POST,
persisted the returned batch ID, and reconciled that same batch on its next
bounded cycle. An independent read-only lookup using the persisted batch ID
returned HTTP 200 in 746 ms and verified:

- batch status `SUCCESS`;
- exactly one payout item with `transaction_status=SUCCESS`;
- persisted provider batch and item IDs match PayPal;
- stable sender batch and item IDs match attempt 1;
- amount `$25.00 USD` and the authorised recipient match.

Pactra captured the reservation only after item-level success. Database and
receipt evidence shows one completed attempt, one captured reservation, one
balanced capture journal with two entries, zero reversal journals, nine
lifecycle/audit events and identical receipt contents after reload. Global
lookups found one transaction and one attempt for each provider identifier and
one attempt for the stable rail request ID. No unresolved payout remains for
the isolated account, and worker logs contain one payout POST.

## Artifact integrity

| Check | Evidence | Status |
|---|---|---|
| Release directory | `/opt/pactra/releases/73fdfb6` | PASS |
| Embedded SHA | `73fdfb692f6daea69ba5f44bc37d9afa1814419a` | PASS |
| Source archive | Preserved inside `.release-metadata` | PASS |
| Archive SHA-256 | `6c16fbcd6b11187182f8ae1d9ea2374f12aa23ca39f629a35f112cabde1792c4` | PASS |
| Tracked contents | 139 archive members compared byte-for-byte, zero mismatches | PASS |
| Permissions | `root:pactra`, read-only; no group/world writable files or directories | PASS |
| Python | 3.12.3, resolved manifest, `pip check`, required imports | PASS |
| Frontend | Actual `dist` plus per-file SHA-256 manifest | PASS |
| Capacity | 86 GiB filesystem free and 9.7 GiB memory available at preflight | PASS |

## Backup, migration and rollback

Backup:

- path:
  `/opt/pactra/backups/pactra-pre-73fdfb692f6daea69ba5f44bc37d9afa1814419a-20261109T170019Z.dump`;
- SHA-256:
  `828a3b966c6dea957125fe9860f3793be9a777b781349edbb7ad8260b75264c0`;
- mode/owner: `0600`, `pactra:pactra`;
- `pg_restore --list`: PASS.

Restore database: `pactra_restore_4534d13_20261109163956`.

The restored clone was at `20261107_0005` with 16 base tables and preserved
the prepared PayPal transaction/reservation. The runtime-equivalent artifact
then passed:

1. an inserted rate-limit row;
2. downgrade `0005 → 0004`;
3. verification that `rate_limit_buckets` was absent;
4. unchanged counts for users (53), transactions (106), reservations (86),
   ledger entries (308), and audit events (861);
5. readiness of legacy release `0e3e905` against the downgraded clone;
6. re-upgrade `0004 → 0005` and recreation of the table/index.

The downgrade intentionally deletes every rate-limit bucket. Immediate
rollback to `4534d13` is schema-compatible and requires no downgrade. Rollback
to `0e3e905` requires both services stopped and the candidate code used to
downgrade first.

## Production deployment

Final closure deployment started `2026-11-09T17:00:40Z`.

| Check | Result | Status |
|---|---|---|
| Active symlink | `/opt/pactra/releases/73fdfb6` | PASS |
| Embedded SHA | `73fdfb69...` | PASS |
| Alembic revision | `20261107_0005` | PASS |
| Rate-limit table/index | Present | PASS |
| API | Active/running, zero restarts | PASS |
| Worker | Active/running, zero restarts, lease acquired | PASS |
| Local health/readiness | 200 | PASS |
| Public health/readiness | 200 | PASS |
| Startup logs | No unexpected error; Alembic pre-start was a no-op at head | PASS |
| PayPal authorised execution | Item `SUCCESS`; one completed attempt and one exactly-once $25 capture | PASS |

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
| Genuine Gemini candidate function-call response | PASS |
| Genuine production Gemini function-call response | NOT TESTED |
| Exact $25 PayPal payout submission | PASS |
| PayPal item-level `SUCCESS` and exactly-once provider capture | PASS |
| Overall product acceptance | BLOCKED |

The remaining Gemini gate is operational: merge and deploy the exact verified
candidate, make the targeted model change, and receive a genuine function call
from the production workflow. Candidate compatibility itself is no longer
blocked by provider capacity.
