# Post-release UI regression report

- Date: 2026-11-10
- Branch: `codex/post-release-hardening-20261110`
- Mission: P1 authentication navigation and responsive sidebar fixes
- Local implementation status: Verified
- Production status: Pending merge and deployment verification
- Final production application commit SHA: Pending

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

The user-reported 1919 × 939 production screenshot was treated as authoritative. The exact supplied image was not present in the workspace, so the repository report uses the local structural reproduction and retained before-state captures.

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

| Surface | Before | After |
|---|---|---|
| Authenticated landing, 1919 × 939 | [Guest actions shown](../artifacts/post-release-ui-regression/before/landing-authenticated-1919x939.png) | [Dashboard actions shown](../artifacts/post-release-ui-regression/after/landing-authenticated-1919x939.png) |
| Authenticated landing menu, 390 × 844 | [Guest mobile actions](../artifacts/post-release-ui-regression/before/landing-authenticated-mobile-390x844.png) | [Dashboard mobile action](../artifacts/post-release-ui-regression/after/landing-authenticated-mobile-390x844.png) |
| Application shell, 1280 × 720 | [Baseline shell](../artifacts/post-release-ui-regression/before/sidebar-1280x720.png) | [Logout pinned and visible](../artifacts/post-release-ui-regression/after/app-1280x720.png) |
| Short desktop shell, 1280 × 600 | [Footer clipped below viewport](../artifacts/post-release-ui-regression/before/sidebar-short-1280x600.png) | [Navigation scrolls; footer remains visible](../artifacts/post-release-ui-regression/after/sidebar-short-1280x600.png) |

After-state viewport captures:

- [320 × 700](../artifacts/post-release-ui-regression/after/app-320x700.png)
- [375 × 812](../artifacts/post-release-ui-regression/after/app-375x812.png)
- [390 × 844](../artifacts/post-release-ui-regression/after/app-390x844.png)
- [768 × 1024](../artifacts/post-release-ui-regression/after/app-768x1024.png)
- [1024 × 768](../artifacts/post-release-ui-regression/after/app-1024x768.png)
- [1280 × 720](../artifacts/post-release-ui-regression/after/app-1280x720.png)
- [1440 × 900](../artifacts/post-release-ui-regression/after/app-1440x900.png)
- [1919 × 939](../artifacts/post-release-ui-regression/after/app-1919x939.png)

Measured after-state evidence:

- Horizontal overflow: 0px at all eight required viewport sizes.
- Desktop footer bottom: y=700 at 1280 × 720 and y=919 at 1919 × 939, both 20px inside the viewport.
- Short desktop at 1280 × 600: navigation client height 407px, scroll height 492px, scroll top reached 85px, `overflow-y: auto`, footer bottom y=580.

## Automated tests added

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

## Test results

Passed locally:

- `npm run lint`
- `npm run build` (includes TypeScript project build)
- Full Chromium browser set: 48/48 passed in 6.9 minutes.
- New P1 regression suite on Chromium: 9/9 passed.
- New P1 regression suite on Firefox: 9/9 passed.
- Axe WCAG 2.1 A/AA suite: 1/1 journey passed across all public and authenticated surfaces.
- Existing judge-flow Chromium suite: 16/16 passed after updating the renamed registration controls.
- Existing public/responsive Chromium matrix: all assertions passed after isolating Playwright artifacts from a concurrent test process.

Browser engines:

- Playwright 1.64.1
- Chromium / Chrome for Testing 156.0.8078.4 (revision 1248)
- Firefox 157.0 (revision 1555)
- WebKit 27.2 (revision 2370)

Not yet verified:

- Local WebKit launch. The installed browser could not start because node1 lacks `libgstreamer-plugins-bad1.0-0` and `libavif16`. System packages were not changed without approval. CI installs browser dependencies with Playwright and will be the release-gating WebKit verification.
- GitHub required checks, PR merge, deployment, and production website verification.

## Production verification

Pending. This section must be updated after the exact merged commit is deployed and verified on the real production website. Local screenshots are not production acceptance evidence.

Required production checks:

- Authenticated direct navigation to the landing page shows Dashboard and no guest actions.
- Guest navigation shows Sign in and Sign up.
- Session refresh and public/private navigation retain authenticated state.
- 1280 × 720 and 1919 × 939 sidebars expose Sign out and every navigation item.
- Mobile drawer exposes Sign out and closes after navigation.
- Production health, API readiness, and deployed SHA match the release record.

## Completion accounting

- Requested: two P1 production UI defects, regression coverage, release, and production verification.
- Implemented: auth-state synchronization, session-error handling, CTA rename, full-height shell, independent scrolling, mobile accessibility, tests, ADR, and screenshot evidence.
- Passed: local lint, TypeScript/build, Chromium full browser suite, Firefox P1 suite, Axe checks, responsive geometry, and screenshot review.
- Failed: local WebKit launch due missing host libraries; application assertions were not reached.
- Incomplete: GitHub checks, merge, production deployment, production verification, and final deployed SHA.
- Risk: production acceptance remains open until hosted verification is complete.
- Next step: create the PR, run required CI including WebKit, merge after checks, deploy the exact merge SHA, verify production, and update this report.

## Scorecard evidence (no self-score)

- Engineering: one shared auth authority; explicit failure states; request deduplication; behavior-level browser tests; build and type checks.
- Design: existing identity preserved; loading/error states designed; no shell redesign; screenshots reviewed at all required sizes.
- Branding: Pactra logo, IBM Plex Sans, black/red palette, icon system, and navigation hierarchy retained.
- Research: root causes traced through router scope, provider behavior, backend session semantics, CSS geometry, and browser measurements.
- Productivity: P1 work completed before demo/video tasks; regressions consolidated into one dedicated suite.
- Memory: relevant organisation memory retrieved before implementation; a durable update will be proposed only after production verification.
