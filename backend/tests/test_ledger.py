"""Double-entry balance, reservation and concurrency invariant tests."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import event, func
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.models import (
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    User,
)
from backend.services.accounts import create_account
from backend.services.ledger import (
    IdempotencyConflict,
    InsufficientFunds,
    LedgerError,
    capture_reservation,
    get_wallet_for_user,
    post_journal,
    release_reservation,
    reserve_funds,
    top_up_wallet,
    wallet_balance,
)


def make_engine(url: str, *, shared_memory: bool = False):
    kwargs = {"connect_args": {"check_same_thread": False, "timeout": 30}}
    if shared_memory:
        kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def ledger_db():
    engine = make_engine("sqlite://", shared_memory=True)
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email="ledger@example.com",
            password_hash="unused-test-hash",
        )
        yield session, account.user
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def transaction_for(user: User, *, amount_cents: int, key: str) -> PaymentTransaction:
    return PaymentTransaction(
        user_id=user.id,
        idempotency_key=key,
        type="vendor_payment",
        vendor="Linear",
        recipient=None,
        amount_cents=amount_cents,
        currency="USD",
        category="software",
        reason="Subscription",
        status="pending_approval",
        sandbox_generation=1,
        policy_version=1,
        policy_result={"decision": "requires_approval"},
        rail="internal_sandbox",
    )


def test_initial_issuance_and_topup_are_balanced_and_idempotent(ledger_db) -> None:
    session, user = ledger_db
    wallet = get_wallet_for_user(session, user.id)
    assert wallet_balance(session, wallet).posted_cents == 100_000

    initial = session.exec(
        select(LedgerJournal).where(LedgerJournal.journal_type == "initial_issuance")
    ).one()
    entries = session.exec(
        select(LedgerEntry).where(LedgerEntry.journal_id == initial.id)
    ).all()
    assert len(entries) == 2
    assert sum(e.amount_cents for e in entries if e.direction == "debit") == 100_000
    assert sum(e.amount_cents for e in entries if e.direction == "credit") == 100_000

    first, first_balance = top_up_wallet(
        session,
        user_id=user.id,
        amount_cents=50_000,
        idempotency_key="ledger-topup-1",
    )
    session.commit()
    replay, replay_balance = top_up_wallet(
        session,
        user_id=user.id,
        amount_cents=50_000,
        idempotency_key="ledger-topup-1",
    )
    session.commit()
    assert first.id == replay.id
    assert first_balance.posted_cents == replay_balance.posted_cents == 150_000

    with pytest.raises(IdempotencyConflict):
        top_up_wallet(
            session,
            user_id=user.id,
            amount_cents=100_000,
            idempotency_key="ledger-topup-1",
        )


def test_posting_rejects_another_users_wallet(ledger_db) -> None:
    session, user = ledger_db
    other = create_account(
        session,
        email="other@example.com",
        password_hash="unused-test-hash",
    )
    other_wallet = get_wallet_for_user(session, other.user.id)
    user_wallet = get_wallet_for_user(session, user.id)

    with pytest.raises(LedgerError, match="does not belong"):
        post_journal(
            session,
            user_id=user.id,
            journal_type="invalid_cross_user",
            idempotency_key="cross-user-post",
            amount_cents=100,
            debit_account_id=user_wallet.ledger_account_id,
            credit_account_id=other_wallet.ledger_account_id,
        )


def test_reserve_release_and_capture_never_make_balance_negative(ledger_db) -> None:
    session, user = ledger_db
    first = transaction_for(user, amount_cents=70_000, key="reserve-1")
    second = transaction_for(user, amount_cents=40_000, key="reserve-2")
    session.add_all([first, second])
    session.flush()

    reservation = reserve_funds(session, user_id=user.id, transaction=first)
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert reservation.amount_cents == 70_000
    assert balance.available_cents == 30_000
    assert balance.reserved_cents == 70_000
    with pytest.raises(InsufficientFunds):
        reserve_funds(session, user_id=user.id, transaction=second)

    release_reservation(
        session, user_id=user.id, transaction_id=first.id, reason="rejected"
    )
    assert wallet_balance(session, get_wallet_for_user(session, user.id)).available_cents == 100_000

    reserve_funds(session, user_id=user.id, transaction=second)
    journal = capture_reservation(session, user_id=user.id, transaction=second)
    session.commit()
    assert journal.journal_type == "payment_capture"
    final = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert final.posted_cents == final.available_cents == 60_000
    assert final.reserved_cents == 0
    assert capture_reservation(session, user_id=user.id, transaction=second).id == journal.id


def test_concurrent_reservations_cannot_overdraw_wallet(tmp_path: Path) -> None:
    database_path = tmp_path / "concurrency.db"
    engine = make_engine(f"sqlite:///{database_path.as_posix()}")
    with Session(engine, expire_on_commit=False) as setup:
        account = create_account(
            setup,
            email="concurrency@example.com",
            password_hash="unused-test-hash",
        )
        user_id = account.user.id

    barrier = Barrier(2)

    def attempt_reservation(index: int) -> str:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, user_id)
            assert user is not None
            transaction = transaction_for(
                user, amount_cents=70_000, key=f"concurrent-{index}"
            )
            session.add(transaction)
            barrier.wait(timeout=5)
            try:
                session.flush()
                reserve_funds(session, user_id=user_id, transaction=transaction)
                session.commit()
                return "reserved"
            except InsufficientFunds:
                session.rollback()
                return "insufficient"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt_reservation, (1, 2)))
    assert sorted(outcomes) == ["insufficient", "reserved"]

    with Session(engine) as session:
        wallet = get_wallet_for_user(session, user_id)
        balance = wallet_balance(session, wallet)
        assert balance.available_cents == 30_000
        assert balance.reserved_cents == 70_000
        assert session.exec(select(func.count(PaymentTransaction.id))).one() == 1
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
