# Pactra Demo Failure Recovery

## Golden rule

Recover only the isolated demo. Do not switch to production credentials,
submit PayPal, change production, or describe a fixture/fallback as a live
provider result.

## Assistant provider unavailable

Expected behavior: deterministic fallback remains governed and labels the
authoritative transaction result.

Action:

1. State that Gemini is optional to governance.
2. Continue with the configured fallback prompt.
3. Show the receipt and policy result.
4. Do not retry repeatedly, change models, rotate keys, or fabricate a live
   function call.

## Local API unavailable

1. Keep the browser open and inspect the API terminal.
2. Confirm the target is the demo SQLite URL.
3. Restart only the local Uvicorn process.
4. Reload and sign in again.
5. If state is uncertain, stop both local servers and use the reset runbook.

## Frontend unavailable

1. Confirm Vite is listening on port 5193.
2. Restart only the local Vite process.
3. Do not use the production Vercel project as a recovery shortcut.

## Scenario state already consumed

If Ada Contractor was already approved or the balance differs, use the safe
reset procedure. Do not hand-edit SQLite rows.

## Browser or layout issue

- Use current Chromium at 1440x900 for the primary presentation.
- Reload once after the API is ready.
- Use the committed real screenshots as explanatory evidence only; do not
  pretend a screenshot is a live interaction.

## PayPal questions

Use the accepted historical evidence and operations document. Never create a
new payout to recover or strengthen the demo.

## Complete reset

```bash
python -m scripts.demo_environment reset --confirm RESET_PACTRA_DEMO
```

Then restart local API/frontend, sign in, and verify the four dashboard values
in `DEMO/DEMO-CHECKLIST.md`.
