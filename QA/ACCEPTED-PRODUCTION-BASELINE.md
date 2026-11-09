# Pactra Accepted Production Baseline

Status: **ACCEPTED / FROZEN**

Verification date: 2026-11-09, Africa/Lagos

Repository: `arinze116/Pactra`

This is the canonical reference for Pactra's accepted production release. It
records what was independently reverified during the release-freeze task,
what remains supported by retained acceptance evidence, and what was not
re-executed. Later documentation-only commits do not change this product
baseline unless a new release is formally accepted.

## Evidence labels

- **Independently reverified**: checked read-only against the live VPS,
  PostgreSQL, GitHub, Vercel, retained files, or persisted audit records on
  2026-11-09.
- **Retained accepted evidence**: a prior result supported by immutable
  artefacts, CI, logs, database state, or the cited evidence file. It was not
  re-executed during this freeze.
- **Not independently rechecked**: preserved as a historical assertion, with
  no new execution or external-provider call during this freeze.

## 1. Acceptance declaration

Pactra's accepted application implementation is commit
`63f25839a6b645a8ca404846ecd82d16c1994b7c`. Its accepted GitHub evidence
baseline is `06d9181eca8d383a79003ac4559ea9c0084b3831`. The latter is a
documentation-only descendant of the runtime implementation.

Production remained read-only throughout this verification. No deployment,
Vercel promotion, symlink change, migration, service restart, configuration
change, database mutation, Gemini request, PayPal request, reconciliation,
approval, or financial transaction occurred.

## 2. Authoritative identity

| Assertion | Accepted value | Verification | Source |
|---|---|---|---|
| GitHub repository/default branch | `arinze116/Pactra` / `main` | Independently reverified | GitHub repository API, 2026-11-09 |
| Runtime implementation SHA | `63f25839a6b645a8ca404846ecd82d16c1994b7c` | Independently reverified | Active release metadata and Git ancestry |
| Accepted GitHub main baseline | `06d9181eca8d383a79003ac4559ea9c0084b3831` | Independently reverified | Local `main`, `origin/main`, and GitHub API agreed before handover documentation |
| Runtime-to-main relationship | Runtime SHA is an ancestor, two commits behind; the delta changes nine documentation files only | Independently reverified | `git merge-base --is-ancestor`, `git diff` |
| Active release | `/opt/pactra/current` -> `/opt/pactra/releases/63f2583` | Independently reverified | VPS symlink and `.release-sha` |
| Database | PostgreSQL `16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)` | Independently reverified | Read-only SQL query |
| Migration | `20261107_0005` | Independently reverified | `alembic_version` and source migration head |
| Gemini | `gemini-3.5-flash-lite`, `google-genai==2.23.0` | Independently reverified | Whitelisted production settings and installed package metadata |
| Vercel production | `dpl_DjHTW75MnGQN11rcNZrY89NkrN9c`, `READY`, alias `pactra-nine.vercel.app` | Independently reverified | Vercel CLI 65.12.1 read-only inspection |
| PayPal acceptance transaction | `bfe1e158-863b-4ddf-93a0-e31146e7cbcb` | Independently reverified from Pactra data; provider was not contacted | Read-only PostgreSQL receipt/ledger queries |

## 3. GitHub, ancestry and CI

PRs [#13](https://github.com/arinze116/Pactra/pull/13),
[#14](https://github.com/arinze116/Pactra/pull/14), and
[#15](https://github.com/arinze116/Pactra/pull/15) are merged into `main`:

| PR | Merge commit | Purpose | Status |
|---:|---|---|---|
| #13 | `60c0843f48351aa1fc611d25dcca14c539f8e843` | PayPal Sandbox acceptance evidence | PASS |
| #14 | `63f25839a6b645a8ca404846ecd82d16c1994b7c` | Gemini compatibility implementation and selected model | PASS |
| #15 | `06d9181eca8d383a79003ac4559ea9c0084b3831` | Gemini production acceptance evidence | PASS |

The exact runtime run
[42674909231](https://github.com/arinze116/Pactra/actions/runs/42674909231)
and exact accepted-main run
[42678033819](https://github.com/arinze116/Pactra/actions/runs/42678033819)
both passed these four required jobs:

- Backend - SQLite;
- Backend - PostgreSQL;
- Frontend - lint, build and audits;
- E2E - journeys, WCAG and homepage Lighthouse.

All pre-existing remote and local feature branches inspected before creating
this handover branch were ancestors of `main`; none was ahead of it. GitHub had
no open pull request at initial verification and no pending or failing
required check. Repository rules prohibit deletion and non-fast-forward
updates to `main` and require the four checks above.

## 4. Backend release integrity

| Check | Result | Status |
|---|---|---|
| Embedded SHA | `.release-sha` contains the full runtime SHA | PASS |
| Source archive | `/opt/pactra/releases/63f2583/.release-metadata/pactra-63f2583.tar` | PASS |
| Archive SHA-256 | `6ba14264e0ee63ca49ae26af5ec15427ca3ae9ed25ab705498ee7c543bac5369` | PASS |
| Commit tree | 142 entries match the recorded Git tree | PASS |
| Tracked contents | 142 Git-filtered object hashes, zero mismatches | PASS |
| Archive extraction | 142 archive files match the deployed source byte-for-byte | PASS |
| Frontend build | 16 files match `.release-metadata/frontend-build.sha256` | PASS |
| Python | 3.12.3; resolved manifest matches installed packages; `pip check` passed | PASS |
| Required imports | FastAPI, Gemini SDK, Psycopg, SQLAlchemy, SQLModel, Uvicorn, API and worker import successfully | PASS |
| Ownership/mode | Release root `root:pactra` `0550`; source/metadata files `0440` | PASS |
| Capacity at verification | Root filesystem 42% used, 84 GiB available; 9.7 GiB memory available | PASS |

The public Vercel assets referenced by the live HTML have the same SHA-256
values as the accepted `frontend/dist` assets.

## 5. Process lineage and service state

This distinction is material:

- `pactra-api.service` is running from cwd
  `/opt/pactra/releases/63f2583`, PID `819381`, started
  `2026-11-09 19:42:06 WAT`, with zero systemd restarts.
- `pactra-worker.service` intentionally retained PID `785136` during the
  Gemini-only rollout. Its process cwd remains
  `/opt/pactra/releases/73fdfb6`, started `2026-11-09 18:00:43 WAT`, with
  zero systemd restarts.
- `backend/worker.py`, the PayPal adapter and service, transaction and ledger
  services, database module, and models are byte-identical between `73fdfb6`
  and `63f2583`. The worker holds the expected PostgreSQL advisory lease and
  its payout backlog query returned zero rows.

Accordingly, the active release and API implementation are `63f2583`; the
long-running worker has prior-release process lineage but identical accepted
payment code. The next separately approved worker restart will load the
active release. No restart was performed merely to normalize this lineage.

Both services were `active/running`. There were zero warning-or-higher journal
entries since their current start times. Loopback, Tailscale, and Vercel
`/api/health` and `/api/ready` checks returned successful JSON, including
database readiness, AI configured, and PayPal Sandbox configured.

## 6. Database baseline

Read-only SQL independently verified:

- database `pactra` on PostgreSQL 16.15;
- migration and source head `20261107_0005`;
- all 16 expected public tables;
- `rate_limit_buckets` and `ix_rate_limit_buckets_expires`;
- expected transaction, provider, ledger, audit, session, policy, wallet, and
  conversation indexes;
- one granted worker advisory lease;
- 8 Pactra-database connections out of `max_connections=100` at the sample;
- no eligible PayPal worker backlog.

No table, row, sequence, schema, or migration was changed.

## 7. Vercel baseline

Read-only inspection resolved `pactra-nine.vercel.app` to deployment
`dpl_DjHTW75MnGQN11rcNZrY89NkrN9c`, URL
`pactra-plm3eotnf-0xmaxizs-projects.vercel.app`, target `production`, state
`READY`. Deployment metadata associates it with commit
`73fdfb692f6daea69ba5f44bc37d9afa1814419a`; subsequent commits did not alter
the frontend runtime. Live asset hashes match the accepted build.

The Vercel project is not connected to a Git repository in its project API
record. Publishing this documentation branch therefore does not trigger a
Vercel build. No deployment, alias, project setting, or promotion was changed.

## 8. Gemini acceptance baseline

### Reverified configuration

| Setting | Value |
|---|---|
| SDK | `google-genai==2.23.0` |
| API | Gemini Developer API v1beta |
| Model | `gemini-3.5-flash-lite` |
| Function calling | `AUTO`; SDK automatic tool execution disabled |
| Request timeout | 12 seconds |
| Application attempts | At most two |
| SDK retries | Disabled; one SDK attempt per application attempt |
| Generation | Temperature `0.0`, maximum 2,000 output tokens |
| Maximum tool rounds | Eight |

The API key is present, but was never printed or used during this freeze.

### Retained compatibility evidence

`QA/GEMINI-MODEL-COMPATIBILITY.md` records:

- `gemini-3.8-flash`: HTTP 503, then timeout;
- `gemini-3.6-flash`: two bounded timeouts;
- `gemini-3.1-flash-lite`: two bounded timeouts;
- `gemini-3.5-flash`: two bounded timeouts;
- `gemini-3.5-flash-lite`: two genuine function calls and two complete
  function-response round trips.

Other models were not tested after a stable candidate passed and are not
labelled incompatible.

### Production acceptance evidence

The retained live request was not repeated. Its persisted audit record was
independently re-read and contains:

- model `gemini-3.5-flash-lite`;
- two provider calls;
- 1,391 ms cumulative provider latency;
- finish reason `STOP`;
- one successful `get_wallet_summary` tool call with no arguments;
- no `assistant.error` or `assistant.fallback_used` event;
- zero transactions for the isolated acceptance user.

The historical public round trip completed in 1.610 seconds. Deterministic
fallback tests for timeout, HTTP 503, malformed/empty responses, strict
argument rejection and post-tool failure are retained CI evidence and were
not re-executed against Gemini during the freeze.

## 9. PayPal Sandbox and ledger acceptance baseline

No PayPal API was called. The accepted transaction's current Pactra state was
independently reverified read-only:

| Invariant | Current evidence | Status |
|---|---|---|
| Amount/environment | 2,500 cents USD; `paypal_sandbox_payouts` | PASS |
| Approval | One `approved` action | PASS |
| Attempt | One completed attempt and one stable request ID | PASS |
| Provider evidence | One batch reference, one item reference, item status `SUCCESS`, response `PAYPAL_ITEM_SUCCESS` | PASS |
| Reservation | One 2,500-cent reservation, state `captured` | PASS |
| Ledger | One posted `payment_capture`; 2,500-cent wallet debit and equal clearing credit | PASS |
| Balance | Posted 97,500; reserved 0; available 97,500 cents | PASS |
| Audit/receipt | Nine lifecycle events; receipt identical across two reads | PASS |
| Duplicate checks | One transaction/attempt for the batch and one attempt for the item; no reversal journal | PASS |

The separately authorised provider execution, one payout POST, batch success,
and item-level success remain **retained accepted evidence** in
`QA/PAYPAL-SANDBOX-EXECUTION-RUNBOOK.md` and
`QA/ACCEPTANCE-EVIDENCE.md`. They were not repeated or reconciled during this
freeze.

## 10. Security, governance, accessibility and E2E

The exact runtime and accepted-main CI runs support the accepted automated
security, authentication, authorization, tenant isolation, CSRF, rate-limit,
policy, audit, receipt, browser, Axe/WCAG, responsive, and Lighthouse results.
These suites were not re-run locally merely for the freeze.

Independently reverified controls include:

- API and PostgreSQL listen on loopback only;
- production uses secure cookies, PostgreSQL, PayPal Sandbox, mock mode off,
  and no demo-account seeding;
- worker advisory lease is held and backlog is empty;
- GitHub secret scanning and push protection are enabled, with zero open
  secret alerts;
- a local scan of all 142 tracked files found no common provider token or
  private-key pattern;
- no tracked `.env` or credential file exists; only `.env.example` is tracked;
- public headers include CSP, HSTS, frame denial, MIME sniffing protection,
  strict referrer policy, and a restricted permissions policy.

The permanent governance rules are defined in
`QA/RELEASE-FREEZE-POLICY.md`, `QA/GEMINI-OPERATIONS.md`, and
`QA/PAYMENT-OPERATIONS-AND-RECONCILIATION.md`.

## 11. Release and rollback artefacts

### Important releases

| Path | Embedded SHA/head | Purpose | Freeze verification |
|---|---|---|---|
| `/opt/pactra/releases/63f2583` | `63f25839...`, schema head `0005` | Accepted active release | Full archive/tree/dependency/build verification passed |
| `/opt/pactra/releases/73fdfb6` | `73fdfb692...`, schema head `0005` | Immediate application rollback | 139 tracked files matched; archive SHA-256 `6c16fbcd6b11187182f8ae1d9ea2374f12aa23ca39f629a35f112cabde1792c4`; `pip check` passed |
| `/opt/pactra/releases/0e3e905` | Directory name only; source head `0004` | Legacy rollback | Present; requires stopped-service downgrade to `0004` |
| `/opt/pactra/releases/4534d13` | `4534d136...` | Prior accepted candidate and restore-drill source | Present; not re-executed |
| `/opt/pactra/releases/2f97cf0` | `2f97cf07...` | PayPal recipient-correction candidate | Present; not re-executed |
| `/opt/pactra/releases/9b4bc77` | `9b4bc77c...` | Accessibility candidate | Present; not re-executed |
| `/opt/pactra/releases/4ac8689` | `4ac86897...` | Older candidate | Present; not accepted for current runtime |

Other retained legacy release directories are `1067e61`, `45d6c61`,
`490febf`, `7570cbb`, `9065c1b`, `936c6de`, `aedb688`, `c28d960`, and
`d04c677`. They were not deleted, remapped, or revalidated as rollback targets.

### Backup inventory

All paths are under `/opt/pactra/backups`. Every `.dump` passed
`pg_restore --list`. Environment backups were hashed and left unread in
reports; restoration was not attempted. The backup directory is
`pactra:pactra` mode `0700`; database archives are `pactra:pactra` mode
`0600`. The accepted pre-Gemini environment backup is `root:root` mode `0600`;
the two older environment backups are `pactra:pactra` mode `0600`.

| File | Created WAT | Bytes | SHA-256 | Associated release/purpose | Verification |
|---|---:|---:|---|---|---|
| `pactra-20261107T062700Z.dump` | 2026-11-07 07:29:42 | 83,045 | `d5f7f32ab03ee9e4233a3edb8eec44b639e2c112f1401b9fb6353afe839bf878` | Early retained backup; SHA not encoded | PASS, 102 archive entries |
| `pactra-pre-aedb688-20261107T070912Z.dump` | 2026-11-07 08:09:12 | 83,743 | `bbee5708c2ff4e5aa871416fe010ccc96405c115411dcf6bd429466f91191be9` | `aedb688` | PASS, 102 entries |
| `pactra-pre-45d6c61-20261107T072107Z.dump` | 2026-11-07 08:22:15 | 105,016 | `a5dc2833d5101696180994bc38f20b74b56504ab586a37546bb79d8d102eaca9` | `45d6c61` | PASS, 106 entries |
| `pactra-pre-0e3e905-20261107T093541Z.dump` | 2026-11-07 10:35:41 | 130,124 | `823e0f456218f23dcff8619ff87e3bc33c32b97ef6edff78db580748d84f12e6` | `0e3e905` | PASS, 106 entries |
| `pactra-pre-2f97cf07e27d572d9f7ad3efdd49d2c485bae347-20261109T135834Z.dump` | 2026-11-09 14:58:34 | 144,379 | `ab45acf669fcafd817df765e4abe2bafc6c59b300bac2b1b77cab1e2f4235a5d` | `2f97cf07...` | PASS, 108 entries |
| `pactra.env-pre-2f97cf07e27d572d9f7ad3efdd49d2c485bae347-20261109T135834Z` | 2026-11-09 14:58:34 | 1,132 | `41786f0daecc906dac785bb45d8ef38c25775151e358fcf488f8f188724cf86a` | Pre-`2f97cf07` configuration | PASS, hash/readability only |
| `pactra-pre-9b4bc77cf65b5ac85be616f6c6afc4a7481de22b-20261109T142947Z.dump` | 2026-11-09 15:29:47 | 153,525 | `3bf750fec8df51d5710b3d40105ebb224c8acb5688f2b698653ca076e4bf6411` | `9b4bc77c...` | PASS, 112 entries |
| `pactra-acceptance-9b4bc77-20261109T152731Z.dump` | 2026-11-09 16:27:31 | 162,736 | `c3812771a3f0c9f669511cc69aca5dac40d683b011f2f02ea9e9545032c67fe3` | `9b4bc77` acceptance | PASS, 112 entries |
| `pactra.env-pre-gemini-key-fix-20261109T160057Z` | 2026-11-09 06:24:17 | 1,132 | `41786f0daecc906dac785bb45d8ef38c25775151e358fcf488f8f188724cf86a` | Gemini key-fix backup; release SHA not encoded | PASS, hash/readability only |
| `pactra-pre-4534d136766a094aeeac4489a9e694111b9257ae-20261109T163956Z.dump` | 2026-11-09 17:39:57 | 170,547 | `e7c1ce7bac3891586d19c0165be42eda0dde21c3da93b2e1fa4178c1c50b7f1e` | `4534d136...` | PASS, 112 entries |
| `pactra-pre-73fdfb692f6daea69ba5f44bc37d9afa1814419a-20261109T170019Z.dump` | 2026-11-09 18:00:19 | 170,927 | `828a3b966c6dea957125fe9860f3793be9a777b781349edbb7ad8260b75264c0` | `73fdfb69...` | PASS, 112 entries |
| `pactra-env-pre-gemini-63f2583-20261109T184028Z.env` | 2026-11-09 19:40:28 | 1,130 | `58a07a9d7d66988466bdb09fffae52f65af0437162d344673489179e14d33778` | Pre-`63f2583` Gemini configuration | PASS, hash/readability; differs from current only at `GEMINI_MODEL` |
| `pactra-pre-63f25839a6b645a8ca404846ecd82d16c1994b7c-20261109T184028Z.dump` | 2026-11-09 19:40:28 | 173,373 | `9f4a9407fc2aa292480e4608f84449be5dbb83e315b193f7c8e7aa68dfe213ac` | Accepted runtime `63f25839...` | PASS, 112 entries |

### Migration drill artefacts

- `pactra_restore_4534d13_20261109163956`: revision `0005`, 16 public
  tables, `rate_limit_buckets` present; this is the retained accepted drill.
- `pactra_restore_audit_20261107_qa`: revision `0003`, retained older audit
  clone.
- `pactra_restore_check_20261107`: revision `0002`, retained older check
  clone.

The accepted drill evidence records `0005 -> 0004 -> 0005`, unchanged
financial/entity counts, deletion of rate-limit bucket data on downgrade, and
legacy `0e3e905` readiness at `0004`. The drill was not repeated in production.

### CI, reports and visual evidence

Primary retained reports:

- `QA/RELEASE-MANIFEST.md`;
- `QA/RELEASE-READINESS.md`;
- `QA/ACCEPTANCE-EVIDENCE.md`;
- `QA/GEMINI-MODEL-COMPATIBILITY.md`;
- `QA/PAYPAL-SANDBOX-EXECUTION-RUNBOOK.md`;
- `QA/DEPLOYMENT-AND-ROLLBACK.md`;
- `QA/SECURITY-REVIEW.md`.

Visual/Lighthouse evidence is retained in `artifacts/release-20261109` and
`artifacts/independent-audit-20261107`, including desktop, tablet, mobile,
payment, receipt, policy, approval, PayPal-mask, and production Lighthouse
artefacts. Important exact paths are:

- `artifacts/release-20261109/dashboard-desktop.png`;
- `artifacts/release-20261109/payment-tablet.png`;
- `artifacts/release-20261109/paypal-mobile.png`;
- `artifacts/release-20261109/lighthouse-production-home.json`;
- `artifacts/release-20261109/lighthouse-production-sign-in.json`;
- `artifacts/release-20261109/lighthouse-production-sign-up.json`;
- `artifacts/independent-audit-20261107/landing-desktop.png`;
- `artifacts/independent-audit-20261107/landing-mobile.png`;
- `artifacts/independent-audit-20261107/dashboard-desktop.png`;
- `artifacts/independent-audit-20261107/policy-editor-desktop.png`;
- `artifacts/independent-audit-20261107/payment-request-desktop.png`;
- `artifacts/independent-audit-20261107/approval-view-desktop.png`;
- `artifacts/independent-audit-20261107/receipt-desktop.png`.

Large release-build working directories and all existing Git stashes were
preserved rather than cleaned.

## 12. Rollback baseline

The verified immediate application rollback target is
`/opt/pactra/releases/73fdfb6`. Its migration tree is identical to the active
release at `20261107_0005`, so no database downgrade is required.

The configuration backup above contains the previous model
`gemini-3.8-flash`; current and backup configuration keys are identical and
only `GEMINI_MODEL` differs. A model-only rollback therefore changes that one
non-secret setting and restarts only the API through the documented
dependency-preserving command, after separate change approval.

Rollback to `/opt/pactra/releases/0e3e905` is a database migration rollback:
both services must be stopped, active-release migration code must downgrade
`0005` to `0004`, `rate_limit_buckets` is lost, and only then may the symlink
move. The exact procedure and stop conditions remain in
`QA/DEPLOYMENT-AND-ROLLBACK.md`.

No rollback was executed during this freeze.

## 13. Known limitations

- The worker's current process lineage is `73fdfb6`, although its payment and
  persistence modules are byte-identical to `63f2583`.
- No external uptime, resource, provider, backlog, ledger-consistency, or
  backup-integrity alerting service is configured. Current capabilities are
  classified in `QA/OBSERVABILITY-BACKLOG.md`.
- Authentication failures and provider failures are available in systemd
  journals and durable application audit records, but there is no centralized
  error aggregation or alert routing.
- The PayPal client-credentials API did not expose the Sandbox sender email in
  the accepted run. Item-level recipient, amount, provider IDs and success
  were verified; the sender-email metadata limitation remains documented.
- Historical provider calls, full E2E, accessibility, Lighthouse, migration
  downgrade, and rollback results were not re-executed during the freeze.

## 14. Operational ownership and escalation

Operational roles, rather than personal contact details, are authoritative:

1. **Release manager** owns baseline identity, PR/CI gates and deployment
   authorization.
2. **SRE/platform operator** owns service, database, capacity, backup and
   rollback diagnosis.
3. **Security reviewer** owns credential exposure, authentication,
   authorization and tenant-isolation incidents.
4. **Financial operations approver** owns transaction-specific payout
   authorization; engineering must never infer it.
5. **Repository/VPS owner** is the final escalation point for destructive or
   irreversible recovery.

No named on-call rota, paging endpoint, RTO or RPO was found. Those remain
operational follow-ups, not fabricated commitments. Procedures are in
`QA/PRODUCTION-OPERATIONS-RUNBOOK.md`.

## 15. Final freeze matrix

| Requirement | Status |
|---|---|
| Runtime SHA, active release and ancestry | PASS |
| Exact accepted-main SHA and CI | PASS |
| Release archive, files, dependencies and frontend assets | PASS |
| PostgreSQL version, schema and migration | PASS |
| API and worker service health/lease | PASS |
| Vercel deployment and alias | PASS |
| Gemini configuration and retained genuine-call audit | PASS |
| PayPal/ledger accepted state and no duplicates | PASS |
| Backup and rollback artefact inventory | PASS |
| Historical E2E/accessibility/provider calls re-executed during freeze | NOT VERIFIED - intentionally not repeated |
| Production mutations during freeze | PASS - none occurred |
