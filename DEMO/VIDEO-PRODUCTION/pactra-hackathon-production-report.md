# Pactra PayPal AI Hackathon final video production report

- Date: 2026-11-11
- Approved master: `pactra-hackathon-final.mp4`
- Public video: <https://youtu.be/685tzja9ey4>
- Duration: `00:02:10.000`
- Delivery: 1920×1080, 16:9, 30 fps, H.264/AAC
- Environment shown: authenticated Pactra application with PayPal Sandbox only

## Publication status

The owner approved the final cut and confirmed the YouTube upload is public.
Public player metadata was independently retrieved on 2026-11-11:

- title: `Pactra : AI-Powered Payment Governance | PayPal AI Hackathon 2026`;
- availability: public;
- duration: 130 seconds;
- playback format available: 1920×1080 video plus audio.

The local approved master has SHA-256
`1aa649223179de0d79a6e84fde07365d029488a10cbe0f69e5926c0d2632d786`
and size `13,903,422` bytes. The MP4 master and its raw production tree remain
local production artefacts; this repository records the public URL, captions,
and evidence without adding the binary video to Git history.

## AI and application authenticity

The configured model is `gemini-3.5-flash-lite`. The active implementation is
`backend/services/assistant.py`, which exposes five functions:

1. `create_payment_request`;
2. `get_wallet_summary`;
3. `get_policy_summary`;
4. `list_recent_transactions`; and
5. `get_transaction_details`.

The captured payment tools were genuine `create_payment_request` calls. Tool
arguments are revalidated through `PaymentRequest`; explicit amount,
vendor/recipient, requested PayPal Sandbox rail, authenticated owner, policy,
and idempotency requirements are checked again before the shared transaction
service runs.

Gemini does not approve or execute a payout. The transaction service evaluates
policy and reserves funds. The user performs the threshold approval. The
worker alone submits and reconciles PayPal Sandbox. Ledger capture requires the
individual payout item to return `SUCCESS`; batch acceptance alone is not
success.

The public **Explore demo** is a separate deterministic, labelled assistant
experience. It does not call Gemini or PayPal and is not presented in the
video as evidence of live AI.

## Captured workflow evidence

### Linear — `$49`

- Gemini tool: `create_payment_request`.
- Extracted vendor, amount, category, reason, recipient, and
  `paypal_sandbox_payouts` rail.
- Initial governed state: `executing`; human approval was not required.
- Final persisted state: `completed`.
- Provider item: `SUCCESS` / `PAYPAL_ITEM_SUCCESS`.
- Evidence: nine policy checks, one execution attempt, two balanced ledger
  entries, and seven lifecycle events.

### Figma Teams — `$120`

- Gemini tool: `create_payment_request`.
- Initial governed state: `pending_approval`.
- Policy: `$100` approval threshold stopped automatic execution.
- Human action: explicit approval in the authenticated UI.
- Final persisted state: `completed`.
- Provider item: `SUCCESS` / `PAYPAL_ITEM_SUCCESS`.
- Evidence: eight passing checks plus the failed threshold check, one execution
  attempt, two balanced ledger entries, and nine lifecycle events.

The requesting account is also the approval actor. Independent maker-checker
separation is not implemented or claimed.

## Scene evidence

| Time | Evidence |
|---|---|
| 00:00–00:15 | Problem, Pactra positioning, and configured PayPal Sandbox surface. |
| 00:15–00:34 | Posted/reserved/available balances and versioned spending policy. |
| 00:34–00:55 | Authenticated Gemini assistant and genuine Linear tool call. |
| 00:55–01:16 | Linear receipt, worker boundary, provider item status, and ledger capture. |
| 01:16–01:40 | Figma Teams tool call, reserved funds, threshold decision, and human approval. |
| 01:40–01:54 | Worker-owned Figma execution and item-level reconciliation. |
| 01:54–02:05 | Policy, approval, attempt, lifecycle, audit, and balanced ledger evidence. |
| 02:05–02:10 | Pactra closing statement. |

## Privacy, copyright, and trademark review

- No credentials, tokens, cookies, private endpoints, or personal browser tabs
  were found in the complete 130-second review.
- The configured Sandbox recipient is covered by an editorial privacy band.
- The requester uses a synthetic dedicated test account.
- Music and sound effects are deterministic procedural synthesis; the retained
  production provenance records no third-party audio recording.
- Voiceover provenance records Kokoro-82M through `kokoro-onnx`, voice
  `am_michael`, with cloning disabled.
- Visible third-party names remain in the approved video: PayPal Sandbox
  throughout provider scenes, Linear approximately 00:34–01:22, Gemini
  approximately 00:43–00:52, and Figma Teams approximately 01:24–02:02.
- No separate permission record for the Linear, Figma Teams, or Gemini marks
  was found. Their appearance is descriptive text inside the demonstrated
  workflow, not a logo or endorsement claim, but the official rules use a
  strict permission standard. The owner must confirm permission or obtain
  organiser guidance before submission. The approved video was not silently
  changed or replaced during this audit.

## Quality control

- `ffprobe`: 130.000 seconds, 1920×1080, 30 fps, H.264/AAC, 48 kHz stereo.
- Full FFmpeg decode: passed with zero reported decode errors.
- Complete visual sampling: 2-second interval contact sheets spanning the
  entire timeline plus first/last frame inspection.
- Captions: 14 English cues; final cue ends at `00:02:09,613`.
- Local master, caption text, scene timings, README, and submission brief agree
  on the final filename and 130-second duration.

Authenticated YouTube Studio was not available in this environment. Public
player metadata and 1080p format availability were verified without changing
the upload, title, visibility, description, or channel settings.
