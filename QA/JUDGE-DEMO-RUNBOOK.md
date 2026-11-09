# Pactra Judge Demo Runbook

Updated: 2026-11-09, Africa/Lagos

This runbook is for the deployed Sandbox product. Never describe a fixture,
deterministic fallback, OAuth response or PayPal batch acceptance as live
provider success.

## Pre-demo gate

Record without exposing credentials:

- `/opt/pactra/current/.release-sha` and the production Vercel deployment ID;
- database revision `20261107_0005`;
- exact-SHA CI URL;
- API and worker active state plus the worker lease log;
- `/api/health` and `/api/ready` responses;
- a fresh synthetic judge account;
- browser console/network state.

Current provider limitation: Gemini is configured but is using the tested
fallback because genuine function-call acceptance is blocked by provider
`503`/timeout. The prepared PayPal payout must not be approved without the
separate transaction-specific authorisation.

## Verified internal Sandbox demonstration

1. Register and show the initial USD 1,000 Sandbox wallet.
2. Edit and save a policy. Show the immutable version and approval threshold.
3. Create a USD 49 software payment. Show policy checks, completed receipt,
   balanced internal ledger entries and audit history.
4. Create an approval-required contractor request. Inspect the approval
   context, then reject it with a reason. Show that no PayPal attempt exists.
5. Run the USD 185 policy-block scenario. Show the persisted block reason,
   zero posted entries and no provider request.
6. Run the insufficient-funds scenario and show that no invalid debit or
   reservation was created.
7. Open the assistant and explain the current evidence boundary. The tested
   deterministic fallback uses the same policy/payment service and creates at
   most one governed internal payment; it is not a genuine Gemini tool call.
8. Open transactions, receipts and audit history. Reload the pages to prove
   server persistence.
9. Show sign-out/session enforcement and tenant isolation using two synthetic
   accounts.
10. Show the desktop, tablet and mobile layouts, keyboard focus, semantic
    landmarks and Axe/Lighthouse evidence.

## PayPal Sandbox checkpoint

The prepared scenario is transaction
`bfe1e158-863b-4ddf-93a0-e31146e7cbcb`, exactly `$25.00 USD`, to the configured
Personal Sandbox recipient. Show:

- the masked recipient in the UI;
- the unmasked persisted recipient only in restricted operator evidence;
- `pending_approval`;
- one active $25 reservation;
- zero attempts, provider IDs and ledger captures.

Stop there unless the user separately authorises that exact payout. If
authorised, approve once and let only the worker submit. Continue the demo only
after reconciliation confirms item-level `SUCCESS`; then show exactly one
capture and unchanged identifiers after reload.

## Failure demonstrations

- Use controlled tests, not production key manipulation, for Gemini errors.
  Show bounded failure, deterministic fallback, no duplicate transaction and
  no policy bypass.
- Use provider doubles for PayPal timeout, unknown, terminal failure, return,
  reversal, repeated reconciliation and duplicate delivery. Label these as
  state-machine tests.
- Never release a reservation after a timeout or batch acceptance. Never
  create a replacement payout for an ambiguous outcome.

## Evidence to retain

- public URL, release SHA, Vercel deployment, migration and CI run;
- synthetic account, transaction and policy identifiers;
- receipts, ledger totals and audit-event identifiers;
- responsive screenshots, Axe and Lighthouse reports;
- redacted provider timestamps and identifiers if provider acceptance later
  succeeds;
- API/worker logs and confirmation that no unrelated VPS service changed.

## Honest closing statement

The deployed application, deterministic financial controls and public flows
are verified. Genuine Gemini function calling and PayPal item-level success
remain blocked until their stated external/approval conditions are satisfied.
