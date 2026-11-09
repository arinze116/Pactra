# Changelog

All notable release-candidate changes are documented here. Pactra has not yet published a semantic versioned release.

## Unreleased

### Added

- Explicit operator-controlled recovery for ambiguous PayPal submissions without a stored batch ID, reusing the original attempt and stable provider identifiers.
- Receipt copy and confirmation that distinguish provider refresh from same-ID ambiguous-submission recovery.
- Approval-threshold boundary and expired/revoked-session authorization regressions.
- README-to-product verification matrix, architecture decision record, contribution guide, and corrected migration rollback documentation.

### Changed

- PayPal submission is worker-only; API routes persist and enqueue work without provider submission.
- PostgreSQL worker claims use row locks and conditional state transitions.
- Documentation distinguishes configured providers, OAuth, batch acceptance, item-level success, deterministic fallback, and mocked state-machine evidence.

### Safety

- Unknown provider outcomes remain reserved and are excluded from automatic resubmission.
- PayPal ledger capture still requires individual item status `SUCCESS`.
- Production remains on release `0e3e905`; this candidate has not been deployed.

## Production baseline `0e3e905`

- Preserves complete payment audit evidence.
- Runs schema revision `20261107_0004`.
- Does not include the worker-only PayPal correction or shared rate-limit migration `0005`.
