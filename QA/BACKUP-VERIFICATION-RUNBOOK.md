# Pactra Backup Verification Runbook

Date: 2026-11-09

This runbook verifies retained PostgreSQL custom archives without restoring or
modifying them. Production restore requires separate approval and an isolated
restore drill first.

## Repository command

```bash
python -m scripts.verify_backup /path/to/archive.dump \
  --sha256 <expected-sha256> \
  --require-checksum \
  --min-bytes 1024 \
  --max-age-hours <policy-hours> \
  --json
```

The verifier rejects symbolic links, requires a regular file, calculates
SHA-256 in bounded chunks, checks size and optional age, and runs
`pg_restore --list` with a 30-second timeout. It suppresses archive contents
and never runs a restore.

Possible checks are:

- `backup_too_small`;
- `backup_stale`;
- `checksum_missing`;
- `checksum_mismatch`;
- `archive_list_failed`.

Any check fails the command. Do not delete or overwrite the archive in
response.

## Accepted release backup

| Field | Value |
|---|---|
| Path | `/opt/pactra/backups/pactra-pre-63f25839a6b645a8ca404846ecd82d16c1994b7c-20261109T184028Z.dump` |
| Associated runtime | `63f25839a6b645a8ca404846ecd82d16c1994b7c` |
| Size | 173,373 bytes |
| Owner/mode | `pactra:pactra`, `0600` |
| SHA-256 | `9f4a9407fc2aa292480e4608f84449be5dbb83e315b193f7c8e7aa68dfe213ac` |
| SHA result | PASS |
| `pg_restore --list` | PASS |

The pre-Gemini environment backup is
`/opt/pactra/backups/pactra-env-pre-gemini-63f2583-20261109T184028Z.env`,
owned by root with mode `0600`. Never print or commit its contents.

## Manual read-only verification on node1

```bash
sudo -u pactra test -s /opt/pactra/backups/<archive>.dump
sudo -u pactra pg_restore --list \
  /opt/pactra/backups/<archive>.dump >/dev/null
sudo -u pactra sha256sum /opt/pactra/backups/<archive>.dump
sudo stat -c 'path=%n size=%s mode=%a owner=%U group=%G mtime=%y' \
  /opt/pactra/backups/<archive>.dump
```

Compare the digest with an independently retained expected value. A checksum
calculated only after corruption is not independent verification.

## Freshness and job diagnosis

For each backup, record associated release, UTC creation time, size, digest,
archive-list result, and last isolated restore result. Investigate:

- no pre-change archive for the proposed release;
- a `.tmp` or zero-byte result;
- an archive materially smaller than the recent baseline without explanation;
- checksum absence/mismatch;
- `pg_restore --list` failure or timeout;
- owner/mode broader than required;
- a failed scheduled job or stale last-success timestamp.

No scheduled backup-verification alert is currently active.

## Restore testing

Restore only into a new disposable database by following
`QA/DEPLOYMENT-AND-ROLLBACK.md`. Never use production `pactra` as the restore
target, never use `--clean` against production, and never claim recoverability
from archive listing alone. Record schema revision, representative aggregate
counts, and read-only financial invariants. Removal of a drill database is a
separate destructive action and requires deliberate authorization.
