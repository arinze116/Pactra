# Pactra Production Operations Runbook

Verified against production: 2026-11-09, Africa/Lagos

Canonical baseline: `QA/ACCEPTED-PRODUCTION-BASELINE.md`

This runbook is for Pactra only. Do not change unrelated VPS services,
containers, Nginx sites, certificates, domains, firewall rules or Tailscale
configuration. Routine diagnosis is read-only. A restart, deployment,
configuration edit, migration, provider action or data repair requires the
approval and release process in `QA/RELEASE-FREEZE-POLICY.md`.

## Production coordinates

| Item | Value |
|---|---|
| API unit | `pactra-api.service` |
| Worker unit | `pactra-worker.service` |
| Environment file | `/etc/pactra/pactra.env` |
| Active symlink | `/opt/pactra/current` |
| Accepted release | `/opt/pactra/releases/63f2583` |
| Immediate rollback | `/opt/pactra/releases/73fdfb6` |
| API bind | `127.0.0.1:8010` |
| PostgreSQL bind | `127.0.0.1:5432` |
| Local health | `http://127.0.0.1:8010/api/health` |
| Local readiness | `http://127.0.0.1:8010/api/ready` |
| Direct public readiness | `https://node1.taild90918.ts.net/api/ready` |
| Public application | `https://pactra-nine.vercel.app` |
| Database | `pactra`, PostgreSQL 16.15 |
| Migration | `20261107_0005` |

The current worker process predates the Gemini-only release and has cwd
`/opt/pactra/releases/73fdfb6`. Its payment and worker modules are byte-for-byte
identical to `63f2583`. Do not restart it merely to normalize the path.

## Safe health check

### Services and process identity

```bash
systemctl show pactra-api.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts \
  -p ExecMainStartTimestamp -p Result

systemctl show pactra-worker.service \
  -p ActiveState -p SubState -p MainPID -p NRestarts \
  -p ExecMainStartTimestamp -p Result

sudo readlink -f /proc/"$(systemctl show pactra-api.service -p MainPID --value)"/cwd
sudo readlink -f /proc/"$(systemctl show pactra-worker.service -p MainPID --value)"/cwd
```

Expected steady state is `active/running`, restart count zero, API cwd
`63f2583`, and the retained worker cwd documented above. A PID change is not
automatically a fault; compare start time, restart count and journal evidence.

### Release identity

```bash
sudo readlink -f /opt/pactra/current
sudo -u pactra sed -n '1p' /opt/pactra/current/.release-sha
sudo stat -c 'path=%n owner=%U:%G mode=%a modified=%y' \
  /opt/pactra/current /opt/pactra/releases/63f2583
```

Expected target: `/opt/pactra/releases/63f2583`; expected embedded SHA:
`63f25839a6b645a8ca404846ecd82d16c1994b7c`.

### API and public path

```bash
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8010/api/health
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8010/api/ready
curl --fail --silent --show-error --max-time 15 \
  https://node1.taild90918.ts.net/api/ready
curl --fail --silent --show-error --max-time 15 \
  https://pactra-nine.vercel.app/api/ready
```

`/api/ready` must report `status=ready`, `database=ok`, Sandbox mode, internal
Sandbox available, AI configured, and PayPal Sandbox configured. It does not
prove either external provider is currently healthy.

### Database connectivity and revision

This command loads the protected environment without printing it, starts a
read-only transaction, and reports only safe metadata:

```bash
sudo -u pactra bash <<'SH'
set -a
. /etc/pactra/pactra.env
set +a
cd /opt/pactra/current
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from sqlalchemy import text
from backend.database import engine

with engine.connect() as connection:
    connection.execute(text("SET TRANSACTION READ ONLY"))
    print("database=" + connection.execute(text("SELECT current_database()" )).scalar_one())
    print("postgres=" + connection.execute(text("SHOW server_version")).scalar_one())
    print("revision=" + connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one())
    print("read_only=" + connection.execute(text("SHOW transaction_read_only")).scalar_one())
    print("connectivity=" + str(connection.execute(text("SELECT 1")).scalar_one()))
    connection.rollback()
PY
SH
```

Expected revision: `20261107_0005`.

### Worker lease and backlog

This does not attempt to acquire the lease:

```bash
sudo -u pactra bash <<'SH'
set -a
. /etc/pactra/pactra.env
set +a
cd /opt/pactra/current
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PY'
from sqlalchemy import text
from backend.database import engine
from backend.worker import RECONCILIATION_LEASE_KEY

with engine.connect() as connection:
    connection.execute(text("SET TRANSACTION READ ONLY"))
    lease = connection.execute(text("""
        SELECT count(*)::int
        FROM pg_locks
        WHERE locktype = 'advisory'
          AND granted
          AND ((classid::bigint << 32) + objid::bigint) = :lease_key
    """), {"lease_key": RECONCILIATION_LEASE_KEY}).scalar_one()
    backlog = connection.execute(text("""
        SELECT count(*)::int
        FROM transaction_attempts AS attempt
        JOIN transactions AS transaction
          ON transaction.id = attempt.transaction_id
        WHERE transaction.rail = 'paypal_sandbox_payouts'
          AND (
            (transaction.status = 'executing'
             AND attempt.status IN ('submitting','claimed','processing','unknown'))
            OR
            (transaction.status = 'completed'
             AND attempt.status IN ('processing','unknown'))
          )
    """)).scalar_one()
    print(f"lease_holders={lease}")
    print(f"eligible_or_unresolved_backlog={backlog}")
    connection.rollback()
PY
SH
```

Expected normal values are one lease holder and zero backlog. A nonzero
backlog is not authorization to invoke reconciliation manually.

### Capacity

```bash
df -h / /opt /var/lib/postgresql
free -h
uptime
cat /proc/loadavg
sudo ss -ltnp '( sport = :8010 or sport = :5432 )'
```

Freeze baseline: 42% disk used with 84 GiB available, 9.7 GiB memory
available, two vCPUs, and 8 of 100 PostgreSQL connections used by `pactra` at
the sample time.

## Log investigation

Keep investigation local. Before copying logs into a ticket or chat, remove
credentials, cookies, authorization headers, email addresses, recipient data,
request bodies and unrelated customer identifiers.

### Recent warnings and errors

```bash
pactra_since='-30 minutes'
sudo journalctl -u pactra-api.service \
  --since "${pactra_since}" -p warning --no-pager -o short-iso
sudo journalctl -u pactra-worker.service \
  --since "${pactra_since}" -p warning --no-pager -o short-iso
```

### API startup and availability

```bash
sudo journalctl -u pactra-api.service --since today --no-pager -o short-iso \
  --grep 'Started server process|Application startup complete|Database readiness check failed'
```

### Authentication and authorization failures

```bash
sudo journalctl -u pactra-api.service --since '-30 minutes' --no-pager -o cat \
  --grep ' 401 | 403 |CSRF|SESSION|AUTH'
```

Do not interpret an individual 401/403 as an incident. Look for rate,
cross-tenant behavior, repeated source patterns and corresponding user reports.

### Policy rejection

Policy decisions are durable transaction audit events. Query counts and event
types, not payloads or recipient fields, unless an authorized incident review
requires a specific transaction.

```sql
BEGIN READ ONLY;
SELECT event_type, count(*)
FROM audit_events
WHERE event_type IN ('payment.blocked', 'payment.pending_approval')
  AND created_at >= now() - interval '30 minutes'
GROUP BY event_type;
ROLLBACK;
```

### Gemini failures and fallback

```bash
sudo journalctl -u pactra-api.service --since '-30 minutes' --no-pager -o cat \
  --grep 'Gemini request failed|Gemini client cleanup failed|deterministic fallback'
```

Durable audit event types are `assistant.provider_completed`,
`assistant.error`, `assistant.fallback_used`, and `assistant.tool_called`.
Inspect only safe fields such as model, classification, HTTP status, provider
status, call count, latency and finish reason. Do not export prompts or keys.

### PayPal submission and reconciliation

```bash
sudo journalctl -u pactra-worker.service --since '-30 minutes' \
  --no-pager -o short-iso \
  --grep 'acquired the database lease|Processed .* PayPal payout|reconciliation failed|reconciliation scan failed'
```

Authoritative durable event types are `paypal.payout_submitted` and
`paypal.payout_reconciled`. Inspect the existing transaction and attempt by
stable local/provider identifier. Never use log absence alone to decide a
provider request was not accepted.

### Database errors

```bash
sudo journalctl -u pactra-api.service -u pactra-worker.service \
  --since '-30 minutes' --no-pager -o cat \
  --grep 'Database readiness check failed|OperationalError|psycopg|connection refused|too many clients'
```

## Incident response

### API unavailable

1. Record current symlink, embedded SHA, API/worker PIDs, start times and
   restart counts.
2. Check loopback health, then readiness, then the public paths.
3. Check PostgreSQL connectivity and capacity.
4. Inspect API warnings/errors since the last successful check.
5. Confirm disk, memory and bind state.
6. Do not restart until the cause, worker dependency effect and approval are
   understood. An ordinary API restart also affects the worker because of
   `PartOf=pactra-api.service`.
7. If an approved rollback trigger is met, follow
   `QA/DEPLOYMENT-AND-ROLLBACK.md` exactly.

### Worker unavailable

1. Preserve the worker PID/start/restart evidence and journal.
2. Query lease holders and unresolved payout backlog read-only.
3. Do not invoke an API payout path or manually create a provider request.
4. Preserve active reservations and attempt/provider identifiers.
5. Before any restart, determine whether a request could have reached PayPal.
6. After an approved restart, require exactly one lease holder and reconcile
   existing identifiers; never create a replacement attempt for ambiguity.

### Database unavailable

1. Confirm PostgreSQL service state, loopback bind, disk, memory, connections
   and readiness error.
2. Preserve database and application logs.
3. Stop additional financial processing only through an authorized incident
   action; do not edit transactions or journals.
4. Do not run Alembic, restore, drop, truncate, reset or `pg_restore --clean`
   as diagnosis.
5. Validate any backup into a new isolated database before a separately
   approved recovery cutover.

### Gemini unavailable, slow or returning malformed data

1. Confirm API and deterministic non-AI paths remain healthy.
2. Read `assistant.error` classification and fallback events.
3. Do not rotate keys, change projects, change models, enable billing or loop
   retries during an incident.
4. Treat AI output as untrusted. Policy, approval, transaction validation and
   ledger controls remain authoritative.
5. A model/configuration change is a normal release, not incident
   reconciliation. Follow `QA/GEMINI-OPERATIONS.md`.

### PayPal unavailable or provider timeout

1. Preserve the reservation and the current attempt state.
2. If a stable provider batch ID exists, reconcile that identifier only.
3. If submission outcome is unknown and no trustworthy provider ID exists,
   do not resubmit automatically. Escalate with all local request evidence.
4. Only confirmed item-level `SUCCESS` permits capture.
5. Confirmed terminal failure releases the reservation exactly once.
6. Returns, reversals and refunds use the implemented idempotent compensation
   path; never hand-write a compensating journal.

### Duplicate-processing suspicion

1. Preserve worker logs, transaction, attempt, stable request ID, batch/item
   IDs, approval action, reservation and journal counts.
2. Query for duplicate provider references and duplicate journal types.
3. If ongoing financial harm is possible, the incident commander may
   authorize stopping `pactra-worker.service`; record the exact time and state.
4. Do not delete a duplicate-looking row or submit a corrective payout.
5. Reconcile provider truth and ledger truth separately, then design an
   idempotent, reviewed remediation.

### Ledger mismatch or unexpected reservation

1. Stop further financial execution only through an authorized incident
   action.
2. Preserve all journals, entries, reservations, audit events and provider
   identifiers.
3. Verify each journal balances and identify whether a provider terminal state
   exists.
4. Never update balances directly or invent a compensation.
5. Escalate to release, security and financial operations owners.

### Authentication or tenant-isolation incident

1. Preserve access logs, affected request IDs, session metadata and timestamps
   without exporting raw cookies or credentials.
2. Confirm whether the issue is authentication, authorization, object
   ownership or frontend disclosure.
3. Contain only the affected Pactra path. Do not disable global controls.
4. Credential rotation, session invalidation or emergency release requires
   explicit owner approval and an incident record.
5. Re-run tenant and authorization regression suites before recovery is
   declared.

## Operational thresholds

No automated alerts are currently configured. These are manual investigation
triggers and proposed starting thresholds, not claims about installed
monitoring:

| Signal | Freeze baseline | Investigate | Escalate |
|---|---:|---:|---:|
| Disk use | 42% | >=80% or <20 GiB free | >=90% or database writes at risk |
| Available memory | 9.7/11 GiB | <20% for 10 minutes or sustained swap-in/out | <10%, OOM, or service eviction |
| CPU/load | 2 vCPU; 15-min load 0.72 | 15-min load >2 with rising latency | sustained saturation plus failed readiness |
| PostgreSQL connections | 8/100 for Pactra | >=70 total | >=85 or connection errors |
| Worker backlog | 0 | any item older than two 20-second cycles | any `unknown` outcome or growing queue |
| Gemini latency | accepted audit 1,391 ms; timeout 12 s | p95 >10 s or fallback >5% in 15 min | sustained provider failure affecting user flow |
| PayPal unknown/reservation | 0 | any unresolved item | any possible duplicate or reservation older than incident window |
| Ledger imbalance | 0 | any nonzero imbalance | immediate financial incident |

Calibrate these thresholds after real telemetry exists; changes belong in a
reviewed observability PR.

## Backup verification

For an existing custom archive, read-only verification is:

```bash
sudo -u pactra pg_restore --list \
  /opt/pactra/backups/<verified-backup>.dump >/dev/null
sudo sha256sum /opt/pactra/backups/<verified-backup>.dump
sudo stat -c 'path=%n size=%s mode=%a owner=%U:%G modified=%y' \
  /opt/pactra/backups/<verified-backup>.dump
```

Do not inspect or copy environment backup contents into reports. Do not test a
restore against production.

## Handover evidence to capture

Every incident or approved change report must include status as `PASS`,
`FAIL`, `BLOCKED`, or `NOT VERIFIED`, with commands, timestamps and sources.
Never equate an active systemd service, HTTP 200, batch acceptance or OAuth
success with complete product/provider success.
