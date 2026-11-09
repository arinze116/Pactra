# Pactra Final Pre-Demo Audit

Audit date: 2026-11-09 (Africa/Lagos)

Branch: `release/final-pre-demo-readiness`

Status: **PASS for repository readiness; production deployment not requested**

## Scope and evidence labels

- **Verified** means inspected or executed during this mission.
- **Retained evidence** means supported by the accepted release records but not re-executed.
- **Not verified** means no safe or available check was completed.

Production was read-only. No deployment, Vercel promotion, service restart,
configuration edit, migration, database mutation, Gemini request, PayPal
request, payout, reconciliation, or financial transaction occurred.

## Verified accepted baseline

| Item | Result | Evidence |
|---|---|---|
| Repository/default branch | `arinze116/Pactra`, `main` | GitHub CLI |
| Current baseline main | `9c6c94b85b75d2ec20c8905aabd77700a7779238` | local, `origin/main`, GitHub CI |
| Accepted runtime | `63f25839a6b645a8ca404846ecd82d16c1994b7c` | active symlink and `.release-sha` |
| Runtime ancestry | Runtime is an ancestor of current main | `git merge-base --is-ancestor` |
| Active release | `/opt/pactra/current` -> `/opt/pactra/releases/63f2583` | read-only VPS check |
| Database | PostgreSQL 16.15, revision `20261107_0005` | read-only SQL transaction |
| Services | API PID `819381`; worker PID `785136`; both active; zero restarts | systemd properties |
| Worker state | One lease holder; zero eligible/unresolved backlog; zero unknown attempts | read-only SQL |
| Vercel | `dpl_DjHTW75MnGQN11rcNZrY89NkrN9c`, production, Ready, alias active | Vercel CLI 65.12.1 |
| Public app | `/`, `/api/health`, `/api/ready` returned expected success | bounded read-only monitor |
| Backup | Accepted 173,373-byte archive checksum and archive list passed | retained archive verification |
| Financial invariants | 10/10 P0/P1 checks passed; zero violations | read-only diagnostic against production |

Current main CI run `42682730207` passed all four required jobs. The new
branch requires its own CI before merge.

## Verified architecture

Pactra is a React/Vite frontend backed by FastAPI, SQLModel/SQLAlchemy,
PostgreSQL, and a separate PayPal reconciliation worker. Vercel serves the
frontend and rewrites same-origin API requests to the Oracle VPS. Nginx and
Tailscale Funnel provide the public backend path. Alembic owns schema changes.

Authentication uses Argon2id passwords, opaque hashed database sessions,
HttpOnly cookies, idle/absolute expiry, synchronizer CSRF tokens, exact-origin
CORS, and database-backed rate limits. Every owned resource query is scoped by
the authenticated user.

Manual and AI-originated payment requests share the same deterministic
transaction service. Policy checks run before reservation or execution.
Approval re-evaluates policy. Internal sandbox payments post balanced ledger
journals. PayPal Sandbox requests are submitted only by the leased worker and
capture only after item-level `SUCCESS`.

Gemini is an untrusted extraction and tool-selection interface. Tool names and
arguments are validated server-side, and the model cannot approve, submit a
payout, mutate a ledger, or bypass policy. Deterministic fallback remains
available.

## Existing capabilities and controls

- Registration, login, logout, password change, expiry, revocation, CSRF, and
  shared rate limiting.
- Per-user sandbox wallets, immutable posted journals, reservations, capture,
  reversal, and derived balances.
- Versioned spending policy, deterministic limits, approval and rejection.
- Manual and AI-assisted payment creation through one governance boundary.
- Receipts, policy traces, attempts, ledger entries, and durable audit events.
- Worker-only PayPal Sandbox submission with stable identifiers and
  reconciliation-safe unknown outcomes.
- Health/readiness endpoints, systemd supervision, release/backup/rollback
  runbooks, and exact-SHA CI.

## Work completed in this mission

- Added bounded, privacy-safe structured API, Gemini, and worker events.
- Added validated request IDs, route-template operation labels, frontend
  correlation IDs, and request timeouts.
- Added strict payment type/rail validation and regression tests.
- Added read-only financial invariant, backup, and public-health diagnostics.
- Added a repository-contained five-minute public health workflow. It remains
  inactive until merged to the default branch and has no paging destination.
- Added a production-refusing, idempotent `APP_ENV=demo` SQLite seed/reset
  workflow and fictional demo dataset.
- Added a real Playwright demo rehearsal covering governed payment, AI
  fallback governance, approval, receipt, audit, tablet, and mobile states.
- Captured seven real demo screenshots under `DEMO/assets/`.
- Corrected email casing and word-aware wrapping in approval/receipt facts.
- Aligned example configuration with the accepted Gemini model and bounded
  attempt count.

## Findings

### P0

No unresolved P0 finding was identified. The production read-only invariant
scan reported zero violations.

### P1

No unresolved repository P1 finding was identified. Production activation of
this branch is intentionally outside scope and requires a separate release.

### P2

- External health checks have no configured email, chat, or paging target.
- Worker/backlog, database pressure, Gemini reliability, PayPal unknown
  outcomes, ledger invariants, and backup freshness are not yet scheduled as
  independent alerts.
- No centralized error aggregation or real-user monitoring is configured.
- Manual NVDA/VoiceOver testing and external DAST were not performed.
- The lazily loaded AG Grid route chunk is about 281 kB gzip. Homepage
  Lighthouse remains strong, but transaction-route performance should be
  measured with representative data before optimization.

### P3

- Approval is currently owner-driven; independent multi-role approver
  separation and approval TTLs are future product work.
- No inbound PayPal webhook exists; reconciliation uses authenticated polling.
- Measured RTO/RPO and a staffed on-call rotation are not configured.

## Documentation and implementation reconciliation

- The accepted production records describe runtime `63f2583`; this branch is
  not deployed and must not be described as current production behavior.
- The previous observability backlog said no external probe existed. This
  branch adds a GitHub Actions probe, but it is only repository-ready until
  merged and still does not page an operator.
- Example configuration previously referenced `gemini-3.8-flash`; it now
  matches the accepted `gemini-3.5-flash-lite` configuration while retaining
  the documented rollback model in application validation.
- Historical security documents predate completed Gemini and PayPal
  acceptance. The canonical accepted facts remain in the later baseline and
  provider operations records.

## Intentionally not performed

- No production change or new provider acceptance request.
- No live or Sandbox PayPal operation.
- No live Gemini request.
- No monitoring vendor installation or account connection.
- No production restore, rollback drill, migration, or demo seeding.
- No unrelated refactor or visual redesign.
