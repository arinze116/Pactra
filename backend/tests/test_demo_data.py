"""The demo dataset is deterministic and cannot target production data."""

from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.auth import verify_password
from backend.demo_data import (
    DEMO_EMAIL,
    seed_demo_dataset,
    validated_demo_database_path,
)
from backend.diagnostics.invariants import collect_financial_invariants
from backend.models import PaymentTransaction, User
from scripts.demo_environment import assert_resettable_database


def test_demo_database_guard_requires_explicit_demo_sqlite_path(tmp_path: Path) -> None:
    safe_url = f"sqlite:///{tmp_path / 'pactra-demo-rehearsal.db'}"
    assert validated_demo_database_path(safe_url, "demo").name == (
        "pactra-demo-rehearsal.db"
    )
    with pytest.raises(ValueError, match="APP_ENV=demo"):
        validated_demo_database_path(safe_url, "production")
    with pytest.raises(ValueError, match="filename"):
        validated_demo_database_path(
            f"sqlite:///{tmp_path / 'customer-data.db'}", "demo"
        )
    with pytest.raises(ValueError, match="SQLite"):
        validated_demo_database_path(
            "postgresql+psycopg://localhost/pactra", "demo"
        )


def test_demo_seed_is_idempotent_and_financially_consistent() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        first = seed_demo_dataset(session)
        second = seed_demo_dataset(session)
        transactions = list(session.exec(select(PaymentTransaction)).all())
        report = collect_financial_invariants(session)

    assert first.replayed is False
    assert second.replayed is True
    assert first.email == DEMO_EMAIL
    with Session(engine) as session:
        fixture_user = session.exec(
            select(User).where(User.email == DEMO_EMAIL)
        ).one()
        assert fixture_user.is_demo
        assert fixture_user.display_name == "Pactra local demo fixture"
        assert not verify_password("PactraDemo2026!", fixture_user.password_hash)
    assert first.transaction_ids == second.transaction_ids
    assert {item.status for item in transactions} == {
        "blocked",
        "completed",
        "pending_approval",
        "rejected",
    }
    assert first.posted_cents == 95_100
    assert first.reserved_cents == 12_500
    assert first.available_cents == 82_600
    assert report.passed is True
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def test_reset_guard_rejects_any_non_demo_user(tmp_path: Path) -> None:
    path = tmp_path / "pactra-demo-guard.db"
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="customer@example.com", password_hash="not-used"))
        session.commit()
    engine.dispose()

    with pytest.raises(RuntimeError, match="non-demo users"):
        assert_resettable_database(path)

    assert DEMO_EMAIL != "customer@example.com"
