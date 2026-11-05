# PRD --- Pactra

> Implementation contract for the autonomous coding agent. Build the
> complete judge-ready sandbox product against the supplied
> `Pactra-main.zip` repository. This document supersedes conflicting
> README claims and existing demo-only behaviour. Do not stop at a
> clickable prototype.

> Core architecture decision: Pactra's own append-only test ledger is
> the source of truth for each user's sandbox balance. PayPal Sandbox
> Payouts is a first-class external test rail for payout requests. The
> internal sandbox rail remains available for every judge journey.
> Provider status and Pactra ledger status are separate facts; never
> fake a PayPal success.

## 0. Document control

  -----------------------------------------------------------------------
  Field                               Value
  ----------------------------------- -----------------------------------
  Project name                        Pactra

  Tagline                             Govern every payment, safely

  Version / date                      v1.1 / 3 November 2026

  Hackathon / track(s) / prizes       PayPal AI Hackathon 2026; Grand
  targeted                            Prize; Best Use of PayPal + AI
                                      Honorable Mention; Best Use of AG
                                      Grid Sponsor Prize. Prize
                                      eligibility is subject to official
                                      rules.

  Build window                        ASSUMPTION: 24-hour implementation
                                      sprint from owner kickoff, WAT.
                                      Submission deadline: 12 November
                                      2026, 12:00 PST (21:00 WAT).

  Builder                             Project owner + autonomous coding
                                      agent

  Repo name                           `arinze116/Pactra`

  Production URL (planned)            Existing Render deployment if
                                      healthy; otherwise stable HTTPS
                                      deployment configured in Section 30

  Source repository snapshot          `Pactra-main.zip`, supplied 3
                                      November 2026

  Hackathon update evidence           Preserve a concise changelog of
                                      substantial post-1-Oct changes for
                                      Devpost submission

  Product mode                        Sandbox-only; no real-money
                                      execution
  -----------------------------------------------------------------------

Official hackathon sources: [Devpost
overview](https://paypalaihackathon.devpost.com/) and [official
rules](https://paypalaihackathon.devpost.com/rules).

## 1. Overview

Pactra is an AI-assisted payment operations workspace for small
businesses that delegate routine vendor and contractor payments but need
hard spending controls. Users can register, receive test funds,
configure policies, request payments manually or in natural language,
approve exceptions, and inspect a complete transaction and ledger
history. The deterministic policy engine---not the model---decides
whether an action is blocked, auto-approved, or held for review.
Pactra's append-only sandbox ledger provides durable user-owned balances
and repeatable test transactions. PayPal Sandbox Payouts is a
first-class provider rail for contractor/vendor payout requests, with
provider state reconciled separately from Pactra's ledger; the internal
sandbox rail keeps every judge journey usable without the judge
supplying credentials. The product is designed for judges to test every
feature through a self-serve account and guided scenarios, not to watch
a scripted demo. All funds and provider interactions are explicitly
sandbox-only.

## 2. Problem

Small operations teams delegate routine vendor and contractor payments
but still need limits, recipient controls, approvals, and a trustworthy
record of what was requested and what happened. An AI payment agent adds
speed but also introduces a new failure surface: model output can be
ambiguous, manipulated, or wrong, so it cannot be the authority for
money movement. Pactra addresses this by routing natural-language intent
through deterministic policy checks, human approval where required, and
an auditable ledger before any sandbox execution.

Verified context: - PayPal Payouts is designed for business
disbursements to recipients such as vendors, contractors, employees, and
customers: [PayPal Payouts
overview](https://developer.paypal.com/payouts/overview/). - PayPal
Sandbox is a virtual test environment that simulates payment activity
without touching live accounts: [PayPal Sandbox testing
guide](https://developer.paypal.com/sandbox-testing/overview/). - The
hackathon requires meaningful use of PayPal Developer Platform and an AI
tool, and judges must be able to interact with a functional build:
[official rules](https://paypalaihackathon.devpost.com/rules).

Repository-specific gap: the current repo has a single global
transaction/policy snapshot model, no user ownership fields, float-based
amounts, and no durable wallet ledger. The current Gemini
dependency/model are also legacy: `google-generativeai` is deprecated
and `gemini-2.0-flash` is listed as shut down in Google's current model
catalogue. The PRD replaces those foundations while preserving the
existing React/FastAPI product direction.

## 3. Target users and personas

  ---------------------------------------------------------------------------
  Persona        Context        Goal           Frustration    Success
  -------------- -------------- -------------- -------------- ---------------
  Maya,          Runs vendor    Delegate       Manual         A payment is
  Operations     and contractor requests while approvals,     governed,
  Lead (primary  payments for a enforcing      unclear        executed in
  judge persona) small team     spending       budgets,       sandbox, and
                                controls       scattered      fully auditable
                                               records        in under two
                                                              minutes

  Theo, Finance  Reviews        Approve only   Approval       Pending
  Reviewer       exceptions and valid requests requests lack  requests show
                 approvals      with enough    policy context amount,
                                context        or duplicate   recipient,
                                                              category,
                                                              policy result,
                                                              balance impact
                                                              and history

  Sam, Hackathon Tests the      Verify the     Demo-only      Can sign up,
  Judge          product        product is     buttons,       fund a sandbox
                 without setup  genuinely      seeded fake    wallet, change
                 help           functional     outcomes,      policy, execute
                                               broken empty   and inspect
                                               states         transactions
                                                              independently
  ---------------------------------------------------------------------------

## 4. Unique angle and prior art

The AI payment-governance space is crowded. Pactra must not claim to be
the first AI payment policy layer. The defensible wedge is a complete,
repeatable, multi-user sandbox operations product with a persistent
user-owned test wallet, atomic policy reservations, a real PayPal
Sandbox Payouts execution path, and receipts that expose the full
policy/ledger/provider lifecycle.

  -----------------------------------------------------------------------------------------------------------------------------------------------
  Closest        Link                                                               What it does                 Won?           How Pactra
  existing                                                                                                                      differs
  project                                                                                                                       
  -------------- ------------------------------------------------------------------ ---------------------------- -------------- -----------------
  BOLT ---       https://devpost.com/software/bolt-agentic-payments-control-plane   PayPal Sandbox               Not verified   Pactra
  Agentic                                                                           policy/approval control                     prioritises the
  Payments                                                                          plane with an AI planner                    fully usable
  Control Plane                                                                     planned in its submission                   multi-user
                                                                                                                                account, wallet,
                                                                                                                                policy editor,
                                                                                                                                lifecycle and
                                                                                                                                judge self-serve
                                                                                                                                product rather
                                                                                                                                than a
                                                                                                                                control-plane
                                                                                                                                prototype

  AgentPay       https://devpost.com/software/agentpay-2lnwmz                       Policy/audit console for AI  Not verified   Pactra governs
                                                                                    shopping agents with a                      business
                                                                                    simulated checkout                          vendor/payout
                                                                                                                                workflows with a
                                                                                                                                persistent ledger
                                                                                                                                and PayPal
                                                                                                                                Sandbox Payouts
                                                                                                                                rail, not
                                                                                                                                synthetic
                                                                                                                                shopping
                                                                                                                                catalogue
                                                                                                                                purchases

  Agent Payment  https://devpost.com/software/agent-payment-firewall-8pdbtw         PayPal Orders                Not verified   Pactra is an
  Firewall                                                                          authorization/capture/void                  operations
                                                                                    with deterministic and AI                   workspace with
                                                                                    escalation controls                         account-level
                                                                                                                                balances, spend
                                                                                                                                budgets,
                                                                                                                                multi-user
                                                                                                                                isolation,
                                                                                                                                manual + AI
                                                                                                                                requests, and
                                                                                                                                payout-specific
                                                                                                                                provider
                                                                                                                                execution

  AgentTab       https://devpost.com/software/agenttab                              PayPal-backed agent tab for  Not verified   Pactra focuses on
                                                                                    paid API usage and                          SMB payment
                                                                                    settlement                                  operations:
                                                                                                                                vendor
                                                                                                                                categories, daily
                                                                                                                                budgets, human
                                                                                                                                approvals,
                                                                                                                                sandbox wallet
                                                                                                                                and transaction
                                                                                                                                receipts

  Existing       https://github.com/arinze116/Pactra                                Gemini agent, policy engine, Not verified   The hackathon
  Pactra                                                                            PayPal client and dashboard                 update adds
  repository                                                                                                                    user-owned
                                                                                                                                accounts, an
                                                                                                                                append-only
                                                                                                                                ledger, durable
                                                                                                                                policy versions,
                                                                                                                                race-safe
                                                                                                                                approvals,
                                                                                                                                provider
                                                                                                                                reconciliation,
                                                                                                                                and judge testing
  -----------------------------------------------------------------------------------------------------------------------------------------------

**Only-we statement:** Pactra turns a natural-language payment request
into a traceable business operation: policy decision, reservation, human
review when required, sandbox execution, ledger posting, and
receipt---all in one workspace.

**10-second wow:** Ask "Send Ada \$125 for freelance work"; Pactra
explains why approval is required, reserves the test funds, sends the
payout through PayPal Sandbox when configured, reconciles its provider
status, and shows the ledger-backed receipt.

**Novelty risk:** The general "AI agent + spending limits + approval"
concept is not novel by itself. Win on complete product quality,
correctness under failure/concurrency, meaningful PayPal integration,
and a clear live end-to-end demonstration.

## 5. Goals, success metrics and judging map

### Product goals

1.  Every judge can create an isolated account and exercise all product
    features without configuring local credentials.
2.  Sandbox balances remain correct under retries, concurrent requests,
    approvals, provider delays, failures and reversals.
3.  Policy decisions are deterministic, explainable, versioned and
    enforced server-side.
4.  Manual and AI-created payment requests share the same application
    service and lifecycle.
5.  PayPal Sandbox Payouts is used in a real, inspectable payout path;
    the internal sandbox rail guarantees a complete deterministic path.

### Success metrics

-   100% of P0 E2E journeys pass in CI and on the deployed judge build.
-   Zero duplicate ledger postings under retry/concurrency tests.
-   Zero cross-user data access in authorization tests.
-   Judge can complete onboarding → payment → approval → receipt in
    under 3 minutes.
-   Every transaction state transition has a durable audit event.
-   At least one Payouts API sandbox batch is created and reconciled in
    the deployed judge environment before submission.
-   No live PayPal endpoint or real-money credential is accepted by the
    public deployment.

### Judging map

Stage One is a pass/fail viability screen: the project must fit the
theme and reasonably apply required APIs/SDKs. Stage Two criteria are
equally weighted (20% each) per [official
rules](https://paypalaihackathon.devpost.com/rules).

  ------------------------------------------------------------------------
  Criterion                                   Weight Exact feature/demo
                                                     moment
  --------------------- ---------------------------- ---------------------
  Technological                                  20% Gemini function
  Implementation                                     calling → typed
                                                     transaction service →
                                                     deterministic policy
                                                     → PayPal Sandbox
                                                     Payouts / internal
                                                     ledger →
                                                     reconciliation and
                                                     audit

  Design                                         20% Complete finance
                                                     workspace with
                                                     onboarding, wallet,
                                                     policy editor,
                                                     approval queue, AG
                                                     Grid transaction
                                                     history, receipt and
                                                     recovery states

  Potential Impact                               20% SMB operations lead
                                                     delegates payments
                                                     without handing the
                                                     model payment
                                                     authority; policies
                                                     and human approvals
                                                     constrain every
                                                     action

  Innovation/Idea                                20% Persistent user-owned
                                                     sandbox treasury plus
                                                     explainable
                                                     governance and
                                                     provider-state
                                                     reconciliation,
                                                     rather than a
                                                     scripted AI payment
                                                     demo

  Presentation                                   20% Live judge flow
                                                     demonstrates
                                                     auto-approval, PayPal
                                                     sandbox payout,
                                                     approval/rejection,
                                                     policy block, receipt
                                                     and reset in under 3
                                                     minutes
  ------------------------------------------------------------------------

### Sponsor-prize map

  ---------------------------------------------------------------------------
  Prize             Requirement       How Pactra meets it   Demo location
  ----------------- ----------------- --------------------- -----------------
  Best Use of AG    Use AG Grid       AG Grid Community is  Transactions page
  Grid              tools; official   used as the real      and receipt
  (1st/2nd/3rd)     rules list        transaction           drill-in
                    \$5,000 / \$2,000 operations grid with  
                    / \$1,000 awards  sorting, filtering,   
                                      status/category       
                                      columns, selection    
                                      and row-to-receipt    
                                      navigation; no        
                                      decorative grid       

  Best Use of       Eligible          Gemini function       Assistant →
  PayPal + AI       submission        calling creates       approval → PayPal
  Honorable Mention meaningfully uses governed payout       sandbox batch →
  (\$5,000)         PayPal and AI     requests; PayPal      receipt
                                      Sandbox Payouts       
                                      executes/reconciles   
                                      approved payout       
                                      requests              
  ---------------------------------------------------------------------------

Prize amounts and eligibility are from [official rules, Section
8](https://paypalaihackathon.devpost.com/rules). The primary target is
Grand Prize + AG Grid sponsor prize; the PayPal + AI Honorable Mention
is an alternative overall prize path, subject to the rules' combination
limits. A prize outcome is not guaranteed.

## 6. Scope

### 6.1 MVP (must ship)

1.  Multi-user registration, login, logout and session persistence
    (US-01).
2.  Per-user sandbox wallet, initial issuance, top-ups and reset
    (US-02).
3.  Per-user policy CRUD, validation and version history (US-03).
4.  Manual payment/payout request form with rail selection (US-04).
5.  Gemini assistant using the current Google Gen AI SDK and typed
    tools, plus deterministic fallback (US-05).
6.  Deterministic policy evaluation, reservations and race-safe budget
    enforcement (US-06).
7.  Approval queue with atomic approve/reject and policy re-evaluation
    (US-07).
8.  Append-only ledger, transaction state machine, idempotency, retry
    and reversal (US-08).
9.  Filterable transaction history, receipts, policy trace and audit
    timeline (US-09).
10. Self-serve judge onboarding, guided scenarios, reset and operational
    health (US-10).
11. CI, integration/E2E/concurrency/security tests and stable deployment
    (US-11).
12. Real PayPal Sandbox Payouts API integration for payout requests,
    provider-status reconciliation and clear sandbox rail labeling
    (US-12). This is a hackathon requirement, not a stretch feature.
13. AG Grid Community is used meaningfully on the transaction history
    page (sponsor-prize target).

### 6.2 Stretch (only after Definition of Done)

1.  PayPal Orders v2 Sandbox Checkout as a separate sandbox
    wallet-funding path; credit the ledger only after server-verified
    capture. This is not required for P0 and must not be confused with
    payout execution.
2.  CSV export.
3.  Team members and reviewer roles beyond account owner.
4.  Scheduled/recurring payment requests that still pass through policy
    and approval.
5.  PayPal webhooks with signature verification; polling reconciliation
    remains the required baseline.

### 6.3 Explicit non-goals

-   Real-money execution or production PayPal endpoints: unsafe and
    outside hackathon scope.
-   Crypto/on-chain funds: not part of this web2 product.
-   Bank linking, KYC or card storage: unnecessary for test funds.
-   Arbitrary model-generated code or scripts: unsafe and irrelevant.
-   Multi-currency ledger: USD only for MVP.
-   AI-generated policy changes: policy mutations require explicit user
    confirmation.
-   Anonymous payment execution: all money actions require an
    authenticated user.
-   Treating PayPal Orders as an outbound payout API: vendor/contractor
    disbursements use PayPal Payouts; Orders are only a future
    checkout/funding path.

## 7. User stories and acceptance criteria

### US-01 --- Account access (P0)

As a judge, I want my own account so my data is isolated. - Given a
valid email and password, when I register, then an account and sandbox
wallet are created and I land on onboarding/dashboard. - Given an
existing account, when I sign in, then I receive a secure session and
see only my data. - Given invalid credentials, when I sign in, then the
API returns a generic error and no account information is leaked. -
Given a logged-out user, when they request protected data, then the API
returns 401 and the UI redirects to sign-in.

### US-02 --- Sandbox funds (P0)

As a judge, I want test funds so I can exercise payments. - Given a new
account, then it receives an initial balance of 1,000.00 USD sandbox
units. - Given my wallet, when I top up using an allowed preset, then a
credit ledger entry is created and balance increases exactly once. -
Given an invalid or repeated idempotency key, then no duplicate credit
is created. - Given another user's wallet ID, when I request it, then
the API returns 404.

### US-03 --- Policy management (P0)

As an operator, I want editable rules. - Given a valid policy, when I
save it, then the policy version increments and is used for new
requests. - Given an invalid limit/category, when I save, then inline
validation explains the issue and nothing changes. - Given existing
pending approval, when the policy changes, then approval re-evaluates
against the current policy and records the policy version used. -
Default policy: daily limit 500 USD; per-transaction cap 150 USD;
approval required above 100 USD; allowed categories ops, software,
cloud, freelance; default category budgets ops 150, software 200, cloud
100, freelance 150; blocked vendors empty.

### US-04 --- Manual payment request (P0)

-   Given valid vendor, amount, category and reason, when submitted,
    then a transaction is created and policy evaluated.
-   Given amount \<= 0, \> 2 decimal places, invalid category or missing
    recipient, then validation blocks submission.
-   Given a policy-blocked request, then it is persisted as blocked with
    a human-readable rule reason and no funds are moved.

### US-05 --- AI payment request (P0)

-   Given a supported natural-language request, when sent, then the
    agent extracts vendor, amount, currency, category, reason and
    recipient where required and calls the same transaction service as
    the manual form.
-   Given Gemini is unavailable, then the deterministic parser handles
    supported patterns or returns a clear "couldn't parse" message with
    a link to the manual form.
-   Given ambiguous amount/recipient/category, then the agent asks for
    clarification and does not create a transaction.
-   Given prompt injection in user text, then the agent cannot bypass
    server-side validation, policy, auth or ledger rules.

### US-06 --- Policy decisions (P0)

-   Given an unsupported category, blocked vendor, over-cap amount,
    daily limit breach or category budget breach, then the request is
    blocked with the first matching rule and no debit.
-   Given an eligible request below approval threshold, then it executes
    automatically.
-   Given an eligible request above approval threshold, then it enters
    pending approval and reserves funds.
-   Given concurrent requests, then policy and available balance checks
    are serialized/transactional so limits cannot be exceeded.

### US-07 --- Approval workflow (P0)

-   Given a pending request, when an authorised owner approves, then the
    request transitions atomically to executing and executes once.
-   Given a pending request, when rejected, then it becomes rejected,
    releases its reservation and records reviewer/reason.
-   Given a stale pending request after policy change, then approval
    re-evaluates current policy and rejects/blocks or requests fresh
    approval if required.
-   Given two simultaneous approvals, then exactly one succeeds and the
    other receives a conflict response.

### US-08 --- Sandbox ledger (P0)

-   Given an executable request, then funds are reserved/debited
    atomically and the ledger balances.
-   Given a definitive provider/sandbox execution failure, then the
    reservation is released and history remains auditable. If PayPal
    reports success but the local capture commit fails, keep the
    transaction executing with provider success recorded and let
    reconciliation retry the ledger capture idempotently; never release
    the hold or submit another payout.
-   Given a retry with the same idempotency key, then the original
    transaction/result is returned without a second debit.
-   Given a reversal action on a completed internal-sandbox transaction,
    then a compensating ledger entry is created; original entries are
    immutable. A completed PayPal Sandbox payout cannot be manually
    reversed through Pactra's Payouts adapter; reject that action with
    `PROVIDER_REVERSAL_UNSUPPORTED`. If PayPal later reports `RETURNED`,
    `REVERSED` or `REFUNDED`, reconciliation posts one compensating
    credit and records the provider outcome.

### US-09 --- Transaction history and receipt (P0)

-   Given transactions, then the list is paginated and filterable by
    state, category, date and vendor.
-   Given a transaction, when opened, then detail shows lifecycle,
    policy checks, amount, recipient, rail, ledger entries and
    timestamps.
-   Given no transactions, then an empty state explains how to make a
    first payment.
-   Given an API failure, then the view shows a recoverable error and
    retry action.

### US-10 --- Judge readiness (P0)

-   Given a new judge account, then seeded onboarding guidance explains
    the sandbox and test funds.
-   Given the judge selects "Reset sandbox", then only that user's test
    balance and policy reset after confirmation; a new sandbox
    generation begins, immutable ledger entries and receipts remain,
    pending requests are cancelled/released, and reset is blocked during
    unresolved provider execution. The current-generation view and spend
    counters are clean while all-history remains accessible.
-   Given the public deployment, then the internal sandbox rail is
    available to every judge and the PayPal Sandbox Payouts adapter uses
    only server-side sandbox credentials; judges never enter API secrets
    and no live PayPal credential or endpoint is accepted.
-   Given the app starts, then health endpoint reports database
    readiness and configured AI/payment mode without exposing secrets.

### US-11 --- Quality gate (P0)

-   Given the repository, then backend tests, frontend lint/build and
    Playwright E2E pass.
-   Given a migration, then a clean database can be migrated and seeded
    from documented commands.
-   Given a public deployment, then smoke tests verify register, login,
    wallet, policy, payment, approval and history.

### US-12 --- PayPal Sandbox payout execution (P0)

As an operations lead, I want an approved payout to execute through
PayPal Sandbox so that Pactra demonstrates a real provider integration
without real money. - Given sandbox credentials are configured, when an
approved payout uses the PayPal Sandbox rail, then Pactra creates one
Payouts batch using a stable transaction-derived idempotency
reference. - Given PayPal reports the batch as processing, then Pactra
keeps the transaction in executing/provider-pending state and keeps the
ledger reservation active. - Given the payout item reports success, then
Pactra posts the ledger capture exactly once and marks the transaction
completed. - Given the payout fails or is denied, then Pactra releases
the reservation, persists the provider failure and shows a recoverable
failure state. - Given PayPal is unavailable or credentials are absent,
then Pactra does not claim provider success; the user can select the
internal sandbox rail and complete the same governed flow. - Given a
judge account, then the app server uses configured sandbox credentials
and exposes a preconfigured sandbox recipient shortcut; judges do not
need to enter API secrets or discover recipient test-account details.
The assistant uses the internal rail unless the user explicitly requests
PayPal Sandbox.

## 8. Feature specifications

### F-01 Authentication and account

Purpose: isolate users and persist sessions. - Register with email and
password; normalise email to lowercase and trim. - Password length
12--128 characters; reject breached/common passwords if a maintained
local list is available, otherwise enforce length and complexity of at
least 3 character classes. - Hash with Argon2id using a maintained
library; never store plaintext. - Use opaque server-side sessions in an
HttpOnly, Secure, SameSite=Lax cookie. Rotate session on login and
privilege changes. Session lifetime 7 days, idle expiry 24 hours. -
Login rate limit: 5 attempts per account/IP per 15 minutes; registration
10/IP/hour. - Messages: "Account created. Your sandbox wallet is
ready.", "Email or password is incorrect.", "You've been signed out." -
Analytics: `auth.registered`, `auth.login_succeeded`,
`auth.login_failed`, `auth.logout`.

### F-02 Wallet and test funds

-   New account receives 1,000.00 USD test funds through a balanced
    journal: debit `sandbox_issuance`, credit the user's wallet ledger
    account.
-   Top-up presets: 100, 500, 1,000 USD; max 5 top-ups per hour and
    10,000 total credited per account. Each top-up posts a balanced
    journal: debit `sandbox_issuance`, credit the user's wallet ledger
    account.
-   Top-up requires confirmation and uses a generated idempotency key;
    repeated request returns prior result.
-   Balance displayed as available, reserved and total. Never derive
    balance from client state.
-   Copy: "Sandbox funds only. No real money is moved."; "Test funds
    added"; "Top-up limit reached. Try again later."
-   Analytics: `wallet.viewed`, `wallet.topup_started`,
    `wallet.topup_completed`, `wallet.reset`.

### F-03 Policy editor

-   Fields: daily limit, per-transaction limit, approval threshold,
    allowed categories, category budgets, blocked vendors.
-   Limits are USD decimal values with max 2 decimal places, \>0 except
    threshold may be 0; max 1,000,000.
-   Category slug regex `^[a-z][a-z0-9_-]{1,31}$`; unique
    case-insensitive.
-   Vendor names trimmed, 1--100 chars; case-insensitive matching.
-   Category budgets must exist for each allowed category; budget totals
    may exceed daily limit but runtime enforcement uses both.
-   Save creates a policy version snapshot. Audit actor, old/new JSON
    and timestamp.
-   Copy: "Policy saved"; "Category budget must be greater than zero";
    "At least one category is required."
-   Analytics: `policy.updated`, `policy.validation_failed`.

### F-04 Payment request

-   Inputs: vendor/recipient display name (1--100), amount
    (0.01--100,000.00), currency fixed USD, category, reason (1--500),
    recipient identifier optional for vendor payment and required for
    payout (valid email for PayPal Sandbox payout).
-   Payment types: `vendor_payment`, `payout`, `sandbox_transfer`.
    Rails: `internal_sandbox` for deterministic internal execution;
    `paypal_sandbox_payouts` for payout only. The manual form exposes
    the rail selector only for payout requests and only when provider
    status is configured. The PayPal rail offers a 'Use configured
    sandbox recipient' action backed by `PAYPAL_TEST_RECIPIENT_EMAIL`,
    plus a validated freeform recipient field. AI-created payouts
    default to `internal_sandbox`; the model may set
    `paypal_sandbox_payouts` only when the user explicitly requests
    PayPal Sandbox execution. The assistant must not silently switch
    rails after a provider error.
-   Create request through one service irrespective of source (manual or
    AI).
-   Every request gets UUID and client-generated idempotency key.
-   No client-supplied user ID, policy decision, status, balance or
    execution result is trusted.
-   Copy: "Payment request created"; "This payment is blocked by your
    policy"; "Review required before funds move."
-   Analytics: `payment.requested`, `payment.blocked`,
    `payment.pending_approval`, `payment.auto_executed`.

### F-05 AI assistant

-   Gemini is server-only and uses `google-genai==2.23.0` with stable
    model `gemini-3.8-flash`. The existing `google-generativeai` SDK is
    deprecated and the configured `gemini-2.0-flash` model is shut down;
    migrate rather than preserving the legacy path. Sources: [Google Gen
    AI SDK](https://pypi.org/project/google-genai/) and [current model
    catalogue](https://ai.google.dev/gemini-api/docs/models). Tool
    schema is strict and uses the same validated transaction service as
    the manual form.
-   Allowed tools: `create_payment_request` (including optional `rail`
    enum `internal_sandbox`/`paypal_sandbox_payouts`),
    `get_wallet_summary`, `get_policy_summary`,
    `list_recent_transactions`, `get_transaction_details`. The model may
    choose the PayPal rail only when the user explicitly says PayPal
    Sandbox; otherwise server defaults to internal sandbox. No direct
    ledger mutation or policy update tool.
-   Tool calls require authenticated user context injected server-side;
    model cannot specify user ID.
-   System prompt must state that user content and external data are
    untrusted; policy/ledger are authoritative.
-   Max 8 model/tool turns per request, 8,000 input characters, 2,000
    output tokens, 20 requests/minute/user.
-   Deterministic fallback supports: "pay \[vendor\] \$\[amount\] for
    \[reason\]" and "send \$\[amount\] to \[email\] for \[reason\]". If
    parse is ambiguous, no transaction is created.
-   Copy: "I couldn't identify the amount or recipient. Use the payment
    form or clarify your request."; "AI is temporarily unavailable; you
    can still create a payment using the form."
-   Analytics: `assistant.message_sent`, `assistant.tool_called`,
    `assistant.fallback_used`, `assistant.error`.

### F-06 Policy engine

Evaluation order: 1. Account/wallet active and currency supported. 2.
Category allowed. 3. Vendor not blocked. 4. Amount \<= per-transaction
cap. 5. Current-day committed + reserved spend + amount \<= daily limit.
6. Category committed + reserved spend + amount \<= category budget. 7.
Available wallet funds \>= amount. 8. If amount \> approval threshold,
require approval; otherwise execute. - Use Decimal or integer cents
only. Never use float for money. - Policy evaluation and reservation
occur in one DB transaction with appropriate row locks/serializable
semantics. For SQLite, use write transaction and busy timeout;
production uses PostgreSQL. - Return stable reason codes:
`CATEGORY_NOT_ALLOWED`, `VENDOR_BLOCKED`, `TRANSACTION_LIMIT_EXCEEDED`,
`DAILY_LIMIT_EXCEEDED`, `CATEGORY_BUDGET_EXCEEDED`,
`INSUFFICIENT_FUNDS`, `APPROVAL_REQUIRED`. - Every evaluation stores
policy version and ordered checks.

### F-07 Approval queue

-   List pending requests ordered oldest first; show requester, vendor,
    amount, category, reason, policy result, available balance, created
    time.
-   Approve/reject requires owner or configured reviewer role.
-   Approval re-evaluates limits, wallet funds and policy version.
    Reserve must exist and be valid.
-   State transition uses conditional update
    `pending_approval → executing`; only one caller wins.
-   Reject requires optional reason up to 300 chars; releases
    reservation.
-   Copy: "Payment approved and completed"; "Payment rejected"; "This
    request was already actioned"; "Policy changed. Review the updated
    decision before approving."
-   Analytics: `approval.approved`, `approval.rejected`,
    `approval.conflict`.

### F-08 Ledger and transaction lifecycle

-   Ledger is authoritative, append-only and double-entry. Each
    `ledger_journal` groups at least two `ledger_entries`; total debit
    cents must equal total credit cents before commit. User wallet
    balance is sum of credits minus debits on its `ledger_account`;
    available = posted balance - active holds.
-   Ledger entries use integer cents, USD, direction `debit`/`credit`,
    journal ID, account ID, transaction ID through journal, and created
    timestamp. Reservations are held in `fund_reservations`, not counted
    as posted ledger entries. A release closes a reservation and emits
    an audit event; it does not create a posted debit/credit.
-   System accounts: `sandbox_issuance` (counter-account for explicitly
    issued test funds) and `sandbox_clearing` (counter-account for
    governed outgoing sandbox payments). Every posting is a balanced
    journal: initial credit/top-up/reset increase = debit issuance +
    credit user wallet; payment capture = debit user wallet + credit
    clearing; refund/reversal/reset decrease = debit clearing or
    wallet + credit wallet or issuance as appropriate. Test-fund
    issuance is never presented as real cash.
-   Transaction states: `draft`, `pending_approval`, `executing`,
    `completed`, `blocked`, `rejected`, `failed`, `cancelled`,
    `reversed`.
-   State transitions:
    -   draft → pending_approval \| executing \| blocked
    -   pending_approval → executing \| rejected \| blocked \| cancelled
    -   executing → completed \| failed
    -   completed → reversed
    -   failed → executing only through explicit retry with new attempt
        and same business idempotency key protection
-   Do not mark a transaction completed until the rail outcome is
    definitive and the internal ledger capture commits. For PayPal
    Payouts, batch `PENDING` or `PROCESSING` is not success; even batch
    `SUCCESS` requires inspecting the individual payout item until its
    state is known. External provider state is stored separately from
    Pactra transaction state.
-   Failed execution releases hold and records failure code. Completed
    reversal creates compensating ledger entry.
-   Store request payload snapshot, policy evaluation snapshot,
    execution attempts, rail reference, failure code and audit events.
-   Analytics: `transaction.state_changed`, `ledger.posted`,
    `transaction.reversed`.

### F-09 History and receipts

-   Default list newest first, 25/page, max 100/page.
-   Filters: status, category, type, vendor substring, date range (max
    90 days).
-   Receipt includes Pactra transaction ID, sandbox label, amount,
    recipient/vendor, category, reason, policy decision, execution
    state, ledger impact, timestamps and external sandbox reference if
    present.
-   CSV export stretch only.
-   Analytics: `transaction.list_filtered`,
    `transaction.receipt_viewed`.

### F-10 Judge controls

-   "Reset sandbox" requires typing `RESET` in confirmation modal;
    restores the wallet's posted test balance to 1,000 USD using an
    immutable `reset_adjustment` journal, resets policy to defaults,
    cancels non-executing pending requests and releases their holds,
    increments `wallet.sandbox_generation`, and records a reset audit
    event. It does not delete ledger entries, completed receipts, or
    PayPal provider records.
-   Reset is disabled while any transaction is `executing` or has a
    non-terminal PayPal provider status. Historical transactions remain
    visible and auditable. The dashboard/history defaults to the current
    generation; an "All runs" filter exposes prior generations. Policy
    spend counters use only the current generation so judges can repeat
    guided tests without old runs consuming budgets.
-   "Run guided test" launches a checklist of actual transactions:
    auto-approved payment, approval-required internal payout, PayPal
    Sandbox payout to the configured recipient, blocked over-limit
    payment, rejected approval, insufficient funds. Each run uses the
    current sandbox generation.
-   Guided scenarios are actual transactions, not fake UI states.
-   Analytics: `judge.guided_test_started`, `judge.reset_confirmed`.

### F-11 PayPal Sandbox Payouts integration (P0)

Purpose: demonstrate a real PayPal Developer Platform interaction for
governed vendor/contractor disbursements while remaining sandbox-only.

-   Use PayPal Payouts REST API v1 from the backend only. OAuth uses
    client-credentials flow with sandbox app credentials. Base URL must
    be exactly `https://api-m.sandbox.paypal.com`; reject any live host
    at startup in `APP_ENV=production`.
-   API operations: `POST /v1/payments/payouts` to create a payout
    batch; `GET /v1/payments/payouts/{payout_batch_id}` to reconcile
    batch and item status. Official docs: [Payouts
    overview](https://developer.paypal.com/payouts/overview/), [Create
    payout
    request](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/create_payout_request/),
    [Show payout
    batch](https://developer.paypal.com/api/payments.payouts-batch/v1/payouts-get/),
    [Sandbox
    testing](https://developer.paypal.com/sandbox-testing/overview/).
-   Use one payout item per Pactra transaction in MVP. For attempt 1,
    `sender_batch_header.sender_batch_id` is
    `pactra-{transaction_uuid}-a1`; `sender_item_id` is
    `pactra-{transaction_uuid}`. Use `PayPal-Request-Id` with the same
    stable attempt reference where supported. For network
    timeout/5xx/unknown outcome, retry the same attempt with the same
    sender batch/request IDs so PayPal deduplicates it. After a
    definitive terminal failure and an explicit user retry, create
    attempt N+1 with a new sender batch ID; never create a new batch
    while the prior attempt is unresolved. PayPal documents duplicate
    sender batch IDs as rejected for 30 days and safe same-ID retries
    for 5xx: [sender batch
    header](https://developer.paypal.com/api/payments.payouts-batch/v1/definitions/sender_batch_header/).
-   Request shape:

``` json
{
  "sender_batch_header": {
    "sender_batch_id": "pactra-550e8400-e29b-41d4-a716-446655440000-a1",
    "email_subject": "Pactra sandbox payout",
    "email_message": "Sandbox payment initiated by Pactra"
  },
  "items": [
    {
      "recipient_type": "EMAIL",
      "amount": { "value": "125.00", "currency": "USD" },
      "receiver": "sandbox-recipient@example.com",
      "note": "Freelance work payment",
      "sender_item_id": "pactra-550e8400-e29b-41d4-a716-446655440000"
    }
  ]
}
```

-   Validate recipient email and amount server-side. Do not include user
    identity or policy decisions in PayPal request fields beyond the
    necessary transaction reference/note.
-   Lifecycle: internal reservation → create payout batch → store batch
    ID/status → poll/reconcile → if item `SUCCESS`, ledger capture and
    transaction `completed`; if batch `DENIED`/`CANCELED` or item
    `FAILED`/`BLOCKED`, release hold and transaction `failed`; if batch
    `PENDING`/`PROCESSING` or item `PENDING`/`UNCLAIMED`/`ONHOLD`, keep
    reservation and transaction `executing`. A batch-level `SUCCESS` is
    not enough: inspect the item. If a previously successful item later
    becomes `RETURNED`/`REVERSED`/`REFUNDED`, post one compensating
    credit and mark the transaction `reversed` with the provider
    outcome.
-   Reconciliation: run a DB-backed worker every 20 seconds for
    executing PayPal payout transactions; also reconcile on transaction
    detail refresh. Stop polling only after a terminal item state. After
    15 minutes without a definitive status, keep transaction status
    `executing`, keep the reservation active, show the derived UI label
    `Provider pending`, and offer manual refresh; never invent a
    separate persisted `provider_pending` transaction status or release
    funds on an unknown provider outcome.
-   Provider failure before a batch ID is returned is treated as an
    unknown outcome if request transmission may have occurred. Retry
    only with the same provider idempotency reference and query by
    batch/sender reference where supported.
-   The internal sandbox rail remains available for vendor payments and
    for payout tests when PayPal Sandbox is unavailable. UI must show
    the rail actually used. Internal sandbox outcomes must never be
    labelled as PayPal transactions. Explicitly disclose: Pactra
    test-wallet funds are a simulated governance ledger; provider-side
    PayPal Sandbox payouts are sent by the configured PayPal sandbox
    business account. The two sandbox balances are not linked at PayPal.
    Pactra posts its own ledger capture only after provider success to
    record the governed test transaction.
-   User-visible copy: "PayPal Sandbox payout submitted"; "PayPal is
    processing this payout"; "PayPal Sandbox payout completed"; "PayPal
    Sandbox payout failed"; "PayPal Sandbox is not configured. Use the
    internal sandbox rail or contact the operator." Display a persistent
    note: "Pactra wallet funds are simulated. PayPal Sandbox payouts are
    sent by Pactra's configured sandbox business account; no real money
    moves."
-   Analytics: `paypal.payout_submitted`, `paypal.payout_reconciled`,
    `paypal.payout_failed`, `paypal.integration_unavailable`.
-   Security: credentials stay server-side; sandbox host allowlist is
    enforced; provider response bodies are redacted before logs;
    recipient email is masked in general logs.

## 9. Information architecture: screen and route inventory

  -----------------------------------------------------------------------------------------------------------------------------------------
  Route                                 Screen            Auth       Purpose                Key components   Data               Rendering
  ------------------------------------- ----------------- ---------- ---------------------- ---------------- ------------------ -----------
  `/`                                   Marketing/entry   No         Explain product and    Wordmark,        Public config      Client
                                                                     route to sign-up       concise product                     
                                                                                            statement,                          
                                                                                            sandbox notice,                     
                                                                                            sign-up/login                       
                                                                                            CTAs                                

  `/sign-up`                            Registration      No         Create account         Email/password   Auth API           Client
                                                                                            form, validation                    

  `/sign-in`                            Login             No         Authenticate           Form, error      Auth API           Client
                                                                                            state                               

  `/app`                                Overview          Yes        Wallet, spend, pending App shell,       Wallet, policy,    Client
                                                                     approvals, recent      balance card,    transactions       
                                                                     activity               spend chart,                        
                                                                                            activity list                       

  `/app/payments/new`                   New payment       Yes        Manual payment request Payment form     Policy, wallet     Client

  `/app/assistant`                      Assistant         Yes        Natural-language       Chat, tool       Conversation,      Client
                                                                     payment requests       outcome cards    transactions       

  `/app/approvals`                      Approvals         Yes        Review pending         Approval         Pending            Client
                                                                     requests               table/cards,     transactions       
                                                                                            detail drawer                       

  `/app/transactions`                   Transaction       Yes        Search/filter          Data table,      Transactions       Client
                                        history                      transactions           filters,                            
                                                                                            pagination                          

  `/app/transactions/:id`               Receipt/detail    Yes        Inspect lifecycle and  Receipt,         Transaction,       Client
                                                                     audit                  timeline, policy ledger, events     
                                                                                            trace                               

  `/app/policies`                       Policy settings   Yes        Configure controls     Policy editor    Current            Client
                                                                                                             policy/version     

  `/app/wallet`                         Wallet            Yes        Balance and test-fund  Balance, top-up, Wallet, ledger     Client
                                                                     actions                reset                               

  `/app/settings`                       Account settings  Yes        Profile, session,      Account form,    User               Client
                                                                     sandbox controls       logout                              

  `/app/settings/integrations/paypal`   PayPal Sandbox    Yes        Show provider          Integration      Client             
                                        integration                  configuration/health   status API                          
                                                                     and last payout                                            
                                                                     reconciliation; never                                      
                                                                     expose credentials                                         

  `/health`                             Health            No         Liveness/readiness     JSON             DB                 Server
                                                                                                             readiness/config   
                                                                                                             mode               

  `*`                                   Not found         No/Yes     Recover from bad route 404, home/app    None               Client
                                                                                            link                                

  Error boundary                        Global error      No/Yes     Recover from render    Error message,   Error context      Client
                                                                     errors                 retry                               
  -----------------------------------------------------------------------------------------------------------------------------------------

No sitemap/robots is required for the authenticated app. Public `/` may
be indexed; all `/app/*` routes must be `noindex`.

## 10. User flows

### Onboarding

1.  Judge opens `/`.
2.  Selects "Create sandbox account".
3.  Registers with email/password.
4.  Backend creates user, default policy, wallet and 1,000 USD sandbox
    issuance ledger entry in one transaction.
5.  Redirect to `/app`; onboarding card explains test funds and links to
    guided test.
6.  User may top up, edit policy or create first payment.

### Core payment loop

1.  User enters payment in manual form or assistant.
2.  Backend validates request and creates transaction/idempotency
    record.
3.  Policy engine evaluates against current policy, reserved/committed
    spend and wallet funds.
4.  Blocked request is persisted with reason; no reservation/debit.
5.  Approval-required request reserves funds and appears in queue.
6.  Auto-approved request transitions to executing.
7.  The selected rail executes. Internal sandbox rail returns a
    deterministic sandbox result; PayPal Sandbox Payouts creates a
    provider batch and remains executing until reconciliation reaches a
    terminal item state.
8.  On definitive success, ledger capture commits atomically; on
    definitive failure, the hold is released. Unknown provider outcomes
    keep the hold active.
9.  Transaction state, provider reference, audit events, wallet and
    history refresh from the server.
10. Receipt shows policy trace, ledger entries, actual rail and provider
    state.

### Judge demo path

1.  Register a fresh judge account.
2.  Show 1,000 USD test balance.
3.  Create an auto-approved \$49 software payment.
4.  Show completed state, reduced available balance and receipt.
5.  Request \$125 freelance payout; show pending approval.
6.  Approve it; show completed and updated balance.
7.  Attempt \$185 cloud payment; show blocked by transaction cap.
8.  Edit policy threshold or budget and show the updated policy version.
9.  Open history and audit timeline.
10. Submit a payout using the PayPal Sandbox rail; show the provider
    batch reference and reconciled state. If the sandbox provider is
    unavailable, show the integration status and complete the same
    scenario on the internal sandbox rail without mislabelling it.
11. Reset sandbox and verify clean baseline.

### Error recovery

-   AI unavailable → manual form remains available.
-   API unavailable → visible banner and retry; do not optimistically
    claim payment success.
-   Duplicate submit → return original request/result.
-   Payment execution fails → release reservation, persist failure and
    allow safe retry.
-   Stale approval → show conflict and refresh request.
-   Session expires → preserve safe draft form data locally only,
    redirect to sign-in, then restore draft after login.

## 11. Design brief

### 11.1 Direction

**Direction:** Finance operations console, not chatbot demo.\
Mood: precise, calm, credible.\
Concept: dense but legible finance workspace with a clear transaction
hierarchy, restrained colour and explicit state labels.

References: - Linear: https://linear.app --- borrow keyboard-friendly
navigation and compact information hierarchy. - Stripe Dashboard:
https://dashboard.stripe.com --- borrow financial data clarity and
transaction detail structure. - Ramp: https://ramp.com --- borrow
finance workflow framing and approval context. - Mercury:
https://mercury.com --- borrow calm account/balance presentation. -
Vercel: https://vercel.com --- borrow disciplined layout and status
clarity.

Avoid: AI chat as the entire product; fake live badges; glowing
gradients; glassmorphism; giant hero + three cards; decorative charts
with no underlying data; ambiguous green "approved" state before
execution; emoji icons; fake provider logos; "live funds" wording.

### 11.2 Design tokens

Typography: use system UI stack for reliability and no external font
dependency in MVP; mono stack for IDs/amount metadata. If adding a web
font, use a licensed self-hosted font and document its source/license.
Scale: `xs 12/16`, `sm 13/18`, `base 14/20`, `md 16/24`, `lg 18/28`,
`xl 22/28`, `2xl 28/34`, `display 36/42`. Weights: 400, 500, 600, 700.

``` css
:root {
  --bg: #f5f6f8;
  --surface-1: #ffffff;
  --surface-2: #f9fafb;
  --surface-3: #eef1f5;
  --border: #dfe3e8;
  --border-strong: #c4cbd4;
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --text-muted: #6b7280;
  --accent: #1457d9;
  --accent-foreground: #ffffff;
  --success: #16794b;
  --warning: #9a5b00;
  --danger: #b42318;
  --info: #175cd3;
  --focus-ring: #2563eb;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.06);
}
```

Contrast requirement: text/background combinations must meet WCAG 2.2 AA
(4.5:1 normal text, 3:1 large text and non-text controls). Do not claim
exact ratios until checked with an automated contrast tool.

Tailwind theme extension:

``` js
// Extend existing Tailwind 3 config; retain current config format.
theme: {
  extend: {
    colors: {
      canvas: "var(--bg)",
      surface: { DEFAULT: "var(--surface-1)", muted: "var(--surface-2)", raised: "var(--surface-3)" },
      border: { DEFAULT: "var(--border)", strong: "var(--border-strong)" },
      ink: { DEFAULT: "var(--text-primary)", secondary: "var(--text-secondary)", muted: "var(--text-muted)" },
      brand: { DEFAULT: "var(--accent)", foreground: "var(--accent-foreground)" },
      state: { success: "var(--success)", warning: "var(--warning)", danger: "var(--danger)", info: "var(--info)" }
    },
    borderRadius: { sm: "6px", md: "10px", lg: "14px" },
    spacing: { "18": "4.5rem", "22": "5.5rem" },
    boxShadow: { subtle: "var(--shadow-sm)" }
  }
}
```

Spacing: 4px base; 4, 8, 12, 16, 20, 24, 32, 40, 48, 64.\
Radius: 6, 10, 14; pills only for compact status labels.\
Borders: 1px standard, 2px focus.\
Elevation: mostly flat surfaces, subtle shadow only for menus/dialogs.\
Z-index: base 0, sticky 10, dropdown 20, overlay 40, modal 50, toast
60.\
Breakpoints: 640, 768, 1024, 1280px. Content max width 1440px.\
Motion: 120ms control, 180ms panel, 220ms page; ease
`cubic-bezier(.2,.8,.2,1)`. Animate opacity/transform only. Respect
`prefers-reduced-motion`; no animated money counters or success
confetti.\
Icons: existing Lucide React, 18px inline, 20px nav, 16px table; 1.75px
stroke.\
Theme: light default. Dark mode is stretch only.

### 11.3 Page-by-page layout specs

-   `/`: narrow centered content, wordmark top-left, headline "Payment
    requests, governed.", supporting copy "AI-assisted requests. Rules
    you control. Sandbox funds only.", primary CTA "Create sandbox
    account", secondary "Sign in"; bottom strip explains policy →
    approval → ledger. Mobile stacks vertically.
-   `/sign-up`: centered 420px form card, heading "Create your Pactra
    account", fields Email and Password, CTA "Create account", link
    "Already have an account? Sign in", sandbox notice. Inline
    validation and password reveal.
-   `/sign-in`: same frame, heading "Welcome back", CTA "Sign in", link
    to registration.
-   `/app`: left sidebar 240px (Overview, New payment, Assistant,
    Approvals with count, Transactions, Policies, Wallet, Settings); top
    bar breadcrumb, sandbox environment label and user menu. Main:
    wallet balance + available/reserved; quick actions; spend by
    category; pending approvals; recent transactions. On mobile sidebar
    becomes drawer and cards stack.
-   `/app/payments/new`: title "New payment"; form sections Recipient,
    Amount, Category, Reason; policy preview panel with current limits
    and likely decision; CTA "Submit payment request". Confirmation
    summary before final submit for amounts \>= threshold.
-   `/app/assistant`: split layout with conversation and contextual
    panel; starter prompts; assistant messages and tool result cards;
    input hint "Describe a payment or ask about your budget...";
    explicit sandbox banner; link to manual payment. Mobile contextual
    panel becomes collapsible.
-   `/app/approvals`: title "Needs your review"; count; filters; rows
    show vendor, amount, category, reason, requester, policy check, age;
    detail drawer with Approve and Reject. Reject opens reason field.
-   `/app/transactions`: title "Transactions"; search/filter toolbar;
    table columns Date, Vendor/Recipient, Type, Category, Amount,
    Status, Rail; row opens receipt. Mobile uses stacked cards.
-   `/app/transactions/:id`: receipt header with status, transaction ID
    copy control, sandbox badge; summary amount/vendor/category;
    lifecycle timeline; policy evaluation; ledger impact; execution
    reference; actions limited to retry failed or reverse completed
    sandbox transaction with confirmation.
-   `/app/policies`: title "Spending policy"; top summary of policy
    version; sections General limits, Category budgets, Allowed
    categories, Blocked vendors, Approval threshold; sticky save bar
    with dirty-state indicator; reset-to-default requires confirmation.
-   `/app/wallet`: available/reserved/total; top-up presets and custom
    amount (10--1,000); ledger history; reset sandbox panel with
    destructive confirmation.
-   `/app/settings`: account email, password change, active
    session/logout; sandbox mode explanation; reset action.
-   Error/404: clear title, explanation and CTA back to Overview or
    home.
-   All routes: loading skeleton matches content geometry; errors
    include retry; no fake chart data.

### 11.4 States

-   Dashboard loading: skeleton balance, chart bars and 5 activity rows.
-   Empty transactions: "No transactions yet" / "Create your first
    sandbox payment".
-   Empty approvals: "You're all caught up."
-   Empty policy vendor list: "No vendors are blocked."
-   Empty assistant: starter prompts plus manual payment CTA.
-   API failure: "We couldn't load this data. Check your connection and
    try again."
-   Payment success: "Payment completed in sandbox."
-   Pending: "Waiting for approval. Funds are reserved until this
    request is actioned."
-   Blocked: show exact rule reason and link to policy.
-   Failed: "Payment failed. No funds were spent." only after ledger
    confirms hold release.
-   Top-up: "Sandbox funds added. No real money moved."
-   Session expired: "Your session expired. Sign in to continue."
-   Partial data: show available sections with per-section error, not a
    blank dashboard.
-   No wallet/network states are not applicable to web2.

### 11.5 Brand assets

Wordmark: "Pactra" in a compact geometric sans, paired with a simple
two-line/checkmark motif suggesting policy and execution. Avoid
shield/chain imagery. Favicon: monochrome mark, 32×32 SVG. OG image:
1200×630, off-white background, wordmark, headline "Payment requests,
governed.", small transaction decision/ledger visual; no fake metrics.
PWA icon is stretch; if implemented, use 192×192 and 512×512 variants.

## 12. Component inventory

  --------------------------------------------------------------------------------------------------------------------------------------------------------------
  Component             Path                                                Base              Props          Variants/states               Used on
  --------------------- --------------------------------------------------- ----------------- -------------- ----------------------------- ---------------------
  AppShell              `frontend/src/components/AppShell.tsx`              Custom            children,      desktop/mobile                App routes
                                                                                              activeRoute                                  

  SidebarNav            `frontend/src/components/SidebarNav.tsx`            Custom + Lucide   activeRoute,   expanded/drawer               App shell
                                                                                              pendingCount                                 

  PageHeader            `frontend/src/components/PageHeader.tsx`            Custom            title,         standard                      All app pages
                                                                                              description,                                 
                                                                                              actions                                      

  StatusBadge           `frontend/src/components/StatusBadge.tsx`           Existing/custom   status         all lifecycle states          Tables/detail

  Money                 `frontend/src/components/Money.tsx`                 Custom            cents,         positive/negative             Wallet/transactions
                                                                                              currency                                     

  WalletSummary         `frontend/src/components/WalletSummary.tsx`         Custom            wallet         loading/error                 Overview/wallet

  PaymentForm           `frontend/src/components/PaymentForm.tsx`           Custom            policy,        pristine/invalid/submitting   New payment
                                                                                              onSubmit                                     

  PolicyEditor          `frontend/src/components/PolicyEditor.tsx`          Existing refactor policy, onSave dirty/saving/error            Policies

  ApprovalPanel         `frontend/src/components/ApprovalPanel.tsx`         Custom            transaction,   pending/conflict              Approvals
                                                                                              actions                                      

  TransactionTable      `frontend/src/components/TransactionTable.tsx`      AG Grid Community rows, filters, loading/empty/error           History
                                                                            31.3.4, custom    column state                                 
                                                                            cell renderers                                                 

  TransactionTimeline   `frontend/src/components/TransactionTimeline.tsx`   Custom            events         complete/failed               Detail

  ReceiptView           `frontend/src/components/ReceiptView.tsx`           Custom            transaction    states                        Detail

  AssistantChat         `frontend/src/components/Chat.tsx`                  Existing refactor messages, send loading/error/empty           Assistant

  ToolResultCard        `frontend/src/components/ToolResultCard.tsx`        Custom            result         success/blocked/pending       Assistant

  ConfirmDialog         `frontend/src/components/ConfirmDialog.tsx`         Custom accessible title, body,   open/busy                     Destructive actions
                                                                            dialog            confirm                                      

  ToastProvider         `frontend/src/components/ToastProvider.tsx`         Custom            ---            success/error/info            App

  ErrorBoundary         `frontend/src/components/ErrorBoundary.tsx`         React             children       error                         App

  FormField             `frontend/src/components/FormField.tsx`             Custom            label, error,  valid/invalid                 Forms
                                                                                              children                                     

  EmptyState            `frontend/src/components/EmptyState.tsx`            Custom            title, body,   ---                           Data views
                                                                                              action                                       

  LoadingSkeleton       `frontend/src/components/LoadingSkeleton.tsx`       Custom            variant        ---                           Data views
  --------------------------------------------------------------------------------------------------------------------------------------------------------------

## 13. Tech stack (exact versions)

Use these direct dependency versions for this implementation. The
existing frontend lockfile versions are preserved where indicated; the
backend additions are pinned in `requirements.txt` and
`requirements-dev.txt`. Do not perform unrelated major upgrades.

  ----------------------------------------------------------------------------------------------------------------------------------
  Layer         Choice                        Exact version Why                     Source checked
  ------------- ---------------------- -------------------- ----------------------- ------------------------------------------------
  Runtime       Python                              3.11.10 Existing Render runtime Existing `render.yaml`
                                                            and backend             
                                                            compatibility           

  API           FastAPI                             0.162.0 Backend API             https://pypi.org/project/fastapi/

  ORM           SQLModel                             0.0.47 Typed SQL persistence   https://pypi.org/project/sqlmodel/

  SQL toolkit   SQLAlchemy                           2.0.50 Transaction/locking     https://pypi.org/project/SQLAlchemy/
                                                            layer                   

  Validation    Pydantic                             2.14.2 Typed schemas and       https://pypi.org/project/pydantic/
                                                            validation              

  Settings      pydantic-settings                    2.16.2 Environment             https://pypi.org/project/pydantic-settings/
                                                            configuration           

  ASGI server   Uvicorn                              0.54.0 API server              https://pypi.org/project/uvicorn/

  HTTP client   httpx                                0.28.1 PayPal REST calls and   https://pypi.org/project/httpx/
                                                            API tests               

  AI SDK        google-genai                         2.23.0 Current Google Gen AI   https://pypi.org/project/google-genai/
                                                            SDK; replaces           
                                                            deprecated              
                                                            `google-generativeai`   

  AI model      Gemini 3.8 Flash         `gemini-3.8-flash` Function calling and    https://ai.google.dev/gemini-api/docs/models
                                                     stable intent parsing          

  Email         email-validator                       2.3.0 Registration and payout https://pypi.org/project/email-validator/
  validation                                                recipient validation    

  Password      argon2-cffi                          25.1.0 Argon2id password       https://pypi.org/project/argon2-cffi/
  hashing                                                   hashing                 

  Migrations    Alembic                              1.20.1 Database schema         https://pypi.org/project/alembic/
                                                            migrations              

  PostgreSQL    psycopg\[binary\]                     3.3.6 Production PostgreSQL   https://pypi.org/project/psycopg/
  driver                                                                            

  Backend tests pytest                                9.2.0 Unit/integration tests  https://pypi.org/project/pytest/

  Async tests   pytest-asyncio                  1.4.1.post1 Async API/provider      https://pypi.org/project/pytest-asyncio/
                                                            tests                   

  Frontend      Node.js                             22.23.2 Build and dev runtime   https://nodejs.org/en/download
  runtime                                                                           

  Frontend      React / React DOM                    18.3.1 Existing app            `frontend/package-lock.json`

  Routing       react-router-dom                     7.18.5 Explicit route handling https://www.npmjs.com/package/react-router-dom

  Build         Vite                                 5.4.21 Existing lockfile       `frontend/package-lock.json`

  Language      TypeScript                            5.7.3 Strict typed UI         `frontend/package-lock.json`

  Styling       Tailwind CSS                         3.4.19 Existing styling system `frontend/package-lock.json`

  Grid          AG Grid Community                    31.3.4 Real transaction        `frontend/package-lock.json`;
                                                            operations grid;        https://www.ag-grid.com/react-data-grid/
                                                            sponsor-prize target    

  Icons         lucide-react                        0.468.0 Existing icon set       `frontend/package-lock.json`

  Frontend      Zod                                   4.6.7 API/form validation     https://www.npmjs.com/package/zod
  validation                                                                        

  E2E           @playwright/test                     1.64.1 Judge journeys          https://www.npmjs.com/package/@playwright/test

  Lint          ESLint                               9.39.5 Existing lockfile       `frontend/package-lock.json`

  React plugin  @vitejs/plugin-react                  4.7.0 Existing lockfile       `frontend/package-lock.json`

  Payment       PayPal Payouts REST                REST API Sandbox payout          https://developer.paypal.com/payouts/overview/
  integration   API v1                                      execution and           
                                                            reconciliation          

  Database      PostgreSQL production;   PostgreSQL managed Durable persistence and https://www.postgresql.org/docs/
                SQLite local/test       by host; SQLite for transactional           
                                                local tests concurrency             

  Web3          Not applicable: web2                    --- No contracts or wallet  ---
                build                                       integration             
  ----------------------------------------------------------------------------------------------------------------------------------

The current `google-generativeai` Python SDK is deprecated and its
support ended 30 November 2025; the existing `gemini-2.0-flash` model is
listed as shut down. Migration to `google-genai` and `gemini-3.8-flash`
is mandatory. Sources: [legacy SDK
notice](https://pypi.org/project/google-generativeai/) and [Gemini model
catalogue](https://ai.google.dev/gemini-api/docs/models).

## 14. Architecture

``` mermaid
flowchart LR
  Browser[React/Vite judge workspace] -->|HTTPS + session cookie| API[FastAPI]
  API --> Auth[Auth/session service]
  API --> Agent[Google Gen AI adapter]
  API --> Tx[Transaction application service]
  Tx --> Policy[Deterministic policy engine]
  Tx --> Ledger[Atomic sandbox ledger]
  Tx --> Rail[Payment rail selector]
  Rail --> Internal[Internal deterministic sandbox rail]
  Rail --> PP[PayPal Sandbox Payouts REST API]
  PP --> OAuth[PayPal OAuth client credentials]
  Auth --> DB[(PostgreSQL)]
  Policy --> DB
  Ledger --> DB
  Tx --> DB
  Agent --> DB
  PP --> Reconcile[Provider reconciliation worker]
  Reconcile --> DB
```

Request lifecycle: authenticated request → schema validation →
idempotency lookup → transaction record → deterministic policy
evaluation and reservation in one DB transaction → approval or execution
→ selected rail → definitive rail result/reconciliation → ledger capture
or reservation release → transaction state/audit event → response. AI
function calls are requests for typed application actions; the server
executes them. Gemini never receives PayPal credentials and cannot
mutate the ledger or policy directly.

PayPal payout lifecycle: policy-approved payout → reservation → PayPal
Payouts batch create → provider batch/item IDs and statuses persisted →
poll batch/item status → item `SUCCESS` captures Pactra test funds;
definitive batch/item failure releases reservation. Batch
`PENDING`/`PROCESSING` and item `PENDING`/`UNCLAIMED`/`ONHOLD` are
non-terminal. Batch `SUCCESS` is not enough without item inspection.
Current PayPal item statuses include `SUCCESS`, `FAILED`, `PENDING`,
`UNCLAIMED`, `ONHOLD`, `BLOCKED`, `RETURNED`, `REFUNDED` and `REVERSED`;
map each explicitly in the adapter. Unknown outcomes keep the
reservation until reconciliation resolves them.

Rendering: authenticated screens are client-rendered SPA routes. API
responses use `Cache-Control: no-store`. Public landing is static.
PostgreSQL uses transactions and row-level locking/conditional updates
for wallet reservations, policy budget enforcement and approval state
transitions. SQLite is supported only for local/test single-process
execution.

## 15. Folder structure

``` text
Pactra-main/
├── backend/
│   ├── main.py                 # FastAPI app and route registration
│   ├── config.py               # Typed environment settings
│   ├── database.py             # Engine, session, migrations
│   ├── models.py               # SQLModel persistence entities
│   ├── schemas.py              # Pydantic request/response contracts
│   ├── auth.py                 # Passwords, sessions, dependencies
│   ├── services/
│   │   ├── accounts.py         # Account/wallet lifecycle
│   │   ├── ledger.py           # Append-only ledger and reservations
│   │   ├── transactions.py     # Payment lifecycle application service
│   │   ├── policies.py         # Policy CRUD/versioning/evaluation
│   │   └── audit.py            # Audit event creation
│   ├── rails/
│   │   ├── base.py             # PaymentRail protocol
│   │   ├── sandbox.py          # Deterministic internal sandbox rail
│   │   └── paypal.py           # PayPal Sandbox Payouts adapter and status reconciliation
│   ├── agent.py                # Gemini orchestration and tool schemas
│   ├── policy_engine.py        # Pure deterministic policy evaluator
│   ├── migrations/              # Alembic migrations
│   ├── worker.py                # Provider reconciliation loop
│   ├── seed.py                  # Demo seed command
│   ├── reset_sandbox.py         # Per-user reset command/service
│   └── tests/
│       ├── test_auth.py
│       ├── test_ledger.py
│       ├── test_policy_engine.py
│       ├── test_transactions.py
│       ├── test_approvals.py
│       ├── test_api_authz.py
│       └── test_agent.py
├── frontend/
│   ├── playwright.config.ts      # Starts backend/frontend and defines baseURL
│   ├── tests/e2e/                # Browser journeys
│   ├── src/
│   │   ├── api.ts               # Typed API client
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/              # Route-level screens
│   │   ├── components/          # Reusable UI components
│   │   ├── hooks/               # Query/session hooks
│   │   ├── types/               # API domain types
│   │   └── styles/              # Tokens and global styles
│   ├── package.json
│   └── package-lock.json
├── tests/
│   └── e2e/                     # Playwright judge journeys
├── .env.example
├── README.md
└── render.yaml                   # Deployment blueprint if Render remains selected
```

## 16. Data model and schema

Use PostgreSQL in deployed environments and Alembic migrations. Money is
integer cents. Every top-level user-owned record includes `user_id`;
child records without a direct owner field must be queried through an
owner-scoped parent join. IDs are UUID strings.

### Tables

-   `users`: `id UUID PK`, `email VARCHAR(254) UNIQUE NOT NULL`,
    `password_hash TEXT NOT NULL`, `created_at TIMESTAMPTZ NOT NULL`,
    `status VARCHAR(16) NOT NULL DEFAULT 'active'`.
-   `sessions`: `id UUID PK`, `user_id FK users`,
    `token_hash BYTEA UNIQUE`, `created_at`, `expires_at`,
    `last_seen_at`, `revoked_at NULL`, index `(user_id, expires_at)`.
-   `ledger_accounts`: `id UUID PK`, `user_id UUID NULL FK`,
    `code VARCHAR(64) UNIQUE`, `account_type VARCHAR(24)`
    (`user_wallet`, `sandbox_issuance`, `sandbox_clearing`),
    `currency CHAR(3)='USD'`, `created_at`; user_wallet requires
    user_id; system accounts have null user_id. Seed one issuance and
    one clearing account per currency.
-   `wallets`: `id UUID PK`, `user_id FK UNIQUE`,
    `ledger_account_id UUID UNIQUE FK ledger_accounts`,
    `currency CHAR(3) DEFAULT 'USD'`,
    `sandbox_generation INTEGER NOT NULL DEFAULT 1`, `created_at`,
    `status`.
-   `ledger_journals`: `id UUID PK`, `user_id FK`,
    `transaction_id UUID NULL FK`, `journal_type VARCHAR(32)`,
    `idempotency_key VARCHAR(128)`, `status VARCHAR(16)='posted'`,
    `created_at`; unique `(user_id,idempotency_key)`; indexes
    `(user_id,created_at DESC)`, `(transaction_id)`.
-   `ledger_entries`: `id UUID PK`, `journal_id FK ledger_journals`,
    `account_id FK ledger_accounts`, `direction VARCHAR(8)`
    (`debit`/`credit`), `amount_cents BIGINT CHECK >0`,
    `currency CHAR(3)='USD'`, `created_at`; index
    `(account_id,created_at)`, `(journal_id)`. Journal balance is
    enforced by ledger service before commit and a deferred PostgreSQL
    constraint trigger.
-   `fund_reservations`: `id UUID PK`, `user_id FK`, `wallet_id FK`,
    `transaction_id UUID FK`, `amount_cents BIGINT CHECK >0`,
    `status VARCHAR(16)`, `created_at`, `released_at NULL`; multiple
    released/captured reservations may exist per transaction across
    retries, but a partial unique index allows at most one active
    reservation per transaction.
-   `policies`: `id UUID PK`, `user_id FK`, `version INT`,
    `policy_json JSONB`, `created_at`, `created_by`; unique
    `(user_id,version)`, index `(user_id,version DESC)`.
-   `transactions`: `id UUID PK`, `user_id FK`,
    `idempotency_key VARCHAR(128)`, `type VARCHAR(24)`,
    `vendor VARCHAR(100)`, `recipient VARCHAR(254) NULL`,
    `amount_cents BIGINT CHECK >0`, `currency CHAR(3)`,
    `category VARCHAR(32)`, `reason VARCHAR(500)`, `status VARCHAR(24)`,
    `sandbox_generation INTEGER NOT NULL`, `policy_version INT`,
    `policy_result JSONB`, `rail VARCHAR(32)`,
    `rail_reference VARCHAR(128) NULL`,
    `provider_batch_id VARCHAR(128) NULL UNIQUE`,
    `provider_item_id VARCHAR(128) NULL`,
    `provider_status VARCHAR(32) NULL`, `failure_code VARCHAR(64) NULL`,
    `created_at`, `updated_at`, `completed_at NULL`; unique
    `(user_id,idempotency_key)`; indexes `(user_id,created_at DESC)`,
    `(user_id,status)`, `(user_id,category)`, `(provider_batch_id)`.
-   `transaction_attempts`: `id UUID PK`, `transaction_id FK`,
    `attempt_number INT`, `rail VARCHAR(32)`,
    `rail_request_id VARCHAR(128)`,
    `provider_batch_id VARCHAR(128) NULL UNIQUE`,
    `provider_item_id VARCHAR(128) NULL`,
    `provider_status VARCHAR(32) NULL`, `status VARCHAR(24)`,
    `response_code VARCHAR(64) NULL`, `started_at`, `finished_at NULL`;
    unique `(transaction_id,attempt_number)`; index
    `(provider_batch_id)` and `(status,started_at)`. Store only
    sanitized provider metadata, never credentials or raw full response
    bodies.
-   `approval_actions`: `id UUID PK`, `transaction_id FK`, `user_id FK`,
    `idempotency_key VARCHAR(128)`, `action VARCHAR(16)`,
    `reason VARCHAR(300) NULL`, `policy_version INT`, `created_at`;
    unique `(user_id,idempotency_key)`.
-   `audit_events`: `id UUID PK`, `user_id FK`,
    `actor_type VARCHAR(16)`, `actor_id UUID NULL`,
    `entity_type VARCHAR(32)`, `entity_id UUID`,
    `event_type VARCHAR(64)`, `payload JSONB`, `created_at`; indexes
    `(user_id,created_at DESC)`, `(entity_type,entity_id)`.
-   `conversations`: `id UUID PK`, `user_id FK`, `created_at`,
    `updated_at`.
-   `conversation_messages`: `id UUID PK`, `conversation_id FK`,
    `role VARCHAR(16)`, `content TEXT`, `tool_calls JSONB NULL`,
    `created_at`; index `(conversation_id,created_at)`.

### Canonical PostgreSQL schema

The following is the migration's required logical schema. Alembic may
express it through SQLModel metadata, but it must preserve these types,
constraints and indexes.

``` sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(254) NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash BYTEA NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_sessions_user_expiry ON sessions(user_id, expires_at);

CREATE TABLE ledger_accounts (
  id UUID PRIMARY KEY,
  user_id UUID NULL REFERENCES users(id) ON DELETE CASCADE,
  code VARCHAR(64) NOT NULL UNIQUE,
  account_type VARCHAR(24) NOT NULL CHECK (account_type IN ('user_wallet','sandbox_issuance','sandbox_clearing')),
  currency CHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK ((account_type = 'user_wallet' AND user_id IS NOT NULL) OR (account_type IN ('sandbox_issuance','sandbox_clearing') AND user_id IS NULL))
);

CREATE TABLE wallets (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  ledger_account_id UUID NOT NULL UNIQUE REFERENCES ledger_accounts(id) ON DELETE RESTRICT,
  currency CHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
  status VARCHAR(16) NOT NULL DEFAULT 'active' CHECK (status IN ('active','locked')),
  sandbox_generation INTEGER NOT NULL DEFAULT 1 CHECK (sandbox_generation > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO ledger_accounts (id, user_id, code, account_type, currency) VALUES
  ('00000000-0000-4000-8000-000000000001', NULL, 'sandbox_issuance_usd', 'sandbox_issuance', 'USD'),
  ('00000000-0000-4000-8000-000000000002', NULL, 'sandbox_clearing_usd', 'sandbox_clearing', 'USD');



CREATE TABLE policies (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  version INTEGER NOT NULL CHECK (version > 0),
  policy_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID NULL REFERENCES users(id),
  UNIQUE(user_id, version)
);
CREATE INDEX ix_policies_user_version ON policies(user_id, version DESC);

CREATE TABLE transactions (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  idempotency_key VARCHAR(128) NOT NULL,
  type VARCHAR(24) NOT NULL CHECK (type IN ('vendor_payment','payout','sandbox_transfer')),
  vendor VARCHAR(100) NOT NULL,
  recipient VARCHAR(254) NULL,
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
  category VARCHAR(32) NOT NULL,
  reason VARCHAR(500) NOT NULL,
  status VARCHAR(24) NOT NULL CHECK (status IN ('draft','pending_approval','executing','completed','blocked','rejected','failed','cancelled','reversed')),
  sandbox_generation INTEGER NOT NULL CHECK (sandbox_generation > 0),
  policy_version INTEGER NOT NULL,
  policy_result JSONB NOT NULL,
  rail VARCHAR(32) NOT NULL CHECK (rail IN ('internal_sandbox','paypal_sandbox_payouts')),
  rail_reference VARCHAR(128) NULL,
  provider_batch_id VARCHAR(128) NULL UNIQUE,
  provider_item_id VARCHAR(128) NULL,
  provider_status VARCHAR(32) NULL,
  failure_code VARCHAR(64) NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ NULL,
  UNIQUE(user_id, idempotency_key)
);
CREATE INDEX ix_transactions_user_created ON transactions(user_id, created_at DESC);
CREATE INDEX ix_transactions_user_status ON transactions(user_id, status);
CREATE INDEX ix_transactions_user_category ON transactions(user_id, category);
CREATE INDEX ix_transactions_provider_batch ON transactions(provider_batch_id);

CREATE TABLE ledger_journals (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  transaction_id UUID NULL REFERENCES transactions(id) ON DELETE RESTRICT,
  journal_type VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'posted' CHECK (status = 'posted'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, idempotency_key)
);
CREATE INDEX ix_journals_user_created ON ledger_journals(user_id, created_at DESC);
CREATE INDEX ix_journals_transaction ON ledger_journals(transaction_id);

CREATE TABLE ledger_entries (
  id UUID PRIMARY KEY,
  journal_id UUID NOT NULL REFERENCES ledger_journals(id) ON DELETE RESTRICT,
  account_id UUID NOT NULL REFERENCES ledger_accounts(id) ON DELETE RESTRICT,
  direction VARCHAR(8) NOT NULL CHECK (direction IN ('debit','credit')),
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  currency CHAR(3) NOT NULL DEFAULT 'USD' CHECK (currency = 'USD'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ledger_account_created ON ledger_entries(account_id, created_at DESC);
CREATE INDEX ix_ledger_journal ON ledger_entries(journal_id);

CREATE OR REPLACE FUNCTION reject_ledger_entry_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'posted ledger entries are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_ledger_entries_immutable
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION reject_ledger_entry_mutation();

CREATE OR REPLACE FUNCTION enforce_balanced_ledger_journal() RETURNS trigger AS $$
DECLARE
  target_journal UUID;
  debit_total BIGINT;
  credit_total BIGINT;
  posting_count INTEGER;
BEGIN
  target_journal := COALESCE(NEW.journal_id, OLD.journal_id);
  SELECT
    COALESCE(SUM(CASE WHEN direction = 'debit' THEN amount_cents ELSE 0 END), 0),
    COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_cents ELSE 0 END), 0),
    COUNT(*)
  INTO debit_total, credit_total, posting_count
  FROM ledger_entries
  WHERE journal_id = target_journal;
  IF posting_count < 2 OR debit_total <> credit_total THEN
    RAISE EXCEPTION 'ledger journal % is unbalanced', target_journal;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;
CREATE CONSTRAINT TRIGGER trg_ledger_journal_balanced
AFTER INSERT OR UPDATE OR DELETE ON ledger_entries
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION enforce_balanced_ledger_journal();

CREATE TABLE fund_reservations (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  wallet_id UUID NOT NULL REFERENCES wallets(id) ON DELETE RESTRICT,
  transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
  amount_cents BIGINT NOT NULL CHECK (amount_cents > 0),
  status VARCHAR(16) NOT NULL CHECK (status IN ('active','captured','released')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  released_at TIMESTAMPTZ NULL
);
CREATE INDEX ix_reservations_user_status ON fund_reservations(user_id, status);
CREATE UNIQUE INDEX uq_active_reservation_transaction ON fund_reservations(transaction_id) WHERE status = 'active';

CREATE TABLE transaction_attempts (
  id UUID PRIMARY KEY,
  transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
  attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
  rail VARCHAR(32) NOT NULL,
  rail_request_id VARCHAR(128) NOT NULL,
  provider_batch_id VARCHAR(128) NULL,
  provider_item_id VARCHAR(128) NULL,
  provider_status VARCHAR(32) NULL,
  status VARCHAR(24) NOT NULL,
  response_code VARCHAR(64) NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ NULL,
  UNIQUE(transaction_id, attempt_number),
  UNIQUE(rail_request_id)
);
CREATE INDEX ix_attempts_provider_batch ON transaction_attempts(provider_batch_id);
CREATE INDEX ix_attempts_status_started ON transaction_attempts(status, started_at);

CREATE TABLE approval_actions (
  id UUID PRIMARY KEY,
  transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE RESTRICT,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  idempotency_key VARCHAR(128) NOT NULL,
  action VARCHAR(16) NOT NULL CHECK (action IN ('approved','rejected')),
  reason VARCHAR(300) NULL,
  policy_version INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, idempotency_key)
);

CREATE TABLE audit_events (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  actor_type VARCHAR(16) NOT NULL,
  actor_id UUID NULL,
  entity_type VARCHAR(32) NOT NULL,
  entity_id UUID NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_user_created ON audit_events(user_id, created_at DESC);
CREATE INDEX ix_audit_entity ON audit_events(entity_type, entity_id);

CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE conversation_messages (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role VARCHAR(16) NOT NULL CHECK (role IN ('user','assistant','tool')),
  content TEXT NOT NULL,
  tool_calls JSONB NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_messages_conversation_created ON conversation_messages(conversation_id, created_at);
```

### ER diagram

``` mermaid
erDiagram
  USERS ||--|| WALLETS : owns
  WALLETS ||--|| LEDGER_ACCOUNTS : posts_to
  USERS ||--o{ LEDGER_JOURNALS : owns
  LEDGER_JOURNALS ||--o{ LEDGER_ENTRIES : contains
  LEDGER_ACCOUNTS ||--o{ LEDGER_ENTRIES : receives
  USERS ||--o{ SESSIONS : has
  USERS ||--o{ POLICIES : versions
  USERS ||--o{ TRANSACTIONS : creates
  USERS ||--o{ LEDGER_ENTRIES : owns
  WALLETS ||--o{ LEDGER_ENTRIES : records
  TRANSACTIONS ||--o{ TRANSACTION_ATTEMPTS : executes
  TRANSACTIONS ||--o| FUND_RESERVATIONS : reserves
  TRANSACTIONS ||--o{ APPROVAL_ACTIONS : reviewed
  USERS ||--o{ AUDIT_EVENTS : generates
  USERS ||--o{ CONVERSATIONS : owns
  CONVERSATIONS ||--o{ CONVERSATION_MESSAGES : contains
```

Balance invariant: each wallet's posted balance equals credits minus
debits on its `ledger_account`; available balance equals posted balance
minus active reservations. `ledger_entries` contains immutable postings
only; reservations live in `fund_reservations` and do not alter posted
balance. Every journal has at least two postings and total debits equal
total credits. The ledger service verifies balance before commit, and
PostgreSQL uses a deferred constraint trigger to reject unbalanced
journals. No update/delete of posted journals or entries. Corrections
are compensating journals. All money columns are integer cents with
`CHECK(amount_cents > 0)`. All mutations that affect balance or spend
limits use one DB transaction and user-scoped row locks/conditional
updates.

Provider lifecycle invariant: a transaction may be `executing` while the
PayPal batch is `PENDING`/`PROCESSING` or the item is
`PENDING`/`UNCLAIMED`/`ONHOLD`; it may become `completed` only after the
payout item is `SUCCESS` and the balanced ledger capture journal
commits. A provider timeout with unknown outcome must never release the
reservation automatically.

Migration implementation: use Alembic migrations; initial migration must
create every table above, all foreign keys, unique constraints, indexes,
check constraints, system ledger accounts and PostgreSQL deferred
journal-balance trigger. `alembic upgrade head` must build a clean
database. Migration and ledger-trigger tests run against PostgreSQL in
CI; SQLite is used only for lightweight metadata/unit tests and must not
be treated as production-equivalent for locking/trigger semantics.

## 17. API specification

Base path `/api`. JSON errors use
`{ "error": { "code": "...", "message": "...", "request_id": "..." } }`.
All protected endpoints require session cookie and CSRF protection on
mutations. Rate limits are per authenticated user and IP.

### Auth

-   `POST /api/auth/register` --- unauthenticated, 10/IP/hour. Request
    `{email,password}`. 201
    `{user:{id,email},wallet:{currency,available_cents},sandbox_funds_cents}`.
    Errors 400 `VALIDATION_ERROR`, 409 `EMAIL_EXISTS`, 429
    `RATE_LIMITED`. Side effects: user, wallet, default policy, initial
    credit, audit.
-   `POST /api/auth/login` --- unauthenticated, 5
    attempts/account/IP/15m. Request `{email,password}`. 200
    `{user:{id,email}}`, sets session cookie. Errors 401
    `INVALID_CREDENTIALS`, 429.
-   `POST /api/auth/logout` --- authenticated, revokes session and
    clears cookie. 204.
-   `GET /api/auth/me` --- authenticated. 200 `{user:{id,email}}`; 401.
-   `POST /api/auth/change-password` --- authenticated. Request
    `{current_password,new_password}`. 204; 400/401.

### Wallet

-   `GET /api/wallet` --- authenticated. 200
    `{currency:"USD",available_cents:...,reserved_cents:...,posted_cents:...,sandbox_generation:...}`.
-   `POST /api/wallet/topups` --- authenticated, 5/hour. Request
    `{amount_cents:10000|50000|100000,idempotency_key}`. 201
    `{topup_id,amount_cents,balance}`; 400 `INVALID_TOPUP`, 409
    `IDEMPOTENCY_CONFLICT`, 429.
-   `GET /api/wallet/ledger?cursor=&limit=` --- authenticated. 200
    `{items:[{journal_id,journal_type,transaction_id,wallet_delta_cents,counter_account_label,created_at}],next_cursor}`.
    Return only the user's wallet posting summary; do not expose other
    users or raw system-account rows.
-   `POST /api/wallet/reset` --- authenticated, 2/hour. Request
    `{confirmation:"RESET",idempotency_key}`. 200
    `{reset:true,balance_cents:100000,sandbox_generation:2,history_preserved:true}`;
    generation increments from the current value; 409
    `TRANSACTION_IN_PROGRESS` for any executing or non-terminal provider
    transaction; 400 `CONFIRMATION_REQUIRED`. Reset posts a balanced
    `reset_adjustment` journal to bring posted balance to 100,000 cents
    after releasing cancellable holds; it never deletes immutable
    history.

### Policies

-   `GET /api/policy` --- authenticated. 200 `{id,version,policy}`.
-   `PUT /api/policy` --- authenticated, 20/hour. Request includes
    daily_limit_cents, per_transaction_limit_cents,
    approval_threshold_cents, allowed_categories,
    category_budgets_cents, blocked_vendors. 200 `{version,policy}`; 400
    `POLICY_INVALID`; side effect creates version and audit.
-   `POST /api/policy/reset` --- authenticated. 200 default policy
    version.

### Transactions

-   `POST /api/transactions` --- authenticated, 30/minute. Request
    `{type,vendor,recipient?,amount_cents,currency:"USD",category,reason,rail:"internal_sandbox"|"paypal_sandbox_payouts",idempotency_key}`.
    `paypal_sandbox_payouts` is valid only for `type=payout` and only
    when integration status is configured. 201
    `{transaction,policy_result,balance}`; 400 validation; 409
    idempotency conflict; 422 `POLICY_BLOCKED` (persisted blocked
    transaction body included); 402 `INSUFFICIENT_FUNDS` (persisted
    blocked transaction); 429. Example request:
    `{"type":"payout","vendor":"Ada Contractor","recipient":"sandbox-recipient@example.com","amount_cents":12500,"currency":"USD","category":"freelance","reason":"Contract work","rail":"paypal_sandbox_payouts","idempotency_key":"payout-550e8400e29b41d4a716446655440000"}`.
    Example success:
    `{"transaction":{"id":"550e8400-e29b-41d4-a716-446655440000","status":"pending_approval","rail":"paypal_sandbox_payouts","amount_cents":12500},"policy_result":{"decision":"approval_required"},"balance":{"available_cents":87500,"reserved_cents":12500}}`.
-   `GET /api/transactions?status=&category=&type=&vendor=&from=&to=&generation=current|all&cursor=&limit=`
    --- authenticated. Defaults to the wallet's current
    `sandbox_generation`; `generation=all` includes historical runs. 200
    `{items,next_cursor}`. Spend-summary and policy budget calculations
    always use current generation only, regardless of history filter.
-   `GET /api/transactions/{id}` --- authenticated, owner-only. 200
    `{transaction,policy_checks,ledger_entries,events,attempts}`; 404.
-   `POST /api/transactions/{id}/retry` --- authenticated. Request
    `{idempotency_key}`. Only a definitively failed transaction may be
    retried; 202 `{transaction,attempt}`; 409 `NOT_RETRYABLE`,
    `PROVIDER_OUTCOME_UNKNOWN`, or `INSUFFICIENT_FUNDS`. Re-evaluate
    current policy and wallet funds, create a new attempt and
    reservation, and for PayPal use a new `sender_batch_id` only after
    the prior attempt is terminal-failed. Unknown provider outcomes must
    be reconciled with the same attempt ID, not retried as a new payout.
-   `POST /api/transactions/{id}/reverse` --- authenticated. Completed
    `internal_sandbox` transactions only; request
    `{reason,idempotency_key}`; 201 `{transaction,ledger_journal}`; 409
    `NOT_REVERSIBLE` or `PROVIDER_REVERSAL_UNSUPPORTED` for completed
    PayPal Sandbox payouts. PayPal item states `RETURNED`, `REVERSED` or
    `REFUNDED` are handled only by provider reconciliation and an
    idempotent compensating journal.
-   `GET /api/spend-summary?date=` --- authenticated. 200 category
    totals, committed, reserved, remaining and utilisation.

### Approvals

-   `GET /api/approvals` --- authenticated. 200
    `{items:[pending transaction summaries]}`.
-   `POST /api/approvals/{id}/approve` --- authenticated. Request
    `{idempotency_key}`. 200 `{transaction}`; 404; 409
    `ALREADY_ACTIONED`, `POLICY_CHANGED`, `INSUFFICIENT_FUNDS`.
-   `POST /api/approvals/{id}/reject` --- authenticated. Request
    `{reason?,idempotency_key}`. 200 `{transaction}`; 404/409.

### Assistant

-   `POST /api/chat` --- authenticated, 20/minute. Request
    `{conversation_id?,message}`. 200
    `{conversation_id,reply,tool_calls,transactions_created}`; 400
    validation; 429; 503 `AI_UNAVAILABLE` only if deterministic parser
    also cannot answer. Conversation persisted server-side; client
    history is not accepted.
-   `GET /api/conversations/{id}/messages` --- authenticated owner-only.
    200 `{items}`; 404.

### PayPal integration

-   `GET /api/integrations/paypal/status` --- authenticated. Returns
    `{configured:boolean,environment:"sandbox",capabilities:["payouts"],test_recipient_email:null|string,last_success_at:null|string,last_error_code:null|string}`.
    `test_recipient_email` is the configured sandbox recipient address
    used by the judge shortcut; it is not a secret. Never returns client
    ID, secret, access token or raw provider error.
-   `POST /api/transactions/{id}/reconcile` --- authenticated,
    owner-only; only for transactions with `rail=paypal_sandbox_payouts`
    and `status=executing`. Returns `{transaction,provider_status}`. 404
    if not owned; 409 `NOT_RECONCILABLE` for non-executing/non-PayPal
    transaction; 502 `PROVIDER_UNAVAILABLE` if provider cannot be
    queried. Read-only provider query; no second payout is created.

PayPal provider calls are internal service operations, not public
raw-proxy endpoints. Payout create uses the transaction's stable
idempotency reference. The provider reconciliation worker updates status
only through a conditional transaction-state transition and records an
audit event for every provider state change.

### System

-   `GET /api/health` --- public liveness `{status:"ok"}`.
-   `GET /api/ready` --- public readiness
    `{status:"ready",database:"ok",sandbox_mode:true,paypal_payouts_configured:boolean}`;
    503 if DB unavailable or unsafe live-money configuration is
    detected. A temporary PayPal API outage does not make the internal
    sandbox app unready. Never include secrets or credentials.

Idempotency: every mutating money action requires a key of 16--128
URL-safe characters. Same key + same canonical payload returns original
result; same key + different payload returns 409. API does not trust
client transaction status or policy output.

## 18. Smart contract specification

Not applicable: web2 build.

## 19. Third-party integrations

  ----------------------------------------------------------------------------------------------------------------------------
  Service      Purpose            SDK/version                    Auth          Limits         Failure behaviour  Prize
  ------------ ------------------ ------------------------------ ------------- -------------- ------------------ -------------
  Google       Natural-language   `google-genai==2.23.0`;        Server API    Provider       Manual form and    Required AI
  Gemini API   intent and typed   `gemini-3.8-flash`             key           quota; enforce deterministic      capability
               function calls                                                  per-user       parser remain      
                                                                               request limits usable; no payment 
                                                                                              action is created  
                                                                                              on ambiguous       
                                                                                              intent             

  PayPal       Real sandbox       REST API v1; backend           Sandbox OAuth PayPal sandbox Keep reservation   Required
  Sandbox      payout batch       `httpx==0.28.1`                client        limits and     for unknown        PayPal
  Payouts      creation and                                      credentials   account        status; release    integration
               provider-state                                                  capabilities   only on definitive 
               reconciliation                                                                 failure; internal  
                                                                                              sandbox rail       
                                                                                              remains available  

  AG Grid      Transaction        `ag-grid-community==31.3.4`,   None          Community      Accessible table   Best Use of
  Community    operations grid    `ag-grid-react==31.3.4`                      feature set    fallback only for  AG Grid
                                                                                              runtime failure;   target
                                                                                              primary table uses 
                                                                                              AG Grid            

  PostgreSQL   Durable production `psycopg==3.3.6`               Server        Host plan      Readiness fails if No
  host         DB                                                connection                   DB unavailable; no 
                                                                 string                       silent fallback to 
                                                                                              ephemeral SQLite   

  Render (if   Hosting            Existing blueprint             Deployment    Host plan      Roll back previous Render prize
  retained)                                                      env vars                     deploy;            only if
                                                                                              health/readiness   qualifying
                                                                                              checks             Render tools
                                                                                                                 are actually
                                                                                                                 used; do not
                                                                                                                 claim
                                                                                                                 eligibility
                                                                                                                 from hosting
                                                                                                                 alone
  ----------------------------------------------------------------------------------------------------------------------------

PayPal docs: [Payouts
overview](https://developer.paypal.com/payouts/overview/), [sandbox
testing](https://developer.paypal.com/sandbox-testing/overview/), [API
request
authentication](https://developer.paypal.com/api/make-api-requests).
Gemini docs: [function
calling](https://ai.google.dev/gemini-api/docs/function-calling).

## 20. Environment variables

  ------------------------------------------------------------------------------------------------------------------------------------
  Name                               Required      Scope          Example format                       Where to get it Used in
  ---------------------------------- ------------- -------------- ------------------------------------ --------------- ---------------
  `APP_ENV`                          Yes           Server         `production`                         Deployment      Safety checks
                                                                                                       config          

  `SECRET_KEY`                       Yes           Server         random 32+ bytes                     Secret manager  Sessions/CSRF

  `DATABASE_URL`                     Yes           Server         `postgresql+psycopg://...`           Managed         DB
                                                                                                       PostgreSQL      

  `CORS_ORIGINS`                     Yes           Server         `https://pactra.example`             Deployment      CORS
                                                                                                       domain          

  `FRONTEND_URL`                     Yes           Server         `https://pactra.example`             Deployment      Links
                                                                                                       domain          

  `GEMINI_API_KEY`                   Required for  Server         secret value                         Google AI       AI assistant
                                     public judge                                                      Studio          
                                     deployment;                                                                       
                                     optional                                                                          
                                     local dev                                                                         

  `GEMINI_MODEL`                     No            Server         `gemini-3.8-flash`                   Google model    AI assistant
                                                                                                       catalogue       

  `AI_ENABLED`                       Required      Server         `true`                               Deployment      AI toggle
                                     `true` for                                                                        
                                     public judge                                                                      
                                     deployment;                                                                       
                                     local default                                                                     
                                     `false`                                                                           

  `PAYPAL_PAYOUTS_ENABLED`           Yes           Server         `true`                               Deployment      PayPal rail
                                                                                                                       availability

  `PAYPAL_CLIENT_ID`                 Required when Server         sandbox client ID                    PayPal          OAuth
                                     PayPal                                                            Developer       
                                     enabled                                                           Dashboard       

  `PAYPAL_CLIENT_SECRET`             Required when Server         sandbox secret                       PayPal          OAuth
                                     PayPal                                                            Developer       
                                     enabled                                                           Dashboard       

  `PAYPAL_BASE_URL`                  Yes           Server         `https://api-m.sandbox.paypal.com`   PayPal docs     Sandbox API
                                                                                                                       host; live host
                                                                                                                       rejected

  `PAYPAL_TEST_RECIPIENT_EMAIL`      Required when Server         sandbox recipient email              PayPal          Preconfigured
                                     PayPal                                                            Developer       judge payout
                                     enabled                                                           Dashboard       recipient;
                                                                                                       sandbox account displayed as
                                                                                                                       sandbox test
                                                                                                                       account

  `PAYPAL_MOCK_MODE`                 No            Server/test    `false` in judge deployment          Local/test      Legacy provider
                                                                                                       configuration   mock switch;
                                                                                                                       never labels
                                                                                                                       mock as real
                                                                                                                       PayPal

  `PAYPAL_REQUEST_TIMEOUT_SECONDS`   No            Server         `15`                                 App config      Provider
                                                                                                                       timeout

  `SESSION_COOKIE_SECURE`            Yes           Server         `true`                               Deployment      Session cookie

  `SESSION_TTL_HOURS`                No            Server         `168`                                App config      Session expiry

  `VITE_API_URL`                     No            Build/client   blank for same-origin                Deployment      API client

  `POLICY_CONFIG_PATH`               No            Server         `./backend/policy.json`              Repo            Default policy
                                                                                                                       seed only

  `SEED_DEMO_ACCOUNT`                No            Server         `false`                              Local-only      Local seed
                                                                                                       config          guard
  ------------------------------------------------------------------------------------------------------------------------------------

Full `.env.example`:

``` dotenv
APP_ENV=development
SECRET_KEY=generate-a-random-secret-at-least-32-bytes
DATABASE_URL=sqlite:///./pactra.db
CORS_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
AI_ENABLED=false
PAYPAL_PAYOUTS_ENABLED=false
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
PAYPAL_MOCK_MODE=true
PAYPAL_REQUEST_TIMEOUT_SECONDS=15
SESSION_COOKIE_SECURE=false
SESSION_TTL_HOURS=168
VITE_API_URL=
POLICY_CONFIG_PATH=./backend/policy.json
SEED_DEMO_ACCOUNT=false
```

Production judge deployment must use
`PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com`. Startup must fail if
PayPal is enabled and the host is not the sandbox host.
`PAYPAL_MOCK_MODE=true` is permitted only for local/test environments;
the hosted judge environment must call the actual sandbox API when
PayPal integration is configured.

## 21. Authentication and authorisation

-   Email/password auth with Argon2id and opaque server-side sessions.
-   Session cookie: HttpOnly, Secure in production, SameSite=Lax,
    Path=/, no Domain; rotate on login; revoke on logout/password
    change.
-   CSRF: synchroniser token for mutating requests; require
    `Origin`/`Referer` same-origin validation.
-   Roles MVP: `owner` for account owner; all user-owned operations
    require ownership. Team roles are stretch.
-   Authorisation matrix: user may read/mutate only their user, wallet,
    policy, transaction, conversation and audit records. No user can
    approve another user's transaction.
-   Logged-out judge sees landing, sign-up/sign-in and public health
    only.
-   Add session expiry and logout UI; do not store auth tokens in
    localStorage.

## 22. State management

-   Server state: use the existing typed fetch layer in
    `frontend/src/api.ts` plus route-level hooks; do not add TanStack
    Query in this sprint.
-   Client state: form drafts, open dialogs, chat input and selected
    filters only.
-   Session state comes from `/api/auth/me`; never trust local persisted
    user identity.
-   Mutations invalidate wallet, spend summary, transactions, approvals
    and transaction detail as applicable.
-   Optimistic updates are prohibited for balances and transaction
    completion. Show pending mutation state until server response.
-   URL state: transaction filters and pagination encoded in query
    params.
-   Chat messages persisted server-side; client cache is a view, not
    source of truth.

## 23. Error handling, empty and loading states

Global error boundary catches render errors and offers "Reload page" and
"Go to overview". API errors follow the JSON shape in Section 17. Log
request ID, route, user ID (internal), error code and stack in server
logs; never log passwords, cookies, API keys, full payment recipient
data unnecessarily, or raw AI prompts by default.

  ------------------------------------------------------------------------
  Code                     User message            Recovery
  ------------------------ ----------------------- -----------------------
  `VALIDATION_ERROR`       Check the highlighted   Correct form
                           fields and try again.   

  `INVALID_CREDENTIALS`    Email or password is    Retry
                           incorrect.              

  `EMAIL_EXISTS`           An account with this    Sign in
                           email already exists.   

  `UNAUTHENTICATED`        Your session expired.   Sign in
                           Sign in to continue.    

  `FORBIDDEN`              You don't have access   Return to overview
                           to this item.           

  `POLICY_BLOCKED`         This request is blocked View policy
                           by your spending        
                           policy.                 

  `INSUFFICIENT_FUNDS`     Your available sandbox  Top up
                           balance is too low.     

  `ALREADY_ACTIONED`       This request has        Refresh
                           already been actioned.  

  `IDEMPOTENCY_CONFLICT`   This request key was    Retry with new action
                           used for a different    
                           action.                 

  `AI_UNAVAILABLE`         Assistant is            Open payment form
                           unavailable. You can    
                           still use the payment   
                           form.                   

  `RATE_LIMITED`           Too many requests. Wait Retry after delay
                           a moment and try again. 

  `INTERNAL_ERROR`         Something went wrong.   Retry/check history
                           Your balance has not    
                           been changed unless the 
                           transaction shows       
                           completed.              
  ------------------------------------------------------------------------

Retry policy: GET requests retry up to 2 times with exponential backoff
and jitter. Money mutations are retried only with the same idempotency
key. Never auto-retry a payment with a new key.

## 24. Security

-   OWASP: enforce authentication, ownership checks, schema validation,
    parameterised DB access, safe output encoding, secure cookies, CSRF
    protection, strict CORS, security headers, rate limits and
    dependency scanning.
-   CSP: restrict scripts to self and required Vite production assets;
    no unsafe-inline where avoidable; frame-ancestors none; object-src
    none; base-uri self.
-   HTTPS only in production; HSTS enabled at host.
-   Secrets only in environment/secret manager; no secrets in frontend
    bundle or logs.
-   AI risks: prompt injection cannot alter policy; tools are
    allowlisted; tool arguments validated; user data minimised; model
    cannot access credentials or arbitrary URLs; bounded tool loop and
    rate limits.
-   Payment safety: every execution rail in judge deployment is
    sandbox-only; internal ledger and PayPal Sandbox Payouts are
    allowed. Startup must refuse any non-sandbox PayPal host or
    live-money mode.
-   Concurrency: row locks/conditional state transitions, unique
    idempotency constraints, atomic reservations and ledger posting.
-   Audit events are append-only; admin reset is user-scoped and logged.
-   Public deployment must not expose SQL debug mode, API docs unless
    intentionally enabled, or stack traces.
-   Dependency audit runs in CI; no known critical/high vulnerabilities
    at release.

## 25. Performance

-   LCP \<2.5s, INP \<200ms, CLS \<0.1 on representative deployed
    desktop/mobile.
-   Initial JS target \<350KB gzip; defer AG Grid to transaction route
    if it exceeds budget.
-   API p95 target \<500ms for local DB-backed reads, excluding
    AI/provider calls.
-   Paginate all transaction/audit lists; default 25, max 100.
-   Index user_id + created_at and user_id + status/category.
-   Avoid polling more frequently than 15 seconds; pause polling when
    tab hidden. Prefer explicit refresh or server events if time
    permits.
-   Measure Lighthouse in CI for public landing and authenticated
    dashboard after seeded login.

## 26. Accessibility

-   Target WCAG 2.2 AA.
-   All forms have persistent labels, described errors and keyboard
    access.
-   Dialogs trap focus, close with Escape where safe, return focus to
    trigger.
-   Tables have accessible headers; status is text plus colour, never
    colour alone.
-   Keyboard order follows visual order; skip link to main content.
-   Focus ring visible at least 2px; no focus removal.
-   Screen reader labels for amount, balance, approval buttons and
    status changes.
-   Toasts use `aria-live=polite`; blocking errors use assertive only
    when necessary.
-   Reduced-motion preference disables nonessential transitions.
-   Contrast verified with axe and browser tooling.

## 27. Analytics and observability

First-party events (no third-party tracking required):
`auth.registered`, `auth.login_succeeded`, `wallet.topup_completed`,
`policy.updated`, `payment.requested`, `payment.blocked`,
`payment.pending_approval`, `payment.auto_executed`,
`approval.approved`, `approval.rejected`, `transaction.completed`,
`transaction.failed`, `transaction.reversed`, `assistant.tool_called`,
`judge.guided_test_started`, `judge.reset_confirmed`.

Each event: event ID, user ID, event name, entity ID where relevant,
timestamp, safe properties. Do not log raw prompts or secrets.

Structured logs include request ID, route, status, duration, error code,
transaction ID. Readiness checks database connectivity and required
config.

Three judge-visible metrics: 1. Sandbox payments completed. 2. Requests
blocked by policy. 3. Approvals completed. All metrics derive from
persisted records, not hard-coded counters.

## 28. Testing plan

### Unit

-   Policy evaluator: every rule and boundary, precedence,
    category/vendor case normalisation.
-   Money conversion: cents parsing, rounding rejection, no float use.
-   Ledger: balance invariant, reservations, releases, reversals,
    idempotency.
-   State machine: allowed and forbidden transitions.
-   Auth: password hashing, session expiry/revocation, CSRF.

Coverage target: \>=85% for policy, ledger and transaction services;
\>=75% backend overall.

### Integration

-   Register creates user/wallet/default policy/initial credit
    atomically.
-   Cross-user access returns 404/403.
-   Auto payment debits exactly once.
-   Approval reserves funds and approve/reject transitions correctly.
-   Failure releases reservation.
-   Concurrent requests cannot exceed wallet or policy budgets.
-   Same idempotency key returns same result; payload mismatch
    conflicts.
-   Reset is user-scoped, blocked during executing/unknown provider
    states, preserves immutable transaction/ledger/provider history, and
    restores the balance through a reset-adjustment entry.
-   Gemini failure falls back to parser/manual flow.
-   PayPal Payouts adapter creates a sandbox batch with stable
    sender/request IDs, reconciles item status, captures ledger only on
    terminal success, releases only on terminal failure, and retains
    holds on unknown status.
-   PayPal API timeout/retry does not create a duplicate batch or ledger
    capture.
-   PayPal item `UNCLAIMED`/`ONHOLD` remains executing and reserved;
    item `SUCCESS` captures once; terminal failure releases once; later
    `RETURNED`/`REVERSED`/`REFUNDED` posts one compensating credit.
-   Provider success followed by local DB failure is reconciled to one
    ledger capture after recovery.

### E2E Playwright P0 scripts

1.  Register → wallet shows 1,000 USD → top up 100 → balance 1,100.
2.  Manual \$49 software payment → completed → balance 1,051 → receipt
    visible.
3.  \$125 freelance payout → pending → approve → completed → balance
    reduced.
4.  \$185 cloud request → blocked by transaction cap → no debit.
5.  Reject pending request → reservation released.
6.  Change policy threshold → policy version increments and next request
    follows new threshold.
7.  User A cannot view User B transaction or wallet.
8.  Reset sandbox → balance returns to 1,000 and historical receipts
    preserved and balance restored through a reset-adjustment journal.
9.  AI configured: prompt creates governed request; AI disabled:
    fallback parser/manual CTA works.
10. API unavailable: UI shows recoverable error and does not claim
    payment succeeded.
11. PayPal Sandbox payout: create approved payout using the PayPal rail,
    verify batch reference/status, refresh/reconcile, and assert ledger
    capture occurs only on terminal success.
12. PayPal provider timeout: transaction remains executing with
    reservation held; retry/reconcile does not create a second batch.

### Commands

``` bash
# Backend
python -m pip install -r requirements-dev.txt
alembic upgrade head
pytest -q

# Frontend
cd frontend
npm ci
npm run lint
npm run build

# E2E
cd ..
npx playwright install --with-deps
npx playwright test
```

### Playwright configuration

Create `frontend/playwright.config.ts` with this server orchestration so
local and CI runs exercise the same flow:

``` ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000",
      cwd: "..",
      url: "http://127.0.0.1:8000/api/ready",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: ".",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
    },
  ],
});
```

Add this script to `frontend/package.json`:
`"test:e2e": "playwright test"`.

### CI workflow

``` yaml
name: CI
on:
  push:
  pull_request:
jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: pactra
          POSTGRES_PASSWORD: pactra
          POSTGRES_DB: pactra_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U pactra -d pactra_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://pactra:pactra@localhost:5432/pactra_test
      APP_ENV: test
      SECRET_KEY: ci-only-secret-key-with-at-least-32-bytes
      AI_ENABLED: "false"
      PAYPAL_PAYOUTS_ENABLED: "false"
      PAYPAL_MOCK_MODE: "true"
      PAYPAL_BASE_URL: https://api-m.sandbox.paypal.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11.10"
          cache: pip
      - run: pip install -r requirements-dev.txt
      - run: alembic upgrade head
      - run: pytest -q
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22.23.2"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: cd frontend && npm ci && npm run lint && npm run build
  e2e:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_USER: pactra
          POSTGRES_PASSWORD: pactra
          POSTGRES_DB: pactra_e2e
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U pactra -d pactra_e2e"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgresql+psycopg://pactra:pactra@localhost:5432/pactra_e2e
      APP_ENV: test
      SECRET_KEY: ci-only-secret-key-with-at-least-32-bytes
      AI_ENABLED: "false"
      PAYPAL_PAYOUTS_ENABLED: "false"
      PAYPAL_MOCK_MODE: "true"
      PAYPAL_BASE_URL: https://api-m.sandbox.paypal.com
      VITE_API_URL: http://127.0.0.1:8000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11.10"
          cache: pip
      - uses: actions/setup-node@v4
        with:
          node-version: "22.23.2"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: pip install -r requirements-dev.txt
      - run: alembic upgrade head
      - run: cd frontend && npm ci && npx playwright install --with-deps chromium
      - run: cd frontend && npx playwright test
```

## 29. Seed and demo data

New account baseline: - Sandbox balance: 1,000.00 USD. - Default policy
as specified in US-03. - No fake completed transactions by default;
guided test creates real persisted sandbox transactions.

Optional local seed account only for development: - Email:
`judge@example.test` - Password: generated by seed command and printed
once to local terminal; never enabled on public production. - Seed mode
must be disabled unless `SEED_DEMO_ACCOUNT=true`.

Guided test scenarios: 1. Auto-approved vendor payment: Linear, 49.00
USD, software, monthly subscription. 2. Approval-required internal
payout: Ada Contractor, 125.00 USD, freelance, `ada@example.test`. 3.
PayPal Sandbox payout: 25.00 USD to `PAYPAL_TEST_RECIPIENT_EMAIL`,
selected through the configured recipient shortcut; complete provider
reconciliation and inspect the PayPal batch/item status. 4. Blocked
over-cap request: AWS, 185.00 USD, cloud. 5. Rejected approval:
Contractor, 120.00 USD, freelance. 6. Insufficient funds: reset then
request 1,500.00 USD.

Reset script resets only the authenticated user's sandbox state, returns
balance to 1,000.00 USD, resets policy to defaults, cancels
non-executing pending requests, and records `sandbox.reset`.

## 30. Deployment

-   Deploy backend and frontend to a stable HTTPS host. Render is the
    repository's current target; retain it if managed PostgreSQL and
    persistent configuration are available.
-   Production database: managed PostgreSQL. Do not use SQLite on
    ephemeral disk.
-   Set `APP_ENV=production`,
    `PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com`,
    `PAYPAL_PAYOUTS_ENABLED=true` when sandbox credentials are
    configured, `SESSION_COOKIE_SECURE=true`, strong `SECRET_KEY`, exact
    CORS origins, frontend URL and database URL.
-   PayPal client ID/secret must be sandbox app credentials stored as
    server secrets. Never put them in Vite variables or README.
-   Configure a PayPal sandbox business account with Payouts capability
    and at least one sandbox recipient account. Set its email in
    `PAYPAL_TEST_RECIPIENT_EMAIL` so judges can select the preconfigured
    recipient without guessing or entering provider credentials. Judges
    use the app's server-side integration and do not enter API secrets.
-   Public judge build must keep the internal sandbox rail enabled so
    every P0 product flow remains testable if PayPal sandbox is
    temporarily unavailable. The UI must disclose provider connectivity
    and the actual rail used.
-   If PayPal sandbox credentials cannot be configured, the deployment
    may still run internal sandbox workflows, but the release is not
    submission-ready until the Payouts API smoke test has passed and the
    integration is visibly available.
-   Run Alembic migrations as a release step before app start; fail
    deployment on migration error.
-   Health checks: `/api/health` liveness and `/api/ready` readiness.
    Readiness includes database connectivity and PayPal configuration
    status without exposing secrets.
-   Smoke test after deploy: register, login, top-up, create manual
    payment, create AI request, approve/reject, create PayPal Sandbox
    payout, reconcile provider status, inspect receipt, reset.
-   Rollback: redeploy previous successful backend/frontend build.
    Migrations must be backward-compatible for one release. Never roll
    back by deleting ledger entries.
-   Preview deployments use isolated DB or disabled write mode; do not
    share public judge data.
-   Keep public repository and deployment free of real PayPal
    credentials and real-money configuration.

## 31. README requirements

Update README with project/tagline, live URL, demo video,
problem/solution, complete feature list, architecture diagram, tech
stack, sandbox-only safety statement, local setup commands, environment
variables, migrations, seed/reset, test commands, deployment, API docs
location, known limitations, license and team. Include screenshots/GIF
captured from the working product, not mockups. Explicitly explain the
internal sandbox ledger rail and PayPal Sandbox Payouts integration,
including provider status semantics and the configured judge test
recipient. Provide complete judge instructions and test access. Judges
self-register; do not require a shared app password. The deployment
operator configures the Gemini API key, PayPal Sandbox business app
credentials and sandbox recipient email server-side, then documents the
visible sandbox recipient shortcut. Hackathon submission requires a
public open-source repository with a visible license, a functional demo,
English submission materials, and a public YouTube demo video under 3
minutes. Because Pactra existed before the submission period, the
Devpost description must explain the substantial hackathon-period
updates: multi-user auth, persistent sandbox ledger, atomic policy
reservations, PayPal Sandbox Payouts reconciliation, full judge
workflows and test coverage. Add an MIT `LICENSE` file at repo root.
Source: https://paypalaihackathon.devpost.com/rules.

## 32. Build order: agent task list with checkpoints

Task estimates total 22 hours 15 minutes, leaving 1 hour 45 minutes
inside the 24-hour sprint for integration blockers and final release
verification. Execute tasks in order; do not skip checkpoints.

### T-01 --- Repository audit and baseline

Goal: map current code and preserve existing features. Files: all
backend/frontend files, requirements, package lock, deployment config.
Instructions: inspect existing routes, config, tests, policy engine,
PayPal client, UI; run baseline tests/lint/build; record failures.
Acceptance: baseline report in `IMPLEMENTATION_NOTES.md`; no unrelated
upgrades. Verification: `pytest -q`,
`cd frontend && npm run lint && npm run build`. Dependencies: none.
Estimate: 30 min.

### T-02 --- Database migrations and money model

Goal: replace float/global snapshot accounting with user-owned
cents-based schema. Files: backend/models.py, database.py, new
migrations, config. Instructions: add PostgreSQL support, Alembic,
tables in Section 16, indexes, uniqueness constraints; SQLite remains
local-compatible. Acceptance: clean DB migration and migration tests
pass. Verification: `alembic upgrade head`; schema inspection.
Dependencies: T-01. Estimate: 75 min.

### T-03 --- Auth and account bootstrap

Goal: secure registration/login/session and create user resources.
Files: backend/auth.py, main.py, schemas.py, account service, frontend
auth routes. Acceptance: US-01 and US-02 registration criteria pass;
cross-user tests pass. Verification:
`pytest backend/tests/test_auth.py`. Dependencies: T-02. Estimate: 75
min.

### T-04 --- Ledger service

Goal: append-only sandbox ledger, top-ups, reservations, releases,
captures and reversals. Files: backend/services/ledger.py, models,
tests, wallet endpoints. Acceptance: cents-only calculations;
idempotency; balance invariant; concurrency tests pass. Verification:
`pytest backend/tests/test_ledger.py`. Dependencies: T-02. Estimate: 90
min.

### CHECKPOINT CP-1

Database migrations, auth and ledger tests pass. No payment features
proceed until user isolation and accounting invariants are verified.

### T-05 --- Policy versioning and evaluator

Goal: per-user policy CRUD/versioning and deterministic checks. Files:
policy_engine.py, policy service, policy routes, PolicyPanel refactor.
Acceptance: rule order and policy snapshots match Section 8; versioned
saves. Verification: `pytest backend/tests/test_policy_engine.py`.
Dependencies: T-03, T-04. Estimate: 75 min.

### T-06 --- Transaction application service and state machine

Goal: one service for manual and AI requests, policy reservation,
execution and lifecycle. Files: transaction service, models,
rails/base.py, rails/sandbox.py, main routes. Instructions:
`vendor_payment` and `sandbox_transfer` use the internal sandbox rail in
MVP; `payout` may use `internal_sandbox` or `paypal_sandbox_payouts`. Do
not use PayPal Orders v2 as an outbound payout API. All rail paths share
policy evaluation, reservation, idempotency, state transitions and
audit. Acceptance: auto payment, blocked, pending, failure, retry and
reversal scenarios work; idempotent. Verification:
`pytest backend/tests/test_transactions.py`. Dependencies: T-04, T-05.
Estimate: 120 min.

### T-07 --- Approval workflow

Goal: atomic approve/reject with policy re-evaluation. Files: approval
service/routes, ApprovalPanel, tests. Acceptance: double approval yields
one execution; reject releases hold; policy changes handled.
Verification: `pytest backend/tests/test_approvals.py`. Dependencies:
T-06. Estimate: 75 min.

### CHECKPOINT CP-2

Complete backend lifecycle tests and concurrency tests pass. Inspect
ledger rows for every scenario and verify no duplicate postings.

### T-08 --- API authZ, filtering and receipts

Goal: owner-scoped list/detail/summary and audit timeline. Files:
main.py, schemas.py, services, tests. Acceptance: all endpoints in
Section 17 implemented with exact errors and pagination. Verification:
`pytest backend/tests/test_api_authz.py`. Dependencies: T-06, T-07.
Estimate: 75 min.

### T-09 --- Gemini SDK migration, agent adapter and fallback

Goal: migrate the deprecated Google SDK/model and preserve the manual
path. Files: `backend/agent.py`, config, requirements, chat routes,
frontend Chat. Instructions: replace `google-generativeai` with
`google-genai==2.23.0`; set stable model `gemini-3.8-flash`; implement
strict function declarations; persist conversation server-side; route
every tool through the transaction service; keep deterministic
parser/manual form fallback. Acceptance: no legacy SDK imports or
`gemini-2.0-flash` config remain; tool schema validation and AI failure
fallback pass. Verification: mocked provider tests and manual prompt
E2E. Dependencies: T-06, T-08. Estimate: 75 min.

### T-10 --- Frontend product routes

Goal: convert dashboard demo into full authenticated workspace. Files:
frontend/src/App.tsx, api.ts, components, routes, styles. Acceptance:
every route in Section 9 exists; auth guards; forms;
loading/empty/error/success states; responsive layout. Verification:
lint/build and manual route walkthrough. Dependencies: T-03, T-08.
Estimate: 150 min.

### T-11 --- Wallet, policy, approvals, history UX

Goal: complete judge-operable finance workflows. Files: Wallet, Policy,
Approvals, Transactions, Receipt components/routes. Acceptance: every P0
interaction is wired to API; no decorative controls; balances only
update from server. Verification: E2E scripts 1--8. Dependencies: T-05,
T-07, T-10. Estimate: 120 min.

### CHECKPOINT CP-3

Run complete judge flow against a fresh account. Confirm no fake data,
no console errors and correct balances after each action.

### T-12 --- Judge guided test and reset

Goal: make all feature paths discoverable and repeatable. Files: guided
test UI, reset endpoint/service, seed script, README. Acceptance: judge
can exercise auto, pending, blocked, rejected, insufficient funds and
reset. Verification: guided test E2E. Dependencies: T-11. Estimate: 45
min.

### T-13 --- Security hardening

Goal: rate limits, CSRF, headers, authZ audit, production sandbox guard.
Files: config, middleware, auth, routes, deployment config. Acceptance:
Section 24 checklist; public deployment refuses real-money rail.
Verification: security tests, dependency audit. Dependencies: T-03,
T-08. Estimate: 75 min.

### T-14 --- PayPal Sandbox Payouts integration (P0, do not cut)

Goal: make the hackathon's PayPal requirement a real, judge-visible
interaction. Files: `backend/rails/paypal.py`, `paypal_client.py`,
transaction service, provider worker, config, API routes, integration
status UI, tests, `.env.example`, README. Instructions: implement OAuth
client credentials against sandbox host; create one payout item per
governed payout; stable transaction-derived sender batch/request IDs;
persist batch/item IDs; reconcile status; keep reservations while
processing/unknown; capture only on terminal item success; release only
on terminal failure; expose status and refresh action. Configure
`PAYPAL_TEST_RECIPIENT_EMAIL` for a judge shortcut. Never use live host.
Acceptance: actual sandbox payout smoke test succeeds with configured
sandbox business/recipient accounts; provider failure and timeout tests
preserve ledger invariants; no mock DEMO ID is presented as a PayPal API
transaction. Verification: mocked provider tests plus live sandbox smoke
documented in `IMPLEMENTATION_NOTES.md`. Dependencies: T-06, T-07, T-08.
Estimate: 90 min.

### T-15 --- CI, deployment and documentation

Goal: deploy stable, repeatable judge build. Files: CI workflow,
render.yaml or host config, README, env example. Acceptance: migrations,
CI, health/readiness, smoke tests, production sandbox configuration.
Verification: CI green; public URL smoke test. Dependencies: T-12, T-13.
Estimate: 90 min.

### CHECKPOINT CP-4

Deploy to public URL. Create a new judge account and complete all core
scenarios on the deployed instance.

### T-16 --- Polish and final QA

Goal: accessibility, responsive QA, visual consistency and demo
readiness. Files: UI components/styles, tests, README screenshots.
Acceptance: WCAG checks, Lighthouse budgets, no broken routes, all
empty/error states checked. Verification: `npm run lint`,
`npm run build`, pytest, Playwright, Lighthouse. Dependencies: T-15.
Estimate: 75 min.

### CHECKPOINT CP-5

Final release gate: all P0 acceptance criteria pass on the deployed URL;
verify sandbox-only mode, reset flow and data isolation.

### 32.1 Human blockers

-   Production database provisioning: needed by T-02/T-15. If
    unavailable, local SQLite may be used for development only; do not
    claim durable public use.
-   Gemini API key: required for the public judge deployment to
    demonstrate the hackathon AI requirement; local development and CI
    may use mocks/fallbacks until the owner supplies it.
-   PayPal sandbox business app credentials and a sandbox recipient
    account email: required for T-14 live provider smoke and submission
    readiness. Owner supplies them as server-side deployment
    secrets/config, including `PAYPAL_TEST_RECIPIENT_EMAIL`. Agent
    continues using internal sandbox rail and mocked provider tests
    until owner supplies them; do not claim live sandbox verification
    without it.
-   Domain purchase: optional T-15; use host-provided URL.
-   Hackathon Devpost registration/submission, public repository
    visibility, license metadata, and YouTube video upload are owner
    actions. Rules and equally weighted judging criteria have been
    verified from https://paypalaihackathon.devpost.com/rules.
-   Public deployment access: if credentials are unavailable, prepare
    deployment config and report exact manual step; do not claim
    deployment succeeded.

### 32.2 Cut lines

If behind schedule, cut in this order: 1. PayPal Orders v2 checkout
wallet-funding stretch. 2. CSV export. 3. Dark mode. 4. Team roles. 5.
Scheduled payments. Do not cut PayPal Sandbox Payouts, AI tool calling,
multi-user auth, internal sandbox ledger, policy enforcement, approvals,
transaction history/receipt, reset/guided tests, or P0 E2E coverage.
Minimum submission-ready build includes a deployed public judge
instance, a verified sandbox payout path, and a complete internal
sandbox path.

## 33. Definition of Done

-   [ ] All P0 user stories pass acceptance criteria.
-   [ ] User accounts and data are isolated.
-   [ ] Initial sandbox credit and top-ups are ledger-backed and
    idempotent.
-   [ ] Ledger invariant holds under concurrency, failure, retry and
    reversal.
-   [ ] Policy checks are deterministic, versioned and server-side.
-   [ ] Manual and AI requests use the same transaction service.
-   [ ] Gemini function calling is configured and exercised on the
    deployed judge instance; deterministic fallback remains tested.
-   [ ] Approval and rejection work and cannot be replayed.
-   [ ] All transaction states are persisted and visible.
-   [ ] All routes and loading/empty/error/success states are
    implemented.
-   [ ] No decorative or inert primary controls remain.
-   [ ] Backend tests, frontend lint/build and P0 E2E pass.
-   [ ] Security checks and cross-user access tests pass.
-   [ ] Public deployment uses sandbox-only configuration and durable
    PostgreSQL.
-   [ ] At least one PayPal Sandbox Payouts API transaction has been
    created and reconciled in the deployed environment; judges can
    trigger a new one without entering credentials.
-   [ ] Health/readiness endpoints work.
-   [ ] README, env example, migrations, seed/reset and demo
    instructions are complete.
-   [ ] No console errors or uncaught API errors in core journeys.
-   [ ] Judge can independently test all features without external
    credentials.

### Completeness check

  Section                      Present
  ---------------------------- ---------
  0\. Document control         Y
  1\. Overview                 Y
  2\. Problem                  Y
  3\. Personas                 Y
  4\. Unique angle/prior art   Y
  5\. Goals/metrics/judging    Y
  6\. Scope                    Y
  7\. User stories             Y
  8\. Feature specs            Y
  9\. Routes                   Y
  10\. Flows                   Y
  11\. Design brief            Y
  12\. Components              Y
  13\. Stack                   Y
  14\. Architecture            Y
  15\. Folder structure        Y
  16\. Data model              Y
  17\. API                     Y
  18\. Contracts               Y
  19\. Integrations            Y
  20\. Environment             Y
  21\. Auth                    Y
  22\. State management        Y
  23\. Errors                  Y
  24\. Security                Y
  25\. Performance             Y
  26\. Accessibility           Y
  27\. Observability           Y
  28\. Testing                 Y
  29\. Seed/demo data          Y
  30\. Deployment              Y
  31\. README                  Y
  32\. Build order             Y
  33\. Definition of Done      Y
  34\. Demo script             Y

## 34. Demo script

**0:00--0:10 --- Hook:** Show Pactra overview and say: "This is a
payment workspace where the AI can request payments, but the policy
engine and ledger decide what actually happens. Every dollar here is
sandbox funds."

**0:10--0:30 --- Onboarding/balance:** Register a fresh account or use a
freshly created judge account. Point out the 1,000 USD sandbox balance
and the explicit test-funds label.

**0:30--0:55 --- Auto-approved payment:** Submit "Pay Linear \$49 for
our monthly software subscription." Show policy checks, completed state,
balance decrement and receipt.

**0:55--1:20 --- PayPal Sandbox payout + approval:** Submit a \$125
freelance payout to the configured sandbox recipient using the PayPal
Sandbox rail. Show pending approval and reserved funds, approve it, then
show the provider batch reference and the reconciled provider/item
status. If PayPal is still processing, show that state honestly; do not
claim completion early.

**1:20--1:40 --- Policy block:** Submit "Pay AWS \$185 for cloud
hosting." Show the per-transaction cap block, reason and unchanged
balance.

**1:40--2:00 --- Policy control:** Change the approval threshold or
category budget, save a new policy version, and show that the next
request uses it.

**2:00--2:20 --- Auditability:** Open transaction detail and show policy
trace, lifecycle timeline and ledger entries.

**2:20--2:40 --- Reset/repeatability:** Reset sandbox, confirm the 1,000
USD baseline and explain that historical receipts remain auditable.
Briefly show the PayPal Sandbox integration status and provider
reference from the payout receipt.

**Closing line:** "Pactra doesn't just let an AI initiate payments. It
makes every request accountable to policy, approval and a ledger---even
when the funds are only sandbox funds."

**Fallback:** If Gemini is unavailable, use the manual payment form and
deterministic parser. If PayPal Sandbox is temporarily unavailable, show
the provider error honestly and complete the same workflow on the
internal sandbox rail; do not label it as a PayPal payout. If the public
deployment is unavailable, use a local build connected to a seeded
database; never substitute a prerecorded clip for a claim that the live
system works. Keep the submitted video under 3 minutes as required by
the official rules.
