# Pactra interface direction

## Product

Pactra is a sandbox payment-governance workspace for small teams. It helps a
team request spending, apply deterministic policy, obtain human approval, and
prove the final ledger or provider outcome.

## Character

Controlled, exact, quietly assured, and evidence-led.

## Visual world

The interface resembles a modern operations control room. Near-black canvases,
charcoal working surfaces, restrained borders, precise figures, and one vivid
red brand accent keep attention on policy decisions and evidence.

The public experience is editorial and spacious. The authenticated workspace
is denser and operational. Both use the same typography, colour tokens, border
language, and sandbox disclosures.

## Design system

- Typography: IBM Plex Sans Variable for the interface. Monetary values and
  identifiers use tabular figures or the configured mono stack.
- Canvas: `#050506` with deeper `#020203` sections.
- Surfaces: `#0b0b0d` and `#141416` with low-contrast `#232326` borders.
- Brand accent: Pactra red, led by `#e0002b`; use it for primary actions,
  selected navigation, focus accents, and editorial emphasis.
- Semantic states: green for confirmed success, yellow for review or pending
  work, and soft red for blocked, rejected, failed, or destructive states.
- Spacing: 4px base rhythm with common 8, 12, 16, 24, 32, 48, and 64px steps.
- Radius: 8px controls, 12 to 14px cards, and 16 to 20px major public panels.
- Elevation: hairline borders and restrained shadows. Avoid glass effects,
  decorative gradients, and unnecessary animation.
- Motion: short opacity and vertical-entry transitions only. Always respect
  `prefers-reduced-motion`.

## Interaction rules

- A request is never presented as a completed payment.
- State labels use text and colour together.
- Primary actions remain obvious; destructive actions stay visually distinct.
- Loading, empty, stale, error, disabled, success, and retry states are part of
  the designed experience.
- Every form uses persistent labels, specific error messages, visible focus,
  and touch targets of at least 44px where practical.
- Illustrative public data must be labelled as a preview. Authenticated screens
  must show only server-authoritative account data.

## Screen inventory

1. Public product page and structured footer.
2. Sign-up, sign-in, Privacy Policy, Terms of Use, and not-found pages.
3. Payment operations overview and guided scenarios.
4. Manual and AI-assisted request creation.
5. Approval, policy, wallet, transaction history, receipt, and audit surfaces.
6. Account and PayPal Sandbox integration settings.

## Responsive behaviour

- Desktop: persistent 272px workspace navigation and multi-column evidence
  layouts.
- Tablet: compact grids and stacked working panels without clipped controls.
- Mobile: one-column forms and cards, collapsible navigation, mobile transaction
  cards, and no page-level horizontal scrolling.
- Supported verification widths: 320, 375, 768, 1024, and 1440 pixels.

## Footer standard

Public pages end with the Pactra identity, a plain-language sandbox statement,
Product, Resources, and Legal groups, Privacy Policy and Terms of Use links,
the MIT licence, copyright, and the no-real-money boundary.
