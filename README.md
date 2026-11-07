# Pactra

Govern every payment, safely.

Pactra is a sandbox-only payment operations workspace built for the PayPal AI Hackathon 2026. A judge can create an isolated account, receive simulated test funds, configure spending policy, request payments manually or through Gemini, approve exceptions, and inspect the complete policy, ledger, and provider lifecycle.

No real money moves. Pactra's append-only ledger is the source of truth for the in-app test wallet. PayPal Sandbox Payouts is a separate external test rail and is never reported as successful until the individual payout item succeeds and Pactra's ledger capture commits.

- Live app: <https://pactra-nine.vercel.app> — independently re-audited against the Oracle PostgreSQL runtime on 7 November 2026
- Demo video: pending owner recording/upload
- Product contract: [`Pactra-PRD-Judge-Ready.md`](./Pactra-PRD-Judge-Ready.md)
- Judge demo and release gates: [`DEMO.md`](./DEMO.md) and [`SUBMISSION.md`](./SUBMISSION.md)

## What works

- Email/password accounts with Argon2id, opaque server-side sessions, CSRF protection, and owner-scoped data
- Per-user double-entry sandbox ledger with initial funds, top-ups, reservations, reset generations, retries, and compensating reversals
- Deterministic, versioned category/vendor/transaction/daily/budget/approval policy enforcement
- Atomic approval and rejection workflow with current-policy re-evaluation
- One validated transaction service shared by manual requests and the Gemini assistant
- Internal sandbox execution for every judge, with honest fallback when external services are unavailable
- PayPal Sandbox Payouts submission, stable provider idempotency references, item-level reconciliation, and reservation-safe failure handling in provider-independent tests; live Sandbox success remains credential-gated
- Transaction receipts, lifecycle audit events, ledger entries, filtering, and AG Grid history
- Authenticated React/TypeScript workspace with loading, empty, failure, and recovery states
- Alembic migrations, PostgreSQL production configuration, backend tests, and Playwright judge journeys

## Architecture

```text
React/Vite workspace
        |
        v
FastAPI session + CSRF boundary
        |
        +--> Gemini typed tools ----+
        |                           |
        +--> manual payment form ---+--> transaction service
                                             |
                                   deterministic policy + reservation
                                             |
                                approval or selected sandbox rail
                                      /                    \
                           internal sandbox       PayPal Sandbox Payouts
                                      \                    /
                               append-only ledger + audit receipt
```

The model can propose typed actions, but it cannot choose a user, alter policy, mutate the ledger, or access provider credentials. Manual and AI-created requests use the same authenticated backend service.

## Quick start

Requirements: Python 3.11.10+ and Node.js 22.23.2. Gemini and PayPal credentials are optional for local development; the internal sandbox rail and deterministic assistant fallback work without them.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
alembic upgrade head

cd frontend
npm ci
cd ..
```

Do not put real-money credentials in `.env`. The safe default is `PAYPAL_MOCK_MODE=false` with payouts disabled. For a real provider test, use only a PayPal Sandbox business app and a distinct Sandbox recipient, keep `PAYPAL_MOCK_MODE=false`, then enable `PAYPAL_PAYOUTS_ENABLED=true`. Pactra never presents mock output as a PayPal result.

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

In a second terminal, start the interface:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173>, create a fresh account, and use the in-product judge walkthrough. Development API documentation is available at <http://localhost:8000/docs>; production disables it.

## Demo prompts

- `Pay Linear $49 for our monthly software subscription.` → approved and captured
- `Send $125 to ada@example.com for freelance contract work` → waits for human approval
- `Pay AWS $185 for cloud hosting.` → blocked by the per-transaction cap
- `Show me today's remaining budget.` → Gemini tool query when AI is configured

## Default policy

Each account receives a versioned database policy seeded from the defaults. Rules run server-side in this exact order:

1. Active account/wallet and USD currency
2. Allowed category
3. Blocked vendor
4. Per-transaction limit
5. Daily committed plus reserved spend
6. Category committed plus reserved spend
7. Available sandbox funds
8. Human-approval threshold

The first failing rule wins, producing a stable machine-readable reason in the audit log.

| Control | Default |
|---|---:|
| Daily limit | $500 |
| Per-transaction cap | $150 |
| Human approval above | $100 |
| Categories | ops, software, cloud, freelance |

Completed transactions consume committed budget. Pending approvals and unresolved provider payouts reserve funds and budget capacity. Blocked and rejected requests do not debit the posted ledger.

## Payment rails

- `internal_sandbox`: deterministic Pactra ledger execution, available to every judge without credentials.
- `paypal_sandbox_payouts`: outbound payout requests from the configured PayPal sandbox business account. Pactra stores batch/item state separately, keeps the reservation while processing or unknown, and posts its ledger capture only after payout-item `SUCCESS`.

Pactra wallet balances and PayPal sandbox account balances are separate systems. The UI always shows the rail actually used. PayPal Orders checkout is not used as an outbound payout API.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | Account and session lifecycle |
| `GET/POST` | `/api/wallet`, `/api/wallet/topups`, `/api/wallet/reset` | Ledger-backed sandbox funds |
| `GET/PUT` | `/api/policy` | Current policy and immutable version save |
| `POST` | `/api/transactions/preview` | Side-effect-free server-authoritative policy preview |
| `POST` | `/api/transactions` | Create one governed manual payment request |
| `GET` | `/api/transactions`, `/api/transactions/{id}` | Filtered history and receipt |
| `POST` | `/api/approvals/{id}/approve`, `/reject` | Single-use human review |
| `POST` | `/api/transactions/{id}/retry`, `/reverse`, `/reconcile` | Safe lifecycle recovery actions |
| `POST` | `/api/chat` | Persisted Gemini/fallback assistant using the same transaction service |
| `POST` | `/api/judge/guided/start`, `/api/judge/scenarios/insufficient-funds` | Persisted judge walkthrough controls |
| `GET` | `/api/integrations/paypal/status` | Sandbox provider capability without secrets |
| `GET` | `/api/health`, `/api/ready` | Liveness and database/config readiness |

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt
alembic upgrade head
cd frontend
npm run lint
npm run build
npm run test:e2e
PUBLIC_BASE_URL=https://pactra-nine.vercel.app npm run test:e2e:public
npm audit --omit=dev --audit-level=high
npm audit --audit-level=moderate
```

Playwright starts the API and frontend, migrates an isolated local SQLite database automatically, and explicitly disables Gemini and PayPal. CI keeps its isolated PostgreSQL database. The suite never inherits the root `.env` database or provider flags. Judges and CI do not need external credentials for the internal sandbox path.

## Judge walkthrough

1. Open the app and create your own account; there is no shared judge password.
2. Confirm the wallet shows `$1,000.00` and the persistent sandbox-only notice.
3. Add `$100.00` test funds from Wallet.
4. Create a `$49.00` software payment to Linear and open its completed receipt.
5. Create a `$125.00` freelance payout to Ada Contractor on the internal rail, then approve it.
6. Create a `$185.00` cloud request to AWS and inspect the persisted 422 policy block with no ledger debit.
7. Run the guided insufficient-funds scenario and confirm its persisted receipt says no ledger posting occurred.
8. Change the approval threshold or categories under Policies and confirm the version increments.
9. Use the Assistant prompt `Pay Notion $20 for our software subscription`.
10. Filter Transactions, inspect actor-labelled lifecycle and balanced account-labelled ledger details, reject another pending request, reverse an internal payment, and reset the sandbox by typing `RESET`.
11. If the PayPal integration page reports `Configured`, stop and obtain operator authorization for the specific Sandbox payout before using the provided test recipient. Completion requires payout-item `SUCCESS` plus Pactra reconciliation; configured status alone is not success.

## Environment configuration

Server-only secrets must be stored in the hosting provider, never in Vite variables or source control.

| Variable | Production value or purpose |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` / `SECRET_KEY_FILE` | Unique random secret, 32+ characters; Oracle uses an absolute `0600` secret file |
| `DATABASE_URL` | PostgreSQL connection string; the Oracle service uses a local peer-authenticated socket |
| `FRONTEND_URL` | Exact HTTPS frontend origin |
| `BACKEND_URL` | Browser-visible HTTPS API origin; use the Vercel origin when `/api` is rewritten same-origin |
| `CORS_ORIGINS` | Comma-separated exact HTTPS frontend origins; no wildcard |
| `SESSION_COOKIE_SECURE` | `true` |
| `SESSION_COOKIE_SAMESITE` | `lax` when Vercel proxies `/api`; `none` only for an intentionally cross-site topology |
| `SESSION_TTL_HOURS`, `SESSION_IDLE_HOURS` | Defaults: `168` and `24` |
| `AUTH_REGISTRATION_RATE_LIMIT_PER_HOUR`, `AUTH_REGISTRATION_GLOBAL_RATE_LIMIT_PER_HOUR` | Per-client and shared database-backed sandbox registration ceilings; defaults: `10` and `100` |
| `AUTH_LOGIN_GLOBAL_RATE_LIMIT_PER_MINUTE` | Shared database-backed ceiling that bounds distinct-account login enumeration; default: `30` |
| `AI_ENABLED` | Set `true` only after `GEMINI_API_KEY` is present |
| `GEMINI_API_KEY` | Server-side Google AI Studio key |
| `GEMINI_MODEL` | Configured model name; validate it against the current provider catalogue before enabling AI |
| `GEMINI_REQUEST_TIMEOUT_SECONDS` | Per-attempt application deadline; default `12` |
| `MAX_CHAT_HISTORY` | Default `20` |
| `PAYPAL_PAYOUTS_ENABLED` | Set `true` only after all Sandbox values below are present |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | PayPal Sandbox business-app credentials |
| `PAYPAL_TEST_RECIPIENT_EMAIL` | Distinct active PayPal Sandbox recipient account |
| `PAYPAL_BASE_URL` | Exactly `https://api-m.sandbox.paypal.com` |
| `PAYPAL_MOCK_MODE` | `false` in production and for real Sandbox tests |
| `PAYPAL_REQUEST_TIMEOUT_SECONDS` | Default `15` |
| `VITE_API_URL` | Leave blank when Vercel rewrites same-origin `/api`; contains no secret when used locally |
| `SEED_DEMO_ACCOUNT` | `false` in production |

The API returns the CSRF synchronizer token through an explicitly exposed response header while keeping both auth cookies HttpOnly. The target Vercel rewrite keeps browser traffic same-origin, so production cookies remain Secure and SameSite=Lax.

## Deployment

The production topology is Vercel for the static frontend and the Oracle Ubuntu VPS for FastAPI, PostgreSQL, and one persistent reconciliation worker. Vercel rewrites same-origin `/api/*` requests to a trusted Tailscale Funnel endpoint, which proxies to the loopback API without exposing PostgreSQL or a plaintext public API:

```text
https://pactra-nine.vercel.app/api/*
        -> https://node1.taild90918.ts.net/api/*
        -> http://127.0.0.1:8010/api/*
```

Oracle's public security list did not admit TCP 80/443, so the direct SSLIP/Certbot route could not complete. Tailscale terminates trusted public HTTPS with a Let's Encrypt certificate while the final hop remains on the VPS loopback interface. `sudo tailscale funnel status` shows the active route; `sudo tailscale funnel --https=443 off` is the rollback command.

Versioned deployment assets live in `deploy/`:

- `systemd/pactra-api.service` runs Alembic before binding Uvicorn to `127.0.0.1:8010`.
- `systemd/pactra-worker.service` runs reconciliation separately from the API. A PostgreSQL advisory lock prevents a second worker from becoming authoritative.
- `pactra.env.oracle-baseline` is a secret-free, loopback-only production baseline.
- `nginx/pactra-api.conf.example` remains the preferred direct-domain template when Oracle admits HTTPS traffic.
- `frontend/vercel.json` contains the active same-origin rewrite and production security headers.

`render.yaml` remains available as the previous fallback and must not be destroyed before the Oracle/Vercel replacement is publicly verified. Because reconciliation is intentionally no longer embedded in the web process, PayPal payouts must remain disabled on any Render deployment that does not also supervise `python -m backend.worker`.

Before a public judge release, add server-side `GEMINI_API_KEY`, PayPal Sandbox client credentials, and `PAYPAL_TEST_RECIPIENT_EMAIL`; then set `AI_ENABLED=true` and `PAYPAL_PAYOUTS_ENABLED=true`. Keep `PAYPAL_MOCK_MODE=false`. Never put those values in Vite variables or the repository. If either optional integration is unavailable, leave only its feature flag off; the internal sandbox ledger and deterministic assistant fallback remain usable and the UI reports the provider state honestly.

The release is not submission-ready until a real PayPal Sandbox Payouts batch has been created and reconciled at item level in the deployed environment. A mock or internal-ledger transaction is never evidence of that provider smoke test.

## Security notes

- Secrets are loaded only from environment variables and `.env` is ignored.
- Gemini sees tool results, never PayPal credentials or bearer tokens.
- Tool inputs are validated independently of model output; payment amounts and payees must be explicit in the current user message, so conversation history and retrieved transaction text cannot authorize movement.
- PayPal error messages are sanitised; credentials and response bodies are not logged.
- Payout emails are validated and all payment amounts must be finite and positive.
- Pending payments are re-evaluated against hard limits immediately before approval.
- CORS is restricted to configured origins.
- Production startup refuses SQLite, insecure cookies, weak secrets, mock-enabled payouts, missing enabled-provider credentials, and any non-sandbox PayPal host.
- Posted ledger journals and their two-entry posting sets are immutable in PostgreSQL; corrections use balanced compensating journals.
- Authentication, payment, policy and assistant fixed-window counters are stored atomically in PostgreSQL, shared across API processes and retained through restarts.

SQLite is supported only for local development and lightweight tests. Public deployment requires PostgreSQL for durable data, locking, and ledger triggers.

The release-candidate toolchain uses Vite 8 with a reviewed `minimatch` override. Production and full development dependency audits are clean in the recorded release-candidate evidence. Keep the development server bound to localhost and rerun both audits whenever the lockfile changes.

## Known external blockers

- The deployed runtime currently has Gemini disabled and no API key. Automated tests verify strict tool validation, prompt-injection resistance, bounded retries, safe fallback, and error redaction, but live Gemini tool execution is unverified.
- The deployed runtime currently has PayPal Payouts disabled, no Sandbox credentials, and mock mode off. Automated tests verify stable provider IDs, item-level reconciliation, unknown outcomes, failure, return, reversal, and restart safety. No live PayPal Sandbox success is claimed, and historical database records are not treated as provider proof by this audit.
- Devpost submission and the public demo-video upload remain owner actions.

## License

MIT © 2026 Arinze
