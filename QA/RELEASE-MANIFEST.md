# Pactra Release Manifest

Updated: 2026-11-09

| Item | Value |
|---|---|
| Feature branch | `codex/paypal-worker-single-authority` |
| Branch baseline | `82e1b75a2ab59a105fee2b59c2aa481f63c738a5` |
| Final feature SHA | `9138cbd7c91170a52c9cc1f0b469964c2cebe637` |
| Pull request | [#5](https://github.com/arinze116/Pactra/pull/5), merged |
| Merge commit | `3d6125bd62b4d202c83b28fcc5a03c752cba525a` |
| Documentation pull requests | [#6](https://github.com/arinze116/Pactra/pull/6) and [#7](https://github.com/arinze116/Pactra/pull/7), merged |
| Previous staged `main` SHA | `4ac86897cf66f66df5d80d024f00e315999f7b95` |
| PayPal verification integration | [#8](https://github.com/arinze116/Pactra/pull/8); its merge commit supersedes the previous staged SHA |
| Previous RC branch | `codex/prd-gap-closure-20261107` |
| Production release | `0e3e905` |
| Production migration | `20261107_0004` |
| Candidate migration | `20261107_0005` |
| Previous staged artifact | `/opt/pactra/releases/4ac8689`, exact SHA `4ac86897...`, read-only, inactive, and not eligible for activation after PR #8 |
| Current staging authority | The full SHA in the new immutable release's `.release-sha`, matched to successful final-main CI |
| Public URL | https://pactra-nine.vercel.app |
| Final feature CI | Run [42576205916](https://github.com/arinze116/Pactra/actions/runs/42576205916), success on exact SHA `9138cbd7...` |
| Implementation merge CI | Run [42576672051](https://github.com/arinze116/Pactra/actions/runs/42576672051), success on exact SHA `3d6125bd...` |
| Previous staged `main` CI | Run [42577769242](https://github.com/arinze116/Pactra/actions/runs/42577769242), success on exact SHA `4ac86897...` |
| Production status | API and worker active on `0e3e905`; current symlink and database unchanged |

## Candidate changes

- Worker-only PayPal submission and PostgreSQL atomic claims.
- Stable provider identifiers and separate submission/reconciliation cycles.
- Explicit same-attempt recovery for ambiguous no-batch outcomes.
- Expanded provider failure, crash, concurrency, approval, and authorization
  regressions.
- Removal of legacy PayPal Orders execution.
- Masked provider recipient status.
- Receipt recovery UI and keyboard/skip-link accessibility coverage.
- Server-side configured-recipient resolution with configuration-level email
  validation; masked status values remain display-only.
- PayPal Sandbox execution runbook with a manual authorization checkpoint.
- README reconstruction, ADR, contribution guide, changelog, and QA truth
  matrix.

## Local evidence timestamp

2026-11-09, Africa/Lagos:

- SQLite: 118 passed, 10 skipped.
- PostgreSQL: 128 passed.
- Frontend lint/build: passed.
- Browser/WCAG: 16 journeys and 14 configured Axe surfaces passed locally.
- Migration drill: passed outside production.

## Remaining blockers

- Gemini function call blocked by provider quota/entitlement.
- PayPal item-level `SUCCESS` and real reconciliation unverified.
- PayPal guided scenario incomplete.
- Candidate not deployed and public smoke not run.

No activation, service restart, configuration change, migration, database
mutation, provider request, or payout occurred during this workstream.
Production remains active on release `0e3e905`.

The `4ac86897...` artifact and CI rows are historical evidence, not the current
release candidate after PR #8. Stage and verify the exact integrated `main`
commit before any deployment. Production release status remains blocked on the
external provider and deployment acceptance gates listed above.
