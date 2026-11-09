# Pactra Pre-Demo Checklist

## Environment

- [ ] Branch/commit under review is known.
- [ ] Production has not been changed.
- [ ] `APP_ENV=demo` and a `pactra-demo-*.db` SQLite URL are set.
- [ ] PayPal payouts are disabled.
- [ ] Gemini state is declared honestly: isolated live configuration or
  deterministic fallback.
- [ ] No production credentials are present.

## Reset and health

- [ ] Reset completed with the exact confirmation phrase.
- [ ] Demo status reports one user, four transactions, and one dataset marker.
- [ ] `/api/health` returns `status=ok`.
- [ ] `/api/ready` returns ready/database ok/internal sandbox available.
- [ ] Frontend loads and sign-in succeeds.

## Golden dashboard

- [ ] Posted `$951.00`.
- [ ] Reserved `$125.00`.
- [ ] Available `$826.00`.
- [ ] One pending approval.
- [ ] Completed, pending, rejected, and blocked rows are visible.

## Rehearsal

- [ ] Scenario A completes `$35.00` and shows a balanced receipt.
- [ ] Scenario B completes allowed `$20.00`, blocks `$200.00`, and truthfully
  identifies fallback/provider state.
- [ ] Scenario C approves `$125.00` once and shows approval/audit/ledger proof.
- [ ] No PayPal or real-money action occurs.
- [ ] Failure-recovery document is open.

## Presentation

- [ ] Browser at 1440x900 and zoom 100%.
- [ ] Credentials are entered off-screen or from a secure presenter note.
- [ ] Notification/chat windows are hidden.
- [ ] Open with the 30-second value statement.
- [ ] State “sandbox-only” explicitly.
- [ ] Do not claim bank-grade, audited, regulator-approved, or live-money status.
