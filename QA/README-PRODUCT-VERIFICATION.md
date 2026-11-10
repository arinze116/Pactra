# README-to-Product Verification Matrix

Updated: 2026-11-09

Branch: `audit/full-codebase-readme-webapp-reconciliation`

This is the current claim matrix. Older inventory, gap-review, and bug-report
files are retained as dated historical snapshots.

| README claim | Implementation evidence | Executed evidence | Status |
|---|---|---|---|
| Sandbox-only product | production config guards; internal and PayPal Sandbox rails | config tests; public copy and route review | PASS |
| Registration uses an 8 to 128 character password policy | `backend/schemas.py`, shared frontend password constants | seven-character rejection and exact eight-character API/browser lifecycle | PASS |
| Argon2id and opaque sessions | `backend/auth.py`, `AuthSession` | auth suite and browser logout/login/change-password path | PASS |
| CSRF and same-origin mutation protection | `require_csrf`, `require_same_origin`, browser token client | backend and browser negative tests | PASS |
| Owner-scoped records | owner filters in API/services | API and browser tenant-isolation tests | PASS |
| Double-entry simulated wallet | `backend/services/ledger.py`; PostgreSQL trigger migrations | SQLite ledger tests; accepted PostgreSQL CI evidence | PASS, current-branch PostgreSQL CI pending |
| Deterministic versioned policy | policy service and preview endpoint | boundary, precedence, re-evaluation, and browser tests | PASS |
| Human approval and rejection | conditional state changes and `ApprovalAction` | duplicate, race, rejection, expiry, and browser tests | PASS |
| Manual and AI requests share governance | assistant tools call transaction service | assistant, transaction, policy, and E2E tests | PASS |
| AI cannot approve, submit a payout, or mutate the ledger directly | tool declarations, server-side handlers, worker boundary | source trace and failure-path tests | PASS |
| Retired pre-account agent cannot contact Gemini or execute a provider payment | provider-free fail-closed shim in `backend/agent.py` | configured-key rejection and disabled-execution tests | PASS |
| Deterministic AI fallback | assistant service fallback parser and audit classification | timeout, 503, empty/malformed, invalid arguments, and E2E tests | PASS |
| Genuine Gemini function calling passed for the accepted model | retained provider acceptance evidence | `QA/GEMINI-MODEL-COMPATIBILITY.md`; not re-executed here | PASS, retained evidence |
| API never submits PayPal | no PayPal client call in API transaction routes | monkeypatched regression and source trace | PASS |
| Worker is the sole PayPal submission authority | `backend/worker.py`, `backend/services/paypal.py` | worker claim/idempotency tests | PASS |
| PayPal capture requires item-level `SUCCESS` | reconciliation state machine | batch-success/item-pending, success, failure, and reversal tests | PASS |
| Unknown provider outcome is not blindly retried | unknown-state exclusion and explicit same-ID recovery | reservation/recovery/idempotency tests | PASS |
| Genuine PayPal Sandbox acceptance completed once | retained accepted transaction evidence | `QA/PAYMENT-OPERATIONS-AND-RECONCILIATION.md`; not re-executed here | PASS, retained evidence |
| Receipts and audit evidence persist | transaction detail and audit services | API, E2E, and isolated demo evidence | PASS |
| Public Privacy Policy, Terms, and structured footer exist | `/privacy`, `/terms`, `PublicFooter` | route, overflow, Axe, and visual checks | PASS |
| Responsive interface | responsive layouts and mobile navigation | six public and ten authenticated routes at five widths | PASS |
| Automated WCAG 2.1 AA surfaces | semantic landmarks, focus styles, labels, status regions | Axe on 16 surfaces; keyboard E2E | PASS automated |
| Homepage performance budget | route-light public bundle and Lighthouse assertion | 0.99 performance, 1.00 accessibility, 1.00 best practices | PASS homepage only |
| Production is publicly healthy | Vercel frontend and same-origin API route | read-only 200 responses for `/`, health, and readiness | PASS availability only |

No fixture, mock, deterministic fallback, OAuth response, HTTP 200, or batch
acknowledgement is counted as genuine provider completion.

The current branch is not deployed. Its PostgreSQL job and exact-SHA GitHub CI
remain pending until the branch is published through the normal review process.
