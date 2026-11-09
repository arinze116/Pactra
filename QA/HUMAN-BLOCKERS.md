# Pactra External and Human Blockers

Updated: 2026-11-09, Africa/Lagos

The verified Gemini release is deployed and publicly accepted. PayPal Sandbox
acceptance is also complete. There is no active external or human release
blocker.

## 1. Gemini production acceptance — RESOLVED / PASS

- Production is configured for `gemini-3.5-flash-lite`; the configured key is
  present and matches the project-local key without either value being shown.
- The account exposes stable `gemini-3.5-flash-lite` with function calling.
- Two genuine calls, two complete tool-result round trips and the full isolated
  Pactra workflow passed after correcting the function-response role and
  payout-recipient schema.
- Timeout, 503, malformed response and deterministic fallback regressions pass.
- PR #14 merged as `63f25839a6b645a8ca404846ecd82d16c1994b7c`.
  Exact-main CI run `42674909231` passed all four jobs.
- Immutable release `/opt/pactra/releases/63f2583` is active. Only
  `GEMINI_MODEL` changed in production configuration.
- The API restarted on the new release while the PayPal worker remained on
  PID `785136` with its original start time and advisory lease.
- A live public request returned one genuine `get_wallet_summary` function
  call. Audit evidence recorded `gemini-3.5-flash-lite`, two provider calls,
  1,391 ms provider latency, finish reason `STOP`, one tool call, no fallback
  or provider error, and zero created transactions.

No new credential, billing change or provider intervention is required.

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
