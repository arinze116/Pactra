# Pactra Release Freeze Policy

Effective: 2026-11-09

Owner: Pactra release manager

Canonical baseline: `QA/ACCEPTED-PRODUCTION-BASELINE.md`

## Accepted baseline

- Accepted runtime implementation:
  `63f25839a6b645a8ca404846ecd82d16c1994b7c`.
- Accepted GitHub main evidence baseline:
  `06d9181eca8d383a79003ac4559ea9c0084b3831`.
- Accepted database revision: `20261107_0005`.
- Accepted production model: `gemini-3.5-flash-lite`.
- Accepted active release path: `/opt/pactra/releases/63f2583`.

Documentation-only descendants do not change the accepted runtime. Any code,
configuration, schema, provider, or infrastructure change creates a new
candidate that must complete the release process below.

## Production change rule

Production is not a development environment. No operator, agent, script, CI
job, or provider integration may directly modify production to test an idea or
demonstrate activity.

Future work must use:

1. a branch created from current `main`;
2. a focused pull request;
3. reviewable changes and explicit impact analysis;
4. all required CI checks on the candidate;
5. a separately identified release SHA and immutable artefact;
6. explicit deployment approval;
7. verified backup and rollback readiness;
8. post-deployment health and acceptance evidence.

No force-push, history rewrite, branch-protection bypass, unreviewed hot patch,
direct database edit, or in-place release modification is permitted.

## Changes requiring a full release process

The following must never be changed directly in production:

- payment processing or PayPal integration;
- ledger accounting, balances, reservations or journals;
- approval or rejection workflows;
- policy evaluation or enforcement;
- authentication, authorization, session or CSRF behavior;
- tenant isolation;
- database schema or migration history;
- Gemini function declarations, schemas or response parsing;
- AI tool execution or deterministic fallback;
- provider model, endpoint, timeout, retry or credentials;
- production secrets or environment files;
- worker concurrency, advisory lease or claim behavior;
- payout submission, reconciliation, recovery or compensation logic;
- Vercel production deployment, alias or security headers;
- systemd units, release symlink or service dependency behavior.

Every such change requires:

1. documented reason and desired outcome;
2. affected users, data, providers and failure modes;
3. security and financial-governance review;
4. automated unit and regression tests;
5. relevant PostgreSQL, concurrency, browser, accessibility or provider
   integration tests;
6. required GitHub CI success;
7. migration upgrade/downgrade and compatibility review where applicable;
8. exact deployment steps, health gates and rollback triggers;
9. immutable release and dependency integrity evidence;
10. explicit deployment approval from the release owner.

Provider billing, new credentials, live PayPal, real money, destructive data
repair, or credential rotation requires its own explicit approval even when a
release is otherwise approved.

## Documentation-only changes

Documentation may use the normal branch/PR/CI process without a production
deployment when all of these are true:

- the diff contains no runtime, workflow, package, deployment or environment
  change;
- it contains no secret, recipient data, session material or unredacted log;
- it does not relabel unverified evidence as PASS;
- required CI succeeds;
- the merge does not trigger a Vercel or backend deployment;
- the accepted runtime and database remain unchanged.

## Emergency definition

An emergency is a current condition with material risk to availability,
confidentiality, tenant isolation, financial correctness, or irreversible
provider action, for example:

- confirmed credential exposure;
- unauthorized access or cross-tenant data access;
- duplicate or potentially duplicate payout processing;
- ledger imbalance or unexplained reservation movement;
- unknown payout outcome with evidence of possible provider acceptance;
- active data corruption;
- API or worker behavior that can create additional financial harm;
- database failure threatening durability;
- critical externally exploitable vulnerability.

Ordinary defects, provider latency, a desired model change, cosmetic problems,
and missed product enhancements are not emergencies.

## Emergency response rules

1. Preserve timestamps, request IDs, transaction IDs, stable provider batch
   and item IDs, systemd state, database revision and relevant redacted logs.
2. Stop the harmful path only as narrowly as necessary. Do not disable
   authentication, policy enforcement, ledger constraints or audit controls.
3. For a financial incident, preserve reservations and stable identifiers.
   Never blindly retry, create a replacement batch or invent a ledger entry.
4. Reconcile an ambiguous PayPal outcome by the existing provider identifier.
   Only item-level `SUCCESS` permits capture.
5. Use an existing verified rollback target and the documented procedure.
   Never run an older application against an incompatible newer schema.
6. Restore a database only after separately approved destructive recovery and
   an isolated restore validation.
7. Record who authorized the action, exact commands, start/end times, evidence,
   result and remaining uncertainty.
8. Open a follow-up PR that brings the repository, documentation and deployed
   state back into traceable agreement.

## Rollback categories

- **Configuration rollback** changes only the verified setting and uses its
  private backup. The current Gemini rollback is
  `gemini-3.5-flash-lite` -> `gemini-3.8-flash` with API-only restart.
- **Application-only rollback** uses `/opt/pactra/releases/73fdfb6`. It shares
  schema `20261107_0005`; no database downgrade is required.
- **Database migration rollback** is required for legacy `0e3e905`: stop both
  services, use current migration code to downgrade to `0004`, verify the
  revision and rate-limit-table consequence, then switch the symlink.
- **Provider incident recovery** does not imply deployment or resubmission.
  Preserve local truth and reconcile through stable provider identifiers.

Exact commands and stop conditions are maintained in
`QA/DEPLOYMENT-AND-ROLLBACK.md`.

## Evidence and audit requirements

Every production change or emergency action must preserve:

- pre-change main and runtime SHA;
- pull request, review and CI run;
- immutable release path and checksum;
- production configuration backup metadata without secret values;
- database backup path, size, checksum and archive validation;
- pre/post migration revision;
- pre/post API and worker PID, start time and restart count;
- local and public health/readiness;
- worker lease and payout backlog state;
- redacted error evidence;
- rollback decision and result;
- provider status only when confirmed by the appropriate item-level record.

## Approval and separation of duties

- The release manager accepts the candidate and authorizes deployment.
- The platform/SRE operator executes and verifies the release.
- A security reviewer signs off changes to identity, tenant or secret
  boundaries.
- A financial operations approver authorizes each payout-specific action.
- No AI model may approve its own action, submit PayPal payouts, or mutate the
  ledger directly.

Where one person fills multiple roles, the evidence and approval boundaries
still apply. Financial transaction approval remains transaction-specific and
cannot be inferred from deployment authority.

## Freeze exit

The accepted baseline remains frozen until a future candidate has completed
the full release process and is explicitly declared the new accepted
production baseline. Merging development work alone does not end the freeze.
