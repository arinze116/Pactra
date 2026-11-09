# Pactra Alerting and Incident Runbook

Date: 2026-11-09

## Current alerting state

The branch contains a five-minute public health GitHub workflow. It is not
scheduled until merged to `main`. GitHub run failure is the only implemented
signal; no pager, email distribution, chat webhook, or staffed on-call rota is
configured.

Do not claim a monitored signal is active until its workflow or external
monitor has been merged, enabled, observed, and routed to an owner.

## Public-health response

Inspect the latest run:

```bash
gh run list --repo arinze116/Pactra \
  --workflow production-health.yml --limit 10
gh run view <run-id> --repo arinze116/Pactra --log-failed
```

Classifications are `ok`, `http_error`, `timeout`, `network_error`,
`invalid_payload`, or `latency_budget_exceeded`.

1. Confirm a second bounded read-only check from an independent path.
2. Separate frontend (`/`) from API liveness (`/api/health`) and database
   readiness (`/api/ready`).
3. Inspect only Pactra service and Vercel state.
4. Preserve timestamps, request IDs, release SHA, migration revision, and
   relevant sanitized logs.
5. Do not restart, deploy, migrate, change DNS, or edit configuration without
   explicit incident authority.

## Incident matrix

| Signal | First checks | Safety rule |
|---|---|---|
| Frontend unavailable | Vercel deployment/alias, public status, build logs | Do not trigger a deployment while diagnosing |
| API unavailable | systemd state/restarts, local health, reverse-proxy path, recent API errors | Do not restart until payout ambiguity is excluded |
| Readiness failure | PostgreSQL service, connectivity, disk, connections, locks | Never run a migration or restore as diagnosis |
| Worker unavailable | service state, PID/start time, lease holder, backlog | Preserve attempts/reservations; never submit manually |
| Gemini failure | structured classification, fallback result, latency | Do not rotate keys/models or evade quota |
| PayPal timeout/unknown | stable request/batch/item IDs, reservation, attempt state | Reconcile existing IDs; never blindly resubmit |
| Ledger invariant failure | invariant code/count, journals, reservations, attempts | Stop authorized execution; never auto-correct balances |
| Backup verification failure | path, size, age, checksum, archive-list result | Do not replace or delete the retained archive |
| Authentication/tenant incident | request IDs, session metadata, ownership path | Preserve evidence; do not disable auth controls |

## Financial incident procedure

1. Preserve the transaction, approval, attempt, reservation, journal, audit,
   and stable provider identifiers.
2. If ongoing submission risk exists, obtain authority to stop only
   `pactra-worker.service`.
3. Keep ambiguous outcomes reserved.
4. Reconcile using the existing provider identifier when one exists.
5. Require PayPal item-level `SUCCESS` before capture.
6. Release only after confirmed terminal failure.
7. Never invent a compensating journal or replacement payout.
8. Verify exactly-once capture/compensation and balanced entries before
   recovery is declared.

## Initial manual investigation thresholds

These are starting triggers, not active alerts or SLOs:

- disk: investigate at 80% or under 20 GiB free; critical at 90%;
- memory: investigate below 20% available for 10 minutes; critical below 10%
  or on OOM/service eviction;
- PostgreSQL: investigate at 70/100 connections; critical at 85/100;
- worker: investigate any item older than two 20-second cycles; critical for
  any unknown outcome or growing backlog;
- Gemini: investigate p95 over 10 seconds or fallback/error over 5% with a
  meaningful sample;
- ledger: any nonzero P0 invariant is an immediate financial incident;
- backup: missing checksum, failed archive list, unexpected size, or age beyond
  the approved recovery policy requires investigation.

Measured 2026-11-09 sample: disk 42% used with 84 GiB free, 8.9 GiB memory
available, PostgreSQL 8/100 connections, one worker lease, and zero backlog.

## Recovery evidence

Record start/end times, incident owner, affected release, user-visible impact,
request IDs, sanitized error classes, database revision, worker lease/backlog,
provider ambiguity, invariant results, corrective action, verification, and
follow-up PR. Never include secrets, recipient addresses, session IDs, raw
provider bodies, or sensitive request content.
