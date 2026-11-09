# ADR: Pre-Demo Diagnostics and Rehearsal Languages

Date: 2026-11-09

Status: accepted for branch review

## Decision

Retain Pactra's existing languages and runtime boundaries:

- Python for backend diagnostics, backup verification, demo data, and reset
  guards;
- TypeScript/Playwright for browser rehearsal and screenshot evidence;
- GitHub Actions YAML for the lightweight external health schedule;
- Markdown for operations and presentation handover.

## Rationale

These choices reuse installed dependencies, application models, migrations,
and CI. The financial checker can query the same SQLModel entities while
enforcing read-only transactions. The demo seed can call the real application
services instead of duplicating policy or ledger behavior. Playwright can
verify real user flows and responsive states. The health monitor uses only the
Python standard library, so the scheduled job needs no dependency install.

## Consequences

- No new service, package, database, or monitoring stack is introduced.
- Demo and diagnostics remain testable in the existing CI/runtime toolchain.
- The GitHub health workflow provides detection but no paging or metrics
  history; those remain explicit backlog items.
- Production activation still requires a normal reviewed release.
