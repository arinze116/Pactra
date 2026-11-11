# Demo video production handover

Status: **HISTORICAL PRE-RECORDING HANDOVER — SUPERSEDED**

This document preserves the verified 2026-11-10 preparation state. Recording
subsequently completed using the normal authenticated application rather than
the deterministic instant-demo assistant. The approved 130-second final video
is public at <https://youtu.be/685tzja9ey4>. Current production evidence is in
[`VIDEO-PRODUCTION/pactra-hackathon-production-report.md`](./VIDEO-PRODUCTION/pactra-hackathon-production-report.md),
with matching captions in
[`VIDEO-PRODUCTION/pactra-hackathon-final.srt`](./VIDEO-PRODUCTION/pactra-hackathon-final.srt).

The preparation notes below remain historical and must not be read as the
current recording or upload status.

## Production access

- Production URL: <https://pactra-nine.vercel.app>
- Entry point: public landing page → **Explore demo**
- Demo lifetime: two hours by default
- Reset: persistent demo banner → **Reset demo** → confirm
- Exit: persistent demo banner → **Exit demo** → confirm
- Final production SHA:
  `28634c13082a61b5c53e75528eacf2263ea1fd5e`
- Vercel deployment: `dpl_FYe3PxM6VXxN8Nh3rLFwFhzd52cL`
- Oracle release: `/opt/pactra/releases/28634c1`
- Database migration: `20261110_0006`

Each **Explore demo** action creates a distinct temporary principal and
Northstar Studio workspace. Refresh restores that workspace. Reset preserves
the session while rebuilding its seed. Exit revokes the demo and returns to
the public site.

## Verified demo scenarios

The following scenarios passed in production:

- seeded Northstar Studio dashboard;
- posted `$965.00`, reserved `$140.00`, available `$825.00`;
- active policy inspection: `$500` daily, `$750` per payment, approval
  above `$100`, restricted vendor;
- `$49.00` Linear software payment completed through the internal sandbox;
- `$120.00` Figma Teams payment entered approval and completed after approval;
- Northstar Print House pending request rejected through the normal approval
  service;
- Restricted Supply Co blocked by deterministic policy;
- completed receipt with lifecycle, policy, audit, and balanced ledger
  evidence;
- reset restored the original dataset and walkthrough state;
- exit revoked only the demo session;
- two simultaneous demo contexts remained isolated;
- a separate normal account session survived demo exit.

## Recording preparation

- Recommended browser: current Chrome/Chromium. Production acceptance used
  Chrome for Testing 156.0.8078.4.
- Primary viewport: `1440 × 900`.
- Optional mobile proof: `390 × 844`.
- Starting route: `/` in a fresh browser context with no Pactra cookies.
- Select **Explore demo** once. Avoid rapid repeated creation; the production
  per-client ceiling is five sessions per hour.
- Wait until the dashboard shows `$825.00 / $140.00 / $965.00` and no loading
  placeholders before recording.
- Use **Reset demo** immediately before the take. Confirm the walkthrough reads
  `0/7`.
- Recommended sequence:
  1. dashboard and balances;
  2. policies;
  3. `$49` request and completed receipt;
  4. `$120` request and approval;
  5. restricted-vendor block;
  6. receipt lifecycle/audit/ledger evidence;
  7. reset and exit.
- Public click-to-usable-dashboard samples ranged from `712–1,548 ms`; keep
  the authentic **Preparing demo…** state rather than cutting around it.
- Do not open normal account settings, provider settings, wallet reset, top-up,
  reversal, or recovery controls during recording.

## Product claims

### Demonstrably true

- Pactra evaluates payment requests against deterministic, versioned policy.
- Pactra enforces limits, category budgets, restricted vendors, and approval
  thresholds before sandbox execution.
- Pactra reserves funds for pending approvals and posts balanced internal
  ledger entries for completed sandbox payments.
- Pactra records lifecycle events, policy decisions, approval actions,
  receipts, and audit evidence.
- Instant-demo workspaces are isolated per session and can be reset or exited.

### Sandbox-only or simulated

- Every demo balance and ledger movement.
- Every demo payment execution outcome.
- Demo receipts and provider references.
- Demo assistant responses.

The UI explicitly labels these outcomes as demo/simulated evidence. No real
money moves.

### Genuinely AI-powered

Pactra's normal authenticated assistant has a configured Gemini function-call
path verified in the prior production release. The instant demo deliberately
uses a deterministic, labelled assistant path and does not contact Gemini.
Do not imply that a Gemini call occurred during the recorded demo.

### Must not be claimed

- real-money movement;
- a PayPal payout or provider request from demo mode;
- a Gemini call from demo mode;
- independent maker-checker role separation;
- live provider success caused by a demo interaction;
- production currencies or rails beyond the documented Sandbox system.

## Known limitations

- Approval and rejection are performed by the same demo principal; separate
  organisational roles are not implemented.
- Manual NVDA/VoiceOver validation was not completed, although production Axe
  WCAG 2.1 A/AA checks passed.
- The public demo's coherent seeded balance is
  `$965 posted / $140 reserved / $825 available`, not the illustrative
  unreserved `$1,000` state from older materials.

Detailed evidence:
[QA/DEMO/DEMO-ACCEPTANCE-REPORT.md](../QA/DEMO/DEMO-ACCEPTANCE-REPORT.md).
