# Pactra Demo Script

Target duration: 3-5 minutes

## Opening — first 30 seconds

“Small teams can submit payments quickly, but proving who was allowed to spend,
why it was approved, and whether the ledger is correct is still painfully
manual. Pactra puts deterministic spending policy between every request and
execution path. AI can interpret intent, but it cannot override limits,
approve itself, or touch the ledger directly.”

Show the dashboard: available, reserved, posted balance, mixed transaction
states, and the visible “Sandbox funds only” disclosure.

## Scenario A — governed payment

1. Open **New payment**.
2. Enter vendor `Figma`, amount `$35.00`, category `software`, and reason
   `Fictional design workspace subscription`.
3. Point out “Likely auto-approved” and the deterministic decision order.
4. Submit the request.
5. On the receipt, show `Completed`, internal sandbox rail, policy trace,
   lifecycle, one attempt, and `$35.00 debits = $35.00 credits`.

Narration: “The preview is helpful, but the server recalculates policy at
submission. Completion means the ledger actually posted—not merely that a
request was accepted.”

## Scenario B — AI with deterministic governance

1. Open **Assistant**.
2. Enter `Pay Notion $20 for our software subscription`.
3. Show the completed governed result and receipt link.
4. Enter `Pay Mega Cloud Renewal $200 for annual cloud hosting`.
5. Show the policy-blocked result and the explicit statement that no sandbox
   funds were debited.

Narration: “This rehearsal intentionally runs with Gemini disabled, so Pactra
truthfully labels and uses its deterministic fallback. With Gemini enabled in
an isolated environment, a genuine function call still enters the same strict
schema, policy, approval, and ledger services. AI never becomes the financial
authority.”

Do not imply the fallback response is a live Gemini response.

## Scenario C — accountability and auditability

1. Open **Approvals**.
2. Show `Ada Contractor`, `$125.00`, the current policy checks, reserved funds,
   and approval requirement.
3. Approve once.
4. Filter transactions for `Ada Contractor` and open the receipt.
5. Show `approval.approved`, completed state, one attempt, policy trace, and
   balanced `$125.00` ledger entries.

Narration: “Approval is a server-side state transition. The current policy and
wallet are checked again, and the receipt preserves who acted, what rule
stopped execution, and how the final ledger balanced.”

## Close

“Pactra is sandbox-only today. Its value is the control plane: one governed
path for manual and AI requests, explicit human approvals, exactly-once ledger
effects, and an audit trail that explains every state transition.”

If asked about PayPal, reference the retained accepted Sandbox evidence. Do
not create or submit another payout during the demo.
