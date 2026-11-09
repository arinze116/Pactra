# Pactra PayPal Sandbox Execution Runbook

Last execution verification: 2026-11-09, Africa/Lagos

This runbook governs one separately authorised PayPal Sandbox payout through
Pactra's application workflow. It does not authorise a payout. Never use it
with PayPal Live, never create a replacement payout automatically, and never
interpret OAuth, batch acceptance, or a batch-level status as item success.

## Current milestone status

These milestones are independent:

| Milestone | Current status | Required evidence |
|---|---|---|
| Automated state-machine tests | PASS on integrated `main` | SQLite, PostgreSQL concurrency, mocked provider, browser, and accessibility results |
| Sandbox OAuth and scope | PASS for the configured production credentials | OAuth completed in 737 ms and included Payouts scope; this is not payout success |
| Payout prepared | PASS | Exact transaction below was revalidated `pending_approval`, reserved and with zero attempts immediately before approval |
| Payout submitted | PASS | One explicit authorisation, one API approval and one worker-owned payout POST |
| Individual item `SUCCESS` | PASS | Persisted batch lookup returned one item with `transaction_status=SUCCESS` |
| Pactra ledger reconciliation | PASS | One captured reservation, one `payment_capture` journal, balanced entries, persistent receipt and audit events |

The runtime release is `73fdfb692f6daea69ba5f44bc37d9afa1814419a` at
`/opt/pactra/releases/73fdfb6`, with production at migration
`20261107_0005`. The masked-recipient correction is deployed: UI masks are
display-only and the API resolves the configured recipient server-side.

## Safety rules

- The only permitted provider host is `https://api-m.sandbox.paypal.com`.
- The sender is the US Business Sandbox account associated with the configured
  client credentials.
- The receiver is the configured US Personal Sandbox account. Never copy the
  masked address shown by the UI into a request.
- The API creates, validates, reserves, and queues. Only `backend.worker` may
  call PayPal's payout-creation endpoint.
- The manual authorisation is consumed when the operator clicks **Approve**.
  The worker may submit during its next scan, normally within 20 seconds.
- Never click **Approve** until the authorisation checkpoint in this document
  is complete.
- Never retry a timeout or unknown outcome automatically.
- Never use the ordinary transaction retry action while provider truth is
  unresolved.
- Item-level `SUCCESS` is the only success condition.

## Preconditions

Record each item as PASS before opening the guided payout form:

1. The deployed backend and worker identify the approved release SHA. The
   Vercel runtime source may be an earlier commit only when the frontend runtime
   tree and built asset hashes are proven identical.
2. The database is at `20261107_0005`.
3. Exact-SHA GitHub Actions is green.
4. `pactra-api.service` and `pactra-worker.service` are active on the approved
   release, and the worker has acquired the PostgreSQL advisory lease.
5. Both units load `/etc/pactra/pactra.env`.
6. Without printing values, configuration inspection confirms:
   `PAYPAL_PAYOUTS_ENABLED=true`, `PAYPAL_MOCK_MODE=false`, non-empty
   `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and
   `PAYPAL_TEST_RECIPIENT_EMAIL`, plus the exact Sandbox `PAYPAL_BASE_URL`.
7. The integration page at `/app/settings/integrations/paypal` reports
   **PayPal Sandbox**, **Configured**, and **Payouts**, with a masked recipient.
8. A fresh isolated test account is available. No previous PayPal transaction
   for that account is `executing`, `processing`, `unknown`, or otherwise
   unresolved.
9. The wallet has at least $25.00 available after all active reservations.
10. The account's current policy allows USD, category `freelance`, the vendor,
    and $25.00 under its per-transaction, daily, and category limits.
11. The policy's **Approval above** value is $24.99 or lower. The rule is
    `amount > threshold`; $25.00 must therefore require approval.
12. The owner has not yet authorised submission. Preparation must stop at
    `pending_approval`.

Safe read-only host checks include:

```bash
sudo readlink -f /opt/pactra/current
sudo -u pactra sed -n '1p' /opt/pactra/current/.release-sha
sudo systemctl is-active pactra-api.service pactra-worker.service
sudo journalctl -u pactra-worker.service --since '-5 minutes' --no-pager
curl --fail --silent http://127.0.0.1:8010/api/health
curl --fail --silent http://127.0.0.1:8010/api/ready
sudo -u postgres psql -d pactra -Atqc 'SELECT version_num FROM alembic_version'
```

Do not print the environment file or process environment. Check only variable
presence, boolean flags, and the exact Sandbox host.

## Prepare the isolated account

1. Register a fresh account or sign in to the dedicated payout test account.
2. Open `/app/wallet`. Record the available, reserved, and posted balances and
   the sandbox generation.
3. Open `/app/policies`.
4. Set **Approval above** to `24.99` or lower.
5. Keep **Per transaction**, **Daily limit**, and the `freelance` budget high
   enough for $25.00 plus current committed and reserved spend.
6. Confirm that `freelance` remains an allowed category and the payout vendor
   is not blocked.
7. Save the policy. Record the new immutable policy version.
8. Return to `/app/wallet` and confirm there is no unexplained reservation.

Do not alter a shared or customer account's policy. Use only the isolated test
account.

## Guided UI journey before authorisation

1. Open `/app/settings/integrations/paypal`.
2. Confirm Sandbox, Payouts, and the masked configured recipient.
3. Select **Create PayPal Sandbox payout**, which opens
   `/app/payments/new?scenario=paypal`.
4. Verify the preset without changing it:
   - type: payout;
   - amount: `$25.00`;
   - currency: `USD`;
   - category: `freelance`;
   - rail: `PayPal Sandbox Payouts`;
   - reason: `PayPal Sandbox payout test`;
   - recipient: **Configured Sandbox recipient**, displayed only in masked form.
5. Wait for the server-authoritative preview. It must say approval is required.
6. Select **Review request**, inspect the confirmation, then select
   **Confirm and create request**.
7. The receipt must show `pending_approval`, policy version/checks, an active
   $25.00 reservation, no provider batch or item ID, and no execution attempt.
8. Open `/app/approvals`. Confirm the same transaction shows the PayPal rail,
   $25.00, `freelance`, the current policy version, and the approval-required
   policy result.

This is the safe stopping point. A `pending_approval` transaction cannot be
claimed by the worker. Do not click **Approve** during preparation.

## Authorised transaction - pre-submission snapshot

Immediately before the consumed approval, the isolated scenario was at the
safe stopping point:

| Field | Exact value |
|---|---|
| Transaction | `bfe1e158-863b-4ddf-93a0-e31146e7cbcb` |
| Amount/currency | `$25.00 USD` |
| Recipient | `sb-4fqlt53808662@personal.example.com` |
| Test account | `pactra-paypal-approval-20261109160306@example.com` |
| Rail | `paypal_sandbox_payouts` |
| Category/reason | `freelance` / `PayPal Sandbox payout test` |
| Policy | version `2`; approval threshold `$1.00` |
| Status | `pending_approval` |
| Posted/reserved/available | `$1,000.00` / `$25.00` / `$975.00` |
| Attempts | `0` |
| Provider batch/item/status | none / none / none |
| Ledger journals | `0` |

The state remained unchanged through worker scans, deployment and public
acceptance until the user supplied the separate transaction-specific
authorisation. The recipient is the persisted unmasked Sandbox address; the UI
continues to show only a mask. The sender is the Business Sandbox account tied
to the configured credentials, but its email is not independently exposed by
the client-credentials API.

That authorisation has now been consumed. Do not approve this transaction
again, create another attempt, or create a replacement payout.

## Manual authorisation checkpoint

Immediately before **Approve**, the user must explicitly authorise transaction
`bfe1e158-863b-4ddf-93a0-e31146e7cbcb`: exactly one $25.00 USD payout to
`sb-4fqlt53808662@personal.example.com` in PayPal Sandbox.
Record:

- authoriser and timestamp;
- deployed SHA and database revision;
- Pactra transaction ID and policy version;
- available, reserved, and posted balances;
- confirmation that the transaction is still `pending_approval`;
- confirmation that no unresolved prior payout exists;
- confirmation that the worker is healthy and holds its lease;
- confirmation that the environment is Sandbox and mock mode is disabled.

If any value changed, stop and repeat preflight. Authorisation for one
transaction does not authorise a second transaction, a new attempt, a changed
recipient, or a changed amount.

### The action that submits the payout

The operator clicks **Approve** for this transaction on `/app/approvals`.
That calls:

```text
POST /api/approvals/{transaction_id}/approve
```

The API re-evaluates policy, atomically changes the transaction from
`pending_approval` to `executing`, and creates one `submitting` PayPal attempt.
It does not call PayPal. The running worker then claims that attempt and is the
only component that calls:

```text
POST https://api-m.sandbox.paypal.com/v1/payments/payouts
```

Do not execute either action without the separate authorisation.

## Completed execution record - 2026-11-09

The user explicitly authorised only transaction
`bfe1e158-863b-4ddf-93a0-e31146e7cbcb`, exactly `$25.00 USD`, to the recipient
shown above. The live preflight revalidated every checkpoint and found no
prior approval, attempt, provider identifier or journal.

| Evidence | Result | Status |
|---|---|---|
| Approval | One live API approval at `18:23:44 WAT`; one action and attempt 1; short-lived operator session revoked | PASS |
| Worker authority | API response had no provider ID; the existing worker made the payout POST | PASS |
| Submission count | One `POST /v1/payments/payouts`, HTTP `201`, at `18:23:47 WAT` | PASS |
| Stable identifiers | Rail request `pactra-bfe1e158-863b-4ddf-93a0-e31146e7cbcb-a1`; provider batch `ZMQQ…3Q8U` | PASS |
| Reconciliation | Worker reused the persisted batch; no manual reconcile or replacement submission | PASS |
| Provider item | One item `E5KZ…KTYA`; batch `SUCCESS`; item `SUCCESS` | PASS |
| Provider recheck | Read-only persisted-batch lookup returned HTTP 200 in 746 ms and matched amount, currency, recipient and sender IDs | PASS |
| Pactra state | Transaction and attempt `completed`; response code `PAYPAL_ITEM_SUCCESS` | PASS |
| Funds | One captured 2500-cent reservation; one balanced `payment_capture`; zero reversal | PASS |
| Final balance | Posted `$975.00`; reserved `$0.00`; available `$975.00` | PASS |
| Duplicate checks | One attempt, batch, item, rail request and capture journal; no unresolved payout | PASS |
| Receipt/audit | Receipt identical after reload; two ledger entries and nine lifecycle events | PASS |

The transaction-specific authorisation is exhausted. Never send another
approval or payout-creation/recovery request for this item. Any later status
refresh must be read-only and use the persisted batch identifier.

## Expected provider request

The worker request contains exactly one item. Secrets and the receiver must be
redacted in evidence:

```json
{
  "sender_batch_header": {
    "sender_batch_id": "pactra-{transaction_uuid}-a1",
    "email_subject": "Pactra sandbox payout",
    "email_message": "Sandbox payment initiated by Pactra"
  },
  "items": [
    {
      "recipient_type": "EMAIL",
      "amount": { "value": "25.00", "currency": "USD" },
      "receiver": "[configured US Personal Sandbox recipient redacted]",
      "note": "PayPal Sandbox payout test",
      "sender_item_id": "pactra-{transaction_uuid}"
    }
  ]
}
```

The `PayPal-Request-Id` header equals the stable sender batch ID. The sender
batch ID, sender item ID, transaction attempt number, and local idempotency key
must remain unchanged throughout initial submission and recovery.

## Expected states

| Stage | Pactra transaction | Attempt | Reservation | Ledger | Provider evidence |
|---|---|---|---|---|---|
| Created | `pending_approval` | none | active | no capture | none |
| Approved | `executing` | `submitting` | active | no capture | none |
| Worker claim | `executing` | `claimed` | active | no capture | stable local IDs only |
| Batch accepted | `executing` | `processing` | active | no capture | batch ID and batch status |
| Item pending | `executing` | `processing` | active | no capture | item ID and non-terminal item status |
| Item success | `completed` | `completed` | captured | exactly one capture | item `SUCCESS` |
| Terminal failure | `failed` | `failed` | released | no capture | `FAILED`, `DENIED`, `BLOCKED`, or `CANCELED` |
| Unknown submission | `executing` | `unknown` | active | no capture | no trustworthy terminal truth |
| Returned/reversed/refunded | `reversed` | `reversed` | released or already captured | at most one compensation | matching item status |

A batch-level `SUCCESS` with a pending or absent item status remains
`executing` and reserved.

## Success evidence

PASS requires all of the following:

1. PayPal's batch response contains the expected batch ID and one item.
2. The individual item has a complete item ID and
   `transaction_status=SUCCESS`.
3. Pactra stores the same batch ID, item ID, and provider status.
4. The transaction is `completed`; the attempt is `completed` with response
   code `PAYPAL_ITEM_SUCCESS`.
5. The original reservation is `captured`, not merely released.
6. Exactly one `payment_capture` journal exists for the transaction.
7. That journal has one equal USD debit and credit for 2500 cents.
8. No `payment_reversal` exists unless PayPal later reports a return,
   reversal, or refund.
9. The receipt shows the provider item evidence, policy trace, one execution
   attempt, balanced ledger impact, and lifecycle events.
10. Audit history includes reservation, approval, payout submission,
    reconciliation, ledger posting, and completion state transition.
11. Reloading the receipt preserves the same provider, ledger, and audit data.
12. Provider submission logs and records show one application-owned payout
    attempt. No replacement batch was created.

Read-only database evidence can be collected after setting the transaction ID
in `psql`:

```sql
\set transaction_id '00000000-0000-0000-0000-000000000000'

SELECT id, status, amount_cents, currency, rail,
       provider_batch_id, provider_item_id, provider_status,
       failure_code, policy_version, completed_at
FROM transactions
WHERE id = :'transaction_id';

SELECT attempt_number, rail_request_id, status, provider_batch_id,
       provider_item_id, provider_status, response_code, started_at, finished_at
FROM transaction_attempts
WHERE transaction_id = :'transaction_id'
ORDER BY attempt_number;

SELECT status, amount_cents, created_at, released_at
FROM fund_reservations
WHERE transaction_id = :'transaction_id';

SELECT journal_type, count(*)
FROM ledger_journals
WHERE transaction_id = :'transaction_id'
GROUP BY journal_type
ORDER BY journal_type;

SELECT j.journal_type, e.direction, sum(e.amount_cents) AS amount_cents,
       e.currency
FROM ledger_journals AS j
JOIN ledger_entries AS e ON e.journal_id = j.id
WHERE j.transaction_id = :'transaction_id'
GROUP BY j.journal_type, e.direction, e.currency
ORDER BY j.journal_type, e.direction;

SELECT event_type, count(*)
FROM audit_events
WHERE entity_type = 'transaction' AND entity_id = :'transaction_id'
GROUP BY event_type
ORDER BY event_type;
```

Mask recipient and provider identifiers in judge-facing reports. Never include
credentials, OAuth tokens, or process environment values.

## Reconciliation and failure handling

### Known batch ID

When a batch ID is stored, automatic worker reconciliation and the receipt's
**Refresh provider** action use PayPal's read-only batch lookup. They do not
create another payout. Continue bounded reconciliation until the item is
terminal. Do not create another transaction while waiting.

The backend also permits an authenticated
`POST /api/transactions/{transaction_id}/reconcile` for a known completed
batch so an operator can check for a later return, reversal, or refund. The
worker still performs only the provider GET for this case.

### Timeout or unknown outcome without a batch ID

The worker marks the attempt `unknown`, keeps the reservation active, and
excludes it from automatic scans. Stop. Search PayPal's Sandbox dashboard using
the stable sender batch ID and preserve all evidence.

The receipt's **Recover submission** action is not a read-only status check.
It queues the same stable POST because PayPal provides no batch ID to query.
Although PayPal idempotency is expected to recover the original batch, this
action requires a new explicit human authorisation. Never automate it and never
replace it with a fresh transaction or attempt.

### Terminal failure

For item `FAILED`, `DENIED`, `BLOCKED`, or `CANCELED`, verify that Pactra marks
the transaction failed, releases the reservation, posts no capture, and records
the provider status and audit event. Stop. A replacement payout needs separate
authorisation.

### Return, reversal, or refund

Before capture, these statuses release the reservation and post no ledger
journal. After capture, Pactra posts one idempotent compensating
`payment_reversal` journal and moves the transaction to `reversed`. Repeated
reconciliation must not duplicate compensation.

## Automated evidence references

- API never submits and configured-recipient resolution:
  `backend/tests/test_transaction_api.py::test_paypal_api_uses_configured_recipient_and_never_submits_directly`.
- Concurrent PostgreSQL worker claim:
  `backend/tests/test_postgres_runtime.py::test_concurrent_worker_claims_have_one_winner`.
- Single worker lease:
  `backend/tests/test_postgres_runtime.py::test_reconciliation_worker_lease_allows_only_one_authority`.
- Duplicate API/worker delivery:
  `backend/tests/test_paypal_payouts.py::test_api_replay_and_duplicate_worker_delivery_submit_once`.
- Timeout and explicit stable-ID recovery:
  `test_unknown_submission_is_not_blindly_retried` and
  `test_unknown_submission_recovery_reuses_the_same_stable_attempt`.
- Crash and restart recovery:
  `test_worker_crash_after_provider_acceptance_reuses_stable_attempt`,
  `test_provider_batch_survives_local_capture_rollback`, and
  `test_worker_restart_reuses_persisted_provider_batch`.
- Item success, receipt, exactly-once capture, and compensation:
  `test_item_success_captures_once_and_later_return_compensates`.
- Terminal failure and pre-capture provider returns:
  `test_terminal_item_failure_releases_hold` and
  `test_pre_capture_provider_return_releases_hold_without_posting`.
- Approval/rejection gate:
  `test_one_dollar_payout_requires_approval_before_worker_submission`.
- Masked-recipient browser regression:
  `frontend/tests/e2e/judge-flow.spec.ts` test
  `guided PayPal form keeps the configured recipient server-side`.

These tests use isolated databases and provider doubles. They do not prove
Sandbox Payouts entitlement or item-level provider success.

## Stop conditions

Stop without approval or submission if any of these is true:

- the host is not the exact PayPal Sandbox host;
- the deployed SHA, frontend, worker, or migration is inconsistent;
- mock mode is enabled or Payouts is disabled;
- configuration is missing or the recipient is not the intended Personal
  Sandbox account;
- the preview does not require approval;
- the transaction is not `pending_approval` before authorisation;
- a prior payout remains unresolved;
- the worker is unhealthy or lacks its lease;
- the amount, currency, recipient, category, policy, or transaction ID changed;
- submission returns an ambiguous result;
- more than one local attempt or provider batch appears.

No automated retry, replacement payout, or compensating payout is permitted.
