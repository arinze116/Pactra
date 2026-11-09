# Pactra External and Human Blockers

Updated: 2026-11-09, Africa/Lagos

The release is deployed and publicly verified. PayPal Sandbox acceptance is
complete. The remaining blocker is the external Gemini provider result; it
does not prevent the application from operating, but it prevents full product
acceptance.

## 1. Gemini function-call acceptance — BLOCKED

- Production is configured for `gemini-3.8-flash` and the configured key is
  present.
- The old production key was rejected with `400 INVALID_ARGUMENT` /
  `API_KEY_INVALID` and was replaced by the validated project key after a
  configuration backup.
- Model lookup succeeded with the replacement key.
- The genuine Pactra function-calling workflow did not return a function call:
  one request received provider `503`; bounded requests then timed out after
  approximately 38 seconds.
- Pactra used its deterministic fallback safely and created the governed
  internal transaction exactly once.

Required external change: Gemini must provide enough capacity for one bounded
Pactra request to return a genuine function-call response. Do not rotate keys,
change models silently, or keep retrying the unavailable provider.

## 2. Exact PayPal Sandbox payout approval — RESOLVED / PASS

The prepared transaction is:

- transaction: `bfe1e158-863b-4ddf-93a0-e31146e7cbcb`;
- amount: exactly `$25.00 USD`;
- recipient: `sb-4fqlt53808662@personal.example.com`;
- isolated account: `pactra-paypal-approval-20261109160306@example.com`;
- rail: `paypal_sandbox_payouts`;
- policy version: `2`, approval threshold `$1.00`;
- authorised preflight state: `pending_approval`, active reservation `$25.00`;
- authorised preflight posted / reserved / available:
  `$1,000.00` / `$25.00` / `$975.00`;
- authorised preflight attempts, provider IDs and ledger journals:
  zero / none / zero.

The user separately authorised this exact transaction. Pactra called the
approval endpoint once at `2026-11-09 18:23:44 WAT`, recorded one approval
action and created one attempt. This approval is consumed. Do not approve,
retry or create a replacement payout for this transaction.

## 3. PayPal item success and reconciliation — PASS

The worker made one payout POST, persisted batch `ZMQQ…3Q8U`, then reconciled
that same identifier. PayPal returned exactly one item, `E5KZ…KTYA`, with
item-level `SUCCESS`. A bounded independent lookup confirmed the persisted
batch/item IDs, stable sender IDs, `$25.00 USD` amount and authorised recipient.

Pactra completed one attempt, captured the reservation once, posted one
balanced `payment_capture` journal, produced a persistent receipt and nine
audit/lifecycle events, and left final posted/reserved/available balances at
`$975.00 / $0.00 / $975.00`. There is no duplicate payout, provider identifier,
journal entry, reversal or unresolved reservation. The sender email remains
unavailable through the client-credentials API, but this metadata limitation
does not negate the verified recipient item success.
