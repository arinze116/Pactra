# Demo video production handover

Status: **NOT READY FOR RECORDING** until production deployment and public
acceptance are complete. This file is intentionally conservative and will be
updated with only production-verified scenarios.

## Production access

- Production URL: <https://pactra-nine.vercel.app>
- Entry point: public landing page → **Explore demo**
- Demo lifetime: two hours by default
- Reset: persistent demo banner → **Reset demo** → confirm
- Exit: persistent demo banner → **Exit demo** → confirm
- Final production SHA: pending

## Locally verified scenarios

These scenarios passed the isolated no-retry browser suite but are not yet
claimed as production recording evidence:

- seeded Northstar Studio dashboard;
- posted/reserved/available wallet balance;
- seeded policy inspection;
- `$49` software completion;
- `$120` approval scenario;
- restricted-vendor policy rejection;
- approval and rejection controls;
- detailed receipt and audit evidence;
- reset, exit, and independent-session isolation.

## Recording preparation

Pending production acceptance. Candidate recommendation:

- Browser: Chromium/Chrome in a fresh context.
- Viewport: `1440 × 900` for primary capture; `390 × 844` only for a brief
  mobile proof.
- Starting route: `/` with no active cookies.
- Reset immediately before recording and wait for the seeded dashboard.
- Avoid provider settings, normal account settings, destructive receipt
  reversal, and repeated rapid demo creation.
- Allow the explicit preparation state to finish; do not cut around an error.

## Product claims

Safe candidate claims, subject to production verification:

- Pactra evaluates payment requests against deterministic, versioned policy.
- Pactra routes above-threshold requests to an approval state.
- Pactra persists receipts, lifecycle events, audit evidence, and balanced
  sandbox ledger entries.
- The instant demo is isolated per session and uses sandbox funds only.

Must be described as sandbox or simulated:

- every demo balance and ledger movement;
- internal demo execution;
- deterministic demo assistant responses.

Must not be claimed:

- real-money movement;
- a PayPal request from demo mode;
- a Gemini call from demo mode;
- independent maker-checker role separation;
- production readiness before the final acceptance report is complete.
