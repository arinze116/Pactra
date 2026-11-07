# Pactra Human Blockers

Only the following human actions remain. Do not place secret values in chat,
source control, logs, screenshots or QA reports.

## Gemini live acceptance

1. Provide an approved Gemini API key with access to the exact PRD model
   `gemini-3.8-flash` through the existing server-side secret mechanism.
2. Authorize enabling `AI_ENABLED=true` on the deployed backend.
3. After an approved deployment, run the redacted live function-calling and
   failure/fallback acceptance sequence from `FINAL-PRD-GAP-REVIEW.md`.

This unlocks AI-006 / INT-005. A deterministic fallback or mocked provider
response cannot close the blocker.

## PayPal Sandbox live acceptance

1. Confirm the Sandbox business account has Payouts capability.
2. Install the Sandbox app client ID and secret using the existing server-side
   secret mechanism.
3. Confirm a distinct valid Sandbox recipient account/email.
4. Explicitly authorize one specific no-real-money Sandbox payout test after
   the values and `api-m.sandbox.paypal.com` endpoint are verified.
5. After an approved deployment, reconcile the same stable attempt until the
   payout item reaches a real terminal state.

This unlocks PAY-010 / INT-002 / INT-003 and the PayPal PLT-006 guided step.
Only item-level `SUCCESS` plus exactly-once Pactra ledger capture closes the
success criterion. If Payouts capability is absent, the account owner must
resolve it with PayPal; live mode and workaround rails are prohibited.

## Deployment approval

The release candidate is not deployed. Separate explicit approval is needed
before backing up production, applying migration `20261107_0005`, restarting
Pactra services or updating Vercel.
