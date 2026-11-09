# Pactra External and Human Blockers

Updated: 2026-11-09, Africa/Lagos

The existing release is deployed and publicly verified. PayPal Sandbox
acceptance is complete. Gemini model compatibility is now resolved in an
isolated environment; only the normal merge, deployment and production
acceptance sequence remains.

## 1. Gemini production acceptance — NOT TESTED

- Production is configured for `gemini-3.8-flash` and the configured key is
  present.
- The account exposes stable `gemini-3.5-flash-lite` with function calling.
- Two genuine calls, two complete tool-result round trips and the full isolated
  Pactra workflow passed after correcting the function-response role and
  payout-recipient schema.
- Timeout, 503, malformed response and deterministic fallback regressions pass.
- The candidate branch has not yet completed GitHub CI, merge, immutable
  release staging or the targeted production model switch.

Required action: follow the repository's normal PR/CI process, deploy the exact
merged SHA, back up the environment, change only `GEMINI_MODEL` to
`gemini-3.5-flash-lite`, restart only the API, and run one genuine non-PayPal
production acceptance call. No new credential, billing change or external
provider intervention is currently required.

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
