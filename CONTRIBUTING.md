# Contributing to Pactra

## Workflow

1. Create a feature branch; do not work directly on `main`.
2. Keep production credentials, `.env`, databases, logs, browser traces, and `artifacts/` out of Git.
3. Preserve the sandbox-only boundary. Never add a live PayPal host or infer provider success from a fixture.
4. Add behaviour-focused tests for every financial state transition.
5. Run the relevant backend, PostgreSQL, frontend, browser, accessibility, and dependency gates.
6. Update the README, QA evidence, and README-to-product matrix when behaviour changes.
7. Open a pull request with migration impact, security considerations, test evidence, and rollback instructions.

## Engineering rules

- The API may validate, evaluate policy, persist state, and enqueue work. Only the worker may submit PayPal payouts.
- Use cents as integers. Do not perform financial calculations with binary floats.
- Reuse client and provider idempotency identifiers after ambiguous outcomes.
- Never release a reservation because of a timeout or unknown provider result.
- Capture only after individual payout-item `SUCCESS`.
- Preserve tenant ownership checks and CSRF on every mutation.
- Corrections to posted ledger activity use compensating journals; do not edit posted entries.

## Verification

Use the commands in [README.md](./README.md#tests). PostgreSQL concurrency tests require an isolated database and must never target production. External provider calls require a separately approved, bounded Sandbox operation.

## Pull request checklist

- [ ] Working tree contains no secrets or generated local artifacts.
- [ ] SQLite and PostgreSQL suites pass.
- [ ] Frontend lint and production build pass.
- [ ] Critical Playwright journeys and automated WCAG checks pass.
- [ ] Dependency audits pass or have a documented approved exception.
- [ ] Migration upgrade/downgrade and rollback impact are documented.
- [ ] README claims match implementation, UI, and evidence.
- [ ] Production was not changed unless the task separately authorized it.
