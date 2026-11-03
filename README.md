# Pactra

Pactra is an AI-agent payment governance layer for PayPal. It lets an operations leader delegate payments to a Gemini-powered agent while enforcing deterministic category, vendor, transaction, daily-spend, and approval rules before any request reaches PayPal.

Built for the PayPal AI Hackathon 2026.

## What works

- Gemini function-calling loop for vendor payments, payouts, and budget queries
- Strict, ordered policy evaluation that the model cannot bypass
- PayPal Orders v2, Payouts, OAuth token caching, and transaction-search client
- Human approval flow for transactions above the automatic threshold
- Live transaction audit log with approved, blocked, and pending states
- Daily and category utilisation dashboard
- Deterministic PayPal mock mode for a credential-free judge experience
- Responsive React/TypeScript operations interface with an accessible transaction ledger
- SQLite persistence via SQLModel and Render deployment blueprint

## Architecture

```text
Operator ──> React dashboard ──> FastAPI ──> Gemini agent
                                      │          │
                                      │          └─ tool request
                                      v
                                Policy engine
                                 │    │    │
                            blocked pending approved
                                      │    │
                                human review └─> PayPal REST APIs
                                      │              │
                                      └────> SQLite audit ledger
```

The Gemini model can request a tool, but it never receives PayPal credentials and cannot execute a payment directly. Every payment tool call is validated and sent through `PolicyEngine.check()` first.

## Quick start

Requirements: Python 3.11+, Node.js 20.19+ (or 22.12+), and a free Gemini API key.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

cd frontend
npm install
cd ..
```

Add `GEMINI_API_KEY` to `.env`. Leave `PAYPAL_MOCK_MODE=true` for the complete no-money demo flow.

Start the API:

```powershell
uvicorn backend.main:app --reload --port 8000
```

In a second terminal, start the interface:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173>. API documentation is available at <http://localhost:8000/docs>.

## Demo prompts

- `Pay Linear $49 for our monthly software subscription.` → approved and captured
- `Send a $125 freelance payout to ada@example.com.` → waits for human approval
- `Pay AWS $185 for cloud hosting.` → blocked by the per-transaction cap
- `Show me today's remaining budget.` → returns current category utilisation

## Default policy

The active policy lives at [`backend/policy.json`](backend/policy.json). Rules run in this exact order:

1. Approved category
2. Blocked vendor
3. Per-transaction limit
4. Daily limit
5. Category budget
6. Human-approval threshold

The first failing rule wins, producing a stable machine-readable reason in the audit log.

| Control | Default |
|---|---:|
| Daily limit | $500 |
| Per-transaction cap | $150 |
| Human approval above | $100 |
| Categories | ops, software, cloud, freelance |

Spend is recorded only after PayPal accepts/completes the transaction. Pending and blocked requests do not consume budget.

## PayPal modes

`PAYPAL_MOCK_MODE=true` generates clearly prefixed `DEMO-ORDER-*` and `DEMO-PAYOUT-*` references while exercising the real policy, persistence, agent, and approval paths. It is the recommended hackathon judging mode.

Set `PAYPAL_MOCK_MODE=false` and provide sandbox credentials to call PayPal REST APIs. Orders are created and captured back-to-back as specified for the demo integration; account capabilities and approval requirements still depend on the configured PayPal sandbox merchant.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/chat` | Run the Gemini agent/tool loop |
| `GET` | `/api/transactions` | Filtered audit log |
| `GET` | `/api/transactions/{id}` | Transaction detail |
| `GET` | `/api/spend-summary` | Today's category utilisation |
| `GET` | `/api/policy` | Active policy |
| `POST` | `/api/policy/approve/{id}` | Human approval and execution |
| `GET` | `/api/health` | Deployment health check |

## Verification

```powershell
pytest
cd frontend
npm run lint
npm run build
```

The policy suite covers every decision branch, case-insensitive vendor blocking, threshold boundaries, daily/category limits, and spend accounting.

## Security notes

- Secrets are loaded only from environment variables and `.env` is ignored.
- Gemini sees tool results, never PayPal credentials or bearer tokens.
- Tool inputs are validated independently of model output.
- PayPal error messages are sanitised; credentials and response bodies are not logged.
- Payout emails are validated and all payment amounts must be finite and positive.
- Pending payments are re-evaluated against hard limits immediately before approval.
- CORS is restricted to configured origins.

SQLite on Render's free, ephemeral filesystem is suitable for the hackathon demo. Use a managed database for durable production audit retention and multi-instance concurrency.

## License

MIT © 2026 Arinze
