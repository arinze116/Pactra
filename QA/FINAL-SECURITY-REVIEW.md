# Pactra Final Security Review

Review date: 2026-11-09

Scope: repository code, isolated tests, dependency audits, retained production
controls, and read-only production verification. No destructive production
testing or provider request was performed.

Status: **PASS — no unresolved known P0 or P1 finding**

## Findings and evidence

| Area | Result | Evidence |
|---|---|---|
| Passwords | PASS | Argon2id; minimum/invalid/replay regressions; hashes never returned |
| Sessions | PASS | Opaque hashed tokens, idle/absolute expiry, revocation, Secure/HttpOnly/SameSite production cookies |
| CSRF/CORS | PASS | synchronizer token and origin enforcement; exact configured origins |
| Brute force/rate limits | PASS | database-backed atomic login/registration limits; PostgreSQL concurrency tests |
| Tenant isolation | PASS | user-scoped wallet, policy, payment, approval, receipt, audit, conversation, retry, reversal, and reconciliation paths |
| Input validation | PASS | strict Pydantic models; bounded amounts/text/pagination; new type/rail compatibility checks |
| AI governance | PASS | declared tools only, strict arguments, same transaction service, policy/approval after extraction, deterministic fallback |
| Payment safety | PASS | stable idempotency, row locks, worker-only PayPal authority, unknown reservation preservation, item-level success capture |
| Ledger integrity | PASS | two-entry balanced journals, immutable PostgreSQL triggers, exactly-once capture/compensation tests and diagnostics |
| Sensitive logging | PASS | bounded request IDs, route templates, safe scalar fields, forbidden sensitive field names, sanitized error classes |
| SQL injection | PASS | parameterized SQLAlchemy/SQLModel queries; no user-concatenated SQL path found |
| XSS | PASS | React escaping; no `dangerouslySetInnerHTML`; browser journeys and CSP |
| SSRF | PASS | no user-controlled server fetch URL; monitor requires an exact credential-free HTTPS origin |
| Secrets | PASS | no secret value added; credentials remain outside source; example values are non-secret placeholders |
| Security headers | PASS | restrictive frontend/API CSP, HSTS in production, nosniff, frame denial, referrer and permissions policies |
| Dependencies | PASS | `pip check`, `pip-audit`, production npm audit, and full npm audit passed |

## Fixes completed

### P1 — raw operation paths in future structured logs

The initial branch implementation logged `request.url.path`, which could have
included transaction or conversation UUIDs and created high-cardinality log
labels. It now resolves the FastAPI route template and uses
`unmatched_route` when no route exists. Regression coverage proves the UUID is
not emitted.

### P1 — ambiguous payment type/rail combinations

The API now rejects:

- non-payout requests using PayPal Sandbox;
- internal payouts without a recipient email;
- sandbox transfers using a provider rail.

The backend remains authoritative even if a client bypasses frontend fields.

### P2 — support correlation and bounded failures

Frontend requests now carry validated correlation IDs and bounded timeouts.
Public errors expose only a stable code, friendly message, and request
reference. Provider errors are classified without logging prompts, recipient
data, credentials, request bodies, or raw responses.

## AI and provider boundaries

- Gemini cannot approve a payment, change policy, select another tenant,
  submit PayPal, or write ledger entries directly.
- Missing or malformed tool data is rejected before application execution.
- A provider error is recorded even when deterministic fallback succeeds.
- PayPal batch acknowledgement is not success; item-level `SUCCESS` remains
  authoritative.
- Unknown payout outcomes remain reserved and are reconciled using stable
  identifiers. They are never blindly resubmitted.

## Production read-only result

The new invariant checker ran in a read-only transaction against production
and reported zero violations across 10 P0/P1 checks. The accepted PayPal
record was not submitted, reconciled, or changed.

## Residual risks

### P2

- Manual screen-reader testing and external DAST were not performed.
- CSP permits inline styles for the current frontend styling model; scripts
  remain self-only.
- No centralized error aggregation or security-anomaly alerting exists.
- The health workflow has no paging destination until one is separately
  approved and configured.

### P3

- The requesting owner can also approve; independent approver roles are not
  implemented.
- PayPal reconciliation is polling-based; no inbound webhook surface exists.

## Safety statement

No production data, configuration, service, infrastructure, Gemini account,
PayPal record, wallet, journal, or provider operation was changed by this
review.
