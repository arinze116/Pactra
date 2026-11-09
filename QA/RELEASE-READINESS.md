# Pactra Release Readiness

Updated: 2026-11-09, Africa/Lagos

Production runtime: `4534d136766a094aeeac4489a9e694111b9257ae`
at `/opt/pactra/releases/4534d13`, database revision `20261107_0005`.

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
| SQLite suite | PASS | 118 passed, 10 PostgreSQL-only skipped |
| PostgreSQL suite | PASS | 128 passed, including concurrency and migration coverage |
| Frontend lint/type/build | PASS | ESLint, TypeScript and Vite production build |
| Dependency audits | PASS | `pip check`, `pip-audit`, production npm audit and full npm audit |
| CI on runtime SHA | PASS | [42656025377](https://github.com/arinze116/Pactra/actions/runs/42656025377), four jobs passed on `4534d136...` |

## Release and production gate

| Requirement | Status | Evidence |
|---|---|---|
| Immutable artifact | PASS | Archive-built release, 139 tracked members matched, archive SHA-256 `7b54f392...d8610` |
| Frontend artifacts | PASS | `frontend/dist` present; all recorded build hashes verified |
| Backup and restore | PASS | Verified custom dump and isolated restore at `0005` |
| Upgrade/downgrade | PASS | Exact artifact passed `0005 → 0004 → 0005`; old release ready at `0004` |
| Production deployment | PASS | Symlink switched at `2026-11-09T16:41:01Z`; API and worker active with zero restarts |
| Worker lease | PASS | Lease acquired at `2026-11-09 17:41:15 WAT` |
| Health/readiness | PASS | Local and public `/api/health` and `/api/ready` returned 200 |
| Public workflow smoke | PASS | Registration, login, wallet, policy, manual payment, AI fallback, rejection, block, receipts, audit, session and isolation |
| Accessibility/responsive | PASS | Axe on authenticated surfaces; inspected 1440×1000, 1024×768 and 390×844 screenshots; no overflow |
| Public Lighthouse | PASS | `/`, `/sign-in`, `/sign-up`: 1.00 performance, accessibility and best practices |
| Security headers | PASS | CSP, HSTS, frame denial, MIME sniffing prevention, referrer and permissions policies |
| Rollback readiness | PASS | Immediate `0005` rollback to `9b4bc77`; tested legacy downgrade for `0e3e905` |

## External provider acceptance

| Requirement | Status | Evidence |
|---|---|---|
| Gemini configured | PASS | Production model `gemini-3.8-flash`; key present and aligned with the validated project key |
| Genuine Gemini function call | BLOCKED | Model lookup passed; Pactra generation returned provider `503`/timeout and no function call |
| Deterministic Gemini fallback | PASS | Governed $20 internal payment completed once; provider errors did not break the application |
| PayPal Sandbox configuration/OAuth | PASS | Sandbox host, Payouts scope, mock disabled, credentials present; OAuth completed in 737 ms |
| PayPal payout submission | BLOCKED | Separate authorisation for transaction `bfe1e158-...` has not been given |
| PayPal item-level `SUCCESS` | NOT TESTED | Submission is prohibited until that authorisation |
| Exactly-once provider capture | NOT TESTED | Requires confirmed item-level `SUCCESS` |

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
- Genuine Gemini function-call acceptance: **BLOCKED**.
- PayPal payout and item-success acceptance: **BLOCKED** pending the mandatory
  transaction-specific approval.
- Overall product acceptance: **BLOCKED**. A successful deployment does not
  override the two unverified provider requirements.
