# Pactra Release Readiness

Updated: 2026-11-09

Candidate branch: `codex/paypal-worker-single-authority`

Production: `0e3e905` / `20261107_0004`

## Engineering merge gate

| Gate | Status | Evidence |
|---|---|---|
| Worker-only provider authority | PASS | Source trace and API no-provider-call regressions |
| Idempotency and duplicate delivery | PASS | Stable identifiers and one-attempt tests |
| PostgreSQL concurrency | PASS | Row-lock/conditional-claim one-winner test |
| Unknown outcome recovery | PASS | Reserved unknown state plus explicit same-ID recovery |
| Approval and rejection | PASS | Threshold, duplicate, race, policy-change, expired/revoked session tests |
| Financial invariants | PASS | Reservation/capture/release/compensation suites |
| SQLite | PASS | 118 passed, 10 expected skips |
| PostgreSQL | PASS | 128 passed |
| Frontend lint/build | PASS | ESLint and TypeScript/Vite production build |
| Browser/WCAG | PASS locally | 15 journeys; Axe passed across 14 configured surfaces |
| Dependencies | PASS locally | Python and npm audits clean |
| Migration | PASS for preparation | Isolated upgrade/failure/recovery/downgrade drill |
| Documentation truth audit | PASS with stated limitations | README matrix and current QA evidence |
| Final exact-SHA CI | PENDING | Required before merge |
| Pull request/merge | PENDING | Required checks may not be bypassed |

## Production release gate

| Gate | Status |
|---|---|
| Gemini configured in production | PASS for configuration only |
| Live Gemini typed function call | BLOCKED — latest result was `429 RESOURCE_EXHAUSTED` |
| PayPal Sandbox configured/OAuth | PASS for configuration and prior OAuth only |
| PayPal payout-item `SUCCESS` | BLOCKED |
| Exactly-once real provider capture | BLOCKED |
| Six guided scenarios | BLOCKED on PayPal scenario |
| Production migration/deployment | NOT AUTHORIZED / NOT RUN |
| Public candidate smoke | NOT RUN |

## Lighthouse scope

Lighthouse covers only the local preview homepage `/`. It is not route-wide
performance evidence. Route-wide functional and accessibility evidence comes
from Playwright and Axe.

## Migration and rollback

`20261107_0005` creates an empty shared rate-limit table and expiry index. It
does not rewrite financial or user data. Downgrade deletes limiter windows.
The old release's Alembic graph cannot recognize `0005`, so rollback requires
both Pactra services stopped and the candidate code used to downgrade to
`0004` before switching the release symlink.

## Recommendation

The branch is eligible for engineering merge only after the final exact-SHA CI
run passes. Production release remains **NO-GO** because genuine Gemini
function calling, PayPal item-level success, the guided PayPal scenario,
deployment, and public post-deployment smoke remain incomplete.

Production services, configuration, database, and release were unchanged. No
payout was submitted.
