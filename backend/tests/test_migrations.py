"""Clean-database migration verification for the judge-ready schema."""

import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, dialect as postgres_dialect

from backend.models import SQLModel


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
    conversation_columns = {
        column["name"] for column in inspector.get_columns("conversations")
    }
    message_columns = {
        column["name"] for column in inspector.get_columns("conversation_messages")
    }
    message_indexes = {
        index["name"]: index
        for index in inspector.get_indexes("conversation_messages")
    }

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
    assert {"title", "archived_at"}.issubset(conversation_columns)
    assert "request_id" in message_columns
    assert message_indexes["uq_messages_request_role"]["unique"] == 1
    assert message_indexes["uq_messages_request_role"]["column_names"] == [
        "conversation_id",
        "request_id",
        "role",
    ]
    assert revision == "20261107_0004"


def test_runtime_models_use_postgresql_uuid_for_migrated_identifiers() -> None:
    identifier_columns = {
        "users": ["id"],
        "sessions": ["id", "user_id"],
        "ledger_accounts": ["id", "user_id"],
        "wallets": ["id", "user_id", "ledger_account_id"],
        "policies": ["id", "user_id", "created_by"],
        "transactions": ["id", "user_id"],
        "ledger_journals": ["id", "user_id", "transaction_id"],
        "ledger_entries": ["id", "journal_id", "account_id"],
        "fund_reservations": ["id", "user_id", "wallet_id", "transaction_id"],
        "transaction_attempts": ["id", "transaction_id"],
        "approval_actions": ["id", "transaction_id", "user_id"],
        "audit_events": ["id", "user_id", "actor_id", "entity_id"],
        "conversations": ["id", "user_id"],
        "conversation_messages": ["id", "conversation_id"],
    }
    pg = postgres_dialect()
    for table_name, column_names in identifier_columns.items():
        table = SQLModel.metadata.tables[table_name]
        for column_name in column_names:
            assert isinstance(
                table.c[column_name].type.dialect_impl(pg), PostgresUUID
            ), f"{table_name}.{column_name} must bind as PostgreSQL UUID"
