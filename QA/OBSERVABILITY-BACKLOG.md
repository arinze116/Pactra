# Pactra Observability Backlog

Assessment date: 2026-11-09

Scope: accepted baseline plus repository-contained pre-demo implementation; no
monitoring vendor was installed or connected

## Current state

| Capability | State | Existing evidence | Gap |
|---|---|---|---|
| API liveness/readiness | Repository-ready | `/api/health`, `/api/ready`; bounded public monitor; five-minute GitHub workflow | Workflow inactive until merge; no paging or SLO |
| API latency | Partially implemented | Structured request duration with bounded route templates | No aggregation, p95/p99, dashboard or alert |
| Worker liveness | Partially implemented | systemd state/restarts and structured worker events | No independent heartbeat or stale-worker alert |
| Worker lease | Partially implemented | PostgreSQL advisory lock and structured acquisition/standby events | No continuous lease monitor |
| Payout backlog | Partially implemented | Queryable transaction/attempt state | No age/count dashboard or alert |
| Database health | Partially implemented | readiness `SELECT 1`, PostgreSQL statistics | No external availability, connection or storage alert |
| Gemini success/latency | Partially implemented | Durable audit fields plus structured fallback classification/latency | No aggregation, success-rate or latency alert |
| PayPal reconciliation | Partially implemented | Stable IDs, attempt states, audit events and worker logs | No unknown-outcome/unreconciled-reservation alert |
| Ledger consistency | Partially implemented | Constraints plus tested read-only 10-check diagnostic | No scheduled invariant scan or alert |
| Disk/memory/CPU | Missing alerting | OS commands and systemd process data | No threshold alert or trend retention |
| Error aggregation | Missing | systemd journal and Vercel logs | No centralized grouping, retention policy or paging |
| Backup integrity | Partially implemented | Tested checksum/age/size/archive verifier and retained restore clones | No scheduled verification/freshness alert |
| Frontend availability | Repository-ready | Public HTML check in five-minute GitHub workflow | Workflow inactive until merge; no notification target |
| Security events | Partially implemented | GitHub secret scanning, audit events, access logs | No auth anomaly or tenant-boundary alerting |

The frontend dependency tree contains transitive Sentry/OpenTelemetry packages
through tooling, but no Pactra source imports or configured error aggregation
were found. This is not an implemented monitoring system.

## Measured freeze baseline

| Signal | 2026-11-09 sample |
|---|---:|
| Root filesystem | 42% used, 84 GiB available |
| Memory | 11 GiB total, 9.7 GiB available |
| Swap | 8 GiB total, about 1 GiB used |
| CPU | 2 vCPU; load averages 0.06 / 0.40 / 0.72 |
| PostgreSQL | 100 max connections; 13 total, 8 for `pactra`, 1 active at query time |
| API process | About 103 MiB RSS at sample |
| Worker process | About 70 MiB RSS at sample |
| Worker backlog | 0 |
| Worker lease | 1 granted holder |
| Accepted Gemini audit | 2 calls, 1,391 ms cumulative, no fallback/error |
| PayPal unknown outcomes | 0 in eligible/unresolved backlog query |
| Ledger imbalance | 0 in accepted transaction evidence |

These are point-in-time measurements, not an SLO or capacity guarantee.

## Pre-demo branch implementation

Implemented and tested in `release/final-pre-demo-readiness`:

- privacy-safe structured API/Gemini/worker events;
- frontend/server correlation IDs and bounded request timeouts;
- public frontend, liveness and readiness monitor;
- five-minute GitHub Actions schedule;
- read-only financial invariant checker;
- backup checksum, size, age and archive-list verifier;
- alert and incident runbook.

These changes are not deployed. The scheduled workflow is not active until a
reviewed merge to the default branch, and it still has no pager. Production
activation of API/worker logging requires a separately approved release.

## P0 - financial and availability safety

### OBS-001 External production availability

The branch implements an independent GitHub-hosted HTTPS monitor for:

- `https://pactra-nine.vercel.app/`;
- `/api/health`;
- `/api/ready`.

Completed:

- five-minute checks from GitHub-hosted runners;
- separate frontend, liveness and database-readiness classification;
- bounded timeout/latency and body-safe output;
- no authentication or persistent test data.

Remaining acceptance:

- decide whether one-minute frequency is justified beyond the current
  five-minute free repository schedule;
- add a confirmation window if paging is connected;
- escalation route and ownership are documented.

### OBS-002 Worker liveness, lease and backlog

Export or safely poll:

- systemd worker active state and restart count;
- current PID/start time;
- advisory lease-holder count;
- eligible attempts by state and oldest age;
- worker scan error count.

Proposed initial triggers, not currently configured:

- lease holders not equal to one for two scan intervals;
- any eligible item older than 40 seconds;
- any `unknown` attempt;
- increasing backlog across three samples;
- any unexpected worker restart while a payout is unresolved.

### OBS-003 Database availability and pressure

Monitor:

- connectivity and migration revision;
- connection use/max;
- database/filesystem size and free space;
- lock waits and long-running transactions;
- PostgreSQL service restarts and errors.

Proposed initial triggers:

- readiness failure twice consecutively;
- connections >=70/100 warning and >=85/100 critical;
- disk >=80% warning, >=90% critical;
- migration revision differs from the accepted release head;
- sustained blocking transaction or connection errors.

### OBS-004 PayPal unknown outcomes and reservations

Create privacy-safe metrics for:

- attempts by `submitting`, `claimed`, `processing`, `unknown`, `completed`,
  terminal failure and reversal state;
- oldest unresolved attempt/reservation age;
- reconciliation success/failure;
- duplicate stable/provider identifier constraint failures;
- item-level success-to-capture lag.

Any `unknown` outcome, possible duplicate provider operation, capture without
item `SUCCESS`, or unresolved reservation beyond the incident window is a P0
page. Labels must not include recipient, email, full transaction ID, provider
payload or credential material.

### OBS-005 Ledger consistency

The read-only checker now covers:

- debit total equals credit total per journal;
- one active/captured/released reservation state per transaction as allowed;
- completed PayPal item success has exactly one capture;
- terminal failure has no capture and no active reservation;
- compensation is at most once;
- derived wallet balance is internally consistent.

Any nonzero inconsistency is a financial incident. The checker never repairs
data automatically. Scheduling and notification remain outstanding.

## P1 - provider and recovery visibility

### OBS-006 Gemini reliability

Aggregate the already durable safe fields:

- model;
- provider-call count;
- success/error/fallback classification;
- latency and finish reason;
- tool-call count and safe function name.

Proposed starting triggers:

- fallback/error rate >5% over 15 minutes with sufficient sample size;
- p95 provider latency >10 seconds;
- repeated authentication, permission, quota or model-unavailable errors;
- any unbounded-attempt or unexpected-model signal.

Do not export prompts, arguments, generated content, user IDs or keys. Model
changes remain a release decision, never an automatic failover.

### OBS-007 Backup freshness and integrity

For each release backup, record:

- path, associated release, created time, size and SHA-256;
- `pg_restore --list` result;
- last isolated restore test and resulting revision;
- age of the last verified backup.

Alert before deployment if no verified pre-change backup exists. Add a
scheduled non-production archive validation. Do not automatically restore or
delete backups.

### OBS-008 Centralized error aggregation

Select and approve a service before integration. Requirements:

- server-side redaction of authorization headers, cookies, keys, recipient
  data, prompts and request bodies;
- separate API/worker release tags and environment;
- grouping for database, Gemini, PayPal and policy failures;
- retention, access control and incident ownership;
- no frontend exposure of backend secrets;
- test evidence that redaction works.

No external service should be connected during a freeze or without security
review.

## P2 - performance and operational maturity

### OBS-009 API and route latency

Add request count, status and duration histograms with bounded route labels.
Avoid raw URLs containing IDs. Establish p50/p95/p99 only after a representative
baseline exists.

### OBS-010 Frontend real-user and synthetic monitoring

Add privacy-reviewed Web Vitals and a small synthetic flow for public page,
sign-in page and an authenticated non-financial route. Do not create payments,
provider calls or persistent test accounts in uptime checks.

### OBS-011 Capacity trends

Retain disk, memory, swap, CPU, process RSS, PostgreSQL connections and
database-size history. Revisit thresholds after at least seven days of data.

### OBS-012 On-call and incident governance

Define:

- named primary/secondary operators;
- secure paging destination;
- acknowledgement and escalation times;
- evidence retention;
- post-incident review owner;
- measured RTO/RPO only after recovery exercises.

No RTO, RPO or 24/7 on-call promise is currently configured and none is
claimed.

## Implementation order

1. External availability and database readiness.
2. Worker lease/backlog and PayPal unknown outcomes.
3. Ledger consistency.
4. Gemini success/failure/latency.
5. Backup freshness/integrity.
6. Host resource exhaustion.
7. Centralized error aggregation.
8. API/frontend performance and on-call maturity.

Every observability change must use a branch, PR, security review and CI. Alert
payloads must use bounded labels and never expose recipient information,
secrets, prompts, cookies, authorization headers or provider response bodies.
