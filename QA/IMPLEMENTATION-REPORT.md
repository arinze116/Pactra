# Pactra PRD Gap Closure Implementation Report

Date: 2026-11-07

Branch: `codex/prd-gap-closure-20261107`

Production baseline preserved: `0e3e905`, migration `20261107_0004`

Release-candidate migration: `20261107_0005`

## Outcome

All code-only backlog rows in `FINAL-PRD-GAP-REVIEW.md` are implemented and
covered by passing isolated tests. Live Gemini and PayPal Sandbox acceptance
remain blocked by credentials, provider capability and operator authorization.
Nothing was deployed and no production data or infrastructure was changed.

## Gap implementation matrix

| Gap | Root cause | Implementation | Primary files | Verified result |
|---|---|---|---|---|
| AUTH-008 | Missing interaction | Added independent accessible reveal buttons for sign-in/sign-up with dynamic name, `aria-pressed`, keyboard use, focus and selection preservation | `frontend/src/pages/PublicPages.tsx`, `frontend/tests/e2e/judge-flow.spec.ts` | PASS on desktop/mobile registration and login |
| AI-006 / INT-005 | Credential/configuration gate | Existing exact `gemini-3.8-flash` implementation retained; no model substitution or fabricated provider result | `backend/services/assistant.py`, `backend/config.py` | BLOCKED for live provider acceptance |
| PAY-010 / INT-002 / INT-003 | Credential/capability/authorization gate | Existing item-level state machine retained; no payout attempted | `backend/services/paypal.py`, `backend/paypal_client.py`, `backend/worker.py` | BLOCKED for real Sandbox item `SUCCESS` |
| PLT-006 internal scenarios | Incomplete checklist/instrumentation | Added persisted insufficient-funds scenario, PayPal truth-state step, reset step and unique guided/reset analytics events | `backend/services/judge.py`, `backend/main.py`, `backend/services/sandbox.py`, `frontend/src/pages/OverviewPage.tsx`, `frontend/src/pages/PaymentPages.tsx` | PASS for all internal scenarios; PayPal step remains blocked |
| PAY-003 | API contract divergence | Persisted blocks now return exact 422/402 domain errors with transaction, policy and balance details; replay returns the same persisted outcome | `backend/main.py`, `frontend/src/api.ts`, `frontend/src/pages/PaymentPages.tsx` | PASS; no journal/reservation and receipt remains retrievable |
| PAY-005 / BUG-007 | DTO/UI omitted decision context | Added server-authoritative requester, current policy/checks/version and balance; rendered created time and age | `backend/schemas.py`, `backend/services/transactions.py`, `backend/main.py`, `frontend/src/pages/TransactionPages.tsx` | PASS with ownership/order/reload/action regressions |
| WAL-007 / PAY-009 / US-08 / US-10 | Acceptance evidence gap | Added browser reversal/retry evidence, second-action conflict, reset analytics, and unresolved-provider reset fixture | `frontend/tests/e2e/judge-flow.spec.ts`, `scripts/seed_e2e_failed_transaction.py`, `backend/tests/test_transactions.py` | PASS for isolated internal/provider-state fixtures |
| POL-007 | Frontend-only approximation | Added owner-scoped preview endpoint using the production evaluator with no mutation | `backend/services/policies.py`, `backend/main.py`, `backend/schemas.py`, `frontend/src/pages/PaymentPages.tsx` | PASS; evaluator boundaries and no-side-effect API checks pass |
| PLT-004 | Coupled page requests | Split overview and wallet requests into independent loaders with section-specific retry and stale labels | `frontend/src/pages/OverviewPage.tsx`, `frontend/src/pages/ControlPages.tsx` | PASS for independent failure/recovery without route reload |
| REC-003 | Existing audit context not presented safely | Added actor labels and allow-listed human summaries; raw payloads are not returned to the browser | `backend/services/transactions.py`, `frontend/src/pages/TransactionPages.tsx` | PASS for ordering, persistence and redaction checks |
| REC-004 | Receipt DTO lacked safe account identity | Added safe account/counter-account labels and balanced debit/credit totals | `backend/services/transactions.py`, `frontend/src/pages/TransactionPages.tsx` | PASS for posted and non-posted receipts |
| INF-005 | Vulnerable dev toolchain and incomplete CI | Upgraded Vite/plugin, pinned safe minimatch override, added full audits, pip-audit and Lighthouse CI gate | `frontend/package.json`, `frontend/package-lock.json`, `requirements-dev.txt`, `.github/workflows/ci.yml`, `frontend/scripts/assert-lighthouse.mjs` | PASS; production/full npm and Python audits report zero findings |
| SEC-005 | Process-local counters | Replaced counters with atomic hashed PostgreSQL/SQLite buckets and `Retry-After`; added forward-only migration | `backend/auth.py`, `backend/models.py`, `backend/migrations/versions/20261107_0005_shared_rate_limits.py` | PASS under concurrent independent sessions and restart-state test |
| PLT-006 PayPal guided step | Depends on real provider truth | Step is discoverable but cannot complete unless a persisted PayPal item is `SUCCESS` | `frontend/src/pages/OverviewPage.tsx`, `frontend/src/pages/PaymentPages.tsx` | BLOCKED, truthfully labelled unconfigured |

## Security and financial review

- Provider success rules were not weakened.
- Policy, ownership, CSRF, idempotency and ledger services remain authoritative.
- Rate-limit keys are SHA-256 hashes; raw emails/IP-derived keys are not stored.
- Preview creates no transaction, reservation, journal, ledger entry or audit event.
- Blocked and insufficient outcomes persist without moving funds.
- Receipt event summaries are allow-listed and exclude raw payloads.
- Migration `0005` is additive and does not rewrite financial or identity data.

Mocks and fixtures prove deterministic failure/state handling only. They do not
prove live Gemini or PayPal functionality. No live provider call was made.
