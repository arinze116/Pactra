# Pactra FAQ and Judge Questions

## What happens if Gemini goes down?

Pactra classifies the provider failure and uses deterministic fallback for
supported requests. Policy, approval, tenant, validation, and ledger controls
remain available. It does not hide the provider failure or retry without a
bound.

## Can AI approve its own payment?

No. AI can propose a typed application action. Approval is a separate
authenticated server-side transition, and the policy and wallet are checked
again at approval time.

## What stops a user exceeding policy?

The backend evaluates fixed rules for category, blocked vendor, transaction
limit, daily/category budget, available funds, and approval threshold. Frontend
previews are non-authoritative.

## How are duplicate payments prevented?

Client idempotency keys, database uniqueness, row locks, conditional state
transitions, one worker claim winner, and stable provider identifiers prevent
duplicate local and provider execution.

## What happens when a provider times out?

Pactra treats the outcome as ambiguous, preserves the reservation and stable
attempt, and reconciles an existing provider identifier when available. It
does not blindly resubmit.

## How do you prevent duplicate ledger entries?

Capture and compensation use stable idempotency keys, unique constraints,
conditional reservation transitions, balanced two-entry journals, and
PostgreSQL immutability triggers. Read-only diagnostics check these invariants.

## How can a business audit a transaction?

The owned receipt shows the policy trace, approval action, execution attempt,
provider-safe evidence, lifecycle events, and equal debit/credit ledger impact.

## Is this live money?

No. Pactra is sandbox-only. The internal wallet is simulated, and the optional
provider rail is PayPal Sandbox only.

## What is sandbox-only?

Wallet balances, internal transfers, and demo transactions are simulated.
PayPal evidence uses Sandbox accounts and does not move real money.

## What is the security model?

Argon2id passwords, opaque hashed sessions, CSRF, exact CORS, tenant-scoped
queries, strict schemas, database-backed rate limits, row locks, immutable
financial/audit records, worker-only provider authority, and secrets outside
source control.

## How is this different from a normal payment interface?

A normal form focuses on submitting a payment. Pactra focuses on governing the
request before execution and proving the decision afterward, regardless of
whether the request came from a person or AI.

## Why not let the model decide policy?

Language models are useful for interpreting intent, not for enforcing
financial authority. Pactra keeps policy deterministic, reviewable, and
testable.

## Has the product been audited or regulator approved?

No such claim is made. The repository has automated security, dependency,
accessibility, and financial-invariant evidence, but it is not presented as a
formal external audit or regulated banking platform.

## What would you build next?

Independent approver roles, approval TTLs, scheduled worker/ledger/provider
alerts, centralized privacy-reviewed error aggregation, measured recovery
objectives, and additional provider integrations through the existing control
boundary.
