# Pactra Release Manifest

Recorded: 2026-11-09, Africa/Lagos

## Release identity

| Field | Verified value |
|---|---|
| Branch | `codex/prd-gap-closure-20261107` |
| Application release SHA | `b50117757347efd86d13bc43838654c5da2bcf0a` |
| Previous candidate SHA | `8c8798a0dd89608c22b4c986428af9d815219771` |
| Candidate migration | `20261107_0005` |
| Production application | `0e3e905` at `/opt/pactra/releases/0e3e905` |
| Production migration | `20261107_0004` |
| Public alias | `https://pactra-nine.vercel.app` |
| Immutable Vercel deployment ID | Unknown; no connected Vercel CLI/project metadata was available locally |

The application release SHA is the deployable code candidate. Later
documentation-only evidence commits do not change the application payload and
must identify this SHA explicitly.

## Changes after the original candidate

| Commit | Purpose |
|---|---|
| `2d5fc7292bcd90ee0339607c9cdb3d6526990087` | Preserve the final verification reports |
| `f09c4713251d01f0eabd0e4173f1e9d14ea18e49` | Add explicit SQLite, PostgreSQL, frontend, E2E, WCAG, Lighthouse and audit CI gates |
| `1a70569fae6d46a167b15e06c488b0dd36012681` | Pin Python CI jobs to Ubuntu 24.04 |
| `6fddc94b0a3ee2cecb78319820ce137f8547c374` | Harden Gemini 3.8 function responses/auditing and PayPal duplicate-batch recovery |
| `b50117757347efd86d13bc43838654c5da2bcf0a` | Raise judge-facing navigation and action touch targets to 44 px |

Changed tracked files from `8c8798a` through the application release SHA:

- `.github/workflows/ci.yml`
- `QA/ACCEPTANCE-EVIDENCE.md`
- `QA/RELEASE-READINESS.md`
- `backend/paypal_client.py`
- `backend/services/assistant.py`
- `backend/tests/test_assistant.py`
- `backend/tests/test_paypal_payouts.py`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/pactra.css`
- `frontend/src/pages/OverviewPage.tsx`
- `frontend/src/pages/PaymentPages.tsx`
- `frontend/src/pages/PublicPages.tsx`

## Test execution record

All times are 2026-11-09 WAT unless stated otherwise.

| Window | SHA/state | Evidence |
|---|---|---|
| Before 04:07 | `8c8798a` clean | Original exact-SHA regression: SQLite 87/9, PostgreSQL 96, 13 journeys, 14-surface WCAG, dependency audits, homepage-only Lighthouse |
| 04:12-04:18 | `1a70569` | GitHub Actions run `42555130996` passed all four mandatory jobs |
| 04:20-04:35 | provider patch before commit | Focused 32 passed; full SQLite 94 passed/9 skipped; full PostgreSQL 103 passed |
| 04:26-04:29 | `6fddc94` | GitHub Actions run `42556435101` passed all four mandatory jobs |
| 04:34-04:40 | UI patch before commit | Lint/build passed; 13 Playwright journeys passed; automated WCAG passed; visual checks at 320, 375, 390, 768, 1024 and 1440 px found no overflow, console errors or failed requests |
| 04:40-04:42 | `b501177` | GitHub Actions run `42557687655` passed all four mandatory jobs |

## Production state at freeze

- `pactra-api` and `pactra-worker` are active on the existing release.
- Both services report zero restarts since 2026-11-07 10:35:59 WAT.
- Gemini is disabled/unconfigured in production.
- PayPal Payouts is disabled/unconfigured in production.
- No candidate deployment, migration, restart, production configuration change,
  provider payout or production-data mutation has occurred.

## Remaining release blockers

1. Genuine Gemini function calling has not passed. The isolated request reached
   Google but returned `429 RESOURCE_EXHAUSTED`; fallback is not live acceptance.
2. PayPal Sandbox business credentials, Payouts capability and a distinct
   recipient are unavailable. No provider call has been made.
3. One USD 25.00 Sandbox payout still requires explicit operation-specific
   authorization after the prerequisites are securely installed.
4. The PayPal guided scenario cannot pass until the persisted item status is
   actual provider `SUCCESS` and reconciliation captures exactly once.
5. Production deployment, migration, service restart and Vercel promotion need
   explicit deployment approval after every preceding gate passes.
6. Public release-candidate smoke testing and deployed visual review remain
   unrun because the candidate is not deployed. A local candidate visual review
   passed at desktop, tablet and mobile widths.
7. A direct switch back to `0e3e905` with the database left at `0005` is not a
   valid rollback: the old release's Alembic graph cannot locate `0005`.
8. No rendered demo video artefact was found; video quality remains unverified.

Current release decision: **NO-GO**.
