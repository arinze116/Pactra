"""Runtime checks that only execute against CI's migrated PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine
from backend.defaults import default_policy
from backend.models import (
    ApprovalAction,
    FundReservation,
    LedgerJournal,
    PaymentTransaction,
    User,
    Wallet,
)
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.services.policies import get_current_policy, save_policy
from backend.services.transactions import (
    AlreadyActioned,
    approve_transaction,
    create_payment_request,
    reject_transaction,
)
from backend.worker import reconciliation_lease


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


def test_reconciliation_worker_lease_allows_only_one_authority() -> None:
    with reconciliation_lease() as first_acquired:
        assert first_acquired is True
        with reconciliation_lease() as second_acquired:
            assert second_acquired is False


def test_concurrent_approval_and_rejection_have_one_terminal_winner() -> None:
    user_id = create_postgres_account()
    with Session(engine, expire_on_commit=False) as session:
        user = session.get(User, user_id)
        assert user is not None
        result = create_payment_request(
            session,
            user=user,
            payload={
                "type": "payout",
                "vendor": "Concurrency Contractor",
                "recipient": "concurrency@example.com",
                "amount_cents": 12_500,
                "currency": "USD",
                "category": "freelance",
                "reason": "Approval race regression",
                "rail": "internal_sandbox",
                "idempotency_key": f"approval-race-{uuid4()}",
                "source": "test",
            },
        )
        session.commit()
        transaction_id = result.transaction.id
        assert result.transaction.status == "pending_approval"

    barrier = Barrier(2)

    def decide(action: str) -> str:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait(timeout=10)
            try:
                if action == "approve":
                    transaction = approve_transaction(
                        session,
                        user=user,
                        transaction_id=transaction_id,
                        idempotency_key=f"approval-race-approve-{uuid4()}",
                    )
                else:
                    transaction = reject_transaction(
                        session,
                        user=user,
                        transaction_id=transaction_id,
                        idempotency_key=f"approval-race-reject-{uuid4()}",
                        reason="Concurrent rejection",
                    )
                session.commit()
                return transaction.status
            except AlreadyActioned:
                session.rollback()
                return "already_actioned"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(decide, ["approve", "reject"]))

    assert outcomes.count("already_actioned") == 1
    terminal = next(outcome for outcome in outcomes if outcome != "already_actioned")
    assert terminal in {"completed", "rejected"}

    with Session(engine) as session:
        transaction = session.get(PaymentTransaction, transaction_id)
        assert transaction is not None
        assert transaction.status == terminal
        assert len(
            session.exec(
                select(ApprovalAction).where(
                    ApprovalAction.transaction_id == transaction_id
                )
            ).all()
        ) == 1
        captures = session.exec(
            select(LedgerJournal).where(
                LedgerJournal.transaction_id == transaction_id,
                LedgerJournal.journal_type == "payment_capture",
            )
        ).all()
        reservation = session.exec(
            select(FundReservation).where(
                FundReservation.transaction_id == transaction_id
            )
        ).one()
        balance = wallet_balance(session, get_wallet_for_user(session, user_id))
        if terminal == "completed":
            assert len(captures) == 1
            assert reservation.status == "captured"
            assert balance.posted_cents == 87_500
        else:
            assert captures == []
            assert reservation.status == "released"
            assert balance.posted_cents == 100_000
        assert balance.reserved_cents == 0
