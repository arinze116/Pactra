# Pactra Worker-Only PayPal Implementation Report

Updated: 2026-11-09

Branch: `codex/paypal-worker-single-authority`

Production baseline: `0e3e905` at migration `20261107_0004`

## Implemented

- Removed direct PayPal Orders and payout execution from the API and deprecated
  compatibility agent.
- Made `backend/services/paypal.py` plus `backend/worker.py` the sole payout
  submission path.
- Added PostgreSQL row locking, conditional attempt claims, and a process-wide
  advisory worker lease.
- Persisted stable sender batch, request, and item identifiers before network
  execution.
- Split provider submission from item-level reconciliation.
- Classified transport failures, HTTP 408/425/429/5xx, and malformed accepted
  responses as ambiguous without releasing reserved funds.
- Added explicit same-attempt recovery for ambiguous submissions without a
  stored batch ID. Automatic scans never perform this replay.
- Preserved item-level `SUCCESS` as the only capture condition.
- Preserved exactly-once terminal release and return/reversal/refund
  compensation.
- Added approval threshold, expired/revoked session, worker crash, duplicate
  delivery, concurrency, unknown outcome, and recovery regressions.
- Updated the receipt to distinguish **Refresh provider** from
  **Recover submission** with an explicit stable-ID confirmation.
- Masked the globally configured Sandbox recipient in the authenticated status
  endpoint.
- Added public and application skip links plus a keyboard-only browser journey.

## Documentation

- Reconstructed `README.md` around actual routes, architecture, configuration,
  testing, deployment, recovery, and limitations.
- Added `CONTRIBUTING.md`, `CHANGELOG.md`, and ADR 0001.
- Added `QA/README-PRODUCT-VERIFICATION.md`.
- Corrected rollback documentation: release `0e3e905` cannot start its Alembic
  runner against a database stamped at `20261107_0005`.

## Verification

| Area | Result |
|---|---|
| SQLite | 118 passed, 10 PostgreSQL-only skipped |
| PostgreSQL | 128 passed |
| Atomic claim | Concurrent workers produced one claim winner |
| Frontend lint/build | PASS |
| Playwright/WCAG | 15 journeys passed; Axe passed across 14 configured surfaces |
| Dependency audits | No known Python or npm vulnerabilities |
| Migration drill | Failure rollback, recovery, concurrent reader, downgrade, old-release compatibility verified |

The tests use fakes for provider terminal states. They prove local state-machine
and ledger behaviour, not external provider success.

## Security considerations

- API requests cannot initiate provider network I/O.
- Unknown provider outcomes remain financially reserved.
- Provider identifiers are stable and tenant-owned transaction reads remain
  owner-scoped.
- The PayPal base URL remains Sandbox-only.
- Configuration status never returns credentials and now masks the recipient.
- No secret, token, or raw provider payload was added to Git or documentation.

## Migration impact

No new migration was introduced by the worker-only correction. Candidate
migration `20261107_0005` remains the additive shared rate-limit table. Its
downgrade deletes limiter buckets and requires the stopped-service procedure
documented in `QA/DEPLOYMENT-AND-ROLLBACK.md`.

## Rollback

Before deployment, rollback is simply reverting the feature PR. After an
authorized deployment at schema `0005`, stop only Pactra services, run the
candidate Alembic downgrade to `0004`, verify the limiter table is absent,
switch the release symlink to `0e3e905`, then start API followed by worker.

Production was not changed and no payout was submitted during this mandate.
