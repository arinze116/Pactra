# Pactra Security Review

## 2026-11-10 instant-demo candidate addendum

- Each instant demo is a distinct `User` with `is_demo=true`, one active
  `DemoWorkspace`, and the normal owner-scoped wallet, policy, transaction,
  receipt, conversation, and audit records. No shared writable account exists.
- Demo and normal sessions use separate opaque HttpOnly cookies and the
  existing same-origin/CSRF mechanism. Exiting a demo does not revoke an
  unrelated normal session.
- Cross-session receipt access, normal/demo separation, expiry, revocation,
  and cleanup were exercised in SQLite and PostgreSQL tests.
- Provider exclusion is enforced in the API, transaction service, PayPal
  service, worker claim, and worker scan. Directly inserted provider-shaped
  demo rows did not invoke the test provider client.
- Demo AI requests bypass Gemini and return a labelled deterministic response.
- PostgreSQL immutable ledger/audit functions permit delete only when a joined
  workspace proves the owner is demo-owned and expired or revoked. Normal-user
  immutability regressions still pass.
- Database-backed creation/reset limits, a PostgreSQL-serialized active cap,
  a per-principal transaction cap, absolute expiry, and bounded cleanup reduce
  resource-exhaustion risk. IP is not used as the ownership boundary.
- Full SQLite/PostgreSQL suites, the no-retry instant-demo journey, 48 Chromium
  regression tests, dependency audits, and secret-pattern review pass locally.
  Exact-head CI and production acceptance remain separate release gates.

Candidate assessment: no known critical/high instant-demo isolation or
provider-boundary finding. Production is not claimed until the deployed
two-context isolation and no-provider-call checks pass.

> The original review below is retained as historical evidence. Current
> production reports provider configuration present. The candidate additionally
> makes the worker the sole PayPal submitter and masks the configured recipient
> in authenticated status responses. Provider success remains unverified.

## 2026-11-09 candidate addendum

- Full SQLite and PostgreSQL security/ownership regressions pass.
- API routes do not call PayPal submission; source tracing restricts
  `create_payout` to the worker orchestration service.
- Ambiguous outcomes retain reservations and cannot be automatically replayed.
- The PayPal configuration endpoint returns a masked recipient and no
  credential material.
- `pip check`, `pip-audit`, production npm audit, and full npm audit pass
  with zero known vulnerabilities.
- Added-line secret-pattern scanning, tracked-file review, and dangerous-source
  pattern review found no credential or critical/high release finding.
- Automated WCAG passes across 14 surfaces and a keyboard-only critical journey
  passes. Manual NVDA/VoiceOver testing and external DAST remain unverified.

Current candidate assessment: no unresolved known critical/high code or
dependency finding. External provider success and production deployment are
separate blocked gates.

Audit date: 2026-11-07  
Scope: application source, automated security regressions, isolated PostgreSQL tests, production-safe HTTP checks, deployment configuration and aggregate database invariants. No destructive penetration testing was performed against production.

## Executive assessment

No P0/P1 vulnerability was confirmed. Authentication, CSRF, tenant ownership, ledger integrity, provider truthfulness and AI tool authorization have direct regression coverage. Production uses secure cookies, exact-origin API CORS, loopback-only API/database listeners, HTTPS, disabled API docs and sandbox-only provider configuration.

The principal remaining security limitations are operational rather than active exploits: rate limits are process-local and therefore depend on the current single Uvicorn worker; live Gemini/PayPal paths are unconfigured; development tooling has known vulnerabilities; and manual screen-reader/DAST coverage was not performed. Audit events are now database-enforced append-only in PostgreSQL.

## Checks and findings

| Area | Check performed | Result | Evidence/limitations |
|---|---|---|---|
| Authentication bypass | Unauthenticated `/api/auth/me` and `/api/wallet`; invalid/revoked/expired sessions | PASS | Production returned 401; backend auth tests pass |
| Password handling | Argon2 hashes; weak password and invalid credential tests; secret/log review | PASS | Passwords are never returned/logged; generic invalid-login response |
| Cookie security | Inspect production cookies | PASS | `pactra_session` and `pactra_csrf`: HttpOnly, Secure, SameSite=Lax |
| CSRF | Missing and invalid tokens; same-origin checks | PASS | Public test returned `403 CSRF_INVALID`; auth tests cover invalid token |
| CORS | Malicious origin preflight | PASS | Production returned 400; API uses configured exact origins |
| Tenant isolation/BOLA | Foreign receipt, conversation, policy, approval, retry, reversal and reconciliation attempts | PASS | Owner-scoped queries return 404; cross-user E2E passes |
| Privilege escalation | Attempt user actions against another user’s objects | PASS | No admin bypass surface found; foreign operations rejected |
| Input validation | Invalid emails, money, policy, filters, UUIDs, payout recipient and tool arguments | PASS | Pydantic constraints plus service validation; regression tests pass |
| SQL injection | Inspect query construction; send malformed filters/identifiers | PASS | SQLModel/SQLAlchemy parameterization used; no user-concatenated SQL path found |
| XSS | Inspect rendering and free-text fields; route tests/browser console | PASS | React escaping; no `dangerouslySetInnerHTML`; no browser runtime findings |
| Open redirects | Inspect auth/navigation and supplied URLs | PASS | No user-controlled redirect target found |
| Error leakage | Invalid API requests and production logs | PASS | Structured errors; API docs/stack traces disabled; zero post-deploy error/trace lines |
| Security headers | Inspect production document headers | PASS | CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options`, Referrer and Permissions policies present |
| API documentation exposure | `/api/docs`, `/api/redoc`, `/api/openapi.json` | PASS | All returned 404 in production |
| Secret exposure | Tracked source scan, built bundle scan, log review, `.env` permissions | PASS | No detected credential patterns; root `.env` is untracked and mode 600 |
| Rate limiting | Registration/login/payment/policy/assistant limiter tests and deployment topology | PASS candidate | Migration `0005` adds atomic database-backed buckets shared across processes |
| Ledger manipulation | Duplicate/retry/concurrency tests; direct aggregate invariants | PASS | Zero unbalanced journals, journals with non-two entry count, duplicate captures or invalid holds |
| Ledger immutability | PostgreSQL journal/entry mutation attempts | PASS | Database triggers reject journal mutation and extra entries |
| Audit immutability | PostgreSQL audit update/delete attempts | PASS | Migration `20261107_0004`; trigger `trg_audit_events_immutable` active |
| AI prompt/tool abuse | Prompt injection, hidden recipient, invalid argument and policy-bypass tests | PASS | Tool allowlist and unified transaction service prevent model authority escalation |
| Provider safety | Non-sandbox/startup guards, worker-only authority, masked status, provider-state tests | PASS for safety; BLOCKED for live success | Production is configured, but no Gemini function call or PayPal item `SUCCESS` is claimed |
| Dependency vulnerabilities | `pip-audit`; production-only and full `npm audit` | PASS | Python, production npm, and full npm audits report zero known vulnerabilities |
| Network exposure | Service units, binds, Funnel and database listeners | PASS | API `127.0.0.1:8010`; PostgreSQL `127.0.0.1:5432`; Funnel terminates HTTPS |
| Backup safety | Pre-migration private archive and isolated restore | PASS | Backup mode 0600; restore drill never targeted production DB |

## Production evidence

```text
401 /api/auth/me
401 /api/wallet
404 /api/docs
404 /api/redoc
404 /api/openapi.json
400 malicious CORS preflight
```

Headers observed on `https://pactra-nine.vercel.app` included:

```text
content-security-policy: default-src 'self'; connect-src 'self'; font-src 'self' data:;
  img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline';
  frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'
strict-transport-security: max-age=63072000; includeSubDomains; preload
x-content-type-options: nosniff
x-frame-options: DENY
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=(), microphone=(), geolocation=(), payment=()
```

TLS validity observed:

- Vercel: 2026-10-31 through 2027-01-29.
- Tailscale Funnel: 2026-11-06 through 2027-02-04.

Production database invariant query results after smoke tests:

```text
unbalanced_journals=0
journals_not_two_entries=0
duplicate_captures=0
completed_internal_without_capture=0
pending_or_executing_without_hold=0
active_hold_invalid_status=0
```

## Remediation completed

1. Approval-time policy blocks now record both the state transition and the reasoned `payment.blocked` audit event.
2. PostgreSQL now rejects audit-event updates/deletes.
3. The payout receipt exposes the recipient to the owning user, closing an evidence gap without weakening privacy.

## Remaining risks

- Migration `0005` must be deployed before shared database-backed rate limiting is active in production.
- CSP still permits inline styles because of the current frontend styling/runtime requirements; scripts remain self-only.
- Provider authentication/configuration was verified previously, but successful Gemini function calling and PayPal item-level success remain unverified.
- Manual assistive-technology testing and external DAST were not completed; automated WCAG and safe application regressions passed.

## Safety limitations

- No destructive SQL, data deletion, balance reset of real users, live payment, live PayPal payout or credential probing was performed.
- Production smoke tests used newly generated isolated accounts and sandbox-only data.
- Reports contain aggregate counts only; no cookie, token, credential or private user record is included.
