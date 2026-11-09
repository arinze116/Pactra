# Pactra Codebase, README, and Web Application Reconciliation

Verification date: 2026-11-09 (Africa/Lagos)

Branch: `audit/full-codebase-readme-webapp-reconciliation`

Base SHA: `70def1db357b3782a0d6fab0891838d49e99c91e`

## Scope and evidence labels

- **Verified**: inspected or executed during this reconciliation.
- **Retained evidence**: supported by an accepted historical record but not re-executed here.
- **Not verified**: not safely or independently exercised during this reconciliation.

Production remained read-only. No deployment, service restart, migration,
configuration change, provider request, payout, reconciliation, or production
data mutation occurred.

## Verified product architecture

| Area | Verified implementation |
|---|---|
| Frontend | React 18, TypeScript 5, Vite 8, React Router, responsive public and authenticated layouts |
| API | FastAPI with strict Pydantic contracts, same-origin mutation checks, synchronizer CSRF, and request IDs |
| Authentication | Argon2id hashes, opaque database sessions, idle/absolute expiry, revocation, and database-backed rate limits |
| Ownership | User filters on wallet, policy, conversation, payment, approval, receipt, audit, and provider-status paths |
| Policy | Versioned deterministic evaluation before reservation, approval, or execution |
| Ledger | Double-entry simulated USD wallet with balanced issuance, reservation, capture, release, reset, and compensation paths |
| AI | `google-genai` SDK function calling with strict tool validation and deterministic fallback |
| PayPal | Sandbox-only, worker-owned submission, stable provider identifiers, and item-level reconciliation |
| Operations | Alembic, systemd assets, Vercel static frontend, read-only health/invariant/backup diagnostics |

## Reconciliation changes

### Authentication

- New-password minimum changed from 12 to 8 characters across backend
  registration, backend password change, sign-up, and Settings.
- The 128-character maximum and requirement for at least three of uppercase,
  lowercase, number, and symbol remain enforced.
- Login intentionally validates the stored credential without imposing a new
  client-side minimum, which preserves access for any valid existing account.
- Added backend and browser regression coverage for seven-character rejection,
  exact eight-character registration, logout/login, password change,
  old-password rejection, and replacement-password login.

### Public application

- Added a semantic, responsive footer with Product, Resources, and Legal
  navigation plus an explicit sandbox disclosure.
- Added public `/privacy` and `/terms` routes with plain-language policies
  specific to Pactra that do not claim live-money or regulated capabilities.
- Added account-creation links to both legal pages.
- Expanded the landing page with the governed request lifecycle and the AI
  authority boundary.
- Replaced the inaccurate "immutable receipts" marketing label with
  "auditable receipts."
- Replaced ambiguous dash placeholders with explicit text such as
  "Unavailable" and "Not available."
- Removed every em dash character from tracked first-party files.
- Preserved the protected-main CI contexts through YAML Unicode escapes. The
  workflow source contains no literal em dash, while GitHub still receives the
  four exact status-check names required by the active repository ruleset.

### README and claim accuracy

- Reworked the README opening around the problem, product boundary, user
  workflow, deterministic authority model, and proof surfaces.
- Corrected the AI stack from a generic REST claim to the installed
  `google-genai` SDK and Gemini Developer API.
- Corrected the worker startup claim: systemd orders and requires the API unit;
  the worker then acquires a PostgreSQL advisory lease. The unit does not poll
  `/api/ready` before starting.
- Added the legal routes and the previously omitted `POLICY_CONFIG_PATH`.
- Updated the PRD password contract from 12 to 8 characters and incremented
  its document version to v1.2.
- Historical audit documents remain historical. Current claim status is in
  `QA/README-PRODUCT-VERIFICATION.md`.
- Reconciled the root changelog, design direction, task history, deployment
  guide, legacy Render blueprint, and frontend protocol with the accepted
  Vercel plus Oracle architecture and current dark/red interface.

### Retired agent safety

- Confirmed that all active `/api/chat` requests use
  `backend/services/assistant.py`.
- Removed obsolete Gemini initialization and response construction from the
  unreferenced pre-account `backend/agent.py` compatibility path.
- The legacy chat entry point now fails closed even when a provider key is
  present. Its retained private payment handlers also remain unable to submit
  a provider operation.

## Functional verification

| Check | Result | Evidence |
|---|---|---|
| Backend SQLite | PASS | 150 collected; 140 passed and 10 PostgreSQL-only tests skipped |
| Authentication unit/API file | PASS | 14 tests in `backend/tests/test_auth.py` |
| Frontend lint | PASS | `npm run lint` |
| TypeScript and production build | PASS | `npm run build`; initial JS 85.04 kB gzip |
| Browser journeys | PASS | 21 Playwright tests |
| Automated WCAG 2.1 AA | PASS | Axe on 16 public/authenticated surfaces |
| Responsive route matrix | PASS | 6 public and 10 authenticated routes at 320, 375, 768, 1024, and 1440 pixels |
| Account lifecycle at 8 characters | PASS | registration, logout, login, password change, old/new credential checks |
| Lighthouse homepage | PASS | performance 0.99, accessibility 1.00, best practices 1.00, LCP 760 ms, CLS 0 |
| Python dependency consistency | PASS | `pip check` |
| Python vulnerability audit | PASS | no known vulnerabilities |
| npm production/full audits | PASS | zero vulnerabilities |
| Public production availability | PASS | `/`, `/api/health`, and `/api/ready` returned 200 in a read-only check |
| Current-branch PostgreSQL suite | NOT VERIFIED | no isolated PostgreSQL service was changed or created on the production VPS; required CI remains the verification gate |

## Visual review

Screenshots were captured from an isolated local database with providers
disabled. They covered landing, sign-up, Privacy, Terms, overview, and Settings
at representative desktop, tablet, and mobile widths. The final automated
matrix additionally loaded every public and authenticated route at all five
supported widths. No clipped content, page-level horizontal overflow, broken
image, runtime console error, or overlapping control was found.

Ephemeral visual evidence: `/tmp/pactra-ui-audit-20261109/`.

Manual screen-reader testing, Safari, and Firefox visual inspection were not
performed. Automated Axe, Chromium keyboard paths, reduced motion, and the
five-width responsive matrix passed.

## Production and GitHub boundary

- Read-only production health passed.
- Production account creation and login were not repeated because they would
  mutate accepted production data. The complete lifecycle passed in the
  isolated application environment.
- Base main CI run
  [42699433176](https://github.com/arinze116/Pactra/actions/runs/42699433176)
  passed all four jobs for exact SHA `70def1db357b3782a0d6fab0891838d49e99c91e`.
- The changes in this report are not deployed and have no current-branch CI
  evidence until the branch is published through the normal review process.

## Residual limitations

- Pactra remains sandbox-only.
- Approval uses the requesting account; distinct requester and approver roles
  are not implemented.
- Provider webhooks are not implemented; PayPal reconciliation uses polling.
- Lighthouse is homepage-only and not real-user monitoring.
- Current-branch PostgreSQL CI, manual assistive-technology testing, and
  non-Chromium visual testing remain outstanding verification gates.
