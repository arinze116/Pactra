# Pactra Bug Report

Audit date: 2026-11-07  
Release deployed after remediation: `0e3e905`

## Severity summary

| Severity | Fixed | Open | Blocked by configuration |
|---|---:|---:|---:|
| P0 | 0 | 0 | 0 |
| P1 | 0 | 0 | 0 |
| P2 | 3 | 5 | 2 |
| P3 | 0 | 5 | 0 |

No confirmed P0 or P1 defect remains. “Blocked by configuration” identifies implemented integration paths that cannot be validated live without safe provider credentials; it does not mean provider success was inferred.

## Fixed defects

### BUG-001 — Approval revalidation could block without a complete state audit

- Severity: P2
- Status: FIXED and deployed
- Reproduction before fix:
  1. Create an above-threshold payment so it is `pending_approval` with an active reservation.
  2. Change policy so the vendor is blocked.
  3. Attempt approval.
  4. Observe the transaction becomes `blocked` and the reservation is released, but no explicit pending→blocked state event or business-level block event is written.
- Root cause: `approve_transaction` updated status and released the hold in its `PolicyChanged` branches without calling `_record_state` or `record_audit_event`.
- Fix: `backend/services/transactions.py::_record_approval_revalidation_block` now writes `transaction.state_changed` and `payment.blocked` with reason and policy-version evidence in the same transaction.
- Regression: `backend/tests/test_transactions.py::test_approval_revalidation_block_is_audited_and_releases_hold`.
- Evidence: SQLite and PostgreSQL full suites pass; production release `0e3e905`.

### BUG-002 — Payout receipt omitted the recipient

- Severity: P2
- Status: FIXED and deployed
- Reproduction before fix:
  1. Create a payout with a valid recipient email.
  2. Open the transaction receipt.
  3. The API response contains `recipient`, but the receipt does not render it.
- Root cause: `ReceiptPage` omitted `transaction.recipient` from its definition list.
- Fix: Render a `Recipient` field when present.
- Regressions: local/PG `fresh judge completes the core sandbox journey`; production `public submission journey remains secure, durable, and tenant isolated` now asserts the recipient before and after approval.
- Evidence: `frontend/src/pages/TransactionPages.tsx`; public test passed after Vercel deployment.

### BUG-003 — Audit events were append-only by convention, not by database enforcement

- Severity: P2 security hardening
- Status: FIXED and deployed
- Reproduction before fix: A database principal with table mutation rights could update or delete `audit_events`; no trigger rejected it.
- Root cause: the initial schema protected ledger entries/journals but did not add an equivalent audit-event trigger.
- Fix: migration `20261107_0004_harden_audit_immutability.py` rejects PostgreSQL `UPDATE` and `DELETE` on `audit_events`.
- Regression: `backend/tests/test_postgres_runtime.py::test_audit_events_are_immutable`.
- Evidence: production migration head `20261107_0004`; trigger `trg_audit_events_immutable` exists.

## Open product defects and deviations

### BUG-004 — Policy-blocked create response deviates from the PRD contract

- Severity: P2
- Status: OPEN; safe behaviour, deliberate contract decision required
- Reproduction: Submit an over-limit request to `POST /api/transactions`.
- Expected from PRD: `422 POLICY_BLOCKED`, or `402 INSUFFICIENT_FUNDS` for insufficient balance.
- Actual: `201` with a persisted blocked transaction/receipt.
- Root cause: deployed remediation `45d6c61` intentionally returns the authoritative created receipt from the `PolicyBlocked` catch branch.
- Risk: API consumers built from the PRD may treat any 2xx as execution acceptance even though `transaction.status` is `blocked`.
- Recommended fix: choose and document one contract, then update OpenAPI/tests/UI together. Do not silently revert the persisted-receipt safety behaviour.

### BUG-005 — Guided walkthrough does not cover all PRD scenarios

- Severity: P2
- Status: OPEN
- Reproduction: Open the overview guided checklist and inspect available payment presets.
- Expected: auto, approval, PayPal Sandbox payout, blocked, rejected, insufficient funds and reset.
- Actual: five internal scenarios; PayPal and insufficient-funds guided cases are absent.
- Root cause: implementation stopped at the deterministic internal demo path.
- Recommended fix: add the missing real persisted scenarios. PayPal step must remain disabled with an explicit reason when provider configuration is absent.

### BUG-006 — Payment preview does not show the likely policy decision

- Severity: P2
- Status: OPEN
- Reproduction: Fill the new-payment form with a blocked vendor or over-limit amount before submitting.
- Expected: PRD policy preview shows current limits and likely decision.
- Actual: the form shows policy limits and an approval-threshold confirmation only.
- Root cause: no read-only server-authoritative preview path exists; the UI checks only the approval threshold.
- Recommended fix: expose a non-mutating evaluation endpoint or reusable server result and show approved/approval-required/blocked with the first reason.

### BUG-007 — Approval cards omit part of the required decision context

- Severity: P2
- Status: OPEN
- Reproduction: Open `/app/approvals` with a pending request.
- Expected: requester, vendor, amount, category, reason, policy result, available balance and age.
- Actual: vendor, amount, category, reason and rail are shown; requester, available balance, age and detailed policy result are absent.
- Root cause: approval list response/UI use the compact transaction object rather than an approval-specific view model.
- Recommended fix: add a server-owned approval context DTO and render it without duplicating policy logic in the browser.

### BUG-008 — Overview core data fails as one request group

- Severity: P2
- Status: OPEN
- Reproduction: Fail one overview request while the others remain available.
- Expected: independent sections keep valid data and show a scoped error for the failed dependency.
- Actual: the combined load path can fail the overview as a group.
- Root cause: coupled request/error state in `OverviewPage`.
- Recommended fix: use independent results or `Promise.allSettled` with section-level errors.

### BUG-009 — Live Gemini functionality is unconfigured

- Severity: P2 integration readiness
- Status: BLOCKED
- Expected: successful configured Gemini function calling plus safe fallback.
- Actual: production reports `ai_enabled=false`, `ai_configured=false`; deterministic fallback works.
- Root cause: no production Gemini credential/enablement.
- Required action: provide approved credential, enable provider, then run live success/timeout/malformed-response tests. Do not claim live Gemini pass before that.

### BUG-010 — Live PayPal Sandbox payout is unconfigured

- Severity: P2 integration readiness
- Status: BLOCKED
- Expected: authenticated Sandbox payout item reaches terminal success and only then captures Pactra ledger funds.
- Actual: production reports `paypal_payouts_configured=false`; mocked provider-independent tests pass.
- Root cause: payouts credentials and test recipient are absent/disabled; a prior item-level attempt was unsuccessful.
- Required action: confirm safe business/recipient Sandbox accounts and obtain explicit authorization before another payout.

## Open P3 issues

### BUG-011 — Receipt lifecycle omits actor and payload context

- Status: OPEN
- Actual: event type and timestamp only, although the API returns actor/payload.
- Fix: render a safe actor label and selected payload fields.

### BUG-012 — Receipt ledger rows omit account/counter-account identity

- Status: OPEN
- Actual: direction, journal type and amount are shown.
- Fix: enrich transaction detail ledger entries with safe account labels.

### BUG-013 — Wallet error state has no explicit retry control

- Status: OPEN
- Actual: an error is shown, but recovery relies on navigation/reload.
- Fix: pass the wallet reload callback to `ErrorNotice`.

### BUG-014 — Password reveal is absent

- Status: OPEN / NOT IMPLEMENTED
- Actual: password fields provide no show/hide control required by the PRD.
- Fix: add accessible toggle buttons with `aria-pressed` and preserved focus.

### BUG-015 — Development dependency audit reports nine findings

- Status: OPEN
- Actual: 8 moderate and 1 high findings in Vite/esbuild and lint/minimatch chains; production dependency audit is clean.
- Fix: plan and test the suggested breaking-major toolchain upgrades rather than applying `npm audit fix --force` blindly.

## Non-defects observed during testing

- A parallel Playwright run collided while cleaning trace files. Sequential clean reruns passed; this was harness interference, not an application failure.
- Running the public suite without required `PUBLIC_BASE_URL` failed configuration before any product test. The corrected command passed.
- Vercel returns the SPA document for unknown non-API paths such as `/docs`; actual API documentation paths `/api/docs`, `/api/redoc`, and `/api/openapi.json` return 404. No secret exposure was found.
