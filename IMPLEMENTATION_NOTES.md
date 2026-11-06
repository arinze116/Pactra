# Pactra judge-ready implementation notes

Source of truth: `Pactra-PRD-Judge-Ready.md` v1.1, dated 3 November 2026.

Status legend: `[x]` complete and verified, `[~]` partially present, `[ ]` not implemented, `[B]` externally blocked.

## Final release candidate — 5 November 2026

- Active release branch: `feat/red-dark-fintech-redesign`; PR #2 targets `main`.
- Backend verification: `63 passed, 2 skipped`; the skipped tests are PostgreSQL-only UUID/runtime and concurrent-policy locking checks that run in CI.
- Frontend verification: lint passed, production build passed, production dependency audit found zero vulnerabilities, and all 9 Chromium judge journeys passed.
- A clean SQLite database migrated through Alembic revisions `20261103_0001` and `20261103_0002`.
- Cross-origin production auth uses Secure SameSite=None HttpOnly cookies plus an exposed synchronizer-token response header; production configuration rejects unsafe secrets, origins, SQLite, mock PayPal, and live PayPal hosts.
- Gemini tool/failure paths are covered deterministically, including a partial provider failure after a payment tool has committed. A real provider request reached Google but returned `503 UNAVAILABLE`; live Gemini success is not claimed.
- A real PayPal Sandbox payout was submitted with mock mode disabled. Its item reached `FAILED`; Pactra released the reservation and preserved the posted balance. Item-level success remains an external release gate.
- The Render blueprint uses unique unassigned service names and managed PostgreSQL, but no Render API/CLI access is available in this workspace. Public deployment is not claimed.

## Historical baseline before judge-ready implementation

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

## Historical phase 0 revalidation — 3 November 2026

The repository is now on `feat/judge-ready-product` at `ed96828`, with `origin/main` already contained in the branch. The working tree also contains an uncommitted frontend route/workflow implementation plus transaction date filtering. These changes pre-date this revalidation and are being preserved in place; no pull, reset, clean, checkout, or branch switch was performed.

| Check | Current result | Evidence / limitation |
| --- | --- | --- |
| Complete PRD read | Passed | Read all 3,004 lines of `Pactra-PRD-Judge-Ready.md` before edits |
| Git/worktree audit | Passed | Existing tracked modifications and untracked PRD/agent/frontend files identified and preserved |
| Backend tests | Passed | `.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider`: 55 passed; writable `TEMP`/`TMP` required by the managed sandbox |
| Clean migration | Passed | `alembic upgrade head` completed against a new SQLite database under `artifacts/` |
| Frontend lint | Passed | `npm run lint` |
| Frontend production build | Passed | `npm run build`; Vite 5.4.21, 1,616 modules transformed |
| Production dependency audit | Passed | `npm audit --omit=dev --json`: 0 vulnerabilities. The full development-tool audit reports 14 advisories (13 moderate, 1 high), primarily in PRD-pinned Vite 5 and ESLint tooling; production output is static and the development server must remain localhost-only. |
| Playwright | Passed | Six Chromium journeys passed against migrated SQLite state and isolated API/Vite servers, including assistant persistence/idempotency and policy failure recovery. The managed Windows sandbox requires approved execution for Vite/esbuild and Chromium; CI uses normal Linux orchestration. |
| Live Gemini | Blocked by external configuration | Local fallback is testable; no live API call is claimed |
| Live PayPal Sandbox | Blocked by external configuration | Mocked adapter tests pass; no live payout is claimed |
| PostgreSQL trigger/locking verification | Not run locally | Requires a PostgreSQL service; migration SQL and SQLite compatibility tests exist |

Current architecture reality:

- The judge-ready backend is committed and active: Alembic schema, user/session auth, ledger, reservations, policies, transaction service, approvals, PayPal payout reconciliation, assistant service, and owner-scoped APIs.
- A legacy demo `agent.py` / `policy_engine.py` / float model path remains in the repository and is exercised only by legacy tests. It is not registered by `backend/main.py`, but it violates the PRD's single-implementation rule and must be retired without removing user files.
- The authenticated React workspace and Playwright tests are integrated with the active API. The production build, lint, and six credential-independent judge journeys pass.
- `.env.example`, `render.yaml`, and `README.md` still describe the obsolete Gemini model, mock-first PayPal flow, and ephemeral SQLite deployment. They are not submission-ready.

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
- [~] Integer-cent money model is active; legacy float demo modules/tables remain and must be retired
- [x] User-owned auth/wallet records and owner-scoped queries; unsafe global legacy payment routes are authenticated and fail closed until replacement
- [x] Append-only double-entry schema, service postings and PostgreSQL balance/immutability triggers
- [x] Immutable PostgreSQL ledger trigger plus compensating internal/provider reversal services
- [x] Atomic reservations, available balance and current-generation committed/reserved spend
- [x] Money-action idempotency with same-key replay and payload/action conflict detection

### Authentication and security

- [x] Registration, login, logout, current user and password change
- [x] Argon2id password hashing
- [x] Opaque server-side sessions with expiry, idle timeout, rotation and revocation
- [x] CSRF plus same-origin mutation checks
- [x] Strict CORS, security headers, production HTTPS/cookie guards and sandbox-only provider startup checks
- [x] Auth, assistant, policy, payment and top-up/reset rate controls
- [x] Cross-user wallet, ledger, transaction, conversation and approval isolation tests

### Wallet and policy

- [x] Atomic account bootstrap with 1,000 USD sandbox issuance
- [x] Idempotent preset top-ups and owner-scoped wallet ledger history
- [x] Available/reserved/posted balance API
- [x] Per-user policy versions, validation, reset and audit
- [x] Deterministic policy order and stable PRD reason codes
- [x] Policy evaluation and reservation in one transaction

### Transaction lifecycle

- [x] Unified manual/AI transaction application service
- [x] Internal sandbox rail
- [x] Full state machine: draft, pending, executing, completed, blocked, rejected, failed, cancelled, reversed
- [x] Atomic approve/reject and current-policy re-evaluation
- [x] Safe retry and internal-sandbox compensating reversal
- [x] Transaction attempts, audit events, receipts and lifecycle timeline API
- [x] Owner-scoped filtering, cursor pagination, bounded date ranges and current/all-generation history

### PayPal Sandbox Payouts

- [x] Sandbox OAuth and one-item Payouts batch creation adapter
- [x] Sandbox-host startup guard and explicit integration status
- [x] Stable transaction/attempt sender batch and request IDs
- [x] Batch plus payout-item reconciliation
- [x] Hold retention for processing/unknown provider outcomes
- [x] Ledger capture only after item `SUCCESS`
- [x] Terminal failure release and returned/reversed/refunded compensation
- [x] DB-backed reconciliation worker and manual refresh endpoint
- [B] Real Sandbox submission was verified through item-level `FAILED`; terminal `SUCCESS` still requires a distinct active Sandbox recipient that can receive USD

### AI assistant

- [x] Migrate active assistant path to `google-genai==2.23.0` and `gemini-3.8-flash`
- [x] Persist user-scoped conversations and complete message history server-side
- [x] Conversation create/list/open/rename/archive/restore APIs with ownership enforcement
- [x] Assistant request replay protection prevents duplicate messages and payments
- [x] Strict allowlisted tools using authenticated transaction services
- [x] Deterministic parser fallback and clarification behavior
- [x] AI rate/turn/input/output limits and prompt-injection boundaries
- [B] Live Gemini request reached the configured model but returned provider `503 UNAVAILABLE`; deployed tool-call success remains unverified

### Frontend and judge experience

- [x] Public landing, sign-up and sign-in routes
- [x] Authenticated app shell and route guards
- [x] Overview, payment form, assistant, approvals, transactions, receipt, policies, wallet, settings and PayPal integration routes
- [x] Wallet top-up/reset, policy category editing, approve/reject, retry/reverse and provider reconcile flows, including explicit top-up confirmation
- [x] Meaningful AG Grid transaction history with mobile fallback and receipt navigation
- [x] Loading, empty, error, success, session-expiry and honest provider-pending states for P0 journeys
- [~] Guided judge checklist uses real persisted transactions; PayPal and insufficient-funds scenarios remain to be added
- [~] Responsive and keyboard-accessible P0 journeys build cleanly; browser/axe verification remains

### Quality, deployment and documentation

- [x] Backend unit/integration/concurrency/security coverage: 63 tests pass locally, with 2 PostgreSQL-only runtime tests delegated to CI
- [x] Nine Playwright journeys cover the core flow, policy lifecycle, cross-user isolation, API recovery, persisted assistant conversations, retry idempotency, auth error handling and mobile layout
- [x] CI with PostgreSQL migration/test jobs, frontend lint/build/audit and Playwright
- [x] Managed PostgreSQL Render blueprint and Alembic pre-deploy migration step
- [x] `/api/health` and `/api/ready`
- [x] README, environment, reset and judge walkthrough documentation
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

### Remaining external or owner-controlled work

1. Add the verified Gemini key to the deployed environment and rerun the configured `gemini-3.8-flash` tool path after the provider's temporary `503 UNAVAILABLE` condition clears.
2. Configure a distinct active PayPal Sandbox recipient that can receive USD, then rerun the payout until item-level `SUCCESS`; the latest real attempt ended `FAILED` and was reconciled safely.
3. Deploy the Render blueprint, run the documented public smoke path, and add the final live/demo URLs.
4. Retire the inactive legacy `agent.py` / `policy_engine.py` / PayPal Orders compatibility code in a separately approved cleanup; it is not imported or mounted by `backend/main.py`, but remains importable for pre-existing legacy tests.

### Exact remaining acceptance tests

- No route mounted by the active FastAPI app uses float money, global policy snapshots, PayPal Orders, or demo-success provider IDs. Legacy compatibility modules remain isolated from the app pending separately approved removal.
- `pytest -ra` covers account isolation, ledger idempotency/concurrency, approval single-use, reset preservation, PayPal item states, unknown outcomes, local capture recovery, and Gemini partial failures.
- Policy UI can add/remove valid categories while keeping one positive budget per category; invalid edits never save.
- A fresh browser account can top up, auto-execute, create/approve/reject, block, use assistant fallback, inspect a receipt, filter history, and reset without duplicate postings.
- PayPal-disabled UI never offers or labels a provider payout; PayPal-enabled configuration exposes only the sandbox recipient shortcut and honest provider state.
- CI migrates a clean PostgreSQL database before backend tests; frontend lint/build and Playwright run from clean installs.
- Production configuration requires PostgreSQL, secure cookies, a strong secret, exact origins, sandbox-only PayPal host, and migrations before startup.
- README and `.env.example` contain no secrets, no live-money instructions, and no claims that mock or unverified provider paths succeeded.

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
- The nine implemented Playwright journeys pass and collectively exercise the credential-independent P0 flow; credential-dependent and public-deployment smoke is reported separately.

## Progress log

- 2026-11-03: Phase 0 repository/PRD audit complete. Baseline backend tests, frontend lint and frontend build pass. No tracked user changes were present.
- 2026-11-03: T-02 schema slice complete. Dependencies pinned, PostgreSQL/SQLite settings added, Alembic initial migration creates all PRD tables/system accounts, PostgreSQL SQL generation succeeds, and 12 backend tests pass including clean migration verification.
- 2026-11-03: CP-1 auth/ledger slice complete. Added Argon2id registration/login/password change, opaque revocable sessions, same-origin CSRF, atomic account bootstrap, wallet summary/top-up/ledger APIs, ownership checks, balanced postings and reservation concurrency coverage. Unsafe global legacy payment routes now fail closed behind authentication until the unified service replaces them. Full backend suite: 21 passed. Clean local `alembic upgrade head`: passed.
- 2026-11-03: Backend lifecycle checkpoint complete. Added versioned per-user policies, deterministic ordered evaluation, unified manual/assistant transaction application, internal execution, approvals/rejections, safe retry/reversal, receipts/history/spend summary, immutable sandbox reset, PayPal Sandbox Payouts submission plus payout-item reconciliation, and persisted Gemini/fallback conversations. Provider timeout, item-success, terminal-failure and returned-payment tests retain/capture/release/compensate correctly. Full backend suite: 45 passed. Live Gemini and PayPal smoke remain credential-blocked.
- 2026-11-03: Phase 0 revalidation of the current branch complete. PRD read in full; current uncommitted work preserved. Backend suite passes 46 tests with a sandbox-local temp directory, clean SQLite migration passes, frontend lint/build pass, and production npm audit reports zero vulnerabilities. Playwright is currently blocked before test execution by the managed sandbox denying its spawned Vite/esbuild child process; this is recorded separately from product failures.
- 2026-11-03: Final local verification complete. Backend suite: 50 passed with one upstream Starlette/httpx deprecation warning. A new SQLite database migrated to head. Frontend lint and Vite production build passed with 1,614 modules transformed. Production dependency audit reported zero vulnerabilities. Four Chromium Playwright journeys passed against fresh migrated state. YAML parsing, secret-pattern scanning, route/auth review and `git diff --check` found no release-blocking local defect. Live PostgreSQL, Gemini, PayPal Sandbox and public deployment smoke remain external-environment blockers and are not claimed.
- 2026-11-03: Conversation, policy UX and frontend redesign complete. Added migration `20261103_0002`, owner-scoped conversation lifecycle APIs, chronological persisted messages, assistant request replay protection, truthful backend-confirmed action wording, strict policy create/edit validation and immutable version history. Reworked the authenticated shell and all judge-facing surfaces into the restrained dark control-room system, including a mobile composer that remains visible with dynamic viewport changes. Final verification: 55 backend tests passed, frontend lint passed, production TypeScript/Vite build passed with 1,616 modules transformed, clean SQLite migration reached `20261103_0002`, and all 6 Chromium journeys passed. Live Gemini, PayPal Sandbox and public deployment smoke remain credential/environment blocked and are not claimed.
- 2026-11-05: Final release hardening complete. Fixed PostgreSQL UUID/runtime compatibility, production cross-origin CSRF/session handling, strict production configuration, policy version concurrency, reservation accounting, Gemini retry/error disclosure and post-tool partial failures, PayPal reconciliation wording, retry-stable frontend mutations, transaction pagination, draft hydration, auth error handling, CI runner setup and unique Render service names. Verification: 63 backend tests passed with 2 PostgreSQL-only skips, clean migration passed, lint/build/pip check/production npm audit passed, and all 9 Chromium journeys passed. Live Gemini success, PayPal item success and public deployment remain explicitly unclaimed.
- 2026-11-06: Oracle runtime hardening complete on branch `codex/submission-ready-20261106`. PostgreSQL 16 is loopback-only; the API and separate advisory-lock reconciliation worker are active under hardened systemd units. Verification: 69 PostgreSQL tests, 67 SQLite tests with 2 expected PostgreSQL skips, lint, production build, 9 Chromium journeys, pip audit, production npm audit, migration/restart recovery, and an internal production-mode judge journey passed. A live Gemini smoke fell back after `ServerError`; a real `$0.01` PayPal Sandbox payout reached item-level `FAILED` and released its hold. Public DNS/TLS, Vercel linkage, Gemini live success, and PayPal item-level `SUCCESS` remain release blockers.
