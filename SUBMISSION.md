# Pactra submission checklist

## Verified in the repository

- [x] Public GitHub repository and MIT licence.
- [x] Multi-user auth, session expiry/revocation, CSRF, owner-scoped data.
- [x] Integer-cent double-entry sandbox ledger, reservations, reset generations, retry/reversal invariants.
- [x] Versioned policy validation and enforcement.
- [x] Approval/rejection and auditable receipts/history.
- [x] Gemini typed-tool path plus deterministic fallback and persisted conversations.
- [x] PayPal Sandbox batch submission and item-level processing/success/failure/unknown/return handling in deterministic tests.
- [x] PostgreSQL/Alembic runtime plus separate API and reconciliation-worker systemd definitions.
- [x] Credential-free internal sandbox judge path.
- [x] README setup, environment, migration, test, security, judge, and fallback instructions.

## External release gates

- [ ] Point a controlled Pactra API hostname to the Oracle VPS and issue its TLS certificate.
- [ ] Link the Vercel frontend project, copy `deploy/vercel.json.example` to `vercel.json` with the verified API hostname, and deploy with `VITE_API_URL` blank.
- [ ] Add `GEMINI_API_KEY`, keep `GEMINI_MODEL=gemini-3.8-flash`, then set `AI_ENABLED=true`.
- [ ] Add `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and a distinct active `PAYPAL_TEST_RECIPIENT_EMAIL`; keep the official Sandbox base URL and `PAYPAL_MOCK_MODE=false`; then set `PAYPAL_PAYOUTS_ENABLED=true`.
- [ ] Confirm Oracle PostgreSQL is healthy, localhost-only, backed up, and Alembic reaches head before the API starts.
- [ ] Run a fresh-account deployed smoke: register/login, top-up, policy save/reload, internal payment, approval/rejection, assistant, receipt/history, reset, persistence after reload.
- [ ] Create and reconcile a real PayPal Sandbox payout to item-level `SUCCESS`. The latest local real smoke reached item-level `FAILED` and correctly released its hold; it is not success evidence.
- [ ] Re-run live Gemini tool execution if Google is no longer returning temporary `503 UNAVAILABLE`.
- [ ] Record and upload the public demo video under the event limit.
- [ ] Add the final live URL and video URL to README/Devpost.
- [ ] Complete the Devpost submission and disclose the sandbox-only behavior and hackathon-period changes.

Do not check an external gate until its URL, provider response, or dashboard state has been observed directly.
