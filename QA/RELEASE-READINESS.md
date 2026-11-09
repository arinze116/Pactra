# Pactra Release Readiness

Assessment updated: 2026-11-09 04:43 WAT

Application release-candidate commit:
`b50117757347efd86d13bc43838654c5da2bcf0a`

Release-candidate migration: `20261107_0005`

Production database migration (read-only verification): `20261107_0004`

## Recommendation

# NO-GO

**Verified.** The application candidate has successful exact-SHA CI and passes
every locally executable backend, PostgreSQL, frontend, browser, automated
accessibility, homepage Lighthouse and dependency gate. Migration `0005` also
upgrades a clone of the current production database successfully.

Release/deployment remains NO-GO because live Gemini acceptance is unverified
after a provider `429`, and no real PayPal Sandbox payout item
has reached item-level `SUCCESS` with exactly-once reconciliation. The PayPal
guided scenario consequently remains blocked. Nothing was deployed and no
production data, service or configuration was changed.

## Release-candidate identity and CI

- Application SHA: `b50117757347efd86d13bc43838654c5da2bcf0a`.
- Branch: `codex/prd-gap-closure-20261107`.
- CI run: `42557687655`.
- URL: https://github.com/arinze116/Pactra/actions/runs/42557687655
- GitHub `headSha`: exact match.
- Conclusion: `success` at 2026-11-09 04:42:54 WAT.
- All four mandatory jobs passed; none was skipped.

## Actual gate results

| Gate | Exact-SHA result | CI result |
|---|---|---|
| SQLite backend | PASS — local 94 passed, 9 skipped | PASS — Backend SQLite job |
| PostgreSQL backend | PASS — local 103 passed | PASS — Backend PostgreSQL job |
| Frontend install/lint/build | PASS — Vite 8.3.6 | PASS — frontend job |
| E2E journeys | PASS — 13 passed | PASS — E2E job |
| WCAG 2.1 AA automation | PASS — 14 public/authenticated surfaces | PASS — E2E job |
| Python dependency checks | PASS — consistent; no known vulnerabilities | PASS — PostgreSQL job |
| npm production/full audits | PASS — 0 vulnerabilities | PASS — frontend job |
| Lighthouse | PASS — homepage only; last recorded scores 0.97 / 1.00 / 0.96 | PASS — homepage-only CI assertion |

The WCAG result is an automated Axe scan, not a manual screen-reader or
assistive-technology certification.

## Lighthouse scope

Lighthouse was run only against the local preview homepage `/`. It did not
cover sign-in, sign-up, authenticated pages, not-found pages or every route.
Do not describe the Lighthouse evidence as route-wide. Separate Playwright/Axe
coverage scanned 14 public and authenticated surfaces.

## Migration `20261107_0005`

**Upgrade safety: PASS on an isolated clone of the current production
database.** Production PostgreSQL 16.15 was inspected read-only at migration
`0004`; the target table/index did not exist. The clone upgraded to `0005` and
created only `rate_limit_buckets` plus its expiry index.

**Locking: low-risk, not lock-free.** The migration uses transactional DDL and
does not alter or rewrite an existing application table. With an active
`ACCESS SHARE` reader on `transactions` and a two-second migration lock
timeout, the upgrade completed in 0.88 seconds. It still takes short
catalog/namespace locks and locks on the new relation, so concurrent schema DDL
must be avoided and the controlled restart window remains appropriate.

**Forward compatibility: PASS.** Existing production table names do not
collide. The new application requires `0005` before serving requests.

**Downgrade: destructive to limiter state.** The tested downgrade drops the
index and table, deleting all active rate-limit buckets. The prior `0e3e905`
application code ignores the table, but its systemd pre-start Alembic graph
ends at `0004` and cannot start against a database stamped at `0005`. Until a
rollback-compatible old artefact exists, rollback must stop both services, use
the candidate release to downgrade to `0004`, verify the table is absent,
switch the symlink and then start the old services.

The migration was not run against production.

## Original backlog disposition

All 14 original backlog rows are mapped to code and acceptance evidence in
`QA/ACCEPTANCE-EVIDENCE.md`, including the separately tracked PayPal guided
scenario.

| Disposition | Rows |
|---|---:|
| PASS for implementation and available acceptance scope | 11 |
| BLOCKED on genuine provider acceptance | 3 — Gemini, PayPal, PayPal guided scenario |

The internal reset/retry/reversal row is passed only for internal and
provider-state-fixture behaviour. It is not evidence of a real PayPal outcome;
live PayPal reconciliation remains within the blocked provider row.

## Provider claims

One isolated Gemini request reached the exact model and returned
`429 RESOURCE_EXHAUSTED`; it produced no tool call and fell back safely. PayPal
state-machine results came from `FakePayPalClient`; no PayPal provider request
was sent. The E2E environment disabled both providers. Synthetic `SUCCESS`
fixture values are not treated as provider acceptance.

## Remaining blockers

1. Resolve Gemini quota/entitlement and verify all required tools through
   genuine function calls on the exact model. Production enablement remains a
   deployment/configuration approval action.
2. After separate PayPal capability, credential, recipient and payout-test
   authorization, verify a real Sandbox payout item reaches `SUCCESS` and is
   reconciled exactly once.
3. Re-run the PayPal guided scenario against that persisted real provider
   result.
4. Only after the preceding gates pass, obtain explicit deployment approval,
   deploy the release candidate and run
   the public smoke suite.

## Non-blocking maintenance findings

- FastAPI TestClient emitted one Starlette/httpx deprecation warning.
- `npm ci` reported ESLint 9.39.5 as no longer supported despite clean audits.
- Lighthouse remains homepage-only.
- The local candidate has a strong, distinctive control-room hierarchy and no
  responsive overflow after the touch-target correction. Public deployed
  visual review remains unrun.
- No rendered demo video artefact was found, so video quality is not verified.

## Prohibited actions respected

No deployment, service restart, production configuration change, credential
provisioning, PayPal call or production-data mutation was performed. The only
external provider operation was the isolated Gemini request that returned 429.
