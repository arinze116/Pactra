"""Policy precedence and unified internal transaction lifecycle tests."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.defaults import default_policy
from backend.models import FundReservation, LedgerJournal, PaymentTransaction, User
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.services.policies import save_policy
from backend.services.transactions import (
    AlreadyActioned,
    PolicyBlocked,
    PolicyChanged,
    TransactionIdempotencyConflict,
    approve_transaction,
    create_payment_request,
    reject_transaction,
    retry_transaction,
    reverse_transaction,
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
def transaction_db():
    engine = make_engine("sqlite://", shared_memory=True)
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email="payments@example.com",
            password_hash="unused-test-hash",
        )
        yield session, account.user
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def payment_payload(
    *, amount_cents: int, key: str, category: str = "software", vendor: str = "Linear"
) -> dict[str, object]:
    return {
        "type": "vendor_payment",
        "vendor": vendor,
        "recipient": None,
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": category,
        "reason": "Monthly subscription",
        "rail": "internal_sandbox",
        "idempotency_key": key,
        "source": "manual",
    }


def test_auto_payment_captures_once_and_reversal_compensates(transaction_db) -> None:
    session, user = transaction_db
    payload = payment_payload(amount_cents=4_900, key="payment-auto-0001")
    result = create_payment_request(session, user=user, payload=payload)
    session.commit()

    assert result.transaction.status == "completed"
    assert result.policy_result["decision"] == "approved"
    wallet = get_wallet_for_user(session, user.id)
    assert wallet_balance(session, wallet).posted_cents == 95_100
    captures = session.exec(
        select(LedgerJournal).where(LedgerJournal.journal_type == "payment_capture")
    ).all()
    assert len(captures) == 1

    replay = create_payment_request(session, user=user, payload=payload)
    session.commit()
    assert replay.replayed is True
    assert replay.transaction.id == result.transaction.id
    assert wallet_balance(session, wallet).posted_cents == 95_100

    with pytest.raises(TransactionIdempotencyConflict):
        create_payment_request(
            session,
            user=user,
            payload={**payload, "amount_cents": 5_000},
        )

    transaction, reversal = reverse_transaction(
        session,
        user=user,
        transaction_id=result.transaction.id,
        idempotency_key="reverse-auto-0001",
        reason="Duplicate vendor invoice",
    )
    session.commit()
    assert transaction.status == "reversed"
    assert reversal.journal_type == "payment_reversal"
    assert wallet_balance(session, wallet).posted_cents == 100_000


def test_approval_reserves_then_captures_and_is_single_use(transaction_db) -> None:
    session, user = transaction_db
    result = create_payment_request(
        session,
        user=user,
        payload=payment_payload(
            amount_cents=12_500,
            key="payment-approval-0001",
            category="freelance",
            vendor="Ada Contractor",
        ),
    )
    session.commit()
    assert result.transaction.status == "pending_approval"
    assert result.balance.available_cents == 87_500
    assert result.balance.reserved_cents == 12_500

    approved = approve_transaction(
        session,
        user=user,
        transaction_id=result.transaction.id,
        idempotency_key="approve-payment-0001",
    )
    session.commit()
    assert approved.status == "completed"
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert balance.posted_cents == balance.available_cents == 87_500
    assert balance.reserved_cents == 0

    replay = approve_transaction(
        session,
        user=user,
        transaction_id=result.transaction.id,
        idempotency_key="approve-payment-0001",
    )
    assert replay.status == "completed"
    with pytest.raises(AlreadyActioned):
        approve_transaction(
            session,
            user=user,
            transaction_id=result.transaction.id,
            idempotency_key="approve-payment-0002",
        )


def test_rejection_releases_hold_without_posting(transaction_db) -> None:
    session, user = transaction_db
    result = create_payment_request(
        session,
        user=user,
        payload=payment_payload(
            amount_cents=12_000,
            key="payment-reject-0001",
            category="freelance",
        ),
    )
    session.commit()
    rejected = reject_transaction(
        session,
        user=user,
        transaction_id=result.transaction.id,
        idempotency_key="reject-payment-0001",
        reason="Invoice not verified",
    )
    session.commit()
    assert rejected.status == "rejected"
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert balance.posted_cents == balance.available_cents == 100_000
    reservation = session.exec(
        select(FundReservation).where(
            FundReservation.transaction_id == result.transaction.id
        )
    ).one()
    assert reservation.status == "released"


@pytest.mark.parametrize(
    ("policy_change", "payload_change", "reason_code"),
    [
        ({"allowed_categories": ["ops"]}, {}, "CATEGORY_NOT_ALLOWED"),
        ({"blocked_vendors": ["Linear"]}, {}, "VENDOR_BLOCKED"),
        ({"per_transaction_limit_cents": 4_000}, {}, "TRANSACTION_LIMIT_EXCEEDED"),
        ({"daily_limit_cents": 4_000}, {}, "DAILY_LIMIT_EXCEEDED"),
        (
            {"category_budgets_cents": {"ops": 15_000, "software": 4_000, "cloud": 10_000, "freelance": 15_000}},
            {},
            "CATEGORY_BUDGET_EXCEEDED",
        ),
    ],
)
def test_policy_block_reason_precedence(
    transaction_db, policy_change, payload_change, reason_code
) -> None:
    session, user = transaction_db
    policy = default_policy()
    policy.update(policy_change)
    if policy_change.get("allowed_categories") == ["ops"]:
        policy["category_budgets_cents"] = {"ops": 15_000}
    save_policy(session, user_id=user.id, policy_json=policy)
    session.commit()

    with pytest.raises(PolicyBlocked) as caught:
        create_payment_request(
            session,
            user=user,
            payload={
                **payment_payload(amount_cents=4_900, key=f"blocked-{reason_code}"),
                **payload_change,
            },
        )
    session.commit()
    assert caught.value.decision.reason_code == reason_code
    assert caught.value.transaction.status == "blocked"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 100_000


def test_policy_version_change_requires_review_before_approval(transaction_db) -> None:
    session, user = transaction_db
    result = create_payment_request(
        session,
        user=user,
        payload=payment_payload(
            amount_cents=12_000,
            key="policy-change-payment",
            category="freelance",
        ),
    )
    session.commit()
    policy = default_policy()
    policy["approval_threshold_cents"] = 5_000
    save_policy(session, user_id=user.id, policy_json=policy)
    session.commit()

    with pytest.raises(PolicyChanged) as caught:
        approve_transaction(
            session,
            user=user,
            transaction_id=result.transaction.id,
            idempotency_key="policy-change-approve-1",
        )
    session.commit()
    assert caught.value.transaction.policy_version == 2
    assert caught.value.transaction.status == "pending_approval"

    approved = approve_transaction(
        session,
        user=user,
        transaction_id=result.transaction.id,
        idempotency_key="policy-change-approve-2",
    )
    session.commit()
    assert approved.status == "completed"


def test_failed_internal_transaction_can_retry_once(transaction_db) -> None:
    session, user = transaction_db
    transaction = PaymentTransaction(
        user_id=user.id,
        idempotency_key="failed-business-request",
        type="vendor_payment",
        vendor="Linear",
        recipient=None,
        amount_cents=4_900,
        currency="USD",
        category="software",
        reason="Monthly subscription",
        status="failed",
        sandbox_generation=1,
        policy_version=1,
        policy_result={"decision": "approved"},
        rail="internal_sandbox",
        failure_code="TEMPORARY_INTERNAL_FAILURE",
    )
    session.add(transaction)
    session.commit()

    retried, attempt = retry_transaction(
        session,
        user=user,
        transaction_id=transaction.id,
        idempotency_key="retry-failed-payment-0001",
    )
    session.commit()
    assert retried.status == "completed"
    assert attempt.attempt_number == 1
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 95_100

    replayed, replayed_attempt = retry_transaction(
        session,
        user=user,
        transaction_id=transaction.id,
        idempotency_key="retry-failed-payment-0001",
    )
    assert replayed.status == "completed"
    assert replayed_attempt.id == attempt.id


def test_concurrent_policy_reservations_do_not_exceed_category_budget(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "transaction-concurrency.db"
    engine = make_engine(f"sqlite:///{database_path.as_posix()}")
    with Session(engine, expire_on_commit=False) as setup:
        account = create_account(
            setup,
            email="tx-concurrency@example.com",
            password_hash="unused-test-hash",
        )
        user_id = account.user.id
    barrier = Barrier(2)

    def attempt(index: int) -> str:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait(timeout=5)
            try:
                result = create_payment_request(
                    session,
                    user=user,
                    payload=payment_payload(
                        amount_cents=12_000,
                        key=f"concurrent-payment-{index}",
                        category="freelance",
                    ),
                )
                session.commit()
                return result.transaction.status
            except PolicyBlocked:
                session.commit()
                return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (1, 2)))
    assert sorted(outcomes) == ["blocked", "pending_approval"]

    with Session(engine) as session:
        active_holds = session.exec(
            select(FundReservation).where(FundReservation.status == "active")
        ).all()
        assert len(active_holds) == 1
        assert sum(hold.amount_cents for hold in active_holds) == 12_000
        transactions = session.exec(select(PaymentTransaction)).all()
        assert sorted(transaction.status for transaction in transactions) == [
            "blocked",
            "pending_approval",
        ]
    SQLModel.metadata.drop_all(engine)
    engine.dispose()

