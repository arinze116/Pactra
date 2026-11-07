# Oracle and Vercel deployment

Pactra is publicly deployed at <https://pactra-nine.vercel.app>. The production
Vercel rewrite uses `https://node1.taild90918.ts.net` as its trusted HTTPS
upstream because Oracle's public security list blocks direct TCP 80/443 access.

## Oracle runtime

1. Keep PostgreSQL on its default loopback listeners and use the dedicated
   `pactra` operating-system/database role pair with peer authentication.
2. Install a release at `/opt/pactra/current`, including a private virtualenv.
3. Generate `/etc/pactra/secret-key` with cryptographically secure random data,
   owned by `pactra:pactra` and mode `0600`.
4. Install `pactra.env.oracle-baseline` as `/etc/pactra/pactra.env`, mode `0600`.
   Replace the localhost origins only after the real HTTPS origins are known.
5. Back up PostgreSQL, then install the two systemd units. The API unit runs
   `alembic upgrade head` before Uvicorn starts on `127.0.0.1:8010`.
6. Start the API first, verify `/api/ready`, then start the worker. The worker
   holds a PostgreSQL advisory lock so only one process reconciles payouts.

Do not add the Nginx site until its placeholders have been replaced. Install it
as a new Pactra site; never edit the existing Clavis virtual host.

The current fallback does not modify Nginx. Tailscale Funnel terminates public
HTTPS and proxies to `http://127.0.0.1:8010`. Verify it with:

```bash
sudo tailscale funnel status
curl --fail https://node1.taild90918.ts.net/api/ready
```

Disable only Pactra's Funnel route with
`sudo tailscale funnel --https=443 off`. Do not reset or reconfigure the base
Tailscale connection.

## PostgreSQL backup and restore drill

Create a private custom-format archive before each release or migration:

```bash
sudo install -d -o pactra -g pactra -m 0700 /opt/pactra/backups
sudo -u pactra pg_dump --format=custom --compress=9 \
  --file=/opt/pactra/backups/pactra-YYYYMMDDTHHMMSSZ.dump pactra
sudo chmod 0600 /opt/pactra/backups/pactra-YYYYMMDDTHHMMSSZ.dump
sudo -u pactra pg_restore --list \
  /opt/pactra/backups/pactra-YYYYMMDDTHHMMSSZ.dump
```

Never test a restore over the live `pactra` database. Create a new drill
database, restore into it, and verify the migration revision and table counts:

```bash
sudo -u postgres createdb --owner=pactra pactra_restore_check_YYYYMMDD
sudo -u pactra pg_restore --exit-on-error \
  --dbname=pactra_restore_check_YYYYMMDD \
  /opt/pactra/backups/pactra-YYYYMMDDTHHMMSSZ.dump
sudo -u pactra psql --dbname=pactra_restore_check_YYYYMMDD \
  --command="SELECT version_num FROM alembic_version;"
```

Keep the live service pointed at `pactra` until the drill database has been
validated. Removing a drill database or rotating archives is a separate,
explicitly approved operation.

## Vercel frontend

The linked Vercel project is `pactra`. Use `frontend` as the upload root,
`npm ci` as the install command, `npm run build` as the build command, Node 22,
and `dist` as the output directory. `frontend/vercel.json` contains the active
rewrite. Leave `VITE_API_URL` absent so browser requests remain same-origin.

After deployment, verify registration, CSRF-protected mutations, cookies,
receipts, persistence, and cross-user isolation through the public Vercel URL.

## Release-candidate migration and rollback

The current release candidate adds migration `20261107_0005`. It creates only
the `rate_limit_buckets` table and its expiry index. It does not rewrite user,
wallet, transaction, audit, or ledger rows. Test the migration on a restored
database before production approval.

For an approved release:

1. Create and verify `/opt/pactra/backups/pactra-pre-<release-sha>-<UTC>.dump`.
2. Install the immutable release directory without changing `/opt/pactra/current`.
3. Stop only `pactra-api` and `pactra-worker`, switch the symlink, and start the
   API. Its pre-start migration advances PostgreSQL to `20261107_0005`.
4. Verify `/api/ready`, registration/login rate limits, wallet, preview,
   payment, approval, receipt, reset, worker lease, Funnel and Vercel rewrite.
5. Start the worker only after API and database readiness pass.

Expected interruption is one API restart, normally under a minute. If the new
release fails before accepting traffic, point `/opt/pactra/current` back to the
previous release and restart the two Pactra services. The previous application
can safely ignore the additive `rate_limit_buckets` table. Do not downgrade the
migration during the immediate rollback; restore the verified backup only for
a separately diagnosed database failure.
