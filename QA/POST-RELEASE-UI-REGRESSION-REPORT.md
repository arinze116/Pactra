# Post-release UI regression report

- Date: 2026-11-10
- Mission: P1 authentication navigation and responsive sidebar fixes
- Implementation PR: [#19](https://github.com/arinze116/Pactra/pull/19)
- Implementation merge SHA: `56740ac67fc78d978ca8a472126c91cd240c69cd`
- Final production application SHA: `28634c13082a61b5c53e75528eacf2263ea1fd5e`
- Production deployment: `dpl_FYe3PxM6VXxN8Nh3rLFwFhzd52cL`
- Production URL: [https://pactra-nine.vercel.app](https://pactra-nine.vercel.app)
- Status: Verified in production

## Requested

1. Ensure public navigation reflects the actual authenticated session without flicker or false guest state.
2. Rename the public registration action from "Create sandbox" to "Sign up".
3. Preserve sessions across refreshes and public/private client-side navigation.
4. Keep every sidebar item and Logout reachable at supported desktop and mobile sizes.
5. Add browser-level regression coverage, accessibility verification, screenshots, release evidence, and production verification.

## Root causes

### Issue 1 — authenticated users saw guest navigation

Verified:

- `/`, `/privacy`, and `/terms` were declared outside the router subtree containing `AuthProvider`.
- The landing and legal headers therefore had no access to the shared session state and always rendered hard-coded guest links.
- `AuthProvider` converted every failed `/api/auth/session` request into `user = null`, so a transport or backend failure was indistinguishable from a valid signed-out response.
- React Strict Mode produced two restoration requests when entering the old authentication scope. The before-state reproduction observed two `/api/auth/session` requests during the registration route load.

The backend session endpoint itself was consistent: it returns `200` with `user: null` for no, invalid, or expired sessions and returns the active user plus the CSRF response header for a valid session.

### Issue 2 — sidebar navigation and Logout could be clipped

Verified:

- The sidebar footer relied on `margin-top: auto`.
- The navigation wrapper had neither `min-height: 0` nor `overflow-y: auto`.
- At 1280 × 600, the before-state navigation used `overflow-y: visible` and the footer ended at y=673 in a 600px viewport, making Logout unreachable.
- At 1280 × 720 and 1919 × 939 the local baseline happened to fit, but it still had no independent sidebar scrolling contract. This made it sensitive to shorter effective viewport heights, browser UI, zoom, and content growth.

The user-reported 1919 × 939 production screenshot was treated as authoritative. The exact supplied image was not present in the workspace, so the retained before-state captures document the reproduced structural failure.

## Implemented

### Authentication

- Moved one `AuthProvider` above all public, guest, and protected routes.
- Added explicit `loading`, `authenticated`, `unauthenticated`, and `error` states.
- Added a shared in-flight session promise to prevent duplicate Strict Mode requests.
- Preserved the existing secure cookie session source; no token or local-storage session was added.
- Added retryable neutral UI for session-check failures.
- Made landing, legal, footer, feature-menu, and hero account actions session-aware.
- Authenticated state now shows Dashboard/Open dashboard and never shows Sign in or Sign up.
- Guest state now shows Sign in and Sign up.
- Renamed registration navigation to Sign up and the registration submit button to Create account.
- Kept logout state unchanged when the logout request fails.

### Application shell

- Rebuilt the existing shell as a `100dvh` constrained grid/flex layout.
- Added a non-shrinking sidebar header.
- Added a flexible navigation region with `min-height: 0`, `overflow-y: auto`, and contained overscroll.
- Added a non-shrinking footer containing the user and Sign out action.
- Added an independent main-content scroll container.
- Preserved the existing mobile navigation pattern while giving its navigation region independent scrolling and a pinned footer.
- Added Escape-to-close with focus restoration and `aria-controls` for the mobile drawer.
- Kept the existing Pactra black/red identity, IBM Plex Sans, icons, spacing, and hierarchy.

## Before and after evidence

| Surface | Before | Production after |
|---|---|---|
| Authenticated landing, 1919 × 939 | [Guest actions shown](../artifacts/post-release-ui-regression/before/landing-authenticated-1919x939.png) | [Dashboard actions shown](../artifacts/post-release-ui-regression/production/landing-authenticated-1919x939.png) |
| Application shell, 1919 × 939 | [User-reported structure reproduced](../artifacts/post-release-ui-regression/before/sidebar-1919x939.png) | [All groups and Sign out reachable](../artifacts/post-release-ui-regression/production/app-1919x939.png) |
| Short desktop shell, 1280 × 600 | [Footer clipped below viewport](../artifacts/post-release-ui-regression/before/sidebar-short-1280x600.png) | [Navigation scrolls; footer remains visible](../artifacts/post-release-ui-regression/production/sidebar-short-1280x600.png) |
| Mobile drawer, 390 × 844 | [Guest actions shown while authenticated](../artifacts/post-release-ui-regression/before/landing-authenticated-mobile-390x844.png) | [Authenticated drawer with reachable Sign out](../artifacts/post-release-ui-regression/production/app-390x844.png) |

Production captures:

- [Guest landing, 1919 × 939](../artifacts/post-release-ui-regression/production/landing-guest-1919x939.png)
- [Authenticated landing, 1919 × 939](../artifacts/post-release-ui-regression/production/landing-authenticated-1919x939.png)
- [320 × 700](../artifacts/post-release-ui-regression/production/app-320x700.png)
- [375 × 812](../artifacts/post-release-ui-regression/production/app-375x812.png)
- [390 × 844](../artifacts/post-release-ui-regression/production/app-390x844.png)
- [768 × 1024](../artifacts/post-release-ui-regression/production/app-768x1024.png)
- [1024 × 768](../artifacts/post-release-ui-regression/production/app-1024x768.png)
- [1280 × 720](../artifacts/post-release-ui-regression/production/app-1280x720.png)
- [1440 × 900](../artifacts/post-release-ui-regression/production/app-1440x900.png)
- [1919 × 939](../artifacts/post-release-ui-regression/production/app-1919x939.png)
- [Short desktop, 1280 × 600](../artifacts/post-release-ui-regression/production/sidebar-short-1280x600.png)

Visual inspection found no clipped menu items, footer overlap, main/sidebar collision, horizontal overflow, branding regression, or unexpected redesign.

## Automated regression coverage

`frontend/tests/e2e/navigation-regressions.spec.ts` covers:

1. Guest Sign in and Sign up on desktop and mobile.
2. Sign up routing to the registration flow.
3. Authenticated Dashboard navigation with no guest actions.
4. Session persistence after refresh.
5. Immediate public/private client-side state synchronization.
6. Logout transition to guest navigation.
7. Invalid/expired session transition to guest navigation.
8. Temporary session-check failure remaining neutral and retryable.
9. One restoration request and no guest-action flicker.
10. Direct authenticated landing navigation.
11. Sidebar link reachability and exact geometry.
12. Independently scrollable sidebar navigation and main content.
13. Footer separation from navigation and main/sidebar non-overlap.
14. No horizontal overflow.
15. Keyboard traversal through every desktop sidebar control.
16. Route-change stability.
17. Mobile drawer scrolling, logout access, closing behavior, and focus restoration.
18. No clipping at 1280 × 720 or 1919 × 939.

## Test and release results

Verified:

- PR #19 passed all required backend, frontend, browser, accessibility, and Lighthouse checks before merge.
- Final exact-main CI: [run 42849003993](https://github.com/arinze116/Pactra/actions/runs/42849003993), all four required jobs passed at `28634c13082a61b5c53e75528eacf2263ea1fd5e`.
- Frontend lint, TypeScript/build, production and development dependency audits passed.
- Browser journeys: 141/141 passed across Chromium, Firefox, and WebKit.
- Axe WCAG 2.1 A/AA suite: 3/3 passed.
- Demo browser suite: 4/4 passed.
- Lighthouse: performance 0.98, accessibility 1.00, best practices 0.96.
- Backend SQLite and PostgreSQL jobs passed; PostgreSQL dependency audit reported no known vulnerabilities.
- Production health returned `200 {"status":"ok"}`.
- Production readiness returned `200` with database `ok`, sandbox mode enabled, and internal sandbox available.

Browser and tool versions:

- Playwright: 1.64.1.
- Production verifier: Chromium 156.0.8078.4.
- Release CI exercised Chromium, Firefox, and WebKit using the Playwright 1.64.1 browser bundle.
- Vercel CLI used for deployment inspection: 65.14.0.

## Production verification

Verified on 2026-11-10 against [https://pactra-nine.vercel.app](https://pactra-nine.vercel.app):

- Vercel deployment `dpl_FYe3PxM6VXxN8Nh3rLFwFhzd52cL` is `READY`, targeted to production, and aliased to `pactra-nine.vercel.app`.
- Deployment metadata identifies exact application SHA `28634c13082a61b5c53e75528eacf2263ea1fd5e`.
- A guest sees Sign in and Sign up; "Create sandbox" is absent.
- Sign up opens `/sign-up` and exposes the existing Create account flow.
- An authenticated user sees Dashboard/Open dashboard and no Sign in or Sign up actions.
- The authenticated session survives a full page refresh.
- Public-to-private and private-to-public navigation preserve the correct authenticated header immediately.
- Session restoration renders a neutral loading state, does not flash guest actions, and sends one session request.
- A synthetic `503` session check renders the explicit neutral error state and does not expose guest actions; retry restores the authenticated state.
- Logout clears the session and returns mobile public navigation to Sign in and Sign up.
- Axe reported zero WCAG 2.1 A/AA violations on the guest landing page, authenticated landing page, and authenticated mobile dashboard.

Viewport verification:

| Viewport | Result |
|---|---|
| 320 × 700 | Mobile drawer scrollable; all links and Sign out reachable; closes after navigation; no horizontal overflow |
| 375 × 812 | Mobile drawer scrollable; all links and Sign out reachable; closes after navigation; no horizontal overflow |
| 390 × 844 | Mobile drawer scrollable; all links and Sign out reachable; closes after navigation; no horizontal overflow |
| 768 × 1024 | Mobile drawer scrollable; all links and Sign out reachable; closes after navigation; no horizontal overflow |
| 1024 × 768 | Full-height desktop sidebar; independent navigation/main scrolling; footer inside viewport; no overlap or horizontal overflow |
| 1280 × 720 | Full-height desktop sidebar; footer bottom y=700; all controls reachable; no overlap or horizontal overflow |
| 1440 × 900 | Full-height desktop sidebar; independent scrolling; all controls reachable; no overlap or horizontal overflow |
| 1919 × 939 | Full-height desktop sidebar; footer bottom y=919; all controls reachable; no overlap or horizontal overflow |
| 1280 × 600 | Browser-confirmed navigation overflow scrolls while the footer remains pinned and Sign out remains visible |

Keyboard verification reached all eight desktop navigation links and the Sign out button in order.

## Release disposition

- PR #19 merged the P1 implementation.
- PR #20 supplied the overlapping CI routing/settling stabilization and merged as final production SHA `28634c13082a61b5c53e75528eacf2263ea1fd5e`.
- Exact-main CI passed before production acceptance.
- Production is serving the exact green SHA.
- PR #21 was closed as a conflicting duplicate after PR #20 and the exact-main run superseded it.
- No backend service restart or production financial/provider operation was performed for this frontend release.

## Completion accounting

- Requested: two P1 production UI defects, regression coverage, release, and production verification.
- Implemented: auth-state synchronization, session-error handling, CTA rename, full-height shell, independent scrolling, mobile accessibility, tests, ADR, and screenshot evidence.
- Tested: frontend lint/TypeScript/build/audits, backend SQLite/PostgreSQL, three-engine browser journeys, Axe, Lighthouse, production health/readiness, and live production browser verification.
- Passed: all required release checks and all production acceptance checks listed above.
- Failed: none in the final release gate.
- Incomplete: none for this mission.
- Not verified: manual screen-reader testing with NVDA or VoiceOver was outside the automated production run.
- Next step: routine monitoring only.

## Scorecard evidence (no self-score)

- Engineering: one shared auth authority; explicit failure states; request deduplication; behavior-level browser tests; exact-main CI; verified deployed SHA.
- Design: existing identity preserved; loading/error states designed; no shell redesign; production screenshots inspected at all required sizes.
- Branding: Pactra logo, IBM Plex Sans, black/red palette, icon system, and navigation hierarchy retained.
- Research: root causes traced through router scope, provider behavior, backend session semantics, CSS geometry, and browser measurements.
- Productivity: P1 work completed and released before demo/video tasks; duplicate stabilization PR closed after its replacement was verified.
- Memory: related organisation memory was retrieved before work; the verified production result is eligible for a durable memory update.
