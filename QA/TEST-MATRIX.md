# Pactra Test Matrix

> Historical matrix. Current command results and external-provider boundaries
> are in `QA/ACCEPTANCE-EVIDENCE.md`.

Audit date: 2026-11-07  
Production: `https://pactra-nine.vercel.app`  
Release under test: `0e3e905`  

`PASS` means the behaviour was exercised successfully with evidence. `PARTIAL` means the implemented subset passed but a documented requirement or live dependency remains. `BLOCKED` means a safe end-to-end test was not possible. `NOT IMPLEMENTED` means source inspection confirmed absence.

## Feature-by-feature results

| Feature ID | Test cases | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|
| PLT-001 | Load landing at desktop/mobile; reload; inspect console/layout | 200, correct content, no runtime error/overflow | Passed; Lighthouse performance 0.99, accessibility 1.0 | PASS | `route-crawl.spec.ts`; `landing-desktop.png`; `landing-mobile.png` |
| PLT-002 | Open every public/protected/not-found route; reload | Correct guard and stable route | All routes passed on desktop/mobile | PASS | Public route crawl, local E2E |
| PLT-003 | Use desktop/mobile navigation and sign-out | Every visible link/control navigates or acts | Passed at 1440px and 390px | PASS | `judge-flow.spec.ts`; route crawl |
| PLT-004 | Abort optional status request; inspect loading/empty/error/retry states | Core data survives optional failure; errors recover | Transaction recovery passes; overview remains grouped and wallet error lacks explicit retry | PARTIAL | `transaction history recovers...`; source review |
| PLT-005 | Axe scan public/auth pages; keyboard-operable controls; overflow checks | No automated WCAG 2.1 AA violations or overflow | Passed automated checks; manual screen-reader run not performed | PASS | `accessibility.spec.ts`; Lighthouse |
| PLT-006 | Run auto, approval, blocked, reject, reset scenarios | Six PRD scenarios create real records | Five internal scenarios available; PayPal and insufficient-funds guided cases absent | PARTIAL | `OverviewPage.tsx`; judge E2E |
| AUTH-001 | Register separate users via API/UI | 201, wallet/policy/session created atomically | Passed in SQLite, PostgreSQL and production | PASS | `test_auth.py`; public journey |
| AUTH-002 | Invalid email, weak password, duplicate email | Validation/409 without data duplication | Passed | PASS | Auth/API tests |
| AUTH-003 | Valid and invalid login | Valid succeeds; invalid returns generic 401 | Passed | PASS | Auth tests; credential E2E |
| AUTH-004 | Reload session; revoke/expire/invalid token | Valid persists; invalid clears and protects routes | Passed | PASS | Auth tests; public reload |
| AUTH-005 | Logout and simulated failed logout | Server revokes session; UI does not discard valid session on ambiguous failure | Passed | PASS | Auth tests; `credential errors and failed logout...` |
| AUTH-006 | Correct/wrong/current-equals-new password | Change only with valid current password; rotate sessions | Passed at backend level | PASS | `test_auth.py` |
| AUTH-007 | Missing/invalid CSRF; foreign Origin; unauthenticated mutations | 403/400/401 as applicable | Passed; production missing CSRF returned `403 CSRF_INVALID` | PASS | Auth/API tests; public journey; curl preflight |
| AUTH-008 | Inspect sign-in/sign-up password controls | Accessible show/hide control exists | No reveal control found | NOT IMPLEMENTED | `PublicPages.tsx` source review; PRD §12 |
| WAL-001 | Register user and query initial wallet/ledger | $1,000 posted/available, zero reserved, balanced issuance | Passed | PASS | Auth/ledger tests; DB invariants |
| WAL-002 | Query balances before/after holds/captures/releases | Integer-cent balance equation remains correct | Passed | PASS | Ledger/transaction tests; production invariant queries |
| WAL-003 | Top up, refresh and simulate lost response/retry | One durable top-up; refreshed balance persists | Passed; no duplicate credit | PASS | Auth tests; core E2E |
| WAL-004 | Same/different idempotency key payload; top-up limits | Replay same result; mismatch/limit rejected | Passed | PASS | Ledger/auth tests |
| WAL-005 | List wallet ledger, cursor and counterpart | Correct ordered page and counterpart labels | API passes; UI shows first 100 without load-more | PASS | Ledger tests; wallet E2E |
| WAL-006 | Reserve, capture, reject/release, policy-change/release, concurrent reserve | Exactly one valid terminal outcome and consistent hold | Passed in PostgreSQL concurrency suite | PASS | `test_transactions.py`; `test_postgres_runtime.py` |
| WAL-007 | Reset with/without confirmation and active work | Require RESET; preserve history; advance generation | Passed | PASS | Sandbox/auth tests; judge E2E |
| POL-001 | Retrieve current policy and cross-user object attempts | Owner sees current version only | Passed | PASS | Policy/API/public isolation tests |
| POL-002 | Save valid/invalid/unchanged policy | Persist valid version; reject invalid/unchanged | Passed | PASS | Policy tests; editor E2E |
| POL-003 | Concurrent version saves and ordered history | Unique monotonic versions | Passed (`[2,3]`) on PostgreSQL | PASS | `test_concurrent_policy_saves_allocate_distinct_versions` |
| POL-004 | Reset policy | New default version and audit event | Passed | PASS | Policy tests/source review |
| POL-005 | Rule precedence, boundaries and combinations | First failing rule and stable reason code | Passed across currency/limits/vendor/category/budget/balance | PASS | `test_policy_engine.py`; transaction tests |
| POL-006 | Threshold below/equal/above; approve after policy change | Only above threshold requires approval; approval rechecks | Passed | PASS | Policy/transaction/PostgreSQL/E2E |
| POL-007 | Inspect new-payment preview for multiple likely decisions | Current limits and server-equivalent likely decision shown | Limits/threshold confirmation shown; no full likely-decision result | PARTIAL | `PaymentPages.tsx`; PRD §12 |
| PAY-001 | Create valid/invalid manual vendor payments | Validate, govern, capture and return receipt | Passed | PASS | Transaction/API/E2E |
| PAY-002 | Payout missing/invalid/valid recipient; refresh receipt | Require email and persist/display it | Passed locally, PostgreSQL and after production deployment | PASS | Backend tests; local/public recipient assertions |
| PAY-003 | Submit policy-blocked request | Persist block/audit, no journal posting, contract error per PRD | Safe state passed, but endpoint intentionally returns 201 receipt rather than PRD 422/402 | PARTIAL | Transaction/API/E2E; `main.py::create_transaction` |
| PAY-004 | Exhaust available balance and request more | No over-reservation/capture; stable insufficient-funds reason | Passed in policy/ledger tests | PASS | Backend suites |
| PAY-005 | List oldest approval, approve, reject, repeat/foreign action | One owner-only terminal action; correct hold outcome | Passed | PASS | Backend/PostgreSQL/E2E/public tests |
| PAY-006 | Change policy to block pending payment, then approve | Block, release hold, audit pending→blocked and reason | Passed after fix | PASS | `test_approval_revalidation_block_is_audited_and_releases_hold` |
| PAY-007 | Duplicate create/approval/retry and lost response | Replay same operation; reject key reuse mismatch | Passed | PASS | Backend tests; ambiguous retry E2E |
| PAY-008 | Concurrent over-reservation and approve/reject race | At most one winner; no duplicate capture/partial state | Passed on isolated PostgreSQL | PASS | `test_postgres_runtime.py` |
| PAY-009 | Retry eligible failure; reverse completed internal payment; invalid states/owner | Compensating journal or safe rejection | Passed at service/API level | PASS | Transaction/API tests |
| PAY-010 | Live PayPal payout item submission and success | Authenticated Sandbox item reaches success before ledger capture | Production is unconfigured; no payout triggered | BLOCKED | `/api/ready`; integration status; safety rule |
| AI-001 | Create/list/rename/archive conversations; cross-user retrieval | Durable owner-only conversation management | Passed | PASS | Assistant/API tests; E2E |
| AI-002 | Send, reload, continue and retry same request | Messages persist once and history reloads | Passed | PASS | Assistant E2E |
| AI-003 | Provider disabled/unavailable and parse supported/ambiguous prompts | Deterministic safe fallback; ask for missing data | Passed | PASS | Assistant unit/E2E |
| AI-004 | Prompt injection, invalid tool args, implicit recipient, foreign IDs | Tool cannot bypass validation/auth/policy | Passed | PASS | Assistant security regressions |
| AI-005 | AI creates auto/approval/blocked governed payment | Same authoritative service and receipt as manual flow | Internal-sandbox path passed | PASS | Assistant tests/E2E |
| AI-006 | Live Gemini model call, timeout and malformed response | Live provider works or safely falls back with audit | Failure mocks pass; live production call unavailable | BLOCKED | Readiness `ai_enabled=false`; assistant tests |
| REC-001 | History empty/filter/sort/date/cursor/invalid filters/provider-status failure | Correct owned page and recoverable optional integration error | Passed | PASS | API tests; AG Grid E2E |
| REC-002 | Receipt status/amount/recipient/policy/attempts/ownership/refresh | Accurate durable owner-only receipt | Passed | PASS | API tests; local/public E2E; `receipt-desktop.png` |
| REC-003 | Inspect lifecycle event ordering and detail | Ordered event, actor and safe payload visible | API data accurate; UI renders only event type/time | PARTIAL | `transaction_detail`; receipt source review |
| REC-004 | Inspect posted ledger entries on receipt | Amount, direction, journal, account/counter-account visible | Amount/direction/journal visible; account labels absent | PARTIAL | Receipt source review |
| REC-005 | Attempt PostgreSQL audit UPDATE and DELETE | Both operations rejected by database | Passed after migration `0004` | PASS | `test_audit_events_are_immutable`; production trigger check |
| INT-001 | Load PayPal status when disabled | Truthfully report unavailable without claiming success | Passed | PASS | Settings route/E2E; API response |
| INT-002 | Mock token, submit, item states and errors | Stable IDs; no unknown/failed outcome reported successful | Provider-independent tests passed; live auth absent | BLOCKED | `test_paypal_payouts.py`; readiness |
| INT-003 | Mock timeouts, duplicates, unknown outcomes and reconciliation | Preserve reservation until terminal; retry safely | Mocked paths pass; live recovery unproven | PARTIAL | PayPal tests; transaction service |
| INT-004 | Worker lease, active service, restart and disabled state | One worker authority; clean startup/restart | Passed; worker active and standing by | PASS | Lease test; systemd/log evidence |
| INT-005 | Enable-without-key startup validation and production status | Refuse invalid config and disclose disabled state | Passed; production disabled | BLOCKED | Config tests; `/api/ready` |
| INF-001 | Direct/Funnel/Vercel health and readiness | All return 200 with DB ready | Passed after deployment | PASS | curl results |
| INF-002 | Clean SQLite/PostgreSQL migration; production head/trigger | Upgrade to head and enforce schema | Passed; production at `20261107_0004` | PASS | Migration tests; psql |
| INF-003 | Service status, binds, rewrite, Funnel and TLS | API/DB loopback; trusted HTTPS path; valid certs | Passed; API/worker active, zero restarts | PASS | systemd/socket/Funnel/Vercel/TLS checks |
| INF-004 | Backup archive list and isolated restore | Valid pre-change backup and restorable data/invariants | Passed; new archive validated; prior latest archive restored to separate DB | PASS | `/opt/pactra/backups/...0e3e905...dump`; restore DB evidence |
| INF-005 | Backend suites, lint/build/E2E, dependency audits | Green release pipeline and no production high vulnerabilities | Functional pipeline green; nine dev-tool findings remain | PARTIAL | `COVERAGE-REPORT.md` |
| SEC-001 | Inspect cookies and unauthenticated protected APIs/logs | HttpOnly/Secure/SameSite=Lax; 401; no tokens logged | Passed | PASS | Public Playwright; curl; journal review |
| SEC-002 | Foreign receipt/conversation/policy/approval/retry/reverse/reconcile | No object disclosure or action | Passed with 404 | PASS | API/public cross-user tests |
| SEC-003 | Malicious CORS, headers, docs, stack/error leakage | Reject origin; security headers; docs 404; safe errors | Passed | PASS | curl/header checks; config tests |
| SEC-004 | SQLi/XSS/open redirect/secret/tool abuse/dependency scan | Typed/escaped/parameterized handling and no bundled secrets | Passed safe regressions and scans | PASS | Backend tests; git/bundle scan; pip/npm production audit |
| SEC-005 | Exercise configured rate limits and assess multi-worker safety | Limits enforce consistently across deployment | Passes with one production worker; state is not shared horizontally | PARTIAL | Auth/config tests; systemd `--workers 1` |

## Commands and actual results

```text
APP_ENV=test DATABASE_URL=sqlite:// PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
  .venv-linux/bin/python -m pytest -q
Result: 91 collected; 83 passed; 8 PostgreSQL-only skipped; 1 deprecation warning.

APP_ENV=test DATABASE_URL=postgresql+psycopg:///pactra_audit_backend_20261107_r2 \
  PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
  .venv-linux/bin/python -m pytest -q
Result: 91 passed; 1 deprecation warning.

npm run lint
Result: PASS.

npm run build
Result: PASS; 1,618 modules; initial JS 253.13 kB / 78.33 kB gzip;
AG Grid lazy chunk 1,107.31 kB / 288.16 kB gzip.

E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:e2e
Result: 9 journeys passed; 1 automated WCAG test passed (SQLite).

E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python \
E2E_DATABASE_URL=postgresql+psycopg:///pactra_audit_e2e_20261107 npm run test:e2e
Result: 9 journeys passed; 1 automated WCAG test passed (PostgreSQL).

PUBLIC_BASE_URL=https://pactra-nine.vercel.app npm run test:e2e:public
Result: 2 passed after deployment.

PUBLIC_BASE_URL=https://pactra-nine.vercel.app npx playwright test \
  --config playwright.public.config.ts tests/public/submission-journey.spec.ts
Result: 1 passed with explicit production recipient assertions.
```

The first public command without `PUBLIC_BASE_URL` failed during configuration before any browser/product test ran. The corrected command above passed. An earlier parallel local Playwright run also had a trace cleanup collision; the sequential clean reruns passed and are the authoritative results.
