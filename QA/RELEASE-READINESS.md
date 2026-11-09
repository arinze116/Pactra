# Pactra Release Readiness

Assessment updated: 2026-11-09, Africa/Lagos

Release-candidate commit: `8c8798a0dd89608c22b4c986428af9d815219771`

Release-candidate migration: `20261107_0005`

Production database migration (read-only verification): `20261107_0004`

## Recommendation

# NO-GO

**Verified.** The release-candidate code passes every locally executable
backend, PostgreSQL, frontend, browser, automated accessibility, homepage
Lighthouse and dependency gate at the exact requested SHA. Migration `0005`
also upgrades a clone of the current production database successfully.

Release/deployment remains NO-GO because the exact commit has no GitHub CI run,
live Gemini acceptance is unverified, and no real PayPal Sandbox payout item
has reached item-level `SUCCESS` with exactly-once reconciliation. The PayPal
guided scenario consequently remains blocked. Nothing was deployed and no
production data, service or configuration was changed.

## Release-candidate identity and CI

- Exact HEAD before and after the test rerun:
  `8c8798a0dd89608c22b4c986428af9d815219771`.
- Tracked working tree before and after the rerun: clean.
- The requested QA report edits are the only expected working-tree changes
  after evidence collection.
- Valid CI run ID for this SHA: **none**.
- GitHub commit association: **none**; GitHub does not contain the commit.
- Actions runs for this SHA: **0**.
- Nearest existing CI run: `42262019828` on unrelated commit
  `1067e611f1405995736bab5221b2af5765db1d3d`; not release evidence.

## Actual gate results

| Gate | Exact-SHA result | CI result |
|---|---|---|
| SQLite backend | PASS — 87 passed, 9 skipped | NOT RUN for this SHA |
| PostgreSQL backend | PASS — 96 passed | NOT RUN for this SHA |
| Frontend install/lint/build | PASS — Vite 8.3.6 | NOT RUN for this SHA |
| E2E journeys | PASS — 13 passed | NOT RUN for this SHA |
| WCAG 2.1 AA automation | PASS — 14 public/authenticated surfaces | NOT RUN for this SHA |
| Python dependency checks | PASS — consistent; no known vulnerabilities | NOT RUN for this SHA |
| npm production/full audits | PASS — 0 vulnerabilities | NOT RUN for this SHA |
| Lighthouse | PASS — homepage only: 0.97 / 1.00 / 0.96 | NOT RUN for this SHA |

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

**Compatibility: PASS.** Existing production table names do not collide. The
new application requires `0005` before serving requests. The prior application
can ignore the additive table, so application rollback should leave `0005` in
place.

**Downgrade: destructive to limiter state.** The tested downgrade drops the
index and table, deleting all active rate-limit buckets. Do not downgrade while
the new application is running. Immediate application rollback should retain
the additive migration.

The migration was not run against production.

## Original backlog disposition

All 14 original backlog rows are mapped to code and acceptance evidence in
`QA/ACCEPTANCE-EVIDENCE.md`, including the separately tracked PayPal guided
scenario.

| Disposition | Rows |
|---|---:|
| PASS for implementation and available acceptance scope | 10 |
| PARTIAL because exact-commit CI did not run | 1 — INF-005 |
| BLOCKED on genuine provider acceptance | 3 — Gemini, PayPal, PayPal guided scenario |

The internal reset/retry/reversal row is passed only for internal and
provider-state-fixture behaviour. It is not evidence of a real PayPal outcome;
live PayPal reconciliation remains within the blocked provider row.

## Provider claims

No provider call was made. Gemini results came from `FakeGeminiClient`; PayPal
state-machine results came from `FakePayPalClient`; the E2E environment disabled
both providers and used no credentials. Synthetic `SUCCESS` fixture values are
not treated as PayPal acceptance. There is no claim of live Gemini or PayPal
success.

## Remaining blockers

1. Push the feature commit through the approved feature-branch workflow and
   obtain a successful CI run whose `head_sha` is exactly
   `8c8798a0dd89608c22b4c986428af9d815219771`.
2. After separate credential/configuration approval, verify a deployed live
   Gemini function call using the required model plus safe failure/fallback.
3. After separate PayPal capability, credential, recipient and payout-test
   authorization, verify a real Sandbox payout item reaches `SUCCESS` and is
   reconciled exactly once.
4. Re-run the PayPal guided scenario against that persisted real provider
   result.
5. Only after the preceding gates pass, deploy the release candidate and run
   the public smoke suite.

## Non-blocking maintenance findings

- FastAPI TestClient emitted one Starlette/httpx deprecation warning.
- `npm ci` reported ESLint 9.39.5 as no longer supported despite clean audits.
- Lighthouse remains homepage-only.

## Prohibited actions respected

No deployment, service restart, production configuration change, credential
provisioning, provider call or production-data mutation was performed.
