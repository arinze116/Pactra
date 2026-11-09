# Pactra Payment Operations and Reconciliation

Accepted: 2026-11-09

Environment: PayPal Sandbox only

Canonical baseline: `QA/ACCEPTED-PRODUCTION-BASELINE.md`

Execution evidence: `QA/PAYPAL-SANDBOX-EXECUTION-RUNBOOK.md`

No PayPal request, approval, reconciliation, retry or financial transaction
was performed while creating this operations document.

Pre-demo review on 2026-11-09 added a read-only invariant diagnostic covering
balanced journals, capture/reservation state, provider identifier uniqueness,
item-level success authority, unknown outcomes and lifecycle linkage. Its
production read-only run passed all 10 checks with zero violations. No PayPal
request or financial mutation was performed. See
`QA/OBSERVABILITY-IMPLEMENTATION.md`.

## Accepted Sandbox transaction

The preserved acceptance transaction is
`bfe1e158-863b-4ddf-93a0-e31146e7cbcb`.

| Assertion | Accepted evidence | Freeze verification |
|---|---|---|
| Amount | Exactly `$25.00 USD` | Current transaction remains 2,500 cents USD |
| Environment | PayPal Sandbox | Rail and production configuration reverified |
| Recipient | Configured US Personal Sandbox account | Retained provider evidence; address not repeated here |
| Approval | One owner approval | One `approved` row |
| Submission | One worker payout POST | Retained worker/provider evidence; not repeated |
| Provider batch/item | One batch and one item | One persisted batch and one persisted item reference |
| Provider outcome | Batch `SUCCESS`, item-level `SUCCESS` | Persisted transaction/attempt status `SUCCESS` |
| Attempt | One completed attempt | One row, one stable request ID, `PAYPAL_ITEM_SUCCESS` |
| Reservation | One 2,500-cent capture | One reservation, state `captured` |
| Journal | One `payment_capture` | One wallet debit and equal clearing credit |
| Balance | `$975.00` posted, `$0.00` reserved, `$975.00` available | Independently recalculated from ledger/reservations |
| Audit/receipt | Nine lifecycle events | Current receipt is stable across repeated reads |
| Duplicates | None | One transaction/attempt per provider reference; no reversal journal |

The provider was not contacted during freeze verification. Item-level success,
one provider POST and the exact Sandbox recipient are retained accepted
evidence from the separately authorized execution.

## Architecture and authority

- The API authenticates, validates, evaluates policy, reserves funds and
  records approval decisions.
- No API route submits a PayPal payout.
- `pactra-worker.service` is the sole payout-submission authority.
- The worker holds a PostgreSQL advisory lease so only one process scans and
  submits.
- Row locks and conditional attempt state transitions provide one claim winner.
- Stable local request, sender batch and sender item identifiers are retained
  for the lifetime of an attempt.
- Reconciliation reuses the persisted provider batch identifier.

The worker interval is 20 seconds and the bounded scan size is 50. A backlog
does not authorize a manual API action or a replacement provider request.

## Permanent financial invariants

1. Worker-only submission must remain true.
2. API paths must never call payout creation.
3. Approval is user-owned and transaction-specific.
4. Policy is re-evaluated at approval where required.
5. A provider batch acceptance or HTTP success alone is not payout success.
6. Only confirmed item-level `SUCCESS` captures internal funds.
7. Unknown or ambiguous outcomes remain reserved.
8. An ambiguous provider request is reconciled, never blindly resubmitted.
9. Confirmed terminal failure releases the reservation exactly once.
10. Returns, reversals and refunds use idempotent compensation where supported.
11. Every state transition has a durable audit event.
12. Every ledger journal balances equal debit and credit amounts.
13. Wallet balances are derived from immutable entries and active
    reservations; they are never directly edited.
14. A masked recipient is display-only and must never become the submitted
    destination.
15. Sandbox credentials and recipients must never appear in metrics, alerts,
    commits or general incident reports.

## State interpretation

| Transaction/attempt state | Meaning | Permitted action |
|---|---|---|
| `pending_approval` / no attempt | Awaiting owner decision | Approve or reject only with current policy and transaction-specific authority |
| `executing` / `submitting` | Approved, not yet claimed | Let the sole worker claim it; do not call PayPal manually |
| `executing` / `claimed` | Worker owns the local attempt | Observe; preserve stable request ID |
| `executing` / `processing` with batch ID | Provider accepted a batch, item not terminal | Reconcile existing batch only |
| `executing` / `unknown` | Outcome ambiguous | Preserve reservation; investigate/reconcile; never replace |
| `completed` / item `SUCCESS` | Provider item succeeded and funds captured | Verify exactly-once ledger/audit evidence |
| `failed` / terminal provider failure | Provider definitively failed | Verify one reservation release and no capture |
| `reversed` | Completed payment later compensated | Verify exactly one compensation journal and provider evidence |

## Routine read-only checks

### Worker service, lease and backlog

Use the service, lease and backlog commands in
`QA/PRODUCTION-OPERATIONS-RUNBOOK.md`. Expected normal state is an active
worker, one granted lease, and zero eligible/unresolved backlog.

### Specific transaction integrity

Run all queries inside `BEGIN READ ONLY` and substitute only an authorized
transaction ID:

```sql
BEGIN READ ONLY;

SELECT status, amount_cents, currency, rail, provider_status,
       provider_batch_id IS NOT NULL AS has_batch,
       provider_item_id IS NOT NULL AS has_item,
       failure_code
FROM transactions
WHERE id = '<transaction-id>';

SELECT action, count(*)
FROM approval_actions
WHERE transaction_id = '<transaction-id>'
GROUP BY action;

SELECT status, provider_status, response_code, count(*),
       count(DISTINCT rail_request_id),
       count(DISTINCT provider_batch_id),
       count(DISTINCT provider_item_id)
FROM transaction_attempts
WHERE transaction_id = '<transaction-id>'
GROUP BY status, provider_status, response_code;

SELECT status, amount_cents, count(*)
FROM fund_reservations
WHERE transaction_id = '<transaction-id>'
GROUP BY status, amount_cents;

SELECT journal_type, status, count(*)
FROM ledger_journals
WHERE transaction_id = '<transaction-id>'
GROUP BY journal_type, status;

ROLLBACK;
```

Do not copy unmasked recipient data or full provider payloads into general
reports.

### Journal balance

```sql
BEGIN READ ONLY;

SELECT journal.id,
       journal.journal_type,
       sum(CASE WHEN entry.direction = 'debit' THEN entry.amount_cents ELSE 0 END) AS debits,
       sum(CASE WHEN entry.direction = 'credit' THEN entry.amount_cents ELSE 0 END) AS credits
FROM ledger_journals AS journal
JOIN ledger_entries AS entry ON entry.journal_id = journal.id
WHERE journal.transaction_id = '<transaction-id>'
GROUP BY journal.id, journal.journal_type;

ROLLBACK;
```

Every row must have equal positive debit and credit totals.

## Unknown or ambiguous payout outcome

1. Preserve the transaction, reservation, attempt and stable request ID.
2. Determine whether a provider batch ID was durably recorded.
3. If a batch ID exists, reconcile that batch only through the existing worker
   path after incident authorization.
4. If no trustworthy batch ID exists but the request may have left Pactra,
   keep the attempt `unknown` and reservation active. Escalate; do not submit a
   replacement.
5. Do not interpret OAuth success, HTTP 200/201, batch acceptance, or worker
   liveness as item success.
6. Capture only when the individual item is confirmed `SUCCESS` and IDs match
   the existing attempt.
7. On confirmed terminal failure, verify one release, zero capture journals
   and a durable failure audit event.

## PayPal unavailable

- Let bounded provider handling classify the failure.
- Do not change to live PayPal, rotate credentials, bypass Sandbox, or hammer
  the API.
- Do not approve additional test payouts to diagnose capacity.
- Keep deterministic internal Sandbox functions available where safe.
- Alert on unresolved reservations and unknown outcomes, not on raw recipient
  or provider payloads.

## Duplicate-processing suspicion

Treat any of these as a financial incident:

- more than one attempt for the same intended execution without a documented
  retry state;
- more than one distinct provider batch or item for one attempt;
- repeated payout POST evidence;
- more than one `payment_capture` journal;
- duplicate stable request identifiers;
- capture before item-level success;
- a completed item with an active reservation;
- an unbalanced journal.

Response:

1. Preserve all evidence and timestamps.
2. If additional submissions are possible, obtain incident authorization to
   stop only `pactra-worker.service`.
3. Reconcile provider and Pactra records by existing IDs.
4. Do not delete, merge or rewrite financial rows.
5. Do not send a compensating payout or hand-write a journal.
6. Design an idempotent remediation through a reviewed release.

## Reversal, return and refund

- Require a confirmed provider terminal state associated with the existing
  item.
- Use the application's idempotent compensation path.
- Preserve the original capture journal; compensation is a new balanced
  journal, never an edit.
- Replays must return the existing compensation rather than post another.
- Audit the provider state, reason, original transaction, compensation journal
  and final wallet balance.

## Approval operations

Payout approval is not a routine SRE action. It requires separate, explicit
authorization for the exact transaction, amount, currency, environment and
recipient. Deployment or incident authority does not imply financial
authority.

Before approval, verify:

- current state is still `pending_approval`;
- exact amount/currency and configured Sandbox recipient;
- policy version and threshold;
- active reservation and current wallet balance;
- zero prior approval, attempt, provider ID and capture journal;
- isolated scenario and one item only;
- worker is the sole submission path;
- a stable reconciliation path exists.

The accepted `$25.00 USD` authorization has been consumed. Never approve,
retry or replace that transaction.

## Audit and receipt requirements

A complete payment receipt must show, without exposing secrets:

- owned transaction and policy result;
- approval decision where applicable;
- attempt number, rail, terminal status and safe response code;
- stable provider evidence in restricted operator views;
- reservation outcome;
- balanced ledger entries and counter-account labels;
- ordered lifecycle events;
- final derived wallet balance.

For the accepted transaction, freeze verification found nine events:
`payment.requested`, `funds.reserved`, two state changes,
`payment.pending_approval`, `approval.approved`,
`paypal.payout_submitted`, `paypal.payout_reconciled`, and `ledger.posted`.

## Change control

Any change to payout state machines, provider parsing, retries, stable IDs,
worker claims, reconciliation, reservations, capture, compensation or ledger
logic requires:

- security and financial-invariant review;
- SQLite and PostgreSQL tests;
- PostgreSQL concurrency tests;
- provider timeout/ambiguous/terminal-state regressions;
- exactly-once journal and compensation tests;
- migration compatibility review where applicable;
- required CI, immutable release and rollback plan;
- explicit production deployment approval.
