# Pactra Release Manifest

Updated: 2026-11-09, Africa/Lagos

## Release identity

| Item | Value |
|---|---|
| Repository | `arinze116/Pactra` |
| Runtime release commit | `4534d136766a094aeeac4489a9e694111b9257ae` |
| Runtime release directory | `/opt/pactra/releases/4534d13` |
| Canonical final commit after evidence merge | The full value in `/opt/pactra/current/.release-sha`; the evidence-only closure commit has identical runtime code |
| Source archive | `/opt/pactra/releases/4534d13/.release-metadata/pactra-4534d13.tar` |
| Source archive SHA-256 | `7b54f3923994af46e7aed7da3e3f60f2d19220d50a2ab0757613d8d1002d8610` |
| Database revision | `20261107_0005` |
| PostgreSQL | `16.15` |
| Public URL | https://pactra-nine.vercel.app |
| Vercel deployment | `dpl_J8HgUXreUmJMdKhC4Eu8MZ3jdfbo` (`Ready`, production alias) |
| Vercel runtime source | `c599f5ca0603c1cc66b25684358c3336227dd8c3`; runtime frontend files are unchanged through `4534d136...` |
| Main CI | [42656025377](https://github.com/arinze116/Pactra/actions/runs/42656025377), all four jobs passed on exact SHA `4534d136...` |
| Deployment start | `2026-11-09T16:41:01Z` |
| Previous production release | `/opt/pactra/releases/9b4bc77`, schema-compatible at `0005` |
| Legacy rollback release | `/opt/pactra/releases/0e3e905`, requires stopped-service downgrade to `0004` |

## Integrated pull requests

| PR | Merge commit | Purpose | Status |
|---:|---|---|---|
| [#7](https://github.com/arinze116/Pactra/pull/7) | `506108663ea6a535e54b3f834f95beaffee83ff6` | Release closure and evidence | PASS |
| [#8](https://github.com/arinze116/Pactra/pull/8) | `2f97cf07e27d572d9f7ad3efdd49d2c485bae347` | Server-side PayPal recipient correction | PASS |
| [#9](https://github.com/arinze116/Pactra/pull/9) | `9b4bc77cf65b5ac85be616f6c6afc4a7481de22b` | Public contrast/accessibility correction | PASS |
| [#10](https://github.com/arinze116/Pactra/pull/10) | `c599f5ca0603c1cc66b25684358c3336227dd8c3` | Semantic `<main>` landmarks | PASS |
| [#11](https://github.com/arinze116/Pactra/pull/11) | `4534d136766a094aeeac4489a9e694111b9257ae` | Bounded assistant/fallback wait in public crawl | PASS |

## Verified contents

- Worker-only PayPal submission with PostgreSQL atomic claims and one worker
  lease.
- Stable provider batch/item identifiers and separated submission and
  reconciliation cycles.
- Unknown outcomes remain reserved and cannot be blindly resubmitted.
- Item-level `SUCCESS` is the only successful capture condition.
- Terminal failure releases reservations once; return/reversal/refund
  compensation is idempotent.
- Masked PayPal recipients remain display-only. The API resolves and persists
  the configured unmasked Sandbox recipient server-side.
- Authentication, authorisation, CSRF, rate limiting, policy enforcement,
  audit, receipt and tenant-isolation regressions passed.
- Frontend `dist`, resolved Python/npm manifests and build hashes are present
  in the immutable release.

## Backup and migration evidence

| Item | Value | Status |
|---|---|---|
| Pre-deploy backup | `/opt/pactra/backups/pactra-pre-4534d136766a094aeeac4489a9e694111b9257ae-20261109T163956Z.dump` | PASS |
| Backup SHA-256 | `e7c1ce7bac3891586d19c0165be42eda0dde21c3da93b2e1fa4178c1c50b7f1e` | PASS |
| Restore database | `pactra_restore_4534d13_20261109163956` | PASS |
| Restore revision/tables | `20261107_0005`, 16 base tables | PASS |
| Downgrade/re-upgrade | `0005 → 0004 → 0005`; measured user/transaction/reservation/ledger/audit counts unchanged | PASS |
| Downgrade consequence | `rate_limit_buckets` and its rows are dropped | PASS |
| Old-release readiness | `0e3e905` returned ready on the downgraded clone | PASS |

## Provider boundary

- Gemini configuration is present, but genuine Pactra function-call
  acceptance is **BLOCKED**. The bounded live workflow returned provider
  `503`/timeout and used the deterministic governed fallback.
- PayPal Sandbox OAuth and Payouts scope are **PASS**. The prepared transaction
  `bfe1e158-863b-4ddf-93a0-e31146e7cbcb` remains `pending_approval` with zero
  attempts and no provider identifiers.
- The exact $25.00 USD Sandbox payout is **BLOCKED** pending separate explicit
  transaction-specific authorisation. No payout was submitted.

Deployment and public acceptance are complete. Overall product acceptance is
still **BLOCKED** by the two provider-success requirements above.
