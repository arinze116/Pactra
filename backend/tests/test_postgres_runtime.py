"""Runtime checks that only execute against CI's migrated PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine
from backend.defaults import default_policy
from backend.models import User, Wallet
from backend.services.accounts import create_account
from backend.services.policies import get_current_policy, save_policy


pytestmark = pytest.mark.skipif(
    settings.is_sqlite,
    reason="PostgreSQL runtime contract runs in CI with the configured database",
)


def create_postgres_account() -> str:
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email=f"postgres-{uuid4()}@example.com",
            password_hash="unused-postgres-test-hash",
        )
        session.commit()
        return account.user.id


def test_postgresql_uuid_bindings_support_account_queries() -> None:
    user_id = create_postgres_account()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).one()
        wallet = session.exec(select(Wallet).where(Wallet.user_id == user_id)).one()
        assert user.id == user_id
        assert wallet.user_id == user_id
        assert get_current_policy(session, user_id).version == 1


def test_concurrent_policy_saves_allocate_distinct_versions() -> None:
    user_id = create_postgres_account()
    barrier = Barrier(2)

    def save(daily_limit_cents: int) -> int:
        policy = default_policy()
        policy["daily_limit_cents"] = daily_limit_cents
        with Session(engine, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            saved = save_policy(session, user_id=user_id, policy_json=policy)
            session.commit()
            return saved.version

    with ThreadPoolExecutor(max_workers=2) as executor:
        versions = list(executor.map(save, [51_000, 52_000]))

    assert sorted(versions) == [2, 3]
    with Session(engine) as session:
        assert get_current_policy(session, user_id).version == 3
