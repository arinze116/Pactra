# Pactra Deployment and Rollback Runbook

Last verified: 2026-11-09, Africa/Lagos

This runbook prepares the Pactra release candidate for the existing Oracle VPS,
PostgreSQL, systemd, Tailscale Funnel and Vercel architecture. It does not
authorize a deployment. Obtain explicit owner approval before the production
backup, service stop, symlink change, migration, restart or Vercel deployment.

## Verified production baseline

- Backend release: `/opt/pactra/releases/0e3e905`.
- Active symlink: `/opt/pactra/current`.
- Database: PostgreSQL 16.15, database `pactra`, approximately 9.8 MB.
- Production migration: `20261107_0004`.
- Candidate migration: `20261107_0005`.
- Production does not contain `rate_limit_buckets` or
  `ix_rate_limit_buckets_expires`.
- API unit: `pactra-api.service`.
- Worker unit: `pactra-worker.service`.
- Both units run as `pactra:pactra` with `/etc/pactra/pactra.env`.
- The API unit runs `python -m alembic upgrade head` as `ExecStartPre`.
- Backup directory: `/opt/pactra/backups`, mode `0700`, owner
  `pactra:pactra`.
- Installed `pg_dump`, `pg_restore` and `createdb`: PostgreSQL 16.15.

## Mandatory pre-deployment gates

Do not begin the production operation until every gate below is recorded as
PASS in the release evidence.

- The final feature-branch SHA is frozen and recorded in the release manifest.
- GitHub Actions completed against that exact SHA with every mandatory job
  passing.
- Backend SQLite and PostgreSQL suites pass.
- Frontend lint, production build, Playwright journeys and automated WCAG
  checks pass.
- Production and full dependency audits pass or have an explicitly approved
  PRD-compatible exception.
- Genuine Gemini function calling and safe fallback acceptance pass.
- One explicitly authorized PayPal Sandbox payout reaches item-level
  `SUCCESS` and exactly-once Pactra reconciliation.
- All six guided scenarios pass using persisted server state.
- Migration `0005` passes on an isolated clone of the current production
  database.
- The rollback procedure in this document is reviewed and accepted.
- No unresolved PayPal provider transaction exists in production.
- The release directory and private virtual environment are complete and
  immutable.
- The owner explicitly approves the production deployment, migration and
  required Pactra service restarts.

Record the deployment inputs without printing secrets:

```bash
pactra_release_sha=<FINAL_RELEASE_SHA>
pactra_release_dir=/opt/pactra/releases/${pactra_release_sha}
pactra_previous_release=/opt/pactra/releases/0e3e905

git rev-parse HEAD
git status --short
gh run list --commit "${pactra_release_sha}" --limit 10

sudo test -d "${pactra_release_dir}"
sudo test -x "${pactra_release_dir}/.venv/bin/python"
sudo test -f "${pactra_release_dir}/backend/migrations/versions/20261107_0005_shared_rate_limits.py"
sudo readlink -f /opt/pactra/current
sudo systemctl is-active pactra-api pactra-worker
```

Inspect only configuration presence. Never print credential values.

## Migration assessment

Migration `20261107_0005` creates one new table and one index:

- `rate_limit_buckets.key_hash`: `VARCHAR(64)` primary key.
- `window_started_at`: timezone-aware timestamp, non-null.
- `expires_at`: timezone-aware timestamp, non-null.
- `event_count`: integer, non-null.
- `ix_rate_limit_buckets_expires` on `expires_at`.

The migration has no backfill, foreign key, default expression or rewrite of
an existing table. PostgreSQL applies the DDL transactionally. The ordinary
index is non-concurrent, but it is built on the newly created empty table.
Short catalog/namespace locks and locks on the new relation still occur.
Avoid concurrent schema DDL during the release.

An isolated production-data clone upgraded from `0004` to `0005` while an
`ACCESS SHARE` reader held the existing `transactions` table. The migration
completed within a two-second lock timeout. Production itself has not been
migrated.

Alembic version tracking makes `upgrade head` operationally repeatable after a
successful migration. The raw `upgrade()` function is not re-entrant if called
outside Alembic version control.

## Backup and integrity verification

Run this after deployment approval and before stopping services. The custom
archive is written as a temporary file and renamed only after basic integrity
checks pass.

```bash
pactra_backup_utc=$(date -u +%Y%m%dT%H%M%SZ)
pactra_backup=/opt/pactra/backups/pactra-pre-${pactra_release_sha}-${pactra_backup_utc}.dump

sudo install -d -o pactra -g pactra -m 0700 /opt/pactra/backups
sudo -u pactra pg_dump \
  --format=custom \
  --compress=9 \
  --file="${pactra_backup}.tmp" \
  pactra

sudo -u pactra test -s "${pactra_backup}.tmp"
sudo -u pactra pg_restore --list "${pactra_backup}.tmp" >/dev/null
sudo -u pactra mv "${pactra_backup}.tmp" "${pactra_backup}"
sudo -u pactra chmod 0600 "${pactra_backup}"
sudo -u pactra sha256sum "${pactra_backup}"
sudo stat -c 'path=%n size=%s mode=%a owner=%U group=%G' "${pactra_backup}"
```

Failure of `pg_dump`, the non-empty check or `pg_restore --list` stops the
deployment. Do not continue with an incomplete archive.

## Isolated restore drill

Restore into a new database only. Never restore over `pactra` as a test.

```bash
pactra_restore_utc=$(date -u +%Y%m%dT%H%M%SZ)
pactra_restore_db=pactra_restore_${pactra_restore_utc}

sudo -u postgres createdb --owner=pactra "${pactra_restore_db}"
sudo -u pactra pg_restore \
  --exit-on-error \
  --no-owner \
  --dbname="${pactra_restore_db}" \
  "${pactra_backup}"

sudo -u pactra psql --dbname="${pactra_restore_db}" --set=ON_ERROR_STOP=1 \
  --command="SELECT version_num FROM alembic_version;"
sudo -u pactra psql --dbname="${pactra_restore_db}" --set=ON_ERROR_STOP=1 \
  --command="SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
```

Record the restored revision and table count. Run the agreed read-only ledger,
reservation and audit invariants against the drill database. Removing a drill
database is a separate destructive cleanup operation and is not part of this
runbook.

## Forward deployment sequence

The API systemd unit is the only migration authority. Do not manually run
`alembic upgrade head` and then start the API. Starting the API executes the
candidate release's `ExecStartPre` and advances `0004` to `0005` once.

Record the start time and current state:

```bash
pactra_deploy_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
sudo readlink -f /opt/pactra/current
sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 \
  --command="SELECT version_num FROM alembic_version;"
sudo systemctl status pactra-api pactra-worker --no-pager
```

Stop only Pactra services, worker first:

```bash
sudo systemctl stop pactra-worker.service
sudo systemctl stop pactra-api.service
sudo systemctl is-active pactra-worker pactra-api || true
```

Atomically switch the release symlink. Abort if the temporary path already
exists.

```bash
sudo test ! -e /opt/pactra/current.next
sudo test ! -L /opt/pactra/current.next
sudo ln -s "${pactra_release_dir}" /opt/pactra/current.next
sudo mv -Tf /opt/pactra/current.next /opt/pactra/current
sudo test "$(sudo readlink -f /opt/pactra/current)" = "${pactra_release_dir}"
```

Start the API. Its pre-start command performs the migration.

```bash
sudo systemctl start pactra-api.service
sudo systemctl is-active pactra-api.service
sudo journalctl -u pactra-api.service \
  --since "${pactra_deploy_started_utc}" --no-pager

sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 --tuples-only \
  --command="SELECT version_num FROM alembic_version;"
sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 --tuples-only \
  --command="SELECT to_regclass('public.rate_limit_buckets'), to_regclass('public.ix_rate_limit_buckets_expires');"
```

Expected revision: `20261107_0005`. Both relations must be present. If the
pre-start or migration fails, do not start the worker and do not attempt a
second ad-hoc migration. Preserve logs and begin the reviewed rollback.

Verify API readiness before starting the worker:

```bash
curl --fail --silent http://127.0.0.1:8010/api/ready
curl --fail --silent https://node1.taild90918.ts.net/api/ready
curl --fail --silent https://pactra-nine.vercel.app/api/ready
```

Start and verify the worker:

```bash
sudo systemctl start pactra-worker.service
sudo systemctl is-active pactra-worker.service
sudo journalctl -u pactra-worker.service \
  --since "${pactra_deploy_started_utc}" --no-pager
```

If PayPal is enabled, the worker should acquire the PostgreSQL advisory lease.
If PayPal is intentionally disabled, it should report that reconciliation is
disabled and stand by. A worker exception or restart loop fails deployment.

Record that unrelated services, Nginx sites, Docker containers, certificates,
firewall rules and Tailscale base configuration were not changed.

Deploy the Vercel frontend only through its existing linked project and record
the resulting deployment ID and alias. Do not place provider secrets in Vercel
or any `VITE_*` variable.

## Critical old-release Alembic incompatibility

The old release contains migrations only through `20261107_0004`. Its Alembic
runner cannot locate `20261107_0005`. The API systemd unit always executes the
current release's Alembic runner before Uvicorn.

Therefore this sequence is unsafe and must not be used:

1. Leave the database stamped at `0005`.
2. Point `/opt/pactra/current` to `0e3e905`.
3. Start `pactra-api`.

The old pre-start would fail with `Can't locate revision identified by
'20261107_0005'`, even though the old application models otherwise ignore the
additive table.

The preferred long-term rollback artefact is the old application plus a
tested migration graph that recognizes `0005`. Until that artefact exists,
use the stopped-application downgrade sequence below.

## Safe stopped-application rollback

This rollback returns the schema to `0004` before the symlink is switched. It
requires the candidate release directory and virtual environment to remain on
disk.

Consequences:

- Downgrade drops `ix_rate_limit_buckets_expires` and
  `rate_limit_buckets`.
- Every active registration/login rate-limit window is lost and starts clean.
- User, session, wallet, policy, transaction, provider, audit and ledger tables
  are not altered by migration `0005`.
- Both Pactra services remain stopped throughout the schema reversal.

Record the rollback start and stop the services:

```bash
pactra_rollback_started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
sudo systemctl stop pactra-worker.service
sudo systemctl stop pactra-api.service
sudo systemctl is-active pactra-worker pactra-api || true

sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 --tuples-only \
  --command="SELECT version_num FROM alembic_version; SELECT coalesce(to_regclass('public.rate_limit_buckets')::text, 'absent');"
```

The commands below assume the revision check returns `20261107_0005`. If the
database is still at `20261107_0004` and the rate-limit table is absent, skip
the downgrade and proceed directly to the old-release symlink switch. Do not
query `rate_limit_buckets` when the table is absent.

When the revision is `0005`, record the limiter rows that will be discarded:

```bash
sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 --tuples-only \
  --command="SELECT count(*) FROM rate_limit_buckets;"
```

Run the downgrade with the candidate migration code, not the old release:

```bash
sudo -u pactra bash -c '
  set -a
  . /etc/pactra/pactra.env
  set +a
  cd "$1"
  .venv/bin/python -m alembic downgrade 20261107_0004
' bash "${pactra_release_dir}"
```

Verify the downgrade before changing the symlink:

```bash
sudo -u pactra psql pactra --set=ON_ERROR_STOP=1 --tuples-only \
  --command="SELECT version_num FROM alembic_version; SELECT coalesce(to_regclass('public.rate_limit_buckets')::text, 'absent');"
```

Expected output: revision `20261107_0004` and table `absent`. If the downgrade
fails, do not point `current` at the old release and do not start the old API.
Keep the candidate symlink in place, preserve logs and diagnose the failure.

Switch back atomically and start the old API:

```bash
sudo test ! -e /opt/pactra/current.next
sudo test ! -L /opt/pactra/current.next
sudo ln -s "${pactra_previous_release}" /opt/pactra/current.next
sudo mv -Tf /opt/pactra/current.next /opt/pactra/current
sudo test "$(sudo readlink -f /opt/pactra/current)" = "${pactra_previous_release}"

sudo systemctl start pactra-api.service
sudo systemctl is-active pactra-api.service
sudo journalctl -u pactra-api.service \
  --since "${pactra_rollback_started_utc}" --no-pager

curl --fail --silent http://127.0.0.1:8010/api/ready
curl --fail --silent https://node1.taild90918.ts.net/api/ready
curl --fail --silent https://pactra-nine.vercel.app/api/ready

sudo systemctl start pactra-worker.service
sudo systemctl is-active pactra-worker.service
```

Restore the previous Vercel deployment only if the frontend is incompatible
with the rolled-back API. Record its deployment ID and alias change.

## Backup restore is a last resort

Do not overwrite or drop the production database during an ordinary rollback.
Use the verified custom archive only for a separately diagnosed database
failure and only after explicit approval for the destructive restore. Restore
into a new database first, validate it, and prepare an explicit controlled
cutover. Never use `pg_restore --clean` against production as an exploratory
step.

## Deployment evidence to retain

- Final branch and SHA.
- Exact GitHub Actions run ID and URL.
- Release and previous-release directory paths.
- Backup filename, size, ownership, checksum and `pg_restore --list` result.
- Restore-drill database name, revision and invariant results.
- Deployment and rollback timestamps.
- API pre-start migration log showing `0004 -> 0005` exactly once.
- Database revision and new relation checks.
- API and worker systemd status and logs.
- Local, Funnel and public readiness responses.
- Vercel deployment ID and alias.
- Public smoke-test identifiers and results, redacted where appropriate.
- Confirmation that no unrelated service or infrastructure was changed.
