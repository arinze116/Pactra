# Pactra External Blockers

Updated: 2026-11-09

The previous staged baseline passed `main` CI. Run
[42577769242](https://github.com/arinze116/Pactra/actions/runs/42577769242)
passed all four mandatory jobs on exact SHA
`4ac86897cf66f66df5d80d024f00e315999f7b95`. PR #8 supersedes that candidate;
its exact merge commit, successful final-main CI run, and new immutable
`.release-sha` are the authority for the next release. The remaining release
gates require external provider state or separately authorized production
operations.

1. **Gemini quota or entitlement**
   - Production is configured for `gemini-3.8-flash`.
   - The latest live request returned `429 RESOURCE_EXHAUSTED`.
   - Required action: restore quota/entitlement, then authorize one bounded
     generation/function-call acceptance check.

2. **PayPal Sandbox payout capability**
   - Sandbox configuration and prior OAuth succeeded.
   - The prior authorized payout was denied because the recipient could not
     accept it. Credentials and recipient were subsequently updated.
   - Required action: separately authorize exactly one bounded Sandbox payout
     through the worker-only candidate after deployment or in an isolated
     approved environment. Item-level `SUCCESS` is required.

3. **PayPal guided scenario**
   - It cannot pass until a real payout item reaches `SUCCESS` and the Pactra
     ledger reconciles exactly once.

4. **Deployment approval**
   - `/opt/pactra/releases/4ac8689` is the inactive historical candidate and
     must not be activated after PR #8.
   - Deployment requires a new immutable release whose `.release-sha` matches
     the successful integrated-main CI commit.
   - Required action after provider gates: approve backup, service stop,
     migration `0005`, release switch, API/worker restart, and Vercel frontend
     deployment.

5. **Public acceptance**
   - Required only after deployment: fresh-account smoke, provider journeys,
     responsive review, and production logs/database invariant checks.

Do not paste credentials into chat. No credential, restart, deployment,
migration, payout, or production-data operation is authorized by this report.
