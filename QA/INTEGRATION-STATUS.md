# Pactra Integration Status

Updated: 2026-11-09

| Integration | Implemented | Production configured | Genuine success evidence | Status |
|---|---|---|---|---|
| Internal Pactra sandbox | Yes | Yes | Persisted ledger journeys | PASS |
| Gemini `gemini-3.5-flash-lite` | Yes | Yes | Candidate probes, full isolated workflow and live production `get_wallet_summary` function call | PASS |
| PayPal Sandbox OAuth | Yes | Yes | Authenticated Sandbox OAuth with Payouts scope | PASS |
| PayPal Sandbox Payouts | Yes | Yes | Authorised $25 item reached item-level `SUCCESS` | PASS |
| PayPal reconciliation | Yes | Yes | Persisted identifiers reconciled once; one ledger capture | PASS |

## Gemini

The assistant uses typed tools, bounded requests, tenant-owned services and a
deterministic fallback. The configured account exposes the tested stable Flash
models. `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.1-flash-lite` and
`gemini-3.5-flash` failed bounded compatibility requests with HTTP 503 or
timeouts. `gemini-3.5-flash-lite` returned genuine, schema-valid function calls
and passed full isolated Pactra workflow acceptance.

The integration also corrected two application defects: function responses now
use the API-supported `user` role, and the payment declaration identifies the
recipient as a payout-only email. Deterministic fallback remains labelled and
audited. Production now runs `gemini-3.5-flash-lite` from release `63f2583`.
The live public acceptance request produced one genuine `get_wallet_summary`
call, no transaction, no fallback and one `assistant.provider_completed`
audit event with finish reason `STOP`.

## PayPal

The host is fixed to the official Sandbox API. Credentials and recipient are
server-side. The status endpoint reports only configured state and a masked
recipient. The worker is the sole submission authority.

OAuth does not prove Payouts capability. Batch acceptance does not prove
success. Only an individual payout item at `SUCCESS`, followed by exactly one
Pactra capture, closes the gate.

No PayPal provider call was made during the Gemini rollout. The previously
authorised payout remains terminal `completed` with one attempt and one
capture journal.
