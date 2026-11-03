"""Clean-database migration verification for the judge-ready schema."""

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_initial_migration_builds_clean_sqlite_database(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": database_url,
            "PAYPAL_MOCK_MODE": "true",
            "SESSION_COOKIE_SECURE": "false",
        }
    )

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(database_url)
    inspector = inspect(engine)
    expected_tables = {
        "users",
        "sessions",
        "ledger_accounts",
        "wallets",
        "ledger_journals",
        "ledger_entries",
        "fund_reservations",
        "policies",
        "transactions",
        "transaction_attempts",
        "approval_actions",
        "audit_events",
        "conversations",
        "conversation_messages",
        "alembic_version",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))

    with engine.connect() as connection:
        system_accounts = connection.execute(
            text(
                "SELECT code, account_type FROM ledger_accounts "
                "WHERE user_id IS NULL ORDER BY code"
            )
        ).all()
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert system_accounts == [
        ("sandbox_clearing_usd", "sandbox_clearing"),
        ("sandbox_issuance_usd", "sandbox_issuance"),
    ]
    assert revision == "20261103_0001"
