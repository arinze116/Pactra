# Gemini Model Compatibility and Failover

Updated: 2026-11-09, Africa/Lagos

This runbook records bounded live-provider evidence without exposing the API
key. It does not authorize Gemini to execute a payment. Pactra remains the only
tool executor, and its policy, approval, validation and ledger services remain
authoritative.

## Runtime contract

| Item | Verified value |
|---|---|
| SDK | `google-genai==2.23.0` |
| API | Gemini Developer API, `https://generativelanguage.googleapis.com/v1beta` |
| Selected model | `gemini-3.5-flash-lite` |
| Documented rollback model | `gemini-3.8-flash` |
| Request timeout | 12 seconds |
| Application attempts | At most 2 |
| SDK retries | Disabled; one SDK attempt per application attempt |
| Function mode | Default `AUTO`; automatic SDK tool execution disabled |
| Generation | Temperature `0.0`, maximum 2,000 output tokens |
| Thinking | Model default; no explicit thinking override |
| Maximum tool rounds | 8 |

Startup accepts only the selected and rollback model identifiers. The API key
stays in `/etc/pactra/pactra.env`; probes load it without printing it.

## Account model discovery

One authenticated `models.list` request verified that the configured account
can see these stable Flash identifiers with `generateContent` support:

- `gemini-3.8-flash`
- `gemini-3.7-flash`
- `gemini-3.6-flash`
- `gemini-3.5-flash`
- `gemini-3.5-flash-lite`
- `gemini-3.1-flash-lite`
- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`

The 2.5 models were not considered for selection because Google documents them
as deprecated. Preview, Pro, image, audio and paid-only choices were not used.
Google's model page identifies `gemini-3.5-flash-lite` as stable and supporting
function calling. Its standard pricing page documents a free tier; no billing
or project change was made.

## Bounded compatibility results

Each candidate used Pactra's real system instruction, five function
declarations, JSON schemas, SDK version and 12-second boundary. Each received
at most two identical attempts. Ordinary JSON text was not accepted as a
function call.

| Model | Attempt 1 | Attempt 2 | Result |
|---|---|---|---|
| `gemini-3.8-flash` | HTTP 503 `UNAVAILABLE`, 6,312 ms | Timeout, 12,011 ms | FAIL |
| `gemini-3.6-flash` | Timeout, 12,027 ms | Timeout, 12,013 ms | FAIL |
| `gemini-3.1-flash-lite` | Timeout, 12,025 ms | Timeout, 12,014 ms | FAIL |
| `gemini-3.5-flash` | Timeout, 12,020 ms | Timeout, 12,014 ms | FAIL |
| `gemini-3.5-flash-lite` | Genuine call, 1,068 ms | Genuine call, 1,024 ms | PASS |

The selected model returned exactly one genuine `create_payment_request` call
on both initial attempts. It produced the expected $49 USD internal-sandbox
arguments, and strict validation rejected locally injected missing, malformed
and additional arguments.

## Integration defects found and fixed

The one-turn probe was necessary but insufficient. A synthetic tool-result
round trip found two application compatibility defects:

1. Pactra sent a function response with role `tool`. The Developer API returned
   HTTP 400 `INVALID_ARGUMENT`: that role is unsupported. SDK fixtures and the
   API require a function-response turn to use role `user`.
2. The payment declaration did not explain that `recipient` is an email used
   only for payouts. Flash Lite sometimes placed a vendor name in that field.
   The schema now marks it as email/payout-only, and Pactra safely normalizes
   irrelevant recipient data to `null` for non-payout transactions. Payout
   recipients still require an explicit email in the current user message.

After both fixes and the final generation configuration, two complete bounded
round trips passed:

| Attempt | Function call | Final response | Finish reasons |
|---|---:|---:|---|
| 1 | 972 ms | 652 ms | `STOP`, `STOP` |
| 2 | 539 ms | 671 ms | `STOP`, `STOP` |

## Full isolated Pactra workflow

`scripts/gemini_workflow_acceptance.py` used an in-memory account and disabled
PayPal. The selected live model passed:

- a genuine internal-sandbox payout call extracting `$49.00`, `USD`, the test
  recipient, category and description;
- backend policy approval and one internal execution attempt;
- one completed transaction, two balanced receipt entries and six receipt
  lifecycle events;
- a `$120.00` vendor request left at `pending_approval`, with one active
  reservation and zero execution attempts;
- a missing-amount request produced a reply and no transaction;
- all created rails remained `internal_sandbox`;
- final isolated posted/reserved/available balances were
  `$951.00 / $120.00 / $831.00`;
- required assistant, payment, policy and completion audit events persisted.

Mocked regressions additionally prove bounded timeout and HTTP 503 handling,
malformed/empty response classification, strict argument rejection,
deterministic fallback, approval enforcement and committed tool-state
preservation after a later provider failure.

## Production acceptance

PR #14 merged as `63f25839a6b645a8ca404846ecd82d16c1994b7c`.
Exact-main workflow-dispatch run
[42674909231](https://github.com/arinze116/Pactra/actions/runs/42674909231)
passed Backend SQLite, Backend PostgreSQL, frontend lint/build/audits and
E2E/WCAG/Lighthouse on that exact SHA.

The immutable release is `/opt/pactra/releases/63f2583`. Its embedded SHA is
the merge commit above, and its source archive SHA-256 is
`6ba14264e0ee63ca49ae26af5ec15427ca3ae9ed25ab705498ee7c543bac5369`.
All 142 tracked files matched the archive byte-for-byte. `pip check`, required
imports, resolved dependencies and frontend build hashes passed.

Before deployment, Pactra created and verified:

- private environment backup
  `/opt/pactra/backups/pactra-env-pre-gemini-63f2583-20261109T184028Z.env`;
- PostgreSQL custom archive
  `/opt/pactra/backups/pactra-pre-63f25839a6b645a8ca404846ecd82d16c1994b7c-20261109T184028Z.dump`;
- database archive SHA-256
  `9f4a9407fc2aa292480e4608f84449be5dbb83e315b193f7c8e7aa68dfe213ac`;
- successful `pg_restore --list` validation.

Only `GEMINI_MODEL` changed in `/etc/pactra/pactra.env`. PayPal keys and
settings compared unchanged. The release symlink switched at
`2026-11-09T18:42:05Z`, and only the API process restarted. API PID changed
from `785075` to `819381`; worker PID `785136`, its start time and its advisory
lease remained unchanged. PostgreSQL stayed at `20261107_0005`. Local,
Tailscale and public readiness returned HTTP 200, and startup logs had no
warning or error.

The live public acceptance request used a new isolated account and asked only
for its wallet summary. It returned HTTP 200 in 1.610 seconds with exactly one
genuine `get_wallet_summary` call, empty arguments, the authoritative
USD 1,000.00 sandbox balance and zero created transactions. Persisted audit
evidence recorded:

- model `gemini-3.5-flash-lite`;
- two provider calls for the function-call and function-response turns;
- 1,391 ms cumulative provider latency;
- finish reason `STOP`;
- one successful tool call;
- no `assistant.error` or `assistant.fallback_used` event.

The completed PayPal Sandbox transaction remained unchanged: one attempt, one
capture journal, no active reservation and the same persisted provider
identifiers. No PayPal request was made during this rollout.

## Commands

```bash
sudo env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pactra/current \
  /opt/pactra/current/.venv/bin/python \
  /opt/pactra/current/scripts/gemini_compatibility_probe.py \
  --env-file /etc/pactra/pactra.env \
  --model gemini-3.5-flash-lite --attempts 2 \
  --timeout-seconds 12 --round-trip

sudo env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/pactra/current \
  /opt/pactra/current/.venv/bin/python \
  /opt/pactra/current/scripts/gemini_workflow_acceptance.py \
  --env-file /etc/pactra/pactra.env \
  --model gemini-3.5-flash-lite --timeout-seconds 12
```

## Production deployment and rollback

The production change completed with these gates:

1. Merge and verify CI on the exact release SHA.
2. Create a private backup of `/etc/pactra/pactra.env`.
3. Deploy the immutable release while leaving PayPal settings unchanged.
4. Change only `GEMINI_MODEL` to `gemini-3.5-flash-lite`.
5. Restart only `pactra-api.service`.
6. Verify readiness, logs and one non-PayPal production function call.

For a model-only rollback, restore only `GEMINI_MODEL=gemini-3.8-flash` from
the private environment backup and restart only the API. For an application
rollback, atomically point `/opt/pactra/current` to
`/opt/pactra/releases/73fdfb6` before restarting the API. Both releases use
schema `20261107_0005`; no downgrade is required.

The worker unit is `PartOf=pactra-api.service`, so an ordinary API restart
would also restart the worker. The verified one-service operation on installed
systemd 255 is:

```bash
worker_pid_before=$(systemctl show pactra-worker.service -p MainPID --value)
sudo systemctl --job-mode=ignore-dependencies restart pactra-api.service
test "$(systemctl show pactra-worker.service -p MainPID --value)" = \
  "${worker_pid_before}"
```

Use that path only after verifying PostgreSQL is active and the selected
release/configuration validates independently. If the worker PID changes,
stop and verify its lease and every unresolved payout before continuing. The
deterministic fallback remains enabled in either model configuration. Do not
retry a failing provider repeatedly, and do not modify PayPal settings or
records as part of Gemini rollback.

## Sources

- <https://ai.google.dev/gemini-api/docs/function-calling>
- <https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite>
- <https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite>
- Authenticated `client.models.list()` and `client.models.get()` results on
  2026-11-09
