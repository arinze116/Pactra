# Pactra Human Blockers

Only the following human actions remain. Do not place secret values in chat,
source control, logs, screenshots or QA reports.

## Gemini live acceptance

A secure local project key reached `gemini-3.8-flash`, but generation returned
`429 RESOURCE_EXHAUSTED`. Production remains disabled and unconfigured.

1. Restore sufficient quota/entitlement for the exact PRD model
   `gemini-3.8-flash`, or securely install another approved project key with
   that entitlement. Do not send the key in chat.
2. Authorize enabling `AI_ENABLED=true` on the deployed backend only after the
   isolated five-tool acceptance succeeds.
3. After an approved deployment, repeat the redacted live function-calling and
   failure/fallback acceptance sequence from `FINAL-PRD-GAP-REVIEW.md`.

This unlocks AI-006 / INT-005. A deterministic fallback or mocked provider
response cannot close the blocker.

## PayPal Sandbox live acceptance

1. Confirm the Sandbox business account has Payouts capability.
2. Install the Sandbox app client ID and secret using the existing server-side
   secret mechanism.
3. Confirm a distinct valid Sandbox recipient account/email.
4. Explicitly authorize one USD 25.00 no-real-money Sandbox payout through the
   guided Pactra workflow after the values and
   `api-m.sandbox.paypal.com` endpoint are verified.
5. After an approved deployment, reconcile the same stable attempt until the
   payout item reaches a real terminal state.

This unlocks PAY-010 / INT-002 / INT-003 and the PayPal PLT-006 guided step.
Only item-level `SUCCESS` plus exactly-once Pactra ledger capture closes the
success criterion. If Payouts capability is absent, the account owner must
resolve it with PayPal; live mode and workaround rails are prohibited.

## Deployment approval

The release candidate is not deployed. Separate explicit approval is needed
before backing up production, applying migration `20261107_0005`, restarting
Pactra services or updating Vercel. Do not approve deployment until Gemini and
PayPal acceptance plus the PayPal guided scenario pass.
