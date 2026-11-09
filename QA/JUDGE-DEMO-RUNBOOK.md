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
`503`/timeout. The separately authorised PayPal Sandbox payout completed with
item-level `SUCCESS`; its one-time approval must not be replayed.

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

## PayPal Sandbox acceptance

The prepared scenario is transaction
`bfe1e158-863b-4ddf-93a0-e31146e7cbcb`, exactly `$25.00 USD`, to the configured
Personal Sandbox recipient completed after separate explicit authorisation.
Show:

- the masked recipient in the UI;
- the unmasked persisted recipient only in restricted operator evidence;
- `completed` and provider item status `SUCCESS`;
- one completed attempt with unchanged masked batch/item identifiers;
- one captured $25 reservation and one balanced capture journal;
- final posted/reserved/available balances of `$975 / $0 / $975`;
- receipt persistence and the approval, submission, reconciliation, ledger and
  completion events;
- one provider payout POST and no duplicate attempt, payout or journal.

Do not approve, retry or create another payout for this transaction. A future
read-only provider refresh must use the persisted batch ID and must never
create a replacement payout for an ambiguous result.

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
are verified. PayPal item-level success and exactly-once capture are verified.
Genuine Gemini function calling remains blocked by the documented provider
`503`/timeout condition.
