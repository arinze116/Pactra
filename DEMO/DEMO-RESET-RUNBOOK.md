# Pactra Demo Reset Runbook

Reset is destructive only to an explicitly named isolated demo SQLite file.
It is not a production or general development reset command.

## Preconditions

```bash
test "$APP_ENV" = demo
test "$DATABASE_URL" = sqlite:////tmp/pactra-demo-live.db
```

The application performs its own stronger validation; these shell checks are
only an operator reminder.

## Reset

Stop the local demo API, then run:

```bash
python -m scripts.demo_environment reset --confirm RESET_PACTRA_DEMO
python -m scripts.demo_environment status
```

Expected status:

```json
{
  "dataset_marker_count": 1,
  "ready": true,
  "transaction_count": 4,
  "user_count": 1
}
```

Restart only the local demo API. Do not run this command through a production
unit, production working directory, or `/etc/pactra/pactra.env`.

## Seed without reset

```bash
python -m scripts.demo_environment seed --confirm SEED_PACTRA_DEMO
```

This is idempotent and useful if a migrated demo database has not been seeded.

## Refusal conditions

The command must stop for production/non-demo environment, PostgreSQL, a
relative path, a filename outside `pactra-demo-*.db`, a symlink, a production
path, the default development database, wrong confirmation, wrong migration,
or an existing non-demo user.

Never weaken these guards to recover a presentation. Choose a new temporary
demo filename instead.

## Verification

The reset path and its refusal behavior are covered by backend tests. The full
Playwright demo invokes reset before every run and passed on 2026-11-09.
