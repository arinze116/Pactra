# Pactra Release Manifest

Updated: 2026-11-09, Africa/Lagos

## Release identity

| Item | Value |
|---|---|
| Repository | `arinze116/Pactra` |
| Runtime release commit | `73fdfb692f6daea69ba5f44bc37d9afa1814419a` |
| Runtime release directory | `/opt/pactra/releases/73fdfb6` |
| Embedded release SHA | `73fdfb692f6daea69ba5f44bc37d9afa1814419a` |
| Source archive | `/opt/pactra/releases/73fdfb6/.release-metadata/pactra-73fdfb6.tar` |
| Source archive SHA-256 | `6c16fbcd6b11187182f8ae1d9ea2374f12aa23ca39f629a35f112cabde1792c4` |
| Database revision | `20261107_0005` |
| PostgreSQL | `16.15` |
| Public URL | https://pactra-nine.vercel.app |
| Vercel deployment | `dpl_DjHTW75MnGQN11rcNZrY89NkrN9c` (`Ready`, production alias) |
| Vercel runtime source | Final closure release; frontend runtime files are unchanged from `4534d136...` |
| Main CI | [42659603721](https://github.com/arinze116/Pactra/actions/runs/42659603721), all four jobs passed on exact SHA `73fdfb69...` |
| Deployment start | `2026-11-09T17:00:40Z` |
| Previous production release | `/opt/pactra/releases/4534d13`, schema-compatible at `0005` |
| Legacy rollback release | `/opt/pactra/releases/0e3e905`, requires stopped-service downgrade to `0004` |

## Integrated pull requests

| PR | Merge commit | Purpose | Status |
|---:|---|---|---|
| [#7](https://github.com/arinze116/Pactra/pull/7) | `506108663ea6a535e54b3f834f95beaffee83ff6` | Release closure and evidence | PASS |
| [#8](https://github.com/arinze116/Pactra/pull/8) | `2f97cf07e27d572d9f7ad3efdd49d2c485bae347` | Server-side PayPal recipient correction | PASS |
| [#9](https://github.com/arinze116/Pactra/pull/9) | `9b4bc77cf65b5ac85be616f6c6afc4a7481de22b` | Public contrast/accessibility correction | PASS |
| [#10](https://github.com/arinze116/Pactra/pull/10) | `c599f5ca0603c1cc66b25684358c3336227dd8c3` | Semantic `<main>` landmarks | PASS |
| [#11](https://github.com/arinze116/Pactra/pull/11) | `4534d136766a094aeeac4489a9e694111b9257ae` | Bounded assistant/fallback wait in public crawl | PASS |
| [#12](https://github.com/arinze116/Pactra/pull/12) | `73fdfb692f6daea69ba5f44bc37d9afa1814419a` | Final release-evidence closure | PASS |

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
| Pre-deploy backup | `/opt/pactra/backups/pactra-pre-73fdfb692f6daea69ba5f44bc37d9afa1814419a-20261109T170019Z.dump` | PASS |
| Backup SHA-256 | `828a3b966c6dea957125fe9860f3793be9a777b781349edbb7ad8260b75264c0` | PASS |
| Restore/migration drill | Runtime-equivalent `4534d13` clone `pactra_restore_4534d13_20261109163956` | PASS |
| Restore revision/tables | `20261107_0005`, 16 base tables | PASS |
| Downgrade/re-upgrade | `0005 → 0004 → 0005`; measured user/transaction/reservation/ledger/audit counts unchanged | PASS |
| Downgrade consequence | `rate_limit_buckets` and its rows are dropped | PASS |
| Old-release readiness | `0e3e905` returned ready on the downgraded clone | PASS |

## Provider boundary

- Gemini configuration is present, but genuine Pactra function-call
  acceptance is **BLOCKED**. The bounded live workflow returned provider
  `503`/timeout and used the deterministic governed fallback.
- PayPal Sandbox acceptance is **PASS** for the separately authorised
  transaction `bfe1e158-863b-4ddf-93a0-e31146e7cbcb`. The API recorded one
  approval, the worker made one payout POST, and PayPal returned one item with
  item-level `SUCCESS`.
- Pactra persisted one attempt and the same provider batch/item identifiers,
  captured the $25.00 reservation once, posted one balanced
  `payment_capture` journal, and completed the receipt and audit trail. No
  duplicate payout, journal or unresolved reservation exists.

Deployment and public acceptance are complete. Overall product acceptance is
still **BLOCKED** only by genuine Gemini function-call acceptance.
