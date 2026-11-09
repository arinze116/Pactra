# Pactra Integration Status

Updated: 2026-11-09

| Integration | Implemented | Production configured | Genuine success evidence | Status |
|---|---|---|---|---|
| Internal Pactra sandbox | Yes | Yes | Persisted ledger journeys | PASS |
| Gemini `gemini-3.8-flash` | Yes | Yes | Latest live generation returned `429 RESOURCE_EXHAUSTED`; no tool call | BLOCKED |
| PayPal Sandbox OAuth | Yes | Yes | Prior OAuth succeeded | PASS for authentication only |
| PayPal Sandbox Payouts | Yes | Yes | Prior payout ended `DENIED`/`FAILED`; no item `SUCCESS` | BLOCKED |
| PayPal reconciliation | Yes | Yes | Deterministic state tests only; no successful real item | BLOCKED for live acceptance |

## Gemini

The active assistant uses typed tools, bounded requests, tenant-owned services,
and deterministic fallback. Fallback is labelled and audited. It is not live
Gemini acceptance. The exact model remains `gemini-3.8-flash`.

## PayPal

The host is fixed to the official Sandbox API. Credentials and recipient are
server-side. The status endpoint reports only configured state and a masked
recipient. The worker is the sole submission authority.

OAuth does not prove Payouts capability. Batch acceptance does not prove
success. Only an individual payout item at `SUCCESS`, followed by exactly one
Pactra capture, closes the gate.

No provider call was made during this engineering mandate.
