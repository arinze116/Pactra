# Pactra Integration Status

Audit date: 2026-11-07  
Production readiness response:

```json
{
  "status": "ready",
  "database": "ok",
  "sandbox_mode": true,
  "internal_sandbox_available": true,
  "ai_enabled": false,
  "ai_configured": false,
  "paypal_payouts_configured": false
}
```

## Summary

| Integration | Implemented | Configured | Reachable | Authenticated | Successfully tested | Production status |
|---|---|---|---|---|---|---|
| Internal sandbox ledger | Yes | Yes | Yes | Yes | Yes, end-to-end | PASS |
| PostgreSQL | Yes | Yes | Loopback only | Peer-auth service role | Yes, migrations/concurrency/invariants | PASS |
| Gemini | Yes | No | Not tested live | No production credential | Failure/fallback mocks only | BLOCKED / disabled |
| PayPal Sandbox Payouts | Yes | No | Not tested live in this audit | No active production credentials | Provider-independent mocks only | BLOCKED / disabled |
| Tailscale Funnel | Yes | Yes | Yes | HTTPS edge | Readiness 200 | PASS |
| Vercel frontend/API rewrite | Yes | Yes | Yes | Public HTTPS/session auth | Full public journey | PASS |
| Reconciliation worker | Yes | Yes | Local DB/API path | Service account | Lease/restart/standby tested | PASS; provider work disabled |

## Gemini

### Implementation

- Provider code: `backend/services/assistant.py::_run_gemini`.
- SDK: `google-genai` pinned in `requirements.txt`.
- Tool use: typed, allowlisted transaction creation arguments.
- Failure behaviour: provider failure is audited and disclosed before deterministic fallback.
- Server authority: all payment tool execution calls the same authenticated transaction/policy/ledger service used by manual payments.

### Actual state

- `AI_ENABLED=false`.
- No active configured Gemini API key was used.
- Production reports `ai_enabled=false` and `ai_configured=false`.
- Deterministic assistant fallback is functional and persisted.

### Verification

- Prompt injection and invalid tool-argument tests pass.
- Provider unavailable/failure audit and fallback tests pass.
- Conversation persistence, reload and idempotent retry pass in SQLite, PostgreSQL and production.
- A live Gemini response was not attempted and is not claimed as passing.

### Required before claiming live readiness

1. Supply an approved Gemini credential through the production secret mechanism.
2. Enable the provider without changing server-side policy enforcement.
3. Test successful tool calling, timeout, quota error, malformed response and fallback.
4. Confirm logs contain no prompt secrets, credentials or private cross-user data.

## PayPal Sandbox Payouts

### Implementation

- Client: `backend/paypal_client.py`.
- Orchestration: `backend/services/paypal.py`.
- State machine: `backend/services/transactions.py` provider attempts, unknown outcomes, failure and reconciliation.
- Manual/user status: `GET /api/integrations/paypal/status` and settings screens.
- Worker: `backend/worker.py` with PostgreSQL advisory lease.

The implementation uses stable rail request IDs, preserves reservations during unknown/processing states, captures Pactra’s ledger only after successful payout-item reconciliation, and never treats batch submission alone as completion.

### Actual state

- `PAYPAL_PAYOUTS_ENABLED=false` or required credentials/recipient absent.
- `paypal_payouts_configured=false` in production readiness.
- Settings correctly show unavailable/unconfigured.
- Worker is active but logs: `PayPal reconciliation is disabled; worker is standing by`.
- No payout was initiated during this audit.

### Provider-independent verification

- Token/submission/reconciliation mocks pass.
- Definite provider failure, timeout/unknown outcome, duplicate request and retry-safety paths pass.
- Stable provider identifiers and ledger capture rules are covered.
- Foreign reconcile/retry access is denied.

### Blocker

A prior report indicated a Sandbox item-level failure. The safety rules prohibit another payout until safe Sandbox business/recipient credentials are confirmed and explicit authorization is provided. Therefore live authentication, item success and real reconciliation remain BLOCKED.

## Internal sandbox

The internal rail is the fully operational demonstration path:

- All funds are simulated.
- Registration creates a $1,000 wallet.
- Policy checks, reservations, approvals, rejection, capture, reversal, reset, history and receipts are durable.
- Integer-cent, double-entry and concurrency invariants passed on PostgreSQL.
- Production post-smoke aggregates reported zero ledger/hold violations.

## Infrastructure integrations

### Vercel

- Production URL: `https://pactra-nine.vercel.app`.
- Deployment: `dpl_J1s82vJdXHaYinj1Y5k61VpS1wQU`.
- Alias points to the new production frontend.
- `/api/*` rewrite reaches the Funnel/API readiness endpoint.

### Tailscale Funnel

- Public upstream: `https://node1.taild90918.ts.net`.
- Target: `http://127.0.0.1:8010`.
- Readiness returned 200 after deployment.

### Nginx

Nginx configuration is valid on the VPS, but Pactra does not use it in the current path. It serves an unrelated Clavis host and was not modified.

## Decision

- Internal sandbox: PASS.
- Gemini live integration: BLOCKED/unconfigured.
- PayPal live Sandbox payout: BLOCKED/unconfigured.
- Integration-dependent submission readiness: PARTIAL.
