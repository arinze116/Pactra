# Instant demo acceptance report

- Report date: 2026-11-10
- Feature branch: `codex/instant-demo-20261110`
- Feature head: `2bb69d40b024bb89ced20b9d5a1480009dced2a0`
- Pull request: `#20`
- Merged production SHA: `28634c13082a61b5c53e75528eacf2263ea1fd5e`
- Production status: deployed and verified

## Test environment

- Oracle node1: Ubuntu 24.04, arm64, 2 vCPU.
- Backend runtime: Python 3.12.3.
- Frontend runtime: Node.js 22.23.4, npm 10.9.9.
- Playwright: 1.64.1.
- Production browser: Chrome for Testing 156.0.8078.4.
- Exact-main CI browsers: Chromium 156.0.8078.4, Firefox 157.0,
  WebKit 27.2.
- Production URL: <https://pactra-nine.vercel.app>.
- Playwright retries: `0` for the critical demo suites and production
  acceptance journey.
- Production provider configuration remained unchanged. No Gemini or PayPal
  request was invoked by demo acceptance.

Local WebKit execution remains unavailable because this arm64 host lacks its
required operating-system libraries. Exact-main GitHub CI installed the
required browser dependencies and passed WebKit.

## Merge and CI evidence

PR `#20` merged normally without bypass. Exact-main run
[`42849003993`](https://github.com/arinze116/Pactra/actions/runs/42849003993)
passed:

| Job | Result |
|---|---|
| Backend — SQLite | PASS; full suite, PostgreSQL-only cases skipped |
| Backend — PostgreSQL | PASS; full suite and migration `0006` |
| Frontend lint, build, production audit, full audit | PASS |
| Cross-browser journeys | PASS; 141 tests in 10.7 minutes |
| Dedicated accessibility group | PASS; 3 tests |
| Instant-demo suite | PASS; 4 tests with retries disabled |
| CI Lighthouse | PASS; performance 0.98, accessibility 1.00, best practices 0.96 |

The exact feature head also passed push run `42845616003` and PR run
`42845631485` before merge.

## Local and isolated-database evidence

| Gate | Evidence | Result |
|---|---|---|
| SQLite and PostgreSQL backend | Full `pytest -q` suites | PASS |
| Demo service | `backend/tests/test_demo_mode.py` | PASS; 10 tests |
| Frontend | `npm run lint`, `npm run build` | PASS |
| Dependencies | `pip check`, `pip-audit`, production and full npm audits | PASS; zero known release-blocking findings |
| Secret review | Added-line, high-confidence tracked-source, bundle, and non-example `.env` scans | PASS |
| Backup | Custom-format archive, `pg_restore --list`, checksum, age, mode | PASS |
| Restore drill | Isolated database restored from the production backup | PASS |
| Migration drill | Clone advanced `0005 -> 0006` | PASS |
| Core row counts | users, wallets, transactions, holds, journals, entries, audit, attempts | PASS; unchanged by migration |
| Financial invariants | Ten read-only ledger/provider/state checks | PASS before and after migration |
| Rollback readiness | `ca361c0` application plus byte-identical `0006` migration | PASS at schema `0006` |

Backup evidence:

- path:
  `/opt/pactra/backups/pactra-pre-28634c13082a61b5c53e75528eacf2263ea1fd5e-20261110T161229Z.dump`;
- size: 178,792 bytes;
- SHA-256:
  `02158efde0f9aa1aa5e43b196a966bb6f274927ae690217a8366ee43dd4c1a0e`;
- isolated restore: `pactra_restore_demo_20261110T161229Z`;
- restored core counts: `56,56,107,87,159,318,905,68`;
- migration-aware rollback:
  `/opt/pactra/releases/ca361c0-0006`.

The isolated restore database was dropped after verification. Temporary
Playwright trace archives were also deleted because traces can contain session
cookies.

## Production deployment evidence

| Surface | Verified result |
|---|---|
| Oracle release | `/opt/pactra/releases/28634c1` |
| Embedded release SHA | `28634c13082a61b5c53e75528eacf2263ea1fd5e` |
| Database | `20261110_0006` |
| API | active/running, release cwd, zero restarts |
| Worker | active/running, release cwd, zero restarts, one advisory lease |
| API readiness | local, Funnel, and Vercel proxy returned `200`/ready |
| Vercel deployment | `dpl_FYe3PxM6VXxN8Nh3rLFwFhzd52cL` |
| Vercel alias | `pactra-nine.vercel.app` |
| Vercel metadata | `gitCommitSha` and `pactraReleaseSha` both equal merged SHA |
| Provider backlog | zero unresolved; zero unknown attempts |
| PayPal attempt count | one historical attempt before and after demo acceptance |
| Financial invariants | all ten passed after production migration and browser journey |
| Service warnings | none since deployment |

Deployment began at `2026-11-10T16:16:46Z`. The API unit performed the
transactional `0005 -> 0006` migration exactly once before Uvicorn started.
Rollback was not triggered. No unrelated service or infrastructure changed.

## Critical production judge journey

The final production browser journey used retries disabled and verified:

1. The fresh landing page showed **Sign in**, **Sign up**, **Explore demo**,
   and the required supporting copy.
2. **Explore demo** showed **Preparing demo…** and returned `201`.
3. Independent contexts had different demo user IDs and isolated cookies.
4. Refresh restored the active demo.
5. The dashboard showed `$825.00` available, `$140.00` reserved, `$965.00`
   posted, one pending approval, policy capacity, and four seeded outcomes.
6. Policy inspection showed `$500.00` daily, `$750.00` per payment, approval
   above `$100.00`, and `Restricted Supply Co` blocked.
7. A `$49.00` Linear software request completed through the internal sandbox.
8. The isolation context could not see that transaction; direct foreign
   transaction access returned `404`.
9. A `$120.00` Figma Teams request required approval and completed after the
   real approval service re-evaluated policy.
10. The seeded Northstar Print House approval was rejected through the normal
    rejection service and audit path.
11. Restricted Supply Co returned the persisted deterministic policy block.
12. Completed receipts exposed lifecycle, policy result, audit evidence,
    balanced ledger impact, and the explicit simulated-demo disclosure.
13. Reset restored the original balances, policy, transactions, and `0/7`
    walkthrough state.
14. Exit revoked the demo and cleared only demo cookies.
15. A separate normal session survived demo exit; normal logout and login then
    passed without a demo banner.
16. The second demo exited to guest navigation.

A direct demo request on `paypal_sandbox_payouts` returned
`403 DEMO_SANDBOX_ONLY`. Session cookies were Secure, HttpOnly, SameSite=Lax,
and absent from URLs and browser storage.

### Production harness notes

Preliminary no-retry runs surfaced test-harness assumptions, not product
failures: one attempted an extra software approval after the real category
budget was consumed; one used an ambiguous vendor text selector; one blanket
console assertion treated the intentional policy-block `422` as an unhandled
error. Each run stopped immediately. The final harness used the seeded pending
request for rejection, role-specific selectors, and allowed only the expected
`403` provider rejection and `422` policy rejection. No production control,
rate limit, policy, or provider boundary was weakened to make the test pass.

## Responsive, keyboard, and accessibility acceptance

Production screenshots and assertions covered:

- `320 × 700`
- `375 × 812`
- `390 × 844`
- `768 × 1024`
- `1280 × 720`
- `1440 × 900`
- `1919 × 939`

For every viewport, the test waited for settled dashboard content, asserted no
document or main-content horizontal overflow, kept banner controls reachable,
and verified independent mobile/desktop navigation scrolling and the sidebar
footer. The `390 × 844` dashboard also passed a 200% root text-size check
without horizontal overflow.

Keyboard acceptance verified visible focus, Enter activation, initial dialog
focus on **Cancel**, and Escape dismissal. Axe reported zero WCAG 2.1 A/AA
violations on the production landing page, dashboard, and reset dialog.
Required mobile controls use 44 px targets. Manual NVDA/VoiceOver remains
unverified.

## Production screenshots

- [320 × 700](./screenshots/production/dashboard-320x700.png)
- [375 × 812](./screenshots/production/dashboard-375x812.png)
- [390 × 844](./screenshots/production/dashboard-390x844.png)
- [768 × 1024](./screenshots/production/dashboard-768x1024.png)
- [1280 × 720](./screenshots/production/dashboard-1280x720.png)
- [1440 × 900](./screenshots/production/dashboard-1440x900.png)
- [1919 × 939](./screenshots/production/dashboard-1919x939.png)

The mobile, tablet, and desktop images were visually inspected. They preserve
Pactra's dark operational hierarchy, persistent restrained demo banner,
readable financial values, unclipped navigation, and reachable reset/exit
controls.

## Performance

Observed public click-to-usable-dashboard measurements were all below the
three-second target. No value was fabricated; the browser emitted each sample.
The final clean, no-retry production run created two fresh sessions
concurrently in `1,548 ms` and `942 ms`, then passed the complete journey in
`24.7 s`. Across recorded production runs, entry samples ranged from `712 ms`
to `1,548 ms`.

Production Lighthouse on the public landing page:

| Metric | Result |
|---|---:|
| Performance | `0.99` |
| Accessibility | `1.00` |
| Best practices | `1.00` |
| Largest Contentful Paint | `1,515 ms` |
| Cumulative Layout Shift | `0.006` |
| Total Blocking Time | `80 ms` |
| Speed Index | `1,515 ms` |

Five command-line samples observed landing-page TTFB/total between
`44–78 ms`. Public `/api/ready` samples completed between `56–251 ms`.

## Known limitations

- Approval uses the requesting account as actor. Independent maker-checker
  role separation is not claimed.
- Demo assistant responses are deterministic and simulated; demo mode does
  not call Gemini.
- All demo funds, execution, receipts, and ledger movements are sandbox-only.
- Local WebKit and manual screen-reader testing remain unverified on node1;
  WebKit passed exact-main CI.
- The seeded pending request requires a `$140.00` reservation, so the coherent
  production dashboard is `$965 posted / $140 reserved / $825 available`.

## Acceptance verdict

**DEMO READY** — critical isolation, provider exclusion, policy, approval,
rejection, receipt, reset, exit, normal-auth regression, responsive/WCAG,
performance, backup, rollback readiness, and exact-SHA production deployment
passed. Video recording itself is intentionally outside this mission.
