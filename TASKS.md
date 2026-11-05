# Pactra submission release tasks

Source of truth: `Pactra-PRD-Judge-Ready.md` and the verified state of PR #2 on 5 November 2026.

| ID | Outcome | Owned paths | Depends on | Owner | Acceptance and verification |
| --- | --- | --- | --- | --- | --- |
| R1 | CI and release configuration work on current runners and unique Render services | `.github/workflows/ci.yml`, `render.yaml` | None | Parent | Python setup succeeds; PostgreSQL migration job runs; Render names/URLs do not collide; sandbox-only guards remain enabled |
| R2 | Production database/auth/provider contracts are correct | `backend/**`, migrations, backend tests | None | Parent | PostgreSQL UUID types align; cross-origin session/CSRF works; production config fails closed; policy/ledger/provider races have regression tests |
| R3 | Judge UI is resilient and safe to test | `frontend/**` | Backend CSRF response-header contract | Frontend specialist | Lint/build pass; E2E cannot inherit provider credentials or an existing DB; retry idempotency, optional provider failures, pagination and mobile smoke are covered |
| R4 | Documentation and environment template match verified behavior | `.env.example`, `README.md`, `IMPLEMENTATION_NOTES.md`, `DEMO.md` | R1-R3 | Parent | Setup, migrations, both sandbox rails, exact variables, judge script, fallbacks and external blockers are accurate and secret-free |
| R5 | Integrated release reaches `origin/main` | Git/GitHub/CI | R1-R4 | Parent | Full local checks pass; PR #2 checks are green and merged; remote `main` SHA verified; PR #1 is closed as superseded; deployment is verified or exact dashboard actions are reported |

Critical path: R2 -> R3 integration -> R4 -> R5. R1 runs independently until the final CI gate.

Integration checkpoints:

1. Backend focused tests after schema/security fixes.
2. Frontend lint/build after the response-header contract lands.
3. Fresh isolated SQLite migration plus complete Playwright suite.
4. PostgreSQL CI migration/runtime verification on the pushed branch.
5. Final secret scan, diff review, PR merge and remote-main verification.

Cut line: no P0 product, PayPal Sandbox, Gemini tool, auth, ledger, policy, approval, receipt, migration, security, or judge-flow requirement may be cut. Unrelated redesign and stretch features remain out of scope.
