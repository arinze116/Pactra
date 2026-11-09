# Pactra Release Manifest

Updated: 2026-11-09, Africa/Lagos

The canonical frozen baseline and artefact inventory is
[`QA/ACCEPTED-PRODUCTION-BASELINE.md`](./ACCEPTED-PRODUCTION-BASELINE.md).
This manifest remains the point-in-time release record.

## Release identity

| Item | Value |
|---|---|
| Repository | `arinze116/Pactra` |
| Runtime release commit | `63f25839a6b645a8ca404846ecd82d16c1994b7c` |
| Accepted GitHub main baseline | `06d9181eca8d383a79003ac4559ea9c0084b3831` (documentation-only descendant of runtime) |
| Runtime release directory | `/opt/pactra/releases/63f2583` |
| Embedded release SHA | `63f25839a6b645a8ca404846ecd82d16c1994b7c` |
| Source archive | `/opt/pactra/releases/63f2583/.release-metadata/pactra-63f2583.tar` |
| Source archive SHA-256 | `6ba14264e0ee63ca49ae26af5ec15427ca3ae9ed25ab705498ee7c543bac5369` |
| Database revision | `20261107_0005` |
| PostgreSQL | `16.15` |
| Public URL | https://pactra-nine.vercel.app |
| Vercel deployment | `dpl_DjHTW75MnGQN11rcNZrY89NkrN9c` (`READY`, production alias) |
| Vercel deployment metadata | Commit `73fdfb692...`; live asset hashes match the accepted frontend build |
| Runtime CI | [42674909231](https://github.com/arinze116/Pactra/actions/runs/42674909231), all four jobs passed on exact SHA `63f25839...` |
| Accepted-main CI | [42678033819](https://github.com/arinze116/Pactra/actions/runs/42678033819), all four jobs passed on exact SHA `06d9181...` |
| Deployment start | `2026-11-09T18:42:05Z` |
| Previous production release | `/opt/pactra/releases/73fdfb6`, schema-compatible at `0005` |
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
| [#13](https://github.com/arinze116/Pactra/pull/13) | `60c0843f48351aa1fc611d25dcca14c539f8e843` | PayPal Sandbox acceptance evidence | PASS |
| [#14](https://github.com/arinze116/Pactra/pull/14) | `63f25839a6b645a8ca404846ecd82d16c1994b7c` | Gemini compatibility, failover and model selection | PASS |
| [#15](https://github.com/arinze116/Pactra/pull/15) | `06d9181eca8d383a79003ac4559ea9c0084b3831` | Gemini production acceptance evidence | PASS |

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
- The API process runs from `63f2583`. The intentionally retained worker
  process has cwd `73fdfb6`; all worker, PayPal, transaction, ledger, database
  and model modules are byte-identical between the two releases, and its
  advisory lease remains held.

## Backup and migration evidence

| Item | Value | Status |
|---|---|---|
| Configuration backup | `/opt/pactra/backups/pactra-env-pre-gemini-63f2583-20261109T184028Z.env` | PASS |
| Pre-deploy database backup | `/opt/pactra/backups/pactra-pre-63f25839a6b645a8ca404846ecd82d16c1994b7c-20261109T184028Z.dump` | PASS |
| Database backup SHA-256 | `9f4a9407fc2aa292480e4608f84449be5dbb83e315b193f7c8e7aa68dfe213ac` | PASS |
| Restore/migration drill | Runtime-equivalent `4534d13` clone `pactra_restore_4534d13_20261109163956` | PASS |
| Restore revision/tables | `20261107_0005`, 16 base tables | PASS |
| Downgrade/re-upgrade | `0005 → 0004 → 0005`; measured user/transaction/reservation/ledger/audit counts unchanged | PASS |
| Downgrade consequence | `rate_limit_buckets` and its rows are dropped | PASS |
| Old-release readiness | `0e3e905` returned ready on the downgraded clone | PASS |

## Provider boundary

- Gemini production acceptance is **PASS** on `gemini-3.5-flash-lite`. The
  public API returned one genuine `get_wallet_summary` call; persisted audit
  evidence recorded two provider calls, 1,391 ms, finish reason `STOP`, one
  successful tool call and no fallback/error.
- PayPal Sandbox acceptance is **PASS** for the separately authorised
  transaction `bfe1e158-863b-4ddf-93a0-e31146e7cbcb`. The API recorded one
  approval, the worker made one payout POST, and PayPal returned one item with
  item-level `SUCCESS`.
- Pactra persisted one attempt and the same provider batch/item identifiers,
  captured the $25.00 reservation once, posted one balanced
  `payment_capture` journal, and completed the receipt and audit trail. No
  duplicate payout, journal or unresolved reservation exists.

Deployment and public provider acceptance are complete. Overall product
acceptance is **PASS**.
