# Pactra Demo Data

Dataset version: 1

All names, addresses, balances, and transactions are fictional.

## Account

- Business/user: Pactra demo workspace
- Email: `demo@pactra-demo.example.com`
- Password: `PactraDemo2026!`
- Environment: local `APP_ENV=demo` only

## Seeded financial state

Initial sandbox funding is `$1,000.00`.

| Record | Amount | State | Effect |
|---|---:|---|---|
| Linear subscription | `$49.00` | completed | one internal capture |
| Ada Contractor milestone | `$125.00` | pending approval | one active reservation |
| Northwind Office Supply | `$120.00` | rejected | no capture/reservation |
| Mega Cloud Renewal | `$200.00` | blocked | no capture/reservation |

Seed result:

- posted: `$951.00`;
- reserved: `$125.00`;
- available: `$826.00`;
- transaction states: completed, pending approval, rejected, blocked;
- one `demo.dataset_seeded` audit marker.

## Rehearsal additions

The automated demo creates:

- Figma `$35.00` internal completed payment;
- Notion `$20.00` assistant/fallback completed payment;
- a second blocked Mega Cloud Renewal `$200.00` assistant request;
- approval and completion of the seeded Ada Contractor `$125.00` request.

After the full script, posted/reserved/available are `$771.00 / $0.00 / $771.00`.

## Idempotency

Seed transaction/action keys are stable. Re-running `seed` returns the same
transaction IDs and does not duplicate journals, reservations, or audit
markers. Reset recreates the designated demo database from migrations and then
seeds it.

The seed refuses an existing database containing any non-demo user.
