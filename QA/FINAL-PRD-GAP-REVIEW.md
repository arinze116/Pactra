# Pactra Final PRD Gap Review

> Historical baseline from the original gap audit. Provider-configuration and
> test-count statements are superseded by `QA/ACCEPTANCE-EVIDENCE.md`,
> `QA/INTEGRATION-STATUS.md`, and `QA/RELEASE-READINESS.md`.

Review date: 2026-11-07 (Africa/Lagos)

PRD baseline: `Pactra-PRD-Judge-Ready.md`

Audited production URL: `https://pactra-nine.vercel.app`

Audited production release: `0e3e905`

Database migration: `20261107_0004`

Vercel deployment: `dpl_J1s82vJdXHaYinj1Y5k61VpS1wQU`

## Executive summary

This review reconciles the completed seven-report QA audit against every material acceptance criterion in the Judge-Ready PRD. It does not repeat the audit and did not execute provider calls, mutate production data, change configuration, deploy code or trigger any payout.

| Measure | Result |
|---|---:|
| Features discovered | 64 |
| Fully functional | 50 |
| Partial | 9 |
| Disabled/unconfigured | 4 |
| Broken | 0 |
| Not implemented | 1 |
| Additional cross-feature PRD gaps | 3: approval context, repeatability E2E evidence, guided analytics |
| Prior audit executions/checks | 201 |
| Passed/clean | 200 |
| Functional failures | 0 |
| Checks with findings | 1 dependency audit |
| Live-provider tests blocked | 2: Gemini and PayPal Sandbox |

The internal governed-payment path is strong: accounts, tenant isolation, policy evaluation, reservations, approval/rejection, double-entry accounting, receipts, history, reset and the deterministic assistant all passed on SQLite, isolated PostgreSQL and the public deployment. Production ledger and reservation invariants were clean.

Full PRD compliance is not achieved. The PRD makes live Gemini function calling and a real PayPal Sandbox Payouts transaction mandatory MVP and Definition-of-Done requirements. Production reports `ai_enabled=false`, `ai_configured=false` and `paypal_payouts_configured=false`. Mocks and deterministic fallback prove safe internal behaviour, not either live integration.

## Scope, method and status vocabulary

Sources reviewed:

- All seven reports under `QA/`.
- All 3,004 lines of `Pactra-PRD-Judge-Ready.md`.
- Relevant frontend, backend, worker, configuration and CI source for each gap.
- Existing test names, commands, outputs and production readiness evidence already recorded by the audit.

Statuses used here:

- **PASS** — the PRD criterion was exercised successfully with evidence.
- **PARTIAL** — meaningful implementation works, but one or more PRD criteria remain unmet or unproved.
- **BLOCKED** — implementation exists, but a safe conclusive test requires missing credentials, provider capability, explicit authorization or external action.
- **NOT IMPLEMENTED** — the PRD requirement is absent from the product.

No result is upgraded to PASS based only on source presence, mocks, deterministic fallback or UI copy.

## Detailed PRD gap register

### 1. AUTH-008 — Password reveal control

| Field | Reconciliation |
|---|---|
| Current state | **NOT IMPLEMENTED** |
| PRD requirement | §11.3, `/sign-up`: inline validation and password reveal. This is also part of T-10's requirement that route forms and interaction states be complete. |
| Current implementation | `frontend/src/pages/PublicPages.tsx:51-65` renders password inputs with `type="password"` and no reveal control. The same shared page serves sign-in and sign-up. |
| Existing evidence | `QA/TEST-MATRIX.md` AUTH-008; source inspection only. No automated test exists because the control is absent. |
| Why incomplete | The interaction was never implemented. |
| Cause | **Code**. No credential or infrastructure dependency. |
| Hackathon impact | Low judging risk, but it is the only wholly absent PRD feature and weakens completion/accessibility polish. |
| Estimated effort | Small: 1–2 hours including tests. |
| Exact closure test | On sign-up and sign-in, activate a keyboard-accessible show/hide button; assert the input toggles `password`/`text`, the value and focus are retained, the control exposes an accessible name and `aria-pressed`, Enter/Space work, and registration/login still pass in desktop and mobile Playwright runs. |

### 2. AI-006 / INT-005 — Live Gemini provider and deployed configuration

| Field | Reconciliation |
|---|---|
| Current state | **BLOCKED / DISABLED / UNCONFIGURED** |
| PRD requirement | §6.1 item 5 requires a Gemini assistant with typed function calling. US-05 requires supported language to call the same governed transaction service as the manual form. F-05 specifies server-only `google-genai`, `gemini-3.8-flash`, typed tools and safe fallback. §19, §20, T-09 and §33 require Gemini function calling to be configured and exercised on the deployed judge instance. §5 counts Gemini function calling in the judging path as a success metric. |
| Current implementation | Tool declarations are in `backend/services/assistant.py:54-119`; authenticated tool execution is in `:539-583`; the live model loop, timeout, retry and function responses are in `:586-701`; deterministic fallback begins at `:704`. `backend/config.py:38-42` defaults AI off and `:177-180` requires a key and exact model before enablement. |
| Existing evidence | Assistant persistence, prompt-injection resistance, tool-argument validation, provider-failure audit and deterministic fallback pass in backend and E2E tests. Production `/api/ready` reports `ai_enabled=false` and `ai_configured=false`. No live Gemini request was made or claimed. |
| Why incomplete | The deployed provider has no approved credential and is disabled. Provider reachability, model entitlement, quota, actual function calling, timeout and malformed-response handling have not been verified against Gemini. |
| Cause | **Credentials + configuration**, with possible **external provider/quota infrastructure**. The application code is substantially implemented. |
| Hackathon impact | **Submission-critical P0.** The AI sponsor/judging story cannot be truthfully demonstrated as live. Deterministic parsing is a fallback, not proof of Gemini integration. |
| Estimated effort | 2–4 hours after a valid credential is supplied; longer if model access, quota or regional availability fails. |
| Human action required | Supply an approved Gemini API key with access to `gemini-3.8-flash`; authorize secret installation and AI enablement on the deployed server. |
| Exact closure test | On the public judge deployment, enable `AI_ENABLED=true` with the approved key and exact model. From a fresh isolated account, send a natural-language request that causes an actual Gemini function call to `create_payment_request`; verify persisted user/assistant/tool messages, tool arguments, governed transaction, policy result, ledger or reservation, and audit events. Then invoke wallet, policy, recent-transaction and transaction-detail tools. Inject provider timeout, quota error and malformed response and verify safe audited fallback without duplicate transactions, policy bypass, tenant leakage, secret logging or uncaught UI error. |

### 3. PAY-010 / INT-002 / INT-003 — PayPal Sandbox execution and live reconciliation

| Field | Reconciliation |
|---|---|
| Current state | PAY-010 and INT-002: **BLOCKED / DISABLED / UNCONFIGURED**. INT-003: **PARTIAL** because provider-independent reconciliation passes but live recovery is unproved. |
| PRD requirement | §6.1 item 12, US-12 and F-11 require real PayPal Payouts REST API v1 execution against Sandbox, stable transaction-derived IDs, item-level status reconciliation, reservation retention while pending/unknown, capture only on item `SUCCESS`, release on terminal failure and compensating credit on later returned/reversed/refunded state. §5 requires at least one deployed payout batch created and reconciled. §28 E2E cases 11–12, §30, T-14 and §33 require an actual Sandbox smoke test and judge-triggerable provider path. The PRD explicitly says T-14 must not be cut. |
| Current implementation | Sandbox-only configuration guards are in `backend/config.py:44-52`, `:112-125` and `:168-176`. OAuth, batch submission and item status retrieval are in `backend/paypal_client.py:46-225`. Stable provider IDs are generated in `backend/paypal_client.py:127-169`. Submission/reconcile orchestration is in `backend/services/paypal.py:26-94`. The worker and PostgreSQL advisory lease are in `backend/worker.py:21-143`. Item-level capture, failure, unknown-state retention and provider reversal are in `backend/services/transactions.py:783-984`. The UI exposes truthful status, configured-recipient selection, provider refresh and provider references. |
| Existing evidence | `backend/tests/test_paypal_payouts.py` and transaction tests cover mocked OAuth/submission/status, stable IDs, definite failure, duplicate requests, timeouts, unknown outcomes, item-level capture rules, terminal release, reversal and cross-user denial. Worker lease/restart/standby tests pass. Production reports `paypal_payouts_configured=false`; the worker stands by. No payout was triggered. |
| Why incomplete | No current Payouts-enabled Sandbox business credential and approved recipient were available. A prior item-level Sandbox failure is previous evidence, not a success. OAuth, real batch creation, item `SUCCESS`, worker/manual reconciliation and retry behaviour against PayPal remain unproved. |
| Cause | **Credentials + configuration + external PayPal account capability/infrastructure**. Code paths are implemented but not provider-validated. |
| Hackathon impact | **Submission-critical P0.** This is the core PayPal judging requirement. A batch submission, mock provider ID, internal sandbox transaction or batch-level success does not satisfy the criterion. |
| Estimated effort | 3–6 hours after working credentials/capability are supplied; 1–2 days or more if PayPal must enable Payouts or resolve an account-level failure. |
| Human action required | Provide a PayPal Sandbox business app `CLIENT_ID` and `CLIENT_SECRET`, confirm that the business account has Payouts capability, supply a valid Sandbox recipient email/account, and explicitly authorize one no-real-money Sandbox payout test. If capability is absent, the account owner must resolve it with PayPal. |
| Exact closure test | Against `https://api-m.sandbox.paypal.com` only: (1) OAuth succeeds; (2) an approved Pactra payout creates exactly one real batch/item using the stable request and sender-batch IDs; (3) batch/item IDs persist; (4) `PENDING`/`PROCESSING`/unknown keeps the reservation; (5) item-level `SUCCESS` causes exactly one ledger capture and completed state; (6) manual refresh and the worker both reconcile safely; (7) retry after timeout reuses the unresolved attempt and creates no duplicate batch or capture; (8) terminal failure releases once; (9) a controlled returned/reversed/refunded provider fixture or permitted Sandbox outcome posts one compensating credit; (10) receipt and integration UI show actual recipient, PayPal rail, provider reference and status. Verify database journals, entries, reservations, attempts and audit events after each transition. |

### 4. PLT-006 — Guided judge scenarios and analytics

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-10 requires repeatable judge operation. F-10 requires guided tests for auto-approved, approval-required internal payout, PayPal Sandbox payout, blocked, insufficient-funds and reset scenarios, with real transactions rather than fake UI state. §29 specifies the seeded scenarios. T-12 requires auto, pending, blocked, rejected, insufficient-funds and reset. F-10 and §27 require `judge.guided_test_started` and `judge.reset_confirmed`. |
| Current implementation | `frontend/src/pages/OverviewPage.tsx:57-68` exposes five checklist steps: auto payment, approval, policy block, rejection and reset. `frontend/src/pages/PaymentPages.tsx:53-70` defines a PayPal preset, but it is not part of the guided checklist. No insufficient-funds preset or guided analytics event implementation was found. |
| Existing evidence | Core Playwright journeys exercise auto, approval, blocked, rejection and reset. `QA/TEST-MATRIX.md` PLT-006 records the missing PayPal and insufficient-funds cases. No evidence exists for the two required analytics events. |
| Why incomplete | The checklist and instrumentation implement only a subset of the PRD. The live PayPal step additionally depends on provider configuration. |
| Cause | **Code** for missing checklist steps and analytics; **credentials/configuration/external provider** for completion of the PayPal step. |
| Hackathon impact | High. Judges cannot discover and repeat the complete required story from the product, and the provider scenario is absent from the main walkthrough. |
| Estimated effort | 4–8 hours for code and E2E after PayPal credentials are available. |
| Exact closure test | Register a fresh judge account and complete all six persisted guided scenarios plus reset from the checklist. Assert each step advances only after the corresponding server record/state exists; the insufficient-funds scenario creates the correct persisted failure/block without a debit; the PayPal scenario reaches a real provider result; reset starts a new generation while history remains; and exactly one `judge.guided_test_started` plus one `judge.reset_confirmed` event is persisted/emitted with no secrets or private data. |

### 5. PAY-003 — Persisted blocked transaction API contract

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-04 requires a policy-blocked request to persist with a human-readable reason and no funds moved. §17 requires `422 POLICY_BLOCKED` with the persisted blocked transaction body, and `402 INSUFFICIENT_FUNDS` with the persisted transaction body. T-08 requires the exact API errors in §17. |
| Current implementation | The unified service safely persists blocked transactions and audits them without posting a journal. `backend/main.py:822-859` declares a 201 response and converts `PolicyBlocked` into a normal `PaymentResponse`, deliberately diverging from the specified error contract. |
| Existing evidence | Backend/API/E2E tests prove persistence, policy reason and no ledger movement. `QA/TEST-MATRIX.md` PAY-003 and BUG-004 record the 201-versus-422/402 mismatch. |
| Why incomplete | Product/API behaviour intentionally favours returning the receipt as success, but the PRD and API specification require typed error status codes with the persisted body. |
| Cause | **Code/product-contract decision**. |
| Hackathon impact | Medium. Financial behaviour is safe, but API-contract reviewers and automated acceptance tests can fail. |
| Estimated effort | 2–4 hours after the owner confirms the contract. |
| Human action required | Product owner confirms whether the PRD remains authoritative. If so, return the specified status codes while preserving the created transaction payload. |
| Exact closure test | Submit an over-limit request and assert HTTP 422, code `POLICY_BLOCKED`, human-readable first rule and persisted transaction ID/body. Submit an insufficient-balance request and assert HTTP 402, code `INSUFFICIENT_FUNDS` and persisted body. Refresh each receipt, verify zero ledger posting and correct audit event, and retry the same idempotency key to receive the original blocked result without a duplicate row. |

### 6. PAY-005 / BUG-007 — Approval decision context

| Field | Reconciliation |
|---|---|
| Current state | Core approval mechanics **PASS**; PRD approval-card UX is **PARTIAL**. |
| PRD requirement | F-07 requires pending requests ordered oldest first and showing requester, vendor, amount, category, reason, policy result, available balance and created time. §11.3 `/app/approvals` also requires requester, policy check and age. |
| Current implementation | `backend/services/transactions.py:987-997` returns owned oldest-first `PaymentTransaction` rows. `frontend/src/pages/TransactionPages.tsx:52-56` renders vendor, reason, amount, category and rail, but not requester, detailed policy result, available balance or age. |
| Existing evidence | Backend, PostgreSQL race, local E2E and public tests prove approve/reject ownership, atomicity, reservation outcomes and single use. BUG-007 records the missing context. |
| Why incomplete | The compact approval DTO and card do not expose/render all information required for a reviewer to make the decision. |
| Cause | **Backend DTO/API + frontend code**. |
| Hackathon impact | Medium-high. The approval workflow functions, but the judge sees less policy/accountability evidence at the decision point than the PRD promises. |
| Estimated effort | 4–6 hours including DTO, UI and regressions. |
| Exact closure test | Create a pending request and assert the approval card or drawer shows requester identity, vendor, amount, category, reason, current policy decision/checks, available balance, created timestamp and human-readable age from server data. Reload and verify persistence; modify policy/balance and verify refreshed authoritative context; confirm another user still receives 404/no card. |

### 7. Reset, retry and reversal repeatability evidence — WAL-007 / PAY-009 / US-08 / US-10

| Field | Reconciliation |
|---|---|
| Current state | Backend behaviour **PASS**; complete browser/provider repeatability evidence is **PARTIAL/BLOCKED**. |
| PRD requirement | US-08 requires idempotent retry and compensating reversal. US-10 and F-10 require reset to start a clean generation while retaining immutable history, releasing/cancelling pending work and blocking during unresolved provider execution. §28 E2E case 8 and §30 require repeatable deployed smoke coverage. |
| Current implementation | Receipt retry/reverse actions are in `frontend/src/pages/TransactionPages.tsx:207-239`; reset is implemented in `frontend/src/pages/ControlPages.tsx`. Backend services preserve history, use compensating journals and enforce eligible states. |
| Existing evidence | Backend transaction, ledger, ownership, idempotency and PostgreSQL concurrency tests pass. Judge E2E proves a basic reset balance/generation path. Browser E2E does not directly exercise retry or reversal, and reset coverage does not explicitly assert every PRD preservation/blocking rule. Live provider retry/reversal reconciliation is blocked by PayPal configuration. |
| Why incomplete | The remaining gap is acceptance evidence, not a confirmed internal-ledger defect. Provider-dependent repeatability cannot be closed with mocks alone. |
| Cause | **Test coverage**; **credentials/configuration/external provider** for live PayPal cases. |
| Hackathon impact | Medium. Reset/repeatability is a judge-readiness differentiator, and unexercised controls create avoidable demo risk. |
| Estimated effort | 3–5 hours for isolated/browser tests; provider cases are included in the PayPal effort. |
| Exact closure test | In Playwright, create and reverse a completed internal payment; assert the original journal is unchanged, one compensating journal appears, balance restores and a second reversal conflicts. Create an eligible failed internal transaction, retry twice with the same key and assert one terminal result/capture. Before reset, create pending approval and assert reset cancels/releases it, increments generation, restores baseline/current counters, retains all-history receipt and records a reset journal/audit. In an isolated provider fixture and then the configured Sandbox, assert reset is blocked while a payout outcome is unresolved and succeeds only after terminal reconciliation. |

### 8. POL-007 — Server-authoritative likely-decision preview

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | §11.3 `/app/payments/new` requires a policy preview showing current limits and the likely decision before submission. T-10 requires the form interactions to be complete. |
| Current implementation | `frontend/src/pages/PaymentPages.tsx:197-200` checks only whether the amount reaches the approval threshold. `:278` displays a static decision order. It does not evaluate vendor blocks, category, cap, daily/category budgets, balance or the first failing rule. |
| Existing evidence | Form E2E confirms current limits/threshold confirmation and authoritative server enforcement after submit. `QA/TEST-MATRIX.md` POL-007 records the missing full preview. |
| Why incomplete | Frontend approximation is not equivalent to the server policy engine and can only predict approval-threshold behaviour. |
| Cause | **Code/API design**. |
| Hackathon impact | Medium. Judges can still submit safely, but the promised proactive control experience is incomplete. |
| Estimated effort | 4–6 hours. |
| Exact closure test | Provide a read-only, owner-scoped, server-authoritative preview that reuses the policy evaluator without creating a transaction or reservation. For exact boundary, blocked vendor, invalid category, per-transaction cap, daily budget, category budget, insufficient balance and approval-threshold cases, assert `approved`, `approval_required` or `blocked` and the same first reason later returned by real creation. Assert database transaction/reservation/journal counts remain unchanged after preview. |

### 9. PLT-004 — Recoverable and partial data states

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-09 requires API failures to show a recoverable error and retry action. §11.4 requires available sections to remain visible when only part of a page fails. §23 requires visible recovery and safe GET retry/backoff. T-10 requires loading, empty, error and success states. |
| Current implementation | `frontend/src/pages/OverviewPage.tsx:22-40` groups wallet, spend summary, transactions and approvals in one inner `Promise.all`; any one failure prevents all four core results from updating. `frontend/src/pages/ControlPages.tsx` groups wallet/ledger and its wallet error notice has no explicit retry callback. Transaction-history recovery does include retry. |
| Existing evidence | Route crawl and transaction recovery E2E pass. `QA/TEST-MATRIX.md` PLT-004, BUG-008 and BUG-013 record the remaining cases. |
| Why incomplete | Error handling is page-level where the PRD requires section-level resilience, and the wallet recovery action is absent. |
| Cause | **Frontend code**. |
| Hackathon impact | Medium. A single transient API failure can blank the overview and make a judge think the whole product is down. |
| Estimated effort | 3–5 hours. |
| Exact closure test | Independently fail wallet, summary, transactions and approvals GETs; assert unaffected overview sections remain populated, the failed section has a specific retry, retry restores it without reloading the route, and stale/partial data is not mislabeled as current. Fail wallet and ledger separately on `/app/wallet`; assert each has a keyboard-accessible retry and successful persistence after refresh. |

### 10. REC-003 — Lifecycle actor and event context

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-09 and F-09 require transaction detail to show lifecycle and timestamps; §10 and §11.3 require an auditable lifecycle timeline. The audit model records actor and operation context. |
| Current implementation | `backend/services/transactions.py:1114-1122` returns ordered `event_type`, `actor_type`, `payload` and time. `frontend/src/pages/TransactionPages.tsx:248` renders only event type and timestamp. |
| Existing evidence | Receipt/API tests prove event ordering and durable audit persistence. PostgreSQL rejects update/delete of audit events. UI source review confirms omitted context. |
| Why incomplete | Required data exists but is not presented to the judge. |
| Cause | **Frontend code**. |
| Hackathon impact | Low-medium. Auditability works technically, but the receipt undersells who/what caused each transition. |
| Estimated effort | 2–3 hours. |
| Exact closure test | For creation, approval, rejection, failure, retry, reversal, reset and provider events, assert the receipt shows chronological event name, safe actor label and a redacted human-readable payload summary after reload. Verify raw secrets, session identifiers and unrelated user data are never rendered. |

### 11. REC-004 — Receipt ledger account/counter-account detail

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-09 and F-09 require receipt ledger impact. F-08 requires append-only balanced journals and identifiable account/counter-account effects. §11.3 requires the receipt to show ledger impact. |
| Current implementation | `backend/services/transactions.py:1076-1113` returns journal type, direction, amount, currency and timestamps but no safe account label. `frontend/src/pages/TransactionPages.tsx:249` renders direction, journal type and amount only. |
| Existing evidence | Ledger/receipt tests and direct production invariant queries prove balanced postings, exactly two entries per journal and no duplicate captures. UI/API source review confirms the missing labels. |
| Why incomplete | Accounting is correct, but the detail DTO/UI cannot explain which wallet and counter-account each row affects. |
| Cause | **Backend DTO + frontend code**. |
| Hackathon impact | Low-medium. It reduces the clarity of the double-entry/accountability story during receipt inspection. |
| Estimated effort | 3–4 hours. |
| Exact closure test | For issuance, top-up, capture, reversal and reset journals, assert the owned receipt shows safe wallet and counter-account labels, debit/credit direction, amount and journal type; debits equal credits; no internal identifier reveals another user's account; blocked/pending receipts correctly show no posted entries. |

### 12. INF-005 — CI and dependency hygiene

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | US-11 requires backend tests, frontend lint/build, Playwright and public smoke to pass. §24 requires no known critical/high dependency vulnerabilities at release. §28 and T-15 require the release pipeline and CI quality gate. T-16 adds Lighthouse/WCAG verification. |
| Current implementation | `.github/workflows/ci.yml:38-58` runs Python dependency consistency, migrations/tests, frontend lint/build and production-only npm audit; E2E runs on PostgreSQL. It does not run `pip-audit`, full dev-tree npm audit or Lighthouse. |
| Existing evidence | SQLite: 83 passed/8 PostgreSQL-only skipped; isolated PostgreSQL: 91 passed; local and PostgreSQL E2E: 9 journeys plus 1 WCAG test each; production E2E: 2 passed; lint/build pass; Python audit and production npm audit are clean. Full npm audit reports 8 moderate and 1 high development-tool finding in Vite/esbuild and lint/minimatch chains. Lighthouse is 0.99 performance, 1.0 accessibility and 1.0 best practices. |
| Why incomplete | Runtime dependencies are clean, but the full development toolchain does not satisfy the PRD's unqualified high-vulnerability wording, and all audit/performance checks are not enforced in CI. Suggested upgrades are breaking majors. |
| Cause | **Dependency/toolchain code and CI configuration**. |
| Hackathon impact | Low for the running production bundle, medium for repository/security review and reproducibility. |
| Estimated effort | 4–8 hours if upgrades are straightforward; potentially longer for Vite/esbuild/lint breaking changes. |
| Exact closure test | Upgrade or replace affected development dependencies, or obtain a documented owner risk exception that explicitly narrows the PRD gate. Run `pip check`, `pip-audit -r requirements.txt`, production and full npm audits, lint, production build, PostgreSQL backend tests, all E2E and Lighthouse. CI must enforce the agreed audits and finish green with zero unaccepted high/critical findings. |

### 13. SEC-005 — Distributed rate limiting

| Field | Reconciliation |
|---|---|
| Current state | **PARTIAL** |
| PRD requirement | F-01, §17 and §24 require rate limits on public authentication endpoints and safe public deployment behaviour. |
| Current implementation | `backend/auth.py:40-67` uses a locked in-process fixed-window limiter. The audited deployment intentionally runs one Uvicorn worker, so current enforcement works, but counters are not shared across processes and reset on restart. |
| Existing evidence | Auth/config rate-limit tests pass, and production is single-worker. No multi-process/shared-state test exists. |
| Why incomplete | The implementation is correct only under the present single-process topology and is not horizontally safe. |
| Cause | **Architecture/code**. |
| Hackathon impact | Low for the preserved deployment; operational/security risk if the API is scaled or frequently restarted. |
| Estimated effort | 4–8 hours for a Redis- or PostgreSQL-backed limiter and concurrency tests. |
| Exact closure test | Run at least two API processes against one shared limiter; distribute concurrent registration/login attempts across them; assert the aggregate threshold produces the correct 429 and retry metadata. Restart one process and verify the active window is retained if durability is part of the chosen design. Confirm financial limits remain database-enforced and independent. |

## Complete PRD compliance matrix

### P0 user stories

| PRD item | Result | Reconciliation |
|---|---|---|
| US-01 Account access | PASS | Registration, login, generic invalid-credential error, protected-route handling and tenant isolation pass. Password reveal is a page-spec gap, not a failure of US-01's security criteria. |
| US-02 Sandbox funds | PASS | Initial $1,000 issuance, top-up idempotency, bounds and cross-user 404 pass. |
| US-03 Policy management | PASS | Validation, versioning, current-policy use and approval-time re-evaluation pass. |
| US-04 Manual payment | PARTIAL | Validation, persistence and policy enforcement pass; §17 blocked/insufficient HTTP contract does not. |
| US-05 AI payment | BLOCKED | Deterministic fallback and governed tool code pass; actual deployed Gemini function calling is unconfigured and untested. |
| US-06 Policy decisions | PASS | Rule order, threshold, reservation, balance and PostgreSQL concurrency pass. |
| US-07 Approval workflow | PARTIAL | Atomic approve/reject/revalidation passes; approval decision context is incomplete in the UI. |
| US-08 Sandbox ledger | PARTIAL | Internal ledger invariants, retry and reversal pass; browser retry/reversal evidence and live provider retry/reversal reconciliation remain incomplete/blocked. |
| US-09 History and receipt | PARTIAL | Ownership, filters, pagination and core receipt data pass; lifecycle context, ledger labels and some recoverable partial-data states are incomplete. |
| US-10 Judge readiness | PARTIAL | Reset, health and internal sandbox pass; full guided set/analytics and configured provider paths do not. |
| US-11 Quality gate | PARTIAL | Functional suites/build/public smoke pass; full development dependency audit has one high finding and several browser acceptance cases remain missing. |
| US-12 PayPal Sandbox payout | BLOCKED | Code/mocks exist; no authenticated real item-level success and reconciliation on the deployed environment. |

### Functional specifications

| PRD item | Result | Reconciliation |
|---|---|---|
| F-01 Authentication/account | PARTIAL | Core auth/security passes; password reveal is absent and rate limiting is process-local. |
| F-02 Wallet/test funds | PASS | Ledger-backed bootstrap, top-up, balance and reset pass. |
| F-03 Policy editor | PASS | Owner-scoped validation, saving and immutable versions pass. |
| F-04 Payment request | PARTIAL | Manual creation/recipient/rails pass; likely-decision preview and exact blocked HTTP contract do not. |
| F-05 AI assistant | BLOCKED | Typed, owner-scoped tools and fallback pass; live Gemini success is unproved. |
| F-06 Policy engine | PASS | Server-side deterministic order, snapshots, reasons and enforcement pass. |
| F-07 Approval queue | PARTIAL | Queue order and actions pass; requester, full policy context, available balance and age are absent. |
| F-08 Ledger/lifecycle | PARTIAL | Accounting/state machine passes; live provider transitions and some receipt account labels remain unproved/incomplete. |
| F-09 History/receipts | PARTIAL | Core records are accurate; actor/payload and account/counter-account display are incomplete. |
| F-10 Judge controls | PARTIAL | Reset and five internal checklist steps exist; full six-scenario set and required analytics are incomplete. |
| F-11 PayPal Sandbox Payouts | BLOCKED | Provider adapter/state machine exist; live authentication, item success and deployed reconciliation are not established. |

### Cross-cutting PRD sections and build checkpoints

| PRD section | Result | Reconciliation |
|---|---|---|
| §5 Goals/success metrics/judging map | PARTIAL | Internal product goals pass; Gemini function calling and deployed PayPal batch/reconciliation metrics do not. |
| §6 MVP scope | PARTIAL | Most MVP items ship; mandatory items 5 and 12 are disabled. |
| §9 Route inventory | PASS | Audited routes exist and production route crawl passes. |
| §10 User flows | PARTIAL | Internal core loop passes; judge demo path's live PayPal step does not. |
| §11 Design brief/page states | PARTIAL | Responsive/product UI passes broadly; password reveal, likely preview, approval context and partial-data recovery have gaps. |
| §12 Component inventory | PARTIAL | Required surfaces exist; missing password-reveal and incomplete decision/audit presentation remain. |
| §13 Exact stack | PASS | Audited implementation uses the specified principal stack/model setting; live model access is a configuration gap. |
| §14 Architecture | PARTIAL | Internal authority boundaries pass; external provider edges are not live-validated. |
| §16 Data model/schema | PASS | Migration `20261107_0004`, constraints, isolation and audit immutability pass. |
| §17 API specification | PARTIAL | Endpoint/authZ coverage passes except the 201 versus 422/402 blocked-transaction contract. |
| §18 Smart contract specification | PASS / N/A | No smart contract is required for the defined MVP. |
| §19 Third-party integrations | BLOCKED | Gemini and PayPal are implemented but unconfigured/unvalidated live. |
| §20 Environment variables | PARTIAL | Validation/guards pass; required Gemini/PayPal secrets and recipient are absent. |
| §21 Authentication/authorization | PASS | Session, CSRF, same-origin, cookie and owner-scope tests pass. |
| §22 State management | PASS | Server-authoritative state, refresh persistence and mutation idempotency pass. |
| §23 Error/loading/empty states | PARTIAL | Most pass; overview section isolation and wallet retry are incomplete. |
| §24 Security | PARTIAL | Core security tests pass; full dev audit has one high finding and rate limiting is not distributed. |
| §25 Performance | PASS | Public Lighthouse and initial bundle budget pass; AG Grid is a large lazy chunk but not a release failure. |
| §26 Accessibility | PASS with limitation | Automated WCAG 2.1 AA scans pass; manual screen-reader testing remains desirable but no confirmed PRD failure was found. |
| §27 Analytics/observability | PARTIAL | Health/log/audit evidence passes; required guided/reset analytics events are absent. |
| §28 Testing plan | PARTIAL | Unit/integration/PostgreSQL/E2E coverage is strong; live Gemini, live PayPal and browser retry/reversal cases remain open. |
| §29 Seed/demo data | PARTIAL | Internal presets exist; insufficient-funds and integrated guided PayPal paths are incomplete. |
| §30 Deployment | BLOCKED | Public sandbox-only deployment is healthy, but the required PayPal smoke test has not passed. |
| §31 README requirements | PARTIAL | Existing documentation is adequate for internal operation; live provider judge instructions cannot be validated until configuration succeeds. |
| T-01 through T-08 | PASS except T-08 contract | Baseline, migrations, auth, ledger, policy, state machine, approvals and owner-scoped detail pass; T-08 exact error contract is partial. |
| T-09 Gemini | BLOCKED | Implementation/mocks/fallback pass; deployed live function call does not. |
| T-10/T-11 frontend workflows | PARTIAL | Routes and primary interactions pass; identified page-state/context gaps remain. |
| T-12 guided/reset | PARTIAL | Reset works; the full guided set and analytics do not. |
| T-13 security | PARTIAL | Core security passes; dependency and distributed-limiter gaps remain. |
| T-14 PayPal, “do not cut” | BLOCKED | Actual Sandbox payout smoke acceptance has not succeeded. |
| T-15 deployment/CI/docs | PARTIAL | Deployment and functional CI are healthy; provider config and full audit gate are incomplete. |
| T-16 polish/final QA | PARTIAL | Automated accessibility/performance pass; listed UX and browser-evidence gaps remain. |

### Definition of Done (§33)

| Definition-of-Done criterion | Result |
|---|---|
| All P0 user stories pass | FAIL — US-05 and US-12 are blocked; several stories are partial. |
| User accounts/data isolated | PASS |
| Initial credit/top-ups ledger-backed and idempotent | PASS |
| Ledger invariant under concurrency, failure, retry and reversal | PARTIAL — internal path passes; live provider outcomes remain unproved. |
| Policy checks deterministic, versioned and server-side | PASS |
| Manual and AI requests use the same transaction service | PASS for implemented/fallback tool path; live Gemini invocation BLOCKED. |
| Gemini function calling configured/exercised on deployed instance | FAIL / BLOCKED |
| Approval/rejection work and cannot be replayed | PASS |
| All transaction states persisted and visible | PARTIAL — persisted; some lifecycle/ledger context is not visible. |
| All routes and loading/empty/error/success states implemented | PARTIAL |
| No decorative or inert primary controls | PASS in audited controls |
| Backend, lint/build and P0 E2E pass | PARTIAL — executed functional suites pass; live-provider P0 cases and browser retry/reversal remain open. |
| Security and cross-user tests pass | PASS with distributed-limiter/dependency limitations |
| Public deployment sandbox-only and durable PostgreSQL | PASS |
| One PayPal Sandbox Payouts transaction created and reconciled; judge can trigger another | FAIL / BLOCKED |
| Health/readiness endpoints work | PASS |
| README, env, migrations, seed/reset and instructions complete | PARTIAL pending live-provider closure |
| No console or uncaught API errors in core journeys | PASS in executed journeys |
| Judge can test all features without external credentials | FAIL — operator-side Gemini and PayPal credentials/configuration are absent. |

**Overall Definition of Done: NOT MET.**

## Prioritised remediation backlog

| Priority | Item | Required outcome | Effort | Blocker type |
|---:|---|---|---:|---|
| 1 | AI-006 / INT-005 live Gemini | Deployed real function calling plus safe failure/fallback evidence | 2–4 h after key | Human credential/config/provider |
| 2 | PAY-010 / INT-002 / INT-003 PayPal | Real Sandbox item `SUCCESS`, persisted IDs, reconciliation and exactly-once capture | 3–6 h after capability/credentials | Human credential/authorization/external provider |
| 3 | PLT-006 PayPal guided scenario | Make the real provider path judge-discoverable and repeatable | Included in 4–8 h guided work | Depends on PayPal |
| 4 | PAY-003 blocked HTTP contract | Align 422/402 response semantics and idempotent persisted body | 2–4 h | Product decision + code |
| 5 | PLT-006 insufficient-funds + analytics | Complete guided cases and required events | 4–8 h total guided work | Code |
| 6 | PAY-005 approval context | Show all PRD decision fields before action | 4–6 h | Code/API DTO |
| 7 | Reset/retry/reversal acceptance | Add complete browser and provider repeatability evidence | 3–5 h plus provider work | Tests/provider |
| 8 | POL-007 policy preview | Add server-authoritative, side-effect-free likely decision | 4–6 h | Code/API |
| 9 | PLT-004 recovery states | Isolate overview data failures and add wallet retry | 3–5 h | Code |
| 10 | REC-003 lifecycle context | Render actor and safe payload summary | 2–3 h | Code |
| 11 | REC-004 ledger labels | Return/render safe account and counter-account labels | 3–4 h | Code/API |
| 12 | AUTH-008 password reveal | Add accessible reveal controls and E2E | 1–2 h | Code |
| 13 | INF-005 dependencies/CI | Resolve or formally accept dev-tool findings; enforce audits | 4–8 h+ | Toolchain/owner decision |
| 14 | SEC-005 distributed limiter | Shared rate-limit state before horizontal scaling | 4–8 h | Architecture/code |

## Human blockers and required actions

1. **Gemini credential and model access** — provide an approved API key with `gemini-3.8-flash` access and authorize installation as a server-side secret plus `AI_ENABLED=true`.
2. **PayPal Sandbox business credentials** — provide Payouts-capable Sandbox business app client ID/secret. Production credentials and live endpoints must never be used.
3. **PayPal Sandbox recipient** — provide and confirm a valid Sandbox recipient account/email for `PAYPAL_TEST_RECIPIENT_EMAIL`.
4. **Explicit payout-test authorization** — authorize one Sandbox-only, no-real-money payout after credentials and recipient are verified. The prior failed/unknown item is not sufficient.
5. **External PayPal capability** — if Payouts is not enabled, the account owner must complete PayPal enablement/support steps; application code cannot grant this capability.
6. **Deployment operator action** — after approval, install secrets through the existing production secret mechanism, restart/deploy safely, and run the acceptance tests without exposing values in logs or reports.
7. **API contract decision** — confirm that the Judge-Ready PRD remains authoritative for `422 POLICY_BLOCKED` and `402 INSUFFICIENT_FUNDS` responses.
8. **Dependency-risk decision** — approve breaking development-tool upgrades or explicitly document a time-bounded risk exception if the PRD security gate is narrowed to shipped/runtime dependencies.

## Updated recommendation

### NO-GO — full PRD and hackathon submission readiness

The deployed internal sandbox product is suitable for controlled internal demonstration and would otherwise merit a **CONDITIONAL GO**. However, the Judge-Ready PRD explicitly classifies live Gemini function calling and real PayPal Sandbox Payouts as P0, must-ship, non-cut requirements and includes both in §33 Definition of Done. Neither has been configured and successfully exercised on the deployed judge instance, and PayPal has not reached verified item-level `SUCCESS` with reconciliation.

Therefore the honest final submission-readiness decision is **NO-GO** until both provider acceptance tests pass. This does not indicate a broken or unsafe core application; it indicates that the two sponsor-critical claims cannot yet be substantiated. Preserve release `0e3e905`, migration `20261107_0004` and the current database until approved credentials/actions are available and the remediation work is separately authorized.
