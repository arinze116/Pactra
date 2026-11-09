# Pactra Gemini Operations and Fallback Policy

Accepted: 2026-11-09

Canonical baseline: `QA/ACCEPTED-PRODUCTION-BASELINE.md`

Detailed compatibility evidence: `QA/GEMINI-MODEL-COMPATIBILITY.md`

No Gemini request was sent while creating this operations document.

## Accepted runtime contract

| Setting | Accepted value |
|---|---|
| SDK | `google-genai==2.23.0` |
| API | Gemini Developer API v1beta |
| Model | `gemini-3.5-flash-lite` |
| Documented configuration rollback | `gemini-3.8-flash` |
| Function calling | `AUTO`; automatic SDK tool execution disabled |
| Request timeout | 12 seconds |
| Application attempts | At most two |
| SDK retries | Disabled; one SDK attempt per application attempt |
| Retry delay | Bounded application backoff only |
| Temperature | `0.0` |
| Output limit | 2,000 tokens |
| Maximum tool rounds | Eight |

Production startup validates the configured model against the approved model
set and rejects AI-enabled startup without a key. The key remains outside
source control in `/etc/pactra/pactra.env` and must never appear in logs,
screenshots, commits or incident reports.

## Compatibility record

These are results from the recorded bounded tests, not permanent claims about
the provider:

| Model | Recorded result | Status |
|---|---|---|
| `gemini-3.8-flash` | HTTP 503 at 6,312 ms, then timeout at 12,011 ms | FAIL in recorded test |
| `gemini-3.6-flash` | Two bounded 12-second timeouts | FAIL in recorded test |
| `gemini-3.1-flash-lite` | Two bounded 12-second timeouts | FAIL in recorded test |
| `gemini-3.5-flash` | Two bounded 12-second timeouts | FAIL in recorded test |
| `gemini-3.5-flash-lite` | 2/2 genuine function calls and two complete function-response round trips | PASS |

Other models were not tested after a stable candidate passed. They must not be
described as incompatible without new evidence.

## Genuine function-call acceptance

The accepted candidate returned real provider function-call parts, not JSON
text. Pactra verified the declared function name and strictly validated the
argument object against the application schema. Missing, malformed and extra
arguments were rejected locally.

The compatibility work corrected two concrete contract defects:

1. Function responses sent to the Developer API use role `user`, not the
   unsupported role `tool`.
2. `recipient` is declared as a payout-only email. Irrelevant recipient data
   is normalized away for non-payout transactions, while payout recipients
   still require an explicit email from the current user message.

The accepted production audit for conversation
`a74e9e11-e4bc-4996-a162-8b6d2d93affa` was independently read during the
freeze and records:

- model `gemini-3.5-flash-lite`;
- two provider calls and 1,391 ms cumulative provider latency;
- finish reason `STOP`;
- one genuine `get_wallet_summary` tool call with no arguments;
- no provider error or fallback event;
- zero financial transaction created for the isolated user.

The historical public request completed in 1.610 seconds. It was not repeated
during the freeze.

## Trust and execution boundary

These rules are permanent:

1. AI output is untrusted input.
2. Gemini cannot approve its own payment.
3. Gemini cannot bypass policy evaluation or approval thresholds.
4. Gemini cannot directly submit PayPal payouts.
5. Gemini cannot directly mutate wallet balances, reservations or journals.
6. Every tool name and argument object is deterministically validated.
7. Every financial action passes normal authentication, ownership, policy,
   transaction and ledger services.
8. Provider failure must not break deterministic payment governance.
9. No uncontrolled retry loop, hidden provider switch, key rotation or quota
   evasion is permitted.
10. Model changes require compatibility testing and a normal release.

## Function and response validation

For every provider response, Pactra must:

- require an actual function-call part for a tool invocation;
- reject unknown function names;
- require an object argument payload;
- reject missing required fields, unexpected fields and invalid formats;
- normalize only explicitly safe, non-financial fields;
- execute tools in application code, never in the SDK;
- persist safe tool-call audit metadata;
- validate the tool result before adding a function response;
- apply policy and approval rules after extraction;
- return authoritative application state rather than trusting model prose.

Ordinary JSON text that resembles a call is not a function call.

## Deterministic fallback

The fallback remains enabled in production and is part of the accepted
release. Recorded regressions cover:

- timeout;
- HTTP 503/provider unavailable;
- quota/rate-limit classification;
- empty response;
- malformed response;
- invalid function or argument shape;
- failure after a tool has already committed authoritative state.

Fallback must preserve policy, approval, transaction and ledger behavior. It
must not hide provider failure in audit records. If a tool completed before a
later provider failure, Pactra keeps that committed state and reports it
authoritatively rather than replaying the tool.

## Operational diagnosis

Use readiness only to confirm AI is configured, not that Gemini is currently
available:

```bash
curl --fail --silent --show-error --max-time 10 \
  http://127.0.0.1:8010/api/ready
```

Inspect classified failures without prompts or keys:

```bash
sudo journalctl -u pactra-api.service --since '-30 minutes' --no-pager -o cat \
  --grep 'Gemini request failed|Gemini client cleanup failed|deterministic fallback'
```

The durable audit fields safe for operational aggregation are:

- event type;
- model identifier;
- provider-call count;
- total latency;
- finish reason;
- error classification;
- HTTP/provider status;
- tool-call count and success boolean.

Do not export prompts, generated prose, tool arguments containing customer
data, API keys, session data or provider headers.

## Failure classification and response

| Classification | Operator response |
|---|---|
| Authentication/permission | Confirm key presence and project authorization without printing the key; do not rotate without approval |
| Model unavailable/inaccessible | Keep the accepted model and fallback; validate any candidate in isolation before release |
| HTTP 503/capacity | Accept bounded fallback; do not hammer the provider |
| Timeout | Confirm 12-second boundary and at most two attempts; investigate latency trend |
| Quota/rate limit | Preserve fallback; do not rotate keys or projects to evade quota |
| Schema/request incompatibility | Reproduce with the real declarations and SDK in isolation; fix through PR and CI |
| Empty/malformed response | Record protocol classification; reject it and use fallback |
| Response parsing defect | Treat as an application defect; add fixtures and regression tests |
| Post-tool provider failure | Preserve committed tool state; do not execute the tool again |

## Model-change acceptance process

Before changing production model configuration:

1. Discover models accessible to the existing account; do not assume a
   documented identifier is enabled.
2. Prefer stable, generally available, already-authorized models.
3. Use the installed SDK, exact system instruction, declarations, schemas,
   mode, timeout and retry settings.
4. Run at most two attempts per candidate, one candidate at a time.
5. Require a genuine function call, exact function, valid arguments and a
   complete function-response round trip.
6. Run the full isolated Pactra workflow, including invalid arguments,
   missing information, policy, approval, fallback, audit and receipt tests.
7. Prove no PayPal or real-money action can occur in the test.
8. Add regression coverage and pass all required CI.
9. Back up production configuration without printing it.
10. Change only the model setting, deploy the verified release, restart only
    the affected service through the approved systemd procedure, and perform
    one non-financial acceptance test.

If no candidate passes, retain the existing model and fallback. Provider
failure is not authorization to change billing, keys or projects.

## Rollback

The private backup
`/opt/pactra/backups/pactra-env-pre-gemini-63f2583-20261109T184028Z.env`
contains `GEMINI_MODEL=gemini-3.8-flash`. Its key set matches the current
environment and only `GEMINI_MODEL` differs.

A model-only rollback requires separate change approval, a targeted update of
that setting, and an API-only restart using the dependency-preserving command
in `QA/DEPLOYMENT-AND-ROLLBACK.md`. It requires no database downgrade.
Deterministic fallback remains enabled before and after rollback.

An application rollback uses `/opt/pactra/releases/73fdfb6`, also at schema
`20261107_0005`. Do not combine a Gemini rollback with PayPal, ledger, worker
or database changes.

## Monitoring requirements

The application already persists provider completion/error/fallback metadata,
but no external alerting or dashboard is configured. The required next steps,
including success rate, latency, fallback rate and error-class monitoring, are
prioritized in `QA/OBSERVABILITY-BACKLOG.md`.
