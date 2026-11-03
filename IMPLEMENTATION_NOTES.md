# Pactra judge-ready implementation notes

Source of truth: `Pactra-PRD-Judge-Ready.md` v1.1, dated 3 November 2026.

Status legend: `[x]` complete and verified, `[~]` partially present, `[ ]` not implemented, `[B]` externally blocked.

## Existing architecture

- Backend: FastAPI + SQLModel monolith in `backend/main.py`.
- Persistence: SQLite through `SQLModel.metadata.create_all`; no Alembic migrations.
- Existing tables: one global float-based `Transaction` table and one global daily `PolicySnapshot` table.
- Policy: one JSON file loaded globally by `PolicyEngine`; no per-user versions or atomic reservations.
- Payments: PayPal Orders v2 for vendor payments and Payouts batch creation for payouts; mock mode returns immediate demo success IDs.
- AI: deprecated `google-generativeai` SDK and `gemini-2.0-flash`; tool handlers contain payment execution logic directly.
- API: unauthenticated global chat, transactions, spend summary, policy and approval endpoints.
- Frontend: React 18, TypeScript, Vite, Tailwind and Lucide; one dashboard screen with no router, auth, wallet, policy editor or receipt routes.
- Deployment: Render static frontend plus free Python service using ephemeral SQLite and mock PayPal mode.
- Tests: 11 backend policy/agent-handler tests; no auth, ledger, API authorisation, migration, provider reconciliation, frontend or E2E tests.

## Baseline verification — 3 November 2026

| Check | Result | Evidence |
| --- | --- | --- |
| Git status | Clean tracked tree | Only user-owned untracked `AGENT.md.txt` and `Pactra-PRD-Judge-Ready.md`; preserved |
| Backend tests | Passed | `python -m pytest -q -p no:cacheprovider`: 11 passed |
| Backend warning | Existing | Deprecated `google.generativeai` import warning |
| Frontend lint | Passed | `npm run lint` |
| Frontend type/build | Passed | `npm run build`; TypeScript project build and Vite production build succeeded |
| Frontend tests | Not available | No test script or test files exist |
| Migrations | Not available | No Alembic configuration or revisions exist |
| E2E | Not available | Playwright is not installed/configured |

Local runtime note: the existing `.venv` uses Python 3.13.14, while deployment and PRD target Python 3.11.10. Node 22.23.2 matches the PRD.

## PRD/repository contradictions and decisions

1. The PRD requires Vite 5.4.21 and `@vitejs/plugin-react` 4.7.0; the current branch has Vite 8.3.5 and plugin 6.2.1. The PRD wins; dependencies will be pinned to the required compatible versions without redesigning the working UI.
2. The PRD requires AG Grid Community 31.3.4 for the transaction history sponsor target; the current UI intentionally uses a semantic table. AG Grid will be restored for desktop transaction operations with an accessible mobile card fallback.
3. The PRD default category budgets are ops 150, software 200, cloud 100 and freelance 150 USD; the current JSON uses much larger demo budgets. New account defaults will follow the PRD.
4. The README says mock PayPal and ephemeral SQLite are judge-ready. The PRD explicitly rejects those claims for submission readiness; documentation and Render configuration must change.
5. The PRD pins SQLModel 0.0.47 and SQLAlchemy 2.0.50; the local environment currently has 0.0.48 and 2.1.6 from range requirements. Requirements will be pinned to the PRD.
6. Route inventory lists `/health`, while the API contract and deployment use `/api/health`. `/api/health` and `/api/ready` are canonical; a lightweight `/health` alias may be retained for host compatibility if needed.
7. The existing self-hosted IBM Plex Sans dependency is permitted by the PRD if documented. It will be kept unless the dependency budget or bundle target requires removal.

## PRD requirement checklist

### Foundations

- [x] Alembic migration environment and initial schema from Section 16
- [x] PostgreSQL production support; SQLite local/test compatibility
- [~] Integer-cent money model added; legacy float demo paths remain until transaction-service migration
- [x] User-owned auth/wallet records and owner-scoped queries; unsafe global legacy payment routes are authenticated and fail closed until replacement
- [x] Append-only double-entry schema, service postings and PostgreSQL balance/immutability triggers
- [ ] Immutable ledger enforcement and compensating corrections
- [~] Atomic reservations and available balance verified; policy/current-generation spend integration pending
- [~] Ledger/top-up idempotency with same-key replay and conflict detection; transaction idempotency pending

### Authentication and security

- [x] Registration, login, logout, current user and password change
- [x] Argon2id password hashing
- [x] Opaque server-side sessions with expiry, idle timeout, rotation and revocation
- [x] CSRF plus same-origin mutation checks
- [~] Strict CORS, baseline security headers and production PayPal/cookie guards; final CSP/HTTPS hardening pending
- [~] Auth and top-up rate limits; remaining action limits pending
- [~] Cross-user wallet/ledger tests pass; owner-only transaction approvals pending

### Wallet and policy

- [x] Atomic account bootstrap with 1,000 USD sandbox issuance
- [x] Idempotent preset top-ups and owner-scoped wallet ledger history
- [x] Available/reserved/posted balance API
- [ ] Per-user policy versions, validation, reset and audit
- [ ] Deterministic policy order and stable PRD reason codes
- [ ] Policy evaluation and reservation in one transaction

### Transaction lifecycle

- [ ] Unified manual/AI transaction application service
- [ ] Internal sandbox rail
- [ ] Full state machine: draft, pending, executing, completed, blocked, rejected, failed, cancelled, reversed
- [ ] Atomic approve/reject and current-policy re-evaluation
- [ ] Safe retry and internal-sandbox reversal
- [ ] Transaction attempts, audit events, receipts and lifecycle timeline
- [ ] Owner-scoped filtering, cursor pagination and current/all-generation history

### PayPal Sandbox Payouts

- [~] OAuth and basic batch creation exist
- [ ] Sandbox-host startup guard and explicit integration status
- [ ] Stable transaction/attempt sender batch and request IDs
- [ ] Batch plus payout-item reconciliation
- [ ] Hold retention for processing/unknown provider outcomes
- [ ] Ledger capture only after item `SUCCESS`
- [ ] Terminal failure release and returned/reversed/refunded compensation
- [ ] DB-backed reconciliation worker and manual refresh endpoint
- [B] Live sandbox smoke test requires owner-provided sandbox credentials and recipient email

### AI assistant

- [ ] Migrate to `google-genai==2.23.0` and `gemini-3.8-flash`
- [ ] Persist conversations server-side
- [ ] Strict allowlisted tools using authenticated transaction services
- [ ] Deterministic parser fallback and clarification behavior
- [ ] AI rate/turn/input/output limits and prompt-injection boundaries
- [B] Live Gemini verification requires deployment `GEMINI_API_KEY`

### Frontend and judge experience

- [ ] Public landing, sign-up and sign-in routes
- [ ] Authenticated app shell and route guards
- [ ] Overview, payment form, assistant, approvals, transactions, receipt, policies, wallet, settings and PayPal integration routes
- [ ] Wallet top-up/reset, policy edit, approve/reject, retry/reverse and provider reconcile flows
- [ ] Meaningful AG Grid transaction history
- [ ] Loading, empty, error, success and session-expiry states
- [ ] Guided judge checklist using real persisted transactions
- [ ] Responsive and keyboard-accessible P0 journeys

### Quality, deployment and documentation

- [ ] Backend unit/integration/concurrency/security coverage
- [ ] Playwright P0 journeys and provider-timeout scenario
- [ ] CI with PostgreSQL migration/test job
- [ ] Managed PostgreSQL Render blueprint and migration release step
- [ ] `/api/health` and `/api/ready`
- [ ] README, environment, seed/reset and judge walkthrough documentation
- [B] Public deployment smoke requires hosting access and managed PostgreSQL
- [B] Submission-ready PayPal path requires real sandbox smoke evidence

## Ordered implementation phases

1. Database model, Alembic migrations and SQLite/PostgreSQL compatibility.
2. Authentication, session/CSRF dependencies and atomic account bootstrap.
3. Ledger service, balance calculations, top-ups, reservations and reset.
4. Per-user policy versions and pure cents-based evaluator.
5. Unified transaction service, internal rail, state machine and idempotency.
6. Approval/rejection, retry/reversal and owner-scoped API/receipts.
7. PayPal Payouts adapter, attempts, reconciliation worker and provider status API.
8. Gemini SDK migration, persisted chat, typed tools and fallback parser.
9. Authenticated frontend routes and all judge-operable P0 workflows.
10. Guided tests, Playwright, security hardening, CI, deployment and documentation.

Checkpoints follow the PRD: database/auth/ledger before payment features; complete backend lifecycle before frontend integration; full fresh-account flow before deployment work.

## Critical invariants and security risks

- Every data read and mutation is scoped to the authenticated user.
- User IDs, policy decisions, balances and execution results are never trusted from clients or Gemini.
- Money is integer cents only; posted balance cannot be negative.
- Every ledger journal is balanced before commit; posted entries are never edited or deleted.
- Active reservations reduce available balance but do not change posted balance.
- Policy checks, spend checks and reservation creation are atomic.
- Approval is a conditional single-use transition; concurrent approvals execute once.
- All money mutations require idempotency; provider retry IDs remain stable for unresolved attempts.
- Pactra transaction status and provider status remain separate.
- PayPal batch submission is not success; payout-item success plus local ledger capture is required.
- Unknown provider outcomes retain reservations and never trigger a second payout.
- Production refuses live PayPal hosts and never exposes credentials.
- Session tokens, passwords, API keys, cookies, access tokens and raw provider responses are never logged.

## External credentials and services

- Managed PostgreSQL and public deployment access: required for production readiness; local SQLite remains available for development.
- `GEMINI_API_KEY`: required only for live AI verification; mocks/fallback cover local tests.
- PayPal Sandbox business client ID/secret with Payouts capability and `PAYPAL_TEST_RECIPIENT_EMAIL`: required for live payout smoke; never entered by judges.
- Devpost registration, repository visibility, YouTube upload and final submission are owner actions.

## Acceptance tests by phase

### Database/auth/ledger checkpoint

- `alembic upgrade head` succeeds on a clean SQLite database and PostgreSQL-compatible SQL is present for production constraints.
- Registration atomically creates user, wallet, default policy and balanced 100,000-cent issuance.
- Login/session/logout/CSRF and cross-user denial tests pass.
- Top-up replay posts once; wallet available = posted - reservations; concurrent reservations cannot overspend.

### Policy/transaction checkpoint

- Every PRD rule and boundary returns the first stable reason code.
- Auto payment captures one balanced journal; blocked payment moves no funds.
- Approval-required payment reserves once; approve/reject is atomic and releases/captures correctly.
- Retry, reversal and idempotency tests produce no duplicate postings.

### Provider/AI checkpoint

- Mocked PayPal create/reconcile tests cover processing, success, failure, timeout, unknown and returned states.
- Provider success followed by local capture failure reconciles to one capture.
- Gemini tool calls and deterministic fallback use the same authenticated transaction service.

### Frontend/judge checkpoint

- A fresh judge can register, see 1,000 USD sandbox funds, top up, edit policy, create manual/AI requests, approve/reject, view receipts and reset.
- AG Grid filters and opens transaction detail; mobile history remains usable.
- Errors never claim completion or optimistic balance changes.
- Playwright scripts 1–12 from PRD Section 28 pass where credentials are not required; credential-dependent smoke is reported separately.

## Progress log

- 2026-11-03: Phase 0 repository/PRD audit complete. Baseline backend tests, frontend lint and frontend build pass. No tracked user changes were present.
- 2026-11-03: T-02 schema slice complete. Dependencies pinned, PostgreSQL/SQLite settings added, Alembic initial migration creates all PRD tables/system accounts, PostgreSQL SQL generation succeeds, and 12 backend tests pass including clean migration verification.
- 2026-11-03: CP-1 auth/ledger slice complete. Added Argon2id registration/login/password change, opaque revocable sessions, same-origin CSRF, atomic account bootstrap, wallet summary/top-up/ledger APIs, ownership checks, balanced postings and reservation concurrency coverage. Unsafe global legacy payment routes now fail closed behind authentication until the unified service replaces them. Full backend suite: 21 passed. Clean local `alembic upgrade head`: passed.
