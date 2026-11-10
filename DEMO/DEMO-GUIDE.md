# Pactra instant demo guide

Pactra's public instant demo is a no-registration, sandbox-only product
workspace. Open the production landing page and select **Explore demo**. No
email, password, wallet connection, or provider credential is required.

Production URL: <https://pactra-nine.vercel.app>

## Judge journey

1. Open the public landing page in a fresh browser context.
2. Select **Explore demo**.
3. Wait for the explicit **Preparing demo…** state to finish.
4. Confirm the **Northstar Studio** dashboard and persistent demo banner appear.
5. Inspect the wallet, active policy, pending approval, and seeded receipts.
6. Create the `$49.00` software scenario. It should complete through the
   internal sandbox ledger.
7. Create the `$120.00` software scenario. It should wait for approval.
8. Approve or reject the request, then inspect its receipt, lifecycle, policy
   checks, audit events, and ledger impact.
9. Create the restricted-vendor scenario. The deterministic policy should
   block it.
10. Use **Reset demo** to restore the original state, then **Exit demo** to
    return to the public site.

The walkthrough on the overview page contains seven shorter prompts and marks
inspection steps complete only after the relevant page or evidence is opened.

## Seeded Northstar Studio workspace

The dataset is fictional and is created through Pactra's normal account,
policy, transaction, approval, audit, and ledger services.

| Surface | Seeded state |
|---|---|
| Posted balance | `$965.00` |
| Reserved balance | `$140.00` |
| Available balance | `$825.00` |
| Policy | `$500` daily limit, `$750` per-payment limit, approval above `$100`, restricted vendor `Restricted Supply Co` |
| Completed | `Frame.io`, `$35.00` |
| Awaiting approval | `Northstar Print House`, `$140.00` |
| Rejected | `Ridgeway Contractor`, `$130.00` |
| Policy blocked | `Restricted Supply Co`, `$75.00` |

The balances intentionally reflect the completed `$35.00` capture and the
active `$140.00` reservation. They reconcile with the current ledger rather
than presenting a contradictory `$1,000/$0/$1,000` snapshot alongside a
pending reserved payment.

## Demo controls

The banner reads:

> DEMO WORKSPACE · SANDBOX FUNDS ONLY · NO REAL MONEY MOVES

- **Reset demo** asks for confirmation, serializes concurrent resets, restores
  the current session's seed data, and clears walkthrough progress.
- **Exit demo** revokes only the temporary demo session and clears only the
  demo cookies. A separate normal account session in the same browser remains
  available.
- Refreshing the browser restores an unexpired demo session. The default
  lifetime is two hours.

## Safety boundary

- Every browser session receives a distinct temporary demo principal and
  owner-scoped wallet, policies, transactions, receipts, and audit records.
- Demo credentials use separate Secure/HttpOnly/SameSite cookies and never
  appear in URLs or browser storage.
- The backend rejects provider rails for demo principals. The transaction
  service, PayPal adapter, and worker scan independently enforce the same rule.
- The demo assistant is deterministic and explicitly states that no external
  AI call occurred.
- Account password changes, wallet top-ups, normal wallet reset, provider
  settings, and provider status details are unavailable in demo mode.
- Session creation, reset, active-session count, and total transaction count
  are bounded.

## Local verification

From `frontend/`, with the project dependencies already installed:

```bash
DEMO_PYTHON=/absolute/path/to/pactra/.venv/bin/python npm run test:demo
```

The Playwright suite uses providers-disabled test configuration, applies all
migrations, creates two independent browser contexts, runs the critical judge
journey with retries disabled, checks seven required viewports, and runs Axe
WCAG 2.1 A/AA checks.

To exercise PostgreSQL instead of the default temporary SQLite database:

```bash
DEMO_DATABASE_URL=postgresql+psycopg://USER@/ISOLATED_TEST_DATABASE \
DEMO_PYTHON=/absolute/path/to/pactra/.venv/bin/python \
npm run test:demo
```

Never point this command at the production database.

## Recovery

- If creation fails, keep the visitor on the public page, show the returned
  safe error, and retry after the rate-limit or capacity window.
- If a demo expires, the session endpoint clears the expired demo cookies and
  the landing page offers a fresh workspace.
- If reset fails, the transaction rolls back; the existing demo data remains
  available and the same idempotency key can be retried.
- If the API is unavailable, do not claim that reset, exit, or a payment
  succeeded.

Architecture and operational details are in
[INSTANT-DEMO-IMPLEMENTATION.md](./INSTANT-DEMO-IMPLEMENTATION.md). Acceptance
evidence is in
[QA/DEMO/DEMO-ACCEPTANCE-REPORT.md](../QA/DEMO/DEMO-ACCEPTANCE-REPORT.md).
