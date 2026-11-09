# Pactra Observability Implementation

Date: 2026-11-09

Status: **repository implementation complete; production activation requires a separate release**

## Implemented in this branch

### Health semantics

- `GET /api/health` is process liveness. It performs no provider check and
  returns a small `status=ok` payload.
- `GET /api/ready` is application readiness. It performs a small database
  `SELECT 1` and reports only safe capability booleans. The public monitor
  applies a 10-second request timeout; a separate application-level database
  connection deadline has not been added in this branch.
- Optional Gemini or PayPal unavailability does not make liveness fail.
- Neither endpoint exposes credentials, hosts, database names, recipient data,
  provider payloads, or stack traces.

### Structured operational events

`backend/observability.py` emits one-line JSON with timestamp, severity,
service, environment, event, outcome, and explicitly supplied safe fields.

Request IDs accept only 8-128 characters from `[A-Za-z0-9._~-]`; invalid or
oversized values are replaced with a server UUID. HTTP operations use FastAPI
route templates such as `/api/transactions/{transaction_id}`. Unmatched paths
use the constant `unmatched_route`, preventing user-controlled identifiers
from becoming metric or log labels.

Sensitive field names are rejected when they contain authorization, cookie,
credential, password, prompt, recipient, request/response body, secret,
session, or token fragments. Values are scalar-only and bounded.

Events cover:

- API startup and completed requests;
- stable 5xx error classification without public exception details;
- Gemini fallback classification, call count, provider status, and latency;
- worker lease acquisition/standby;
- processed worker batches and reconciliation/scan failure classes.

The frontend sends a fresh `X-Request-ID` and uses a 15-second default timeout.
Assistant calls allow 35 seconds because the backend can make two bounded
12-second Gemini attempts plus tool work. API errors retain the returned
request reference for support.

### Financial invariant diagnostics

Run:

```bash
python -m scripts.check_financial_invariants --json
```

The command enables PostgreSQL `SET TRANSACTION READ ONLY` or SQLite
`PRAGMA query_only=ON`, rolls back, and never repairs data. It checks:

1. balanced two-entry USD journals;
2. at-most-once capture and reversal journals;
3. tenant and amount linkage;
4. reservation ownership and state;
5. non-negative derived wallet balances;
6. unique stable/provider identifiers;
7. PayPal item-level success authority;
8. preservation of unknown outcomes and reservations;
9. attempt/transaction state linkage;
10. allowed audited state transitions.

The 2026-11-09 read-only production run passed all checks with zero
violations. A failure is diagnostic evidence and must never trigger an
automatic ledger update.

### Backup verification

`python -m scripts.verify_backup` verifies a regular, non-symlink file's size,
age, SHA-256, optional required checksum, and `pg_restore --list` readability.
It does not restore, delete, rename, or modify the archive.

### Public monitor

`python -m scripts.check_public_health` checks the public HTML shell,
`/api/health`, and `/api/ready` with bounded timeouts and a latency budget.
It emits route, status, latency, and classification only; it does not retain
page or API bodies.

`.github/workflows/production-health.yml` schedules this check every five
minutes and supports manual dispatch. GitHub marks a failed run, but no paging
or notification destination beyond repository defaults is configured.

The workflow is not active on the accepted production baseline. It becomes
scheduled only after a reviewed merge to the default branch.

## Verification

- Diagnostic unit tests cover clean and deliberately inconsistent ledgers,
  non-mutation, route-template logging, sensitive-field rejection, backup
  checksum/archive failure, symlink rejection, health payloads, latency, and
  unsafe monitor origins.
- Production public sample: homepage 200, health 200, readiness 200.
- Production financial diagnostic: 10/10 checks passed, zero violations.
- Accepted backup: 173,373 bytes, expected SHA-256 matched, archive list valid.

## Not implemented

- Paging/on-call integration.
- Centralized log or error aggregation.
- Metrics storage, dashboards, SLOs, or alert history.
- Scheduled worker, ledger, backup, provider, database, or host-resource
  diagnostics.
- Real-user monitoring.

These remain in `QA/OBSERVABILITY-BACKLOG.md`. No monitoring system should
export prompts, recipient data, transaction bodies, cookies, tokens, keys, or
raw provider responses.
