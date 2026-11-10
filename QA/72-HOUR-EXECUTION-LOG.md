# Pactra 72-Hour Release Execution Log

> Continuation, 2026-11-09: the worker-only PayPal correction is now on
> `codex/paypal-worker-single-authority`. Production provider configuration is
> present, but Gemini still lacks a successful function call and PayPal still
> lacks item-level `SUCCESS`. Current engineering evidence is in
> `QA/ACCEPTANCE-EVIDENCE.md`.

Started: 2026-11-09, Africa/Lagos  
Branch: codex/prd-gap-closure-20261107  
Decision at this checkpoint: **NO-GO**

This log records completed operations and observed results only. A provider
prerequisite or approval is not recorded as passed.

## Baseline

| Item | Verified value |
|---|---|
| Original release candidate | 8c8798a0dd89608c22b4c986428af9d815219771 |
| Production release | 0e3e905 |
| Production migration | 20261107_0004 |
| Candidate migration | 20261107_0005 |
| Public application | https://pactra-nine.vercel.app |
| Production services | pactra-api and pactra-worker active; start timestamp remains 2026-11-07 10:35:59 WAT |

Production was inspected read-only. No deployment, migration, service restart,
configuration change or production-data mutation was performed.

## Commit and CI timeline

| Time (WAT) | Commit or run | Verified event |
|---|---|---|
| 2026-11-07 12:02:39 | 8c8798a | Non-provider PRD gap closure candidate created |
| 2026-11-09 04:07:39 | 2d5fc72 | Final release-candidate QA evidence committed |
| 2026-11-09 04:08:46 | f09c471 | Exact release quality gates added to CI |
| 2026-11-09 04:12:47 | 1a70569 | Python CI jobs pinned to Ubuntu 24.04 |
| 2026-11-09 04:12:50–04:15:48 | CI 42555130996 | All four jobs passed for exact SHA 1a70569fae6d46a167b15e06c488b0dd36012681 |
| 2026-11-09 04:26:31 | 6fddc94 | Provider acceptance paths hardened |
| 2026-11-09 04:26:41–04:29:42 | CI 42556435101 | All four jobs passed for exact SHA 6fddc94b0a3ee2cecb78319820ce137f8547c374 |
| 2026-11-09 04:40:17 | b501177 | Judge-facing touch targets raised to 44 px after desktop/tablet/mobile review |
| 2026-11-09 04:40:27–04:42:54 | CI 42557687655 | All four jobs passed for exact SHA b50117757347efd86d13bc43838654c5da2bcf0a |

Green base run:
https://github.com/arinze116/Pactra/actions/runs/42555130996

Provider-hardening run:
https://github.com/arinze116/Pactra/actions/runs/42556435101

Current-candidate run:
https://github.com/arinze116/Pactra/actions/runs/42557687655

GitHub reported the workflow completed successfully at 2026-11-09 04:42:54
WAT for exact SHA b50117757347efd86d13bc43838654c5da2bcf0a:

- Backend - SQLite: PASS.
- Backend - PostgreSQL: PASS.
- Frontend - lint, build and audits: PASS.
- E2E - journeys, WCAG and homepage Lighthouse: PASS.

Exact-SHA CI blocker: **CLOSED** for the current application candidate
`b50117757347efd86d13bc43838654c5da2bcf0a`.

## Verified local test evidence

### Original application candidate 8c8798a

    APP_ENV=test \
    DATABASE_URL=sqlite:////tmp/pactra-rc-8c8798a-backend-20261109-r2.db \
    PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m pytest -o addopts='' -q

Result: 87 passed, 9 skipped, 1 warning in 62.34 seconds.

    APP_ENV=test \
    DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_backend_20261109_r2 \
    PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m alembic upgrade head

    APP_ENV=test \
    DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_backend_20261109_r2 \
    PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m pytest -o addopts='' -q

Result: migration through 20261107_0005 passed; 96 passed, 1 warning in
62.45 seconds.

    cd frontend
    npm ci
    npm run lint
    npm run build
    npm audit --omit=dev --audit-level=high
    npm audit --audit-level=moderate
    ../.venv-linux/bin/python -m pip check
    ../.venv-linux/bin/python -m pip_audit -r ../requirements.txt

Result: install, lint and Vite 8.3.6 production build passed; both npm audits
reported zero vulnerabilities; Python reported no broken requirements and no
known vulnerabilities.

    cd frontend
    E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python \
    E2E_DATABASE_URL=postgresql+psycopg:///pactra_rc_8c8798a_e2e_20261109 \
    npm run test:e2e

Result: 13 journeys passed in 1.4 minutes. The automated WCAG suite passed
across 14 surfaces in 26.4 seconds.

Homepage-only Lighthouse result: performance 0.97, accessibility 1.00, best
practices 0.96. No route-wide Lighthouse claim is made.

### Provider hardening candidate 6fddc94

    APP_ENV=test \
    DATABASE_URL=sqlite:////tmp/pactra-provider-targeted-20261109-v3.db \
    AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false \
    PAYPAL_MOCK_MODE=true SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m pytest -o addopts='' -q \
      backend/tests/test_assistant.py \
      backend/tests/test_paypal_payouts.py

Result: 32 passed in 6.25 seconds before commit
6fddc94b0a3ee2cecb78319820ce137f8547c374.

The same provider patch passed the full database suites before commit:

    APP_ENV=test \
    DATABASE_URL=sqlite:////tmp/pactra-provider-full-20261109-v2.db \
    SECRET_KEY=provider-full-secret-key-at-least-32-bytes \
    AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=true \
    SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/alembic upgrade head

    APP_ENV=test \
    DATABASE_URL=sqlite:////tmp/pactra-provider-full-20261109-v2.db \
    SECRET_KEY=provider-full-secret-key-at-least-32-bytes \
    AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=true \
    SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m pytest -o addopts='' -q

Result: 94 passed, 9 skipped in 19.73 seconds.

    APP_ENV=test \
    DATABASE_URL=postgresql+psycopg:///pactra_provider_full_20261109_0432 \
    SECRET_KEY=provider-full-secret-key-at-least-32-bytes \
    AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=false \
    SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/alembic upgrade head

    APP_ENV=test \
    DATABASE_URL=postgresql+psycopg:///pactra_provider_full_20261109_0432 \
    SECRET_KEY=provider-full-secret-key-at-least-32-bytes \
    AI_ENABLED=false PAYPAL_PAYOUTS_ENABLED=false PAYPAL_MOCK_MODE=false \
    SESSION_COOKIE_SECURE=false \
    .venv-linux/bin/python -m pytest -o addopts='' -q

Result: 103 passed in 20.71 seconds.

These tests verify provider-independent orchestration and failure handling.
They do not prove a live Gemini function call or PayPal Sandbox payout.

### Judge-facing UI candidate b501177

    cd frontend
    npm run lint
    npm run build
    E2E_PYTHON=/home/ubuntu/pactra/.venv-linux/bin/python npm run test:e2e

Result: lint and production build passed; 13 Playwright journeys passed in 2.7
minutes; the automated WCAG 2.1 AA suite passed in 30.6 seconds across the 14
configured surfaces.

An isolated local visual review captured desktop, tablet and mobile candidate
screens. Viewport checks at 320, 375, 390, 768, 1024 and 1440 pixels found no
horizontal overflow, browser console errors or failed HTTP responses. Primary
navigation, guided-scenario actions, payment-type controls and mobile menus
were raised to a 44-pixel minimum target without changing product hierarchy or
branding. This is local pre-deployment evidence, not public production smoke.

## Gemini acceptance

A secure local project key was exercised from an isolated local acceptance
database without changing production configuration. The provider returned HTTP 429
quota/resource exhaustion. Pactra used its deterministic fallback and persisted
sanitized error/fallback audit events.

Observed isolated-database evidence:

- Five assistant.error events.
- Five assistant.fallback_used events.
- Zero assistant.tool_called events.
- Zero persisted tool-role messages.
- One internal-sandbox payment created by deterministic fallback, not by a
  genuine Gemini function call.

Result: **BLOCKED**. Live Gemini function calling has not been demonstrated.
A fallback result is not provider acceptance.

## PayPal Sandbox acceptance

Production configuration was inspected without printing secrets:

| Setting | Verified state |
|---|---|
| PAYPAL_PAYOUTS_ENABLED | false |
| PAYPAL_MOCK_MODE | false |
| Sandbox base URL | https://api-m.sandbox.paypal.com |
| Client ID present | No |
| Client secret present | No |
| Test recipient present | No |

Payouts capability and a valid Sandbox recipient have not been verified. No
specific payout operation has been authorised. No OAuth request, payout batch,
payout item or reconciliation request was sent.

Result: **BLOCKED**. No provider batch/item identifiers exist and no PayPal
success is claimed.

## Migration and rollback

Migration 20261107_0005 was previously exercised on an isolated clone of the
production database. Upgrade from 0004 passed, including a concurrent-reader
test with a two-second lock timeout. The observed upgrade completed in 0.88
seconds.

Downgrade drops `rate_limit_buckets` and deletes active limiter state. The old
`0e3e905` release cannot start against a database stamped at `0005` because its
systemd pre-start runs an Alembic graph that ends at `0004`. The reviewed
rollback is therefore a stopped-application downgrade using the candidate
release's migration code, followed by the atomic switch to `0e3e905`. This
does not alter financial, user, transaction, audit or ledger tables. A tested
rollback-compatible old artefact that recognizes `0005` would avoid the
destructive limiter reset.

Production remains at 0004. No production backup, migration or rollback was
executed because deployment approval has not been granted and the provider
release gates are not closed.

## Current blockers

1. Gemini quota/entitlement must permit a genuine typed function call.
2. PayPal Sandbox business credentials, Payouts capability and a valid
   recipient must be available.
3. A specific no-real-money Sandbox payout requires explicit authorisation.
4. The PayPal guided scenario cannot pass before a real item-level SUCCESS.
5. Production deployment, migration and service restart require explicit
   deployment approval.
6. Public post-deployment acceptance has not run.

## Checkpoint decision

**NO-GO.** Exact-SHA CI is green. Both live provider acceptance gates, the
guided PayPal scenario, production migration/deployment and public smoke test
remain incomplete.
