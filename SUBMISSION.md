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

- [x] Establish a trusted HTTPS API origin. The verified Tailscale Funnel endpoint proxies only to `127.0.0.1:8010`; direct SSLIP issuance was unavailable because Oracle blocked public TCP 80/443.
- [x] Link the `pactra` Vercel project, deploy `frontend` with `VITE_API_URL` absent, and rewrite `/api/*` to the verified HTTPS origin.
- [x] Production readiness reports Gemini configured with `GEMINI_MODEL=gemini-3.8-flash` and AI enabled. This is configuration evidence only.
- [x] Production readiness reports PayPal Sandbox Payouts configured with mock mode disabled. The recipient is masked in the application.
- [x] Confirm Oracle PostgreSQL is healthy, localhost-only, backed up, and Alembic reaches head before the API starts.
- [x] Run a fresh-account deployed smoke through <https://pactra-nine.vercel.app>: register/login, top-up, policy save/reload, internal payment, approval/rejection, assistant fallback, receipt/history, reset, persistence, CSRF, logout, and tenant isolation.
- [ ] Create and reconcile a separately authorized PayPal Sandbox payout to item-level `SUCCESS`. Prior OAuth and a denied/failed payout are not provider success.
- [ ] Resolve Gemini quota/entitlement, then verify one live typed-tool read and one governed payment request. The latest generation returned `429 RESOURCE_EXHAUSTED`.
- [ ] Record and upload the public demo video under the event limit.
- [ ] Add the final video URL to README/Devpost; the verified live URL is already recorded.
- [ ] Complete the Devpost submission and disclose the sandbox-only behavior and hackathon-period changes.

Do not check an external gate until its URL, provider response, or dashboard state has been observed directly.
