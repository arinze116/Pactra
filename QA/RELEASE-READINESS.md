# Pactra Release Readiness

Assessment updated: 2026-11-07

Production URL: `https://pactra-nine.vercel.app`

Production release preserved: `0e3e905`

Production migration preserved: `20261107_0004`

Release-candidate migration: `20261107_0005`

## Decision

# NO-GO

The non-provider remediation phase is complete and all available local,
PostgreSQL, browser, accessibility, performance and dependency gates pass.
Full PRD/hackathon readiness remains NO-GO because no deployed live Gemini
function call and no real PayPal Sandbox payout-item `SUCCESS` with
reconciliation have been verified. The release candidate was not deployed.

## Gap closure summary

- Backlog rows: **14**.
- PASS: **11**.
- BLOCKED: **3**.
- PARTIAL: **0** for code-only rows.
- Live provider calls performed: **0**.
- Production changes performed: **0**.

| Priority | Gap IDs | Status | Evidence |
|---:|---|---|---|
| 1 | AI-006 / INT-005 | BLOCKED | Exact model retained; provider-independent tests pass; missing approved key/config/deployment test |
| 2 | PAY-010 / INT-002 / INT-003 | BLOCKED | State-machine tests pass; no authorized real Sandbox payout or item `SUCCESS` |
| 3 | PLT-006 PayPal guided scenario | BLOCKED | Step is truthful and gated by persisted provider `SUCCESS`; depends on PayPal blocker |
| 4 | PAY-003 | PASS | Exact 422/402 bodies, persistence, receipt, audit, zero movement and replay tests |
| 5 | PLT-006 internal guided scenarios/analytics | PASS | Internal scenarios/reset represented; persisted unique start/reset events; PayPal separately blocked |
| 6 | PAY-005 / BUG-007 | PASS | Server-authoritative requester/policy/checks/balance/timestamps/age displayed |
| 7 | WAL-007 / PAY-009 / US-08 / US-10 | PASS | Browser retry/reversal, second-action conflict, reset preservation and unresolved-provider reset fixture |
| 8 | POL-007 | PASS | Side-effect-free authoritative preview endpoint and UI |
| 9 | PLT-004 | PASS | Independent overview/wallet failures, stale labels and targeted retries |
| 10 | REC-003 | PASS | Ordered actor-labelled redacted lifecycle summaries |
| 11 | REC-004 | PASS | Safe account labels and balanced debit/credit display |
| 12 | AUTH-008 | PASS | Desktop/mobile keyboard reveal and successful sign-up/sign-in |
| 13 | INF-005 | PASS | Vite 8 upgrade; full/production npm and Python audits clean; CI expanded |
| 14 | SEC-005 | PASS | Shared atomic database limiter, restart persistence and `Retry-After` |

## Definition of Done

| Requirement | Status | Notes |
|---|---|---|
| All internal P0 payment, policy, approval, ledger, receipt and reset paths | PASS | SQLite, isolated PostgreSQL and Playwright evidence |
| Authentication, CSRF and tenant isolation | PASS | Existing and expanded regression suites |
| Shared rate limiting | PASS | PostgreSQL concurrent independent-session test |
| Clean migration and quality gates | PASS | `0005`; 96 PostgreSQL tests; lint/build/audits/E2E/WCAG/Lighthouse pass |
| Deployed Gemini function calling with required model | BLOCKED | Credential/configuration/deployment acceptance missing |
| Real PayPal Sandbox item-level success and reconciliation | BLOCKED | Capability/credentials/recipient/explicit authorization missing |
| Public release-candidate smoke test | BLOCKED | Deployment correctly withheld pending approval |

## Release plan (not executed)

- Affected services: Oracle `pactra-api`, `pactra-worker`, PostgreSQL migration;
  Vercel frontend after backend verification.
- Migration: additive `20261107_0005` table/index only.
- Backup target: `/opt/pactra/backups/pactra-pre-<release-sha>-<UTC>.dump`.
- Expected downtime: one Pactra API restart, normally under one minute.
- Rollback: restore the previous release symlink and restart Pactra services;
  leave the additive table in place. Restore the verified backup only for a
  diagnosed database failure.

## Remaining risks

- Provider entitlement, quota, response behavior and deployment configuration
  remain unproved until genuine acceptance tests run.
- The public production release does not include these changes.
- The FastAPI TestClient emits one deprecation warning; it is not a functional
  failure but should be addressed in a later dependency maintenance pass.
