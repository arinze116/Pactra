# Pactra External and Human Blockers

Updated: 2026-11-09, Africa/Lagos

The release is deployed and publicly verified. The remaining blockers do not
prevent the application from operating, but they prevent full provider and
product acceptance.

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

## 2. Exact PayPal Sandbox payout approval — BLOCKED

The prepared transaction is:

- transaction: `bfe1e158-863b-4ddf-93a0-e31146e7cbcb`;
- amount: exactly `$25.00 USD`;
- recipient: `sb-4fqlt53808662@personal.example.com`;
- isolated account: `pactra-paypal-approval-20261109160306@example.com`;
- rail: `paypal_sandbox_payouts`;
- policy version: `2`, approval threshold `$1.00`;
- state: `pending_approval`, active reservation `$25.00`;
- posted / reserved / available: `$1,000.00` / `$25.00` / `$975.00`;
- attempts, provider IDs and ledger journals: zero / none / zero.

Separate explicit user authorisation is required for this exact transaction,
amount, currency and recipient. Until then, do not call the approval endpoint,
click **Approve**, invoke the worker submission path or create a replacement
payout.

## 3. PayPal item success and reconciliation — NOT TESTED

OAuth authentication succeeded and the token includes Payouts scope, but no
payout was submitted. The sender email cannot be independently read through
the client-credentials API and remains unverified metadata. Full acceptance
requires the separately authorised transaction to reach item-level `SUCCESS`,
then exactly one internal capture, receipt and audit trail.

Anything other than item-level `SUCCESS` remains **BLOCKED** or **FAIL**. HTTP
200, OAuth success or batch acceptance is not payout success.
