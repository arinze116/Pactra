# Pactra final PayPal AI Hackathon readiness audit

- Audit date: 2026-11-11
- Repository: <https://github.com/arinze116/Pactra>
- Authoritative base at audit start: `e8d96c3370a5527219924b50473dcd4998cda1a4`
- Live application: <https://pactra-nine.vercel.app>
- Public video: <https://youtu.be/685tzja9ey4>

## Scope and evidence labels

- **Verified**: inspected or executed during this audit.
- **Retained evidence**: supported by a cited historical record but not
  repeated during this audit.
- **Blocked**: cannot be completed without owner eligibility/IP evidence or a
  separately prohibited production/provider action.

Production remained read-only. No deployment, service restart, environment or
secret change, database migration, production-data mutation, PayPal request,
payout, reconciliation, Gemini request, or infrastructure operation occurred.

## Repository state before changes

| Item | Verified state |
|---|---|
| Repository root | `/home/ubuntu/pactra` |
| Remote | `https://github.com/arinze116/Pactra.git` |
| Existing local branch | `codex/post-release-hardening-20261110` |
| Existing local HEAD | `99bf646e54e1160386cd8380e827f97af6257ab6` |
| Fetched `origin/main` | `e8d96c3370a5527219924b50473dcd4998cda1a4` |
| Existing divergence | local branch one commit ahead and fifteen commits behind `origin/main` |
| Existing work | extensive untracked video-production artefacts; preserved and excluded from this release worktree |
| Open pull requests | none |
| Latest exact-main CI | run `42882155040`, success |
| Latest production monitor at audit start | run `43023643369`, success |

All audit edits were isolated in a detached worktree created from the fetched
`origin/main`. Existing local commits and untracked owner artefacts were not
modified, stashed, cleaned, or silently added.

## Official requirement verification

The official rules at
<https://paypalaihackathon.devpost.com/rules> returned HTTP 200 and were read on
2026-11-11. Verified requirements include a functional project, public source
repository, visible open-source licence, complete setup/run access, a public
YouTube demonstration under three minutes, and permission for third-party
trademarks or copyrighted material in the video. The five equally weighted
criteria are Technological Implementation, Design, Potential Impact,
Innovation/Idea, and Presentation.

GitHub reports the repository as public and detects the root MIT licence. The
live application, repository, YouTube URL, and official rules each returned
HTTP 200 during the audit.

## Architecture and claim verification

### Active AI implementation

`backend/services/assistant.py` is the active service imported by
`backend/main.py`. `backend/agent.py` is an unmounted compatibility shim whose
public `run` method fails closed.

- Configured production model: `gemini-3.5-flash-lite`.
- SDK: `google-genai==2.23.0`.
- Function tools: `create_payment_request`, `get_wallet_summary`,
  `get_policy_summary`, `list_recent_transactions`, and
  `get_transaction_details`.
- Automatic SDK function execution is disabled. Pactra executes allowlisted
  calls itself.
- Payment amount and vendor/recipient must be explicit in the current user
  message. PayPal Sandbox must be explicitly requested.
- Tool payloads are validated again through `PaymentRequest` and owner-scoped
  service calls.
- Tool results, errors, transaction IDs, messages, and audit events are
  persisted; the UI renders governed action/result cards.
- Demo principals never enter the Gemini branch.

### Payment and governance implementation

- Manual and assistant requests call the same `create_payment_request`
  transaction service.
- Policy evaluation precedes reservation and execution.
- Above-threshold requests remain `pending_approval`; approval re-evaluates
  current policy and uses a conditional state transition.
- Restricted vendors and other first-matching policy failures are persisted as
  blocked outcomes.
- Demo principals are rejected by the API/transaction service/PayPal service
  and excluded from worker queries.
- Only `backend/services/paypal.py`, called by `backend/worker.py`, invokes
  `PayPalClient.create_payout`.
- Batch acceptance is not ledger success. Only individual item `SUCCESS`
  captures the reservation and completes the transaction.
- Terminal item failure releases once; unknown outcomes remain reserved;
  returns/reversals/refunds use compensating journals.

No P0 financial-correctness or authorisation defect was found in the reviewed
paths. This audit did not refactor frozen payment, ledger, policy,
authentication, or infrastructure code.

## Final-video verification

| Check | Verified result |
|---|---|
| Local filename | `DEMO/VIDEO-PRODUCTION/pactra-hackathon-final.mp4` |
| SHA-256 | `1aa649223179de0d79a6e84fde07365d029488a10cbe0f69e5926c0d2632d786` |
| Local media | 130.000 seconds; 1920×1080; 30 fps; H.264/AAC; 48 kHz stereo |
| Full decode | PASS; FFmpeg reported no decode errors |
| Complete visual review | 2-second contact sheets covering the full timeline plus first/last frames |
| Captions | 14 English cues; final cue ends at 02:09.613; committed SRT matches the approved local SRT byte-for-byte |
| YouTube | public; 130 seconds; 1920×1080 playback format available |
| YouTube title | `Pactra : AI-Powered Payment Governance \| PayPal AI Hackathon 2026` |
| YouTube description | accurately states Gemini tool use, policy/approval controls, PayPal Sandbox, audit/ledger evidence, and no real-money transfer |

The retained capture evidence supports both demonstrated workflows: the `$49`
Linear request began `executing` and completed only after provider item
`SUCCESS`; the `$120` Figma Teams request began `pending_approval`, failed the
`$100` threshold check, received explicit human approval, and completed only
after provider item `SUCCESS`. Each has one completed attempt and two balanced
ledger entries.

Authenticated YouTube Studio was not available. Public metadata and playback
format were verified without changing the video or channel.

## Findings and disposition

| ID | Severity | Finding and evidence | Disposition |
|---|---|---|---|
| SUB-001 | P1 | README and `SUBMISSION.md` lacked the final YouTube URL and still called recording/upload unfinished. | Fixed. Both now link the exact public video and record its verified duration/status. |
| SUB-002 | P1 | The submission checklist was not a judge-facing description and did not explain the tools used. | Fixed. `SUBMISSION.md` now covers problem, users, differentiation, Gemini, PayPal, architecture, hackathon-period work, access, tools, and limitations. |
| SUB-003 | P1 | Judge access and the distinction between deterministic demo and authenticated Gemini were not prominent enough. | Fixed in README and submission brief; no shared credentials were invented. |
| SUB-004 | P1 | README lacked embedded current product visuals. | Fixed with three existing product screenshots and descriptive alt text. |
| DOC-001 | P2 | Video handover still said recording had not started. | Fixed with an explicit historical/superseded label and links to final evidence. |
| DOC-002 | P2 | Technical overview named migration `0005` and described only an isolated SQLite demo. | Fixed to distinguish the public PostgreSQL `0006` instant demo from local SQLite tests. |
| DOC-003 | P2 | `.env.example` implied all demo data came from the legacy script. | Fixed to distinguish public API-created sessions from isolated scripted rehearsal data. |
| DOC-004 | P2 | Older `DEMO.md` and `DEMO-CHECKLIST.md` could be mistaken for the approved final walkthrough. | Preserved as historical records and linked to current evidence. |
| VID-001 | P1 owner decision | The approved video visibly names Linear, Figma Teams, and Gemini. No separate permission record was found. Official rules require permission for third-party marks. | Not silently altered. Owner must confirm permission or obtain organiser guidance before Devpost submission. Exact timing is recorded in the production report. |
| ELG-001 | P1 owner decision | Entrant age-of-majority and legal eligibility cannot be established from repository evidence. | Owner must resolve directly against the official rules/organisers. No identity or age data was entered or inferred. |
| A11Y-001 | P2 residual | Automated Axe/keyboard checks exist, but manual NVDA/VoiceOver validation is not recorded. | Disclosed in README and submission brief; no false manual-accessibility claim. |
| DEP-001 | P3 deferred | `npm ci` warns that pinned ESLint 9.39.5 is no longer supported; several major upgrades are available. Audits report zero vulnerabilities. | Retained to avoid last-minute ecosystem migration risk. Revisit after the hackathon. |

## Dependency and security review

- `npm ci`: lockfile-consistent install; zero vulnerabilities.
- Production and full npm audits: zero vulnerabilities.
- `pip check`: no broken requirements.
- `pip-audit -r requirements.txt`: no known vulnerabilities.
- Tracked secret-pattern scan found only empty configuration fields and
  explicit test placeholders.
- No non-example `.env` file or tracked file above 5 MiB exists.
- No broad dependency upgrade was made; `google-genai` remains pinned at the
  tested 2.23.0 integration.

## Verification record

### Local and isolated checks

| Check | Result |
|---|---|
| `/tmp/pactra-final-venv/bin/python -m compileall -q backend scripts` | PASS |
| SQLite migration through `20261110_0006` | PASS |
| SQLite `python -m pytest -q -ra` | PASS: 150 passed, 12 PostgreSQL-only skips |
| Ephemeral PostgreSQL 17 migration and `python -m pytest -q -ra` | PASS: 162 passed; the disposable Docker container was removed |
| `npm ci` | PASS: committed lockfile installed; zero vulnerabilities |
| `npm run lint` | PASS |
| `npm run build` | PASS: 1,605 modules transformed |
| `npm run test:demo` | PASS: 4 passed |
| E2E journeys in Chromium and Firefox | PASS: 94 passed |
| E2E journeys in local WebKit | BLOCKED before assertions: host lacks `libgstreamer-plugins-bad1.0-0` and `libavif16`; no system package was installed |
| Axe WCAG suite in Chromium and Firefox | PASS: 2 passed |
| CI-equivalent homepage Lighthouse assertion | PASS: performance 0.97, accessibility 1.00, best practices 0.96 |
| `npm audit --omit=dev --audit-level=high` | PASS: zero vulnerabilities |
| `npm audit --audit-level=moderate` | PASS: zero vulnerabilities |
| `pip check` | PASS |
| `pip-audit -r requirements.txt` | PASS: no known vulnerabilities |
| Full MP4 FFmpeg decode | PASS |
| Internal Markdown links and key external URLs | PASS |
| Tracked secret-pattern and large-file scan | PASS |

The local aggregate `npm run test:e2e` exited non-zero only because all 47
WebKit journey cases could not launch on this host. Chromium and Firefox
completed the same 47 cases each without a failure. The required GitHub E2E
job installs all Playwright system dependencies and is the authoritative
WebKit gate.

- Release branch: `chore/final-paypal-hackathon-readiness`
- Pull request: <https://github.com/arinze116/Pactra/pull/24>

The exact final-head CI run and merge SHA are generated after this audit file
is committed, so they are reported in the owner completion report rather than
retroactively written into this evidence snapshot.

## Outstanding owner actions

1. Confirm entrant eligibility, including age of majority, directly against
   the official rules.
2. Confirm permission or obtain organiser guidance for third-party names in
   the approved video.
3. Review the merged repository and complete the Devpost submission personally.

Repository-level completion does not resolve these owner-level gates and is
not an eligibility determination.
