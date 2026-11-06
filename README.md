# Pactra

Govern every payment, safely.

Pactra is a sandbox-only payment operations workspace built for the PayPal AI Hackathon 2026. A judge can create an isolated account, receive simulated test funds, configure spending policy, request payments manually or through Gemini, approve exceptions, and inspect the complete policy, ledger, and provider lifecycle.

No real money moves. Pactra's append-only ledger is the source of truth for the in-app test wallet. PayPal Sandbox Payouts is a separate external test rail and is never reported as successful until the individual payout item succeeds and Pactra's ledger capture commits.

- Live app: pending deployment and smoke verification at the unique Render service names in `render.yaml`
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
- PayPal Sandbox Payouts submission, stable provider idempotency references, item-level reconciliation, and reservation-safe failure handling
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
| `POST` | `/api/transactions` | Create one governed manual payment request |
| `GET` | `/api/transactions`, `/api/transactions/{id}` | Filtered history and receipt |
| `POST` | `/api/approvals/{id}/approve`, `/reject` | Single-use human review |
| `POST` | `/api/transactions/{id}/retry`, `/reverse`, `/reconcile` | Safe lifecycle recovery actions |
| `POST` | `/api/chat` | Persisted Gemini/fallback assistant using the same transaction service |
| `GET` | `/api/integrations/paypal/status` | Sandbox provider capability without secrets |
| `GET` | `/api/health`, `/api/ready` | Liveness and database/config readiness |

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
alembic upgrade head
cd frontend
npm run lint
npm run build
npm run test:e2e
npm audit --omit=dev --audit-level=high
```

Playwright starts the API and frontend, migrates an isolated local SQLite database automatically, and explicitly disables Gemini and PayPal. CI keeps its isolated PostgreSQL database. The suite never inherits the root `.env` database or provider flags. Judges and CI do not need external credentials for the internal sandbox path.

## Judge walkthrough

1. Open the app and create your own account; there is no shared judge password.
2. Confirm the wallet shows `$1,000.00` and the persistent sandbox-only notice.
3. Add `$100.00` test funds from Wallet.
4. Create a `$49.00` software payment to Linear and open its completed receipt.
5. Create a `$125.00` freelance payout to Ada Contractor on the internal rail, then approve it.
6. Create a `$185.00` cloud request to AWS and inspect the transaction-limit block with no ledger debit.
7. Change the approval threshold or categories under Policies and confirm the version increments.
8. Use the Assistant prompt `Pay Notion $20 for our software subscription`.
9. Filter Transactions, inspect lifecycle/ledger details, reject another pending request, and reset the sandbox by typing `RESET`.
10. If the PayPal integration page reports `Configured`, use the provided test-recipient shortcut, approve the payout, and refresh until the payout item reaches a truthful terminal state.

## Environment configuration

Server-only secrets must be stored in the hosting provider, never in Vite variables or source control.

| Variable | Production value or purpose |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` / `SECRET_KEY_FILE` | Unique random secret, 32+ characters; Oracle uses an absolute `0600` secret file |
| `DATABASE_URL` | PostgreSQL connection string; the Oracle service uses a local peer-authenticated socket |
| `FRONTEND_URL` | Exact HTTPS frontend origin |
| `BACKEND_URL` | Exact HTTPS API origin |
| `CORS_ORIGINS` | Comma-separated exact HTTPS frontend origins; no wildcard |
| `SESSION_COOKIE_SECURE` | `true` |
| `SESSION_COOKIE_SAMESITE` | `lax` when Vercel proxies `/api`; `none` only for an intentionally cross-site topology |
| `SESSION_TTL_HOURS`, `SESSION_IDLE_HOURS` | Defaults: `168` and `24` |
| `AI_ENABLED` | Set `true` only after `GEMINI_API_KEY` is present |
| `GEMINI_API_KEY` | Server-side Google AI Studio key |
| `GEMINI_MODEL` | `gemini-3.8-flash`, verified in the provider model catalogue |
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

The target topology is Vercel for the static frontend and the Oracle Ubuntu VPS for FastAPI, PostgreSQL, and one persistent reconciliation worker. Versioned deployment assets live in `deploy/`:

- `systemd/pactra-api.service` runs Alembic before binding Uvicorn to `127.0.0.1:8010`.
- `systemd/pactra-worker.service` runs reconciliation separately from the API. A PostgreSQL advisory lock prevents a second worker from becoming authoritative.
- `pactra.env.oracle-baseline` is a secret-free, loopback-only production baseline.
- `nginx/pactra-api.conf.example` and `vercel.json.example` require a verified API domain before activation.

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
- Posted ledger entries are immutable in PostgreSQL; corrections use balanced compensating journals.

SQLite is supported only for local development and lightweight tests. Public deployment requires PostgreSQL for durable data, locking, and ledger triggers.

The PRD-pinned Vite 5 development toolchain currently reports upstream dev-server advisories in a full npm audit. Production dependencies audit cleanly, the deployed artifact is static, and the development server must remain bound to localhost. Upgrading the PRD-pinned major version requires a deliberate compatibility pass.

## Known external blockers

- Gemini credentials and the configured model catalogue entry are verified, but live balance-tool smokes returned a provider `ServerError` and then timed out. The application now enforces a 12-second per-attempt deadline, retries three times, and reached deterministic fallback in 37.7 seconds. Regression coverage also proves malicious conversation history and retrieved transaction text cannot authorize a payment. Live Gemini tool execution is therefore not claimed.
- A new `$0.01` PayPal Sandbox Payouts smoke ran on 6 November 2026 with mock mode off. PayPal returned an item-level `FAILED` state; Pactra released the reservation and preserved the full balance correctly. A terminal-success smoke still requires a distinct active Sandbox recipient able to receive USD and a Payouts-capable business app.
- No controlled Pactra API domain/TLS certificate or Vercel project linkage is present on this VPS. The operator must point a controlled API hostname to the VPS and provide/link the Vercel project before the Nginx and rewrite templates can be activated.
- Devpost submission and the public demo-video upload remain owner actions.

## License

MIT © 2026 Arinze
