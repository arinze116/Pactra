# Changelog

Pactra has not published a semantic-versioned release. This file records
notable repository changes and points to the separately accepted production
baseline.

## Unreleased

### Added

- Final PayPal AI Hackathon submission brief, public video link, production
  evidence, captions, and repository-readiness audit.
- Judge-access guidance that distinguishes the credential-free deterministic
  instant demo from the authenticated Gemini experience.
- Public Privacy Policy and Terms of Use routes.
- A structured responsive footer with product, resource, legal, licence, and
  sandbox-boundary links.
- Browser coverage for every public and authenticated route at 320, 375, 768,
  1024, and 1440 pixels.
- Registration, login, logout, and password-change coverage at the exact
  eight-character password boundary.

### Changed

- New-account and password-change minimum length is now 8 characters instead
  of 12. The 128-character maximum and three-character-class requirement stay
  in place.
- The landing page and README now explain the governed request lifecycle, AI
  authority boundary, sandbox limitation, architecture, and evidence model
  more directly.
- The retired pre-account agent is now a provider-free compatibility shim that
  always fails closed. Active AI requests continue through
  `backend.services.assistant`.
- Root design and deployment documentation now match the actual dark/red
  interface and Vercel plus Oracle production architecture.

### Safety

- Unknown PayPal outcomes remain reserved and are never blindly resubmitted.
- PayPal ledger capture still requires individual item status `SUCCESS`.
- These unreleased changes are repository-only. No production deployment,
  service restart, migration, provider request, or financial operation was
  performed for them.

## Accepted production baseline `63f2583`

- Runtime SHA: `63f25839a6b645a8ca404846ecd82d16c1994b7c`.
- Database revision: `20261107_0005`.
- Active Gemini model: `gemini-3.5-flash-lite`.
- Canonical retained evidence:
  [QA/ACCEPTED-PRODUCTION-BASELINE.md](./QA/ACCEPTED-PRODUCTION-BASELINE.md).
