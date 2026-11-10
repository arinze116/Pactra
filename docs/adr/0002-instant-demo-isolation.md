# ADR 0002: Isolated instant-demo principals

- Status: Accepted
- Date: 2026-11-10

## Context

Hackathon judges need to enter a populated Pactra workspace without registering
or receiving shared credentials. The feature must preserve existing normal
authentication and owner checks, prevent cross-visitor data access, and make
external provider execution impossible for demo activity.

## Decision

- Retain TypeScript/React/Vite for the browser and Python/FastAPI/Pydantic/
  SQLModel for the API and worker. This is the smallest change compatible with
  the deployed architecture and existing tests.
- Represent each demo as a distinct temporary `User` plus one
  `DemoWorkspace`, using the normal ownership model for wallet, policies,
  payments, approvals, receipts, conversations, and audit records.
- Reuse opaque database sessions and CSRF validation, but use separate demo
  cookie names so an unrelated normal session can survive demo entry and exit.
- Store no session credential in a URL, local storage, or frontend-only flag.
- Allow only the internal sandbox rail for demo owners. Enforce the rule in
  the API, transaction service, provider adapter, and worker query.
- Seed and reset through existing policy, transaction, approval, ledger, and
  audit services.
- Clean expired/revoked demo principals in bounded worker batches. Permit
  immutable ledger/audit deletion only when PostgreSQL can prove the owner is
  an expired or revoked demo principal.
- Bound creation, active sessions, resets, and transactions.

## Consequences

- Simultaneous judges receive independent owner IDs and cannot access each
  other's records through existing owner-scoped queries.
- Normal registration, login, logout, and session restoration remain on their
  existing code path.
- Demo cleanup adds a narrow, testable exception to append-only PostgreSQL
  triggers; updates and normal-user deletion remain prohibited.
- A migration-aware rollback artifact is required after schema `0006`; an old
  release whose Alembic graph ends at `0005` cannot be started directly against
  a database stamped `0006`.
- Seeded pending approval reserves funds, so the coherent dashboard balance is
  `$965 posted / $140 reserved / $825 available`, not the illustrative landing
  preview's `$1,000` available balance.

## Alternatives rejected

- Shared writable demo account: permits cross-visitor observation and
  modification.
- Frontend-only `isDemo` bypass: does not establish a backend principal and
  weakens authorization.
- Hardcoded demo password: creates a public shared credential and shared data.
- New token/session format: duplicates security-sensitive authentication code.
- Separate demo policy or ledger tables: would not demonstrate the real Pactra
  policy and financial workflows.
- Provider mock presented as PayPal execution: misrepresents the outcome and
  risks entering provider code.
