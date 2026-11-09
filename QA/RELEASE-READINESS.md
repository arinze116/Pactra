# Pactra Release Readiness

Updated: 2026-11-09, Africa/Lagos

Production runtime: `73fdfb692f6daea69ba5f44bc37d9afa1814419a`
at `/opt/pactra/releases/73fdfb6`, database revision `20261107_0005`.

## Engineering gate

| Requirement | Status | Evidence |
|---|---|---|
| Worker-only PayPal authority | PASS | API regressions and source trace; only the worker calls payout creation |
| Atomic claim / duplicate prevention | PASS | PostgreSQL one-winner concurrency tests and stable attempt identifiers |
| Ambiguous provider outcome | PASS | Reservation retained; no automatic retry; explicit same-ID recovery only |
| Item-success capture rule | PASS | Only item-level `SUCCESS` captures; batch acceptance does not |
| Failure and compensation | PASS | Terminal failure release and exactly-once reversal/refund tests |
| Authentication/authorisation/CSRF | PASS | Backend suites and public CSRF/session acceptance |
| Policy, audit and receipt | PASS | Backend suites plus production completed/rejected/blocked receipts |
| SQLite suite | PASS | 121 passed, 10 PostgreSQL-only skipped on the Gemini candidate |
| PostgreSQL suite | PASS | 131 passed after one non-reproducing concurrency rerun; isolated test and second full run passed |
| Frontend lint/type/build | PASS | ESLint, TypeScript and Vite production build |
| Dependency audits | PASS | `pip check`, `pip-audit`, production npm audit and full npm audit |
| CI on runtime SHA | PASS | [42659603721](https://github.com/arinze116/Pactra/actions/runs/42659603721), four jobs passed on `73fdfb69...` |
| CI on Gemini candidate | NOT TESTED | Dedicated branch has not yet been published |

## Release and production gate

| Requirement | Status | Evidence |
|---|---|---|
| Immutable artifact | PASS | Archive-built release, 139 tracked members matched, archive SHA-256 `6c16fbcd...92c4` |
| Frontend artifacts | PASS | `frontend/dist` present; all recorded build hashes verified |
| Backup and restore | PASS | Verified custom dump and isolated restore at `0005` |
| Upgrade/downgrade | PASS | Exact artifact passed `0005 → 0004 → 0005`; old release ready at `0004` |
| Production deployment | PASS | Symlink switched at `2026-11-09T17:00:40Z`; API and worker active with zero restarts |
| Worker lease | PASS | Lease acquired at `2026-11-09 18:00:44 WAT` |
| Health/readiness | PASS | Local and public `/api/health` and `/api/ready` returned 200 |
| Public workflow smoke | PASS | Registration, login, wallet, policy, manual payment, AI fallback, rejection, block, receipts, audit, session and isolation |
| Accessibility/responsive | PASS | Axe on authenticated surfaces; inspected 1440×1000, 1024×768 and 390×844 screenshots; no overflow |
| Public Lighthouse | PASS | `/`, `/sign-in`, `/sign-up`: 1.00 performance, accessibility and best practices |
| Security headers | PASS | CSP, HSTS, frame denial, MIME sniffing prevention, referrer and permissions policies |
| Rollback readiness | PASS | Immediate `0005` rollback to `4534d13`; tested legacy downgrade for `0e3e905` |

## External provider acceptance

| Requirement | Status | Evidence |
|---|---|---|
| Gemini production configuration | PASS | Production still uses `gemini-3.8-flash`; key present and aligned with the project key |
| Candidate discovery | PASS | Account exposes stable `gemini-3.5-flash-lite` with `generateContent`; Google documents function calling and a free tier |
| Genuine candidate function call | PASS | Two genuine calls and two full function-response round trips passed with validated arguments |
| Full candidate Pactra workflow | PASS | Completed internal payout, approval reservation, missing-data rejection, receipt and audit checks passed in isolation |
| Genuine production function call | NOT TESTED | Do not switch production until candidate CI and release checks pass |
| Deterministic Gemini fallback | PASS | Timeout, 503, malformed/empty response and post-tool failure regressions preserve governance |
| PayPal Sandbox configuration/OAuth | PASS | Sandbox host, Payouts scope, mock disabled, credentials present; OAuth completed in 737 ms |
| PayPal payout submission | PASS | Exact transaction `bfe1e158-...` approved once; worker issued one payout POST and persisted one batch |
| PayPal item-level `SUCCESS` | PASS | PayPal lookup of the persisted batch returned one item with `transaction_status=SUCCESS` |
| Exactly-once provider capture | PASS | One attempt, one captured reservation, one balanced $25 capture journal, no duplicate identifiers or reversal |

## Lighthouse measurements

Desktop-profile production reports are stored under
`artifacts/release-20261109/lighthouse-production-*.json`.

| Route | Performance | Accessibility | Best practices | LCP | CLS |
|---|---:|---:|---:|---:|---:|
| `/` | 1.00 | 1.00 | 1.00 | 206 ms | 0.00006 |
| `/sign-in` | 1.00 | 1.00 | 1.00 | 206 ms | 0.00002 |
| `/sign-up` | 1.00 | 1.00 | 1.00 | 208 ms | 0.00004 |

## Verdict

- Production deployment: **PASS**.
- Engineering and public acceptance: **PASS**.
- Gemini candidate compatibility and isolated workflow: **PASS**.
- Genuine production Gemini function-call acceptance: **NOT TESTED**.
- PayPal payout, item-success and exactly-once capture acceptance: **PASS**.
- Overall product acceptance: **BLOCKED** pending exact-SHA CI, deployment and
  a genuine non-financial production function-call acceptance test.
