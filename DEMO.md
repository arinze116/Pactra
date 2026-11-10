# Pactra judge demo

Target length: 2 minutes 40 seconds. Use a fresh account so every balance and receipt is created during the walkthrough.

## Primary walkthrough

| Time | Action | Narration and proof |
| --- | --- | --- |
| 0:00-0:12 | Open Pactra and register | “Pactra lets AI request a payment, but policy, approval, and an append-only sandbox ledger decide what happens. No real money moves.” Show the `$1,000.00` test balance. |
| 0:12-0:35 | Ask the Assistant: `Pay Linear $49 for our monthly software subscription` | Show the governed tool call, completed receipt, policy checks, and the wallet reduction. If Gemini is unavailable, state that the deterministic parser handled the same authenticated transaction service. |
| 0:35-1:05 | Create a `$125.00` freelance payout | Show that it requires approval and reserves funds. Approve it once. If PayPal Sandbox is configured, select its provided test recipient and show the real batch/item status; do not call a pending batch “completed.” |
| 1:05-1:25 | Create the `$185.00` AWS cloud scenario | Show `TRANSACTION_LIMIT_EXCEEDED` and verify the posted balance did not change. |
| 1:25-1:48 | Edit the approval threshold and save | Show the immutable policy version increment, then create a request that follows the new version. |
| 1:48-2:18 | Open Transactions and a receipt | Filter the history, then show lifecycle events, ordered policy trace, execution attempt, and balanced ledger impact. |
| 2:18-2:35 | Reset the sandbox | Type `RESET`; show the restored `$1,000.00` current-generation balance and preserved historical receipts. |
| 2:35-2:40 | Close | “Pactra makes every AI-initiated payment accountable to policy, a human decision when needed, and a ledger, even when every fund is sandbox-only.” |

## Rehearsal data

- Auto-approved: Linear, `$49.00`, `software`.
- Approval: Ada Contractor, `$125.00`, `freelance`.
- Policy block: AWS, `$185.00`, `cloud`.
- Rejection: Contractor, `$120.00`, `freelance`.
- PayPal Sandbox smoke: use only the server-configured test-recipient shortcut.

## Honest fallback

- Gemini unavailable: show the provider-unavailable message and deterministic parser; never imply that the model handled the request.
- PayPal unavailable or item failed: show the actual provider state and released/retained reservation, then repeat the governed flow on `internal_sandbox`; never label it a PayPal success.
- Deployment unavailable: run the verified local build with an isolated database and say that the public host is unavailable. Do not claim a live deployment.

## Likely judge questions

- **Are these real funds?** No. Pactra’s wallet is an internal double-entry sandbox ledger. PayPal Sandbox is a separate test rail.
- **Can Gemini bypass policy?** No. It can call only allowlisted typed tools, and every payment reaches the same authenticated transaction service as the manual form.
- **What prevents duplicates?** User-scoped idempotency keys, stable PayPal request IDs, conditional state transitions, and one ledger capture per transaction.
- **What happens when PayPal times out?** Pactra retains the reservation, records an unknown outcome, and reconciles the same stable attempt instead of creating a second payout.
- **How is user data isolated?** Opaque server sessions and ownership filters scope wallets, policies, conversations, approvals, transactions, and receipts to the authenticated user.
