# ADR: Authentication navigation and full-height sidebar hardening

- Date: 2026-11-10
- Status: Accepted
- Scope: Pactra frontend authentication presentation and application shell

## Context

Pactra's public routes were outside `AuthProvider`, so the landing and legal-page navigation could not observe an existing server-side session. The provider also collapsed session-check failures into an unauthenticated state. Separately, the application sidebar used a fixed viewport position and `margin-top: auto` for its footer, but its navigation region had no constrained height or overflow behavior.

## Decision

1. Mount one `AuthProvider` above every route and treat it as the only client-side source of authentication state.
2. Model authentication as four explicit states: `loading`, `authenticated`, `unauthenticated`, and `error`.
3. Continue using the existing opaque server-side cookie session. Do not introduce local-storage tokens or a second session cache.
4. Deduplicate the initial session request so React Strict Mode cannot issue parallel restoration calls.
5. Render public account actions from shared authentication state. Loading and session-error states remain neutral and never display guest actions.
6. Use a `100dvh` application shell with two independently constrained columns on desktop.
7. Make the sidebar a vertical flex container with a non-shrinking header, `min-height: 0` scrollable navigation region, and non-shrinking footer.
8. Give main content its own vertical scroll container and preserve the existing responsive drawer pattern on smaller screens.

## Language and framework choice

The change remains in TypeScript, React 18, React Router, and Tailwind CSS because those are the existing production frontend technologies. Introducing another language, state library, routing layer, or sidebar implementation would add synchronization risk without improving the required behavior.

## Rejected alternatives

- Pathname-based button hiding: it would not establish whether a session exists.
- CSS-only hiding of guest links: it would preserve stale state and accessibility defects.
- Treating network errors as logout: it would incorrectly discard a potentially valid session.
- Reducing navigation spacing or typography: it would only postpone sidebar clipping.
- A second mobile or desktop navigation tree: it would duplicate behavior and increase drift.
- Persisting authentication in local storage: it would create a second session authority and weaken the existing cookie-based security model.

## Consequences

- Public entry points now perform one session discovery request per full application load.
- Authenticated public navigation updates immediately during client-side routing.
- A backend outage produces a retryable session-error state rather than guest navigation.
- Sidebar navigation and main content scroll independently, including at short viewport heights.
- The existing Pactra visual system, navigation hierarchy, icons, and typography remain unchanged.
