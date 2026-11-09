# ADR 0001: Technology and PayPal execution authority

- Status: Accepted
- Date: 2026-11-09

## Context

Pactra needs a browser application, authenticated policy API, durable financial state, concurrent worker processing, provider integration, and a deployment that fits the existing Vercel/Oracle VPS architecture.

## Decision

- Use TypeScript/React/Vite for the browser interface.
- Use Python/FastAPI/Pydantic/SQLModel for the API and background worker.
- Use PostgreSQL for production locking, uniqueness, immutable-ledger triggers, shared rate limits, and advisory worker lease. Retain SQLite only for local/lightweight tests.
- Make the worker the sole PayPal payout submission authority.
- Persist an attempt before network I/O and derive stable PayPal request, batch, and item identifiers from the transaction and attempt number.
- Treat individual item `SUCCESS`, not batch acceptance, as the capture condition.
- Keep ambiguous outcomes reserved. Automatic scans do not replay an `unknown` attempt without a batch ID; explicit authenticated recovery reuses the same attempt and identifiers.

## Consequences

- API latency and retries cannot directly duplicate a provider payout.
- Provider submission and final settlement are asynchronous.
- Production requires a supervised worker and PostgreSQL; a web-only deployment must keep PayPal disabled.
- Ambiguous recovery may receive a duplicate-batch response and must validate the returned Sandbox self link before persisting it.
- Operational rollback from migration `0005` to release `0e3e905` requires stopped services and a candidate-code downgrade to `0004`.

## Alternatives rejected

- API-owned submission: couples user request retries to provider side effects.
- Batch-acceptance capture: can debit Pactra before the individual payout succeeds.
- New provider attempt after timeout: can create a duplicate payout.
- SQLite production: does not provide the required multi-process locking and trigger guarantees.
