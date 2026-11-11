# Pactra — PayPal AI Hackathon 2026 submission brief

- Live demo: <https://pactra-nine.vercel.app>
- Public video: <https://youtu.be/685tzja9ey4>
- Source repository: <https://github.com/arinze116/Pactra>
- Licence: [MIT](./LICENSE)

## Project description

Pactra is a sandbox-only payment-governance workspace for small teams. A
payment button can move a request forward, but a business also needs to know
whether the vendor is permitted, whether budget remains, whether a person must
approve the request, and what evidence proves the final outcome.

Pactra lets a person describe a payment in natural language or use a manual
form. Gemini may interpret the request and call a declared application tool,
but the backend remains authoritative. The shared transaction service
validates the request, evaluates versioned policy, reserves funds, and either
blocks, routes for approval, or makes the request executable. Gemini cannot
approve a request, submit a payout, choose another tenant, or mutate the
ledger.

For PayPal Sandbox payouts, the API persists one stable attempt and returns.
A separately leased worker is the only component allowed to submit to PayPal.
Pactra does not treat batch acceptance as payment success: the internal ledger
captures funds only after the individual payout item reports `SUCCESS`.
Receipts preserve the policy trace, approval action, provider attempt,
lifecycle events, audit history, and balanced journal entries.

The target users are founders, finance operators, and small-team managers who
want an AI-assisted request interface without delegating financial authority
to the model.

## What makes Pactra different

Pactra is not a chatbot that merely recommends a payment. The assistant is an
untrusted request source connected to a deterministic, owner-scoped financial
state machine. Manual and AI requests pass through the same policy, approval,
reservation, execution, audit, and ledger controls.

## Judge access

Select **Explore demo** on the live site for an isolated Northstar Studio
workspace without registration or shared credentials. This path demonstrates
the real policy, approval, receipt, audit, ledger, reset, and session-isolation
workflows. Its assistant is deterministic and explicitly labelled; it does not
call Gemini and cannot reach PayPal.

The normal authenticated application uses the Gemini function-calling path
when server-side AI configuration is available. Judges may create a normal
account through **Sign up** using an email address they control. Pactra does not
publish shared judge credentials. Routine evaluation should use the internal
sandbox; the public video contains the retained evidence for the approved
PayPal Sandbox scenarios.

## Demonstration evidence

The 130-second public video shows the authenticated application, not the
deterministic instant demo. It records:

1. a genuine Gemini `create_payment_request` tool call for a `$49` Linear
   PayPal Sandbox payout;
2. server-side policy evaluation and a request that did not require approval;
3. worker-owned PayPal Sandbox submission and item-level `SUCCESS` before
   ledger capture;
4. a genuine `$120` Figma Teams request held at the `$100` approval threshold;
5. explicit human approval before worker submission; and
6. the persisted receipt, provider attempt, lifecycle, audit, policy, and
   balanced-ledger evidence.

The requesting account performs its own approval. Pactra does not claim
independent maker-checker role separation.

## Tools and how they are used

| Tool | Use in Pactra |
|---|---|
| PayPal Payouts REST API v1 | Sandbox-only OAuth, one-item payout submission, stable request identifiers, payout status lookup, and item-level reconciliation. |
| Gemini Developer API through `google-genai` | Typed function calling for payment-request interpretation and owned wallet, policy, transaction-list, and receipt queries. |
| FastAPI, Pydantic, SQLModel, SQLAlchemy | Strict API contracts, authentication boundaries, transaction orchestration, persistence, and database access. |
| PostgreSQL and Alembic | Production persistence, migrations, row locking, uniqueness constraints, advisory worker lease, and ledger/audit immutability controls. |
| React, TypeScript, Vite, React Router, AG Grid | Responsive public and authenticated product interfaces, forms, approvals, transaction operations, and receipts. |
| Pytest, Playwright, Axe, Lighthouse | Backend state-machine tests, browser journeys, automated accessibility checks, and homepage performance budgets. |
| Vercel, systemd, Tailscale Funnel | Existing hosted frontend, API/worker process definitions, and HTTPS routing. These systems are not changed by the submission-documentation release. |

## Hackathon-period work

During the hackathon period, Pactra advanced from an early single-user
SQLite/mock prototype to the current governed application: multi-user
authentication and ownership, versioned policy, integer-cent double-entry
ledger and reservations, human approval, the active Gemini typed-tool service,
worker-owned PayPal Sandbox reconciliation, PostgreSQL/Alembic operations,
receipts and audit evidence, responsive judge workflows, and an isolated
credential-free instant demo.

## Sandbox and product limitations

- Pactra moves no real money. The wallet is simulated and the provider rail is
  PayPal Sandbox only.
- The public instant demo does not call Gemini or PayPal.
- The approval actor is the requesting account; separate requester and
  approver roles are not implemented.
- PayPal webhooks are not implemented; reconciliation uses authenticated
  polling.
- Manual NVDA/VoiceOver verification remains outstanding; automated Axe and
  keyboard checks have passed.
- The live production application is an accepted earlier runtime. A repository
  merge does not imply a new deployment.

## Repository verification checklist

- [x] Public GitHub repository.
- [x] MIT licence detected by GitHub and present at repository root.
- [x] Project description, features, architecture, setup, environment, and
  testing instructions.
- [x] Credential-free functional instant demo.
- [x] Authenticated Gemini implementation clearly distinguished from the
  deterministic public demo.
- [x] PayPal Sandbox integration and worker/item-status boundary documented.
- [x] Public YouTube video, 130 seconds, with 1080p playback available.
- [x] Final video URL included in README and this submission brief.
- [x] Tools used and their roles listed.
- [ ] Owner eligibility confirmed directly against the official rules.
- [ ] Owner confirms permission or obtains organiser guidance for third-party
  names visible in the approved video (`Linear`, `Figma Teams`, and `Gemini`).
- [ ] Owner completes the Devpost form and final submission.

Do not interpret this file as an eligibility determination or as a completed
Devpost submission. Those decisions remain with the owner and organisers.
