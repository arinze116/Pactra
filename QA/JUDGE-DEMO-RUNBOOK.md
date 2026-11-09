# Pactra Judge Demo Runbook

This runbook is for the deployed, approved release only. Do not describe a
fixture, deterministic fallback or batch-creation response as live provider
success.

## Pre-demo gate

Record these values before opening the product:

- deployed application SHA and Vercel deployment ID;
- backend release path and database migration revision;
- exact-SHA successful CI run URL;
- `/api/ready` result showing the intended Gemini model and PayPal Sandbox
  configuration without exposing credentials;
- a fresh judge account identifier, redacted in screenshots;
- confirmation that the browser console and network panel are clear.

Stop the live-provider portion if Gemini is falling back, PayPal is not
configured, or a previous payout remains unresolved.

## Primary demonstration

1. Register a fresh account and show the initial USD 1,000 sandbox wallet.
2. Open the policy editor. Show the active policy version, allowed categories,
   vendor controls and approval threshold. Save one small change and confirm
   that the server returns the persisted version.
3. Open the assistant. Enter a natural-language request such as “Pay Linear
   $49 for our monthly software subscription.”
4. Prove the request used live Gemini function calling: capture the persisted
   user, assistant and tool messages plus `assistant.message_sent` and
   `assistant.tool_called`. The resulting transaction must use the same
   governed payment service as the manual form.
5. Open the receipt. Show the policy version/checks, actor and lifecycle audit
   events, balanced ledger entries and internal execution reference.
6. Start the USD 125 Ada Contractor guided scenario. Show the authoritative
   preview, submit it, open Approvals, inspect requester/policy/balance context,
   and approve it. Confirm that the receipt becomes completed.
7. Run the USD 185 AWS scenario. Confirm a persisted policy block and no ledger
   debit or reservation.
8. Run the rejection scenario. Reject the pending request with an audit reason
   and confirm the persisted rejected receipt.
9. Run the guided insufficient-funds test. Confirm
   `INSUFFICIENT_FUNDS`, no invalid debit and no active reservation.
10. Open Settings → PayPal Sandbox. Show that the environment is Sandbox, the
    capability is Payouts and the configured recipient is a test account.
11. Create the guided USD 25.00 PayPal Sandbox payout. Show the Pactra
    reservation first. Batch submission alone is not completion.
12. Reconcile the same batch/item until PayPal reports item-level `SUCCESS`.
    Show the actual redacted batch and item references, exactly one ledger
    capture, released reservation, persisted reconciliation and the same status
    after a page reload.
13. Return to the overview. Confirm all six persisted scenarios are complete.
14. Type `RESET` on the wallet page. Confirm a new sandbox generation starts,
    pending internal requests are cancelled, immutable receipts remain, and
    the judge can repeat the walkthrough.

## Failure demonstrations

- Disable or isolate Gemini only in an approved non-production test context.
  Confirm a bounded error, `assistant.error`, `assistant.fallback_used`, no
  duplicate transaction and no policy bypass.
- For PayPal, use controlled test doubles for timeout, unknown, terminal
  failure, repeated reconciliation and duplicate retry behaviour. Label these
  as state-machine tests. Do not call them provider acceptance.
- Never release a PayPal reservation after only a timeout or batch acceptance.
  Only actual item-level `SUCCESS` may use the successful capture path.

## Evidence to retain

- timestamps, routes and redacted judge account identifier;
- transaction, policy version and audit-event identifiers;
- redacted Gemini function-call/tool-message evidence;
- redacted PayPal batch/item references and provider timestamps;
- before/after wallet, reservation and ledger state;
- browser console/network screenshots and backend/worker log excerpts;
- public URL, deployed SHA, migration revision and CI run URL.

## Honest fallback if providers remain blocked

Demonstrate the complete internal sandbox policy, approval, ledger, receipt,
reset and accessibility flows. Show the tested Gemini fallback and PayPal state
machine separately. State plainly that live Gemini and/or PayPal acceptance is
blocked. Do not mark the provider checklist row complete and do not use the
word “live” for fixtures or fallback output.
