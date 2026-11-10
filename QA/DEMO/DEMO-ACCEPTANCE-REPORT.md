# Instant demo acceptance report

Report date: 2026-11-10
Candidate branch: `codex/instant-demo-20261110`
Production status: pending merge and deployment

## Test environment

- Host: Oracle node1, Ubuntu 24.04, arm64, 2 vCPU.
- Backend runtime: Python 3.12 project virtual environment.
- Frontend runtime: Node.js 22.23.4, npm 10.9.9.
- Databases: disposable SQLite file and isolated PostgreSQL database.
- Provider configuration: Gemini disabled; PayPal payouts disabled; no
  external provider request authorized or performed.
- Playwright retries: `0` for the critical demo and normal journey suites.
- Playwright: `1.64.1`; local Chromium/Chrome for Testing:
  `156.0.8078.4`; local Firefox: `157.0`.

The exact GitHub CI run and its WebKit version are added after exact-head CI.

## Local acceptance evidence

| Gate | Command/evidence | Result |
|---|---|---|
| Python syntax | `python -m compileall -q backend scripts` | PASS |
| SQLite migration | `python -m alembic upgrade head` through `20261110_0006` | PASS |
| SQLite backend | full `pytest -q` | PASS; PostgreSQL-only tests skipped |
| PostgreSQL migration | clean isolated database, upgrade through `20261110_0006` | PASS |
| PostgreSQL backend | full `pytest -q` | PASS |
| Demo service tests | `pytest -q backend/tests/test_demo_mode.py` | PASS, 10 tests |
| Frontend lint | `npm run lint` | PASS |
| Frontend build | `npm run build` | PASS |
| Critical demo | `npm run test:demo` with isolated PostgreSQL and production Vite preview | PASS, 4 tests, 59.3 s |
| Chromium regression | journeys, navigation, responsive matrix, Axe | PASS, 48 tests, 10.5 min |
| Firefox regression | full no-retry local suite | PASS, 48 tests, 12.9 min |
| WebKit local | host system libraries unavailable | NOT VERIFIED LOCALLY; CI installs dependencies |

## Critical judge journey

Verified in two simultaneous independent browser contexts:

1. Guest landing page showed Sign in, Sign up, Explore demo, and the required
   supporting copy.
2. Explore demo showed a preparation state and returned `201`.
3. Both contexts received different user IDs.
4. Seeded dashboard showed `$825 available`, `$140 reserved`, `$965 posted`,
   policy capacity, pending approvals, and all four seeded outcomes.
5. `$49` Linear software request completed through the internal sandbox.
6. The second context did not see the first context's Linear transaction.
7. `$120` Figma Teams request required approval.
8. Approval completed the request and exposed lifecycle, policy, audit, and
   ledger evidence.
9. Restricted Supply Co request was blocked with the actual policy reason.
10. Reset restored the seed and removed current-generation judge-created
    transactions.
11. Exit returned to guest navigation.
12. Normal registration, logout, and login still worked without a demo banner.

## Isolation and security tests

- distinct demo principals and cookies;
- cross-session receipt access returns `404`;
- normal/demo account separation;
- expiry and revocation rejection;
- reset row/wallet serialization;
- cleanup refuses owners without `is_demo=true`;
- normal records survive demo cleanup;
- direct provider-row injection is excluded by service and worker;
- PayPal client methods are not invoked for demo owners;
- session creation, reset, active count, and transaction count are bounded;
- separate normal session survives demo exit.

## Responsive and accessibility acceptance

The instant demo suite checked:

- `320 × 700`
- `375 × 812`
- `390 × 844`
- `768 × 1024`
- `1280 × 720`
- `1440 × 900`
- `1919 × 939`

For every size it asserted no document/main horizontal overflow, persistent
banner controls, independent mobile/desktop navigation scrolling, and a
reachable sidebar footer. Axe reported zero WCAG 2.1 A/AA violations on the
landing page, dashboard, and reset dialog. The broader Chromium suite passed
keyboard focus, Escape behavior, skip link, auth flicker, sidebar, and 48
responsive/accessibility journeys.

Manual NVDA/VoiceOver testing remains unverified.

## Screenshots

- [320 × 700](./screenshots/dashboard-320x700.png)
- [375 × 812](./screenshots/dashboard-375x812.png)
- [390 × 844](./screenshots/dashboard-390x844.png)
- [768 × 1024](./screenshots/dashboard-768x1024.png)
- [1280 × 720](./screenshots/dashboard-1280x720.png)
- [1440 × 900](./screenshots/dashboard-1440x900.png)
- [1919 × 939](./screenshots/dashboard-1919x939.png)

## Performance

The critical browser test asserts each of two concurrent demo entries completes
in less than three seconds from click to usable dashboard under local test
conditions. Both assertions passed. Exact local values were not emitted, so no
invented number is reported. Production timing, TTFB, and bottleneck analysis
remain pending deployment.

One earlier run used the Vite development server and measured `4,829 ms` for
one cold click-to-dashboard path. Its retained trace showed demo creation API
times of `1,229 ms` and `2,837 ms`; cold development-module compilation and
dashboard rendering accounted for the remaining delay. The acceptance config
now builds and serves the production bundle. The final no-retry production-
preview run passed both three-second assertions. This is local evidence only;
the deployed public timing remains the release gate.

## Known limitations

- Production behavior, public latency, and production session isolation are
  not yet verified in this candidate report.
- Local WebKit is not verified because required system libraries are absent;
  CI is configured to install them.
- Approval uses the requesting account as actor; independent maker-checker
  separation is not claimed.
- Demo assistant output is deterministic and simulated; no Gemini call is
  claimed.
- The seeded pending request requires a `$140` reservation, so the coherent
  wallet state differs from the landing preview's illustrative `$1,000`.

## Production acceptance

To be completed after merge and deployment:

- merged and deployed SHA;
- GitHub Actions run and all required jobs;
- Vercel deployment ID and production alias;
- Oracle active release and migration revision;
- API/worker health and restart counts;
- public creation latency;
- two-context production isolation;
- production reset and exit;
- normal authentication regression;
- provider/worker no-call evidence.
