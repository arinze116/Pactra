# README-to-product verification matrix

Verified against branch `codex/paypal-worker-single-authority`. Provider acceptance rows deliberately distinguish implementation/mocked evidence from genuine external success.

| README claim | Implementation evidence | UI evidence | Test/evidence | Status |
|---|---|---|---|---|
| Sandbox-only product | Production config rejects SQLite/insecure/provider-live settings; rails are `internal_sandbox` and `paypal_sandbox_payouts` | Persistent sandbox copy and rail labels | Config tests; public landing inspection | PASS |
| Email/password accounts and opaque sessions | `backend/auth.py`, `AuthSession` | Sign-up, sign-in, settings/logout | `test_auth.py`; Playwright journeys | PASS |
| CSRF and same-origin mutations | `require_csrf`, `require_same_origin` | Browser sends synchronizer header | Auth/API/public E2E checks | PASS |
| Owner-scoped data | Owner filters in services/routes | Foreign receipts show not found | API and browser tenant-isolation tests | PASS |
| Double-entry wallet | `backend/services/ledger.py`; PostgreSQL immutability triggers | Wallet and receipt ledger panels | Ledger, transaction, PostgreSQL tests | PASS |
| Deterministic versioned policy | `backend/services/policies.py` | Policy editor, preview, version history | Boundary, precedence, race and E2E tests | PASS |
| Approval and rejection | Conditional transaction updates and `ApprovalAction` | Approval cards and rejection reason | Duplicate/race/revalidation/session-expiry tests | PASS |
| Manual and AI requests share transaction service | Assistant tool calls `create_payment_request` | Manual form and assistant receipts | Assistant and transaction tests | PASS |
| Deterministic AI fallback | `backend/services/assistant.py` | Assistant reports fallback/provider state | Provider-failure and E2E tests | PASS |
| Live Gemini function calling | Gemini client/tool schema exists | Assistant route exists | Latest live generation returned 429, no function call | BLOCKED |
| API never submits PayPal | No client call in transaction routes/services | Receipt shows queued/executing state | Monkeypatched API regression | PASS |
| Worker-only PayPal submission | `backend/worker.py`, `backend/services/paypal.py` | Provider status appears asynchronously | Worker tests and source trace | PASS |
| Atomic worker claim | `FOR UPDATE SKIP LOCKED` plus conditional attempt update | Not directly visual | PostgreSQL concurrent one-winner test | PASS |
| Stable provider idempotency | `paypal_client.py` stable request/batch/item IDs | Attempt evidence on receipt | Request-shape and duplicate-batch tests | PASS |
| No blind unknown retry | Unknown/no-batch excluded from scan | Recover submission confirmation | Unknown hold and explicit same-ID recovery tests | PASS |
| Capture only on item `SUCCESS` | `apply_paypal_reconciliation` | Receipt provider/ledger separation | Batch-success/item-pending and capture tests | PASS |
| Terminal failure releases once | Failure transition and idempotent reservation release | Failed receipt | Provider status parameter tests | PASS |
| Return/reversal/refund compensates once | Provider reversal journal idempotency | Reversed receipt | Return/reversal/refund tests | PASS |
| Genuine PayPal item success | Provider adapter exists and production is configured | PayPal integration page | OAuth/prior denial are not item success | BLOCKED |
| Provider configuration privacy | Status API masks the global recipient and never returns credentials | Settings shows only the masked recipient | API regression asserts the full address is absent | PASS |
| Persisted receipts and audit | `transaction_detail`, audit service | Receipt lifecycle/policy/ledger panels | API/E2E evidence | PASS |
| Shared rate limits | `RateLimitBucket`, migration `0005` | Rate-limit errors | PostgreSQL atomic counter test | PASS candidate; not deployed |
| WCAG 2.1 AA automated surfaces | Semantic components and focus styles | 14 public/authenticated surfaces | Axe Playwright suite | PASS automated |
| Responsive interface | Responsive layout and mobile navigation | Desktop/tablet/mobile visual inspection | Screenshot audit and E2E overflow checks | PASS inspected |
| Homepage performance budget | Lighthouse assertion script | Homepage | CI homepage-only Lighthouse | PASS homepage only |
| Production worker-only candidate deployed | Candidate branch only | Public app still older release | `/opt/pactra/current` → `0e3e905` | BLOCKED / not deployed |

No fixture, mock, fallback, OAuth result, batch acceptance, or historical provider record is counted as live provider success.
