# Pactra

Govern every payment, safely.

Pactra is a sandbox-only payment operations workspace built for the PayPal AI Hackathon 2026. A judge can create an isolated account, receive simulated test funds, configure spending policy, request payments manually or through Gemini, approve exceptions, and inspect the complete policy, ledger, and provider lifecycle.

No real money moves. Pactra's append-only ledger is the source of truth for the in-app test wallet. PayPal Sandbox Payouts is a separate external test rail and is never reported as successful until the individual payout item succeeds and Pactra's ledger capture commits.

- Live app: pending owner deployment and smoke verification
- Demo video: pending owner recording/upload

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

Do not put real-money credentials in `.env`. For a real provider test, use only a PayPal sandbox business app and sandbox recipient, set `PAYPAL_MOCK_MODE=false`, then enable `PAYPAL_PAYOUTS_ENABLED=true`. Mock mode never produces a PayPal-branded success.

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

Playwright starts the API and frontend in normal local/CI environments. Run `alembic upgrade head` first. Tests use the internal rail and deterministic assistant fallback, so judges and CI do not need external credentials.

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

## Deployment

`render.yaml` provisions a managed PostgreSQL database, runs `alembic upgrade head` before the API starts, and deploys the Vite SPA separately. Before a public judge release, configure server-side `GEMINI_API_KEY`, PayPal sandbox client credentials, and `PAYPAL_TEST_RECIPIENT_EMAIL`; then set `AI_ENABLED=true` and `PAYPAL_PAYOUTS_ENABLED=true`. Never put those values in Vite variables or the repository.

The release is not submission-ready until a real PayPal Sandbox Payouts batch has been created and reconciled at item level in the deployed environment. A mock or internal-ledger transaction is never evidence of that provider smoke test.

## Security notes

- Secrets are loaded only from environment variables and `.env` is ignored.
- Gemini sees tool results, never PayPal credentials or bearer tokens.
- Tool inputs are validated independently of model output.
- PayPal error messages are sanitised; credentials and response bodies are not logged.
- Payout emails are validated and all payment amounts must be finite and positive.
- Pending payments are re-evaluated against hard limits immediately before approval.
- CORS is restricted to configured origins.
- Production startup refuses SQLite, insecure cookies, weak secrets, mock-enabled payouts, missing enabled-provider credentials, and any non-sandbox PayPal host.
- Posted ledger entries are immutable in PostgreSQL; corrections use balanced compensating journals.

SQLite is supported only for local development and lightweight tests. Public deployment requires PostgreSQL for durable data, locking, and ledger triggers.

The PRD-pinned Vite 5 development toolchain currently reports upstream dev-server advisories in a full npm audit. Production dependencies audit cleanly, the deployed artifact is static, and the development server must remain bound to localhost. Upgrading the PRD-pinned major version requires a deliberate compatibility pass.

## Known external blockers

- Live Gemini verification requires an operator-supplied API key.
- Live PayPal verification requires a sandbox business app with Payouts capability and a sandbox recipient account.
- Public deployment smoke testing and Devpost/YouTube submission require the owner's hosting and submission access.

## License

MIT © 2026 Arinze
