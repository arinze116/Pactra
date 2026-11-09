"""Runtime checks that only execute against CI's migrated PostgreSQL database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session, select

from backend.config import settings
from backend.auth import FixedWindowRateLimiter
from backend.database import engine
from backend.defaults import default_policy
from backend.errors import ApiError
from backend.models import (
    ApprovalAction,
    AuditEvent,
    FundReservation,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
    User,
    Wallet,
)
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.services.policies import get_current_policy, save_policy
from backend.services.transactions import (
    AlreadyActioned,
    PolicyBlocked,
    approve_transaction,
    create_payment_request,
    reject_transaction,
)
from backend.worker import claim_paypal_transaction, reconciliation_lease


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


def test_concurrent_worker_claims_have_one_winner() -> None:
    user_id = create_postgres_account()
    with Session(engine, expire_on_commit=False) as session:
        transaction = PaymentTransaction(
            user_id=user_id,
            idempotency_key=f"postgres-paypal-claim-{uuid4()}",
            type="payout",
            vendor="Sandbox claim test",
            recipient="claim-test@example.com",
            amount_cents=100,
            currency="USD",
            category="freelance",
            reason="Concurrent worker claim regression",
            status="executing",
            sandbox_generation=1,
            policy_version=1,
            policy_result={"decision": "approved"},
            rail="paypal_sandbox_payouts",
        )
        session.add(transaction)
        session.flush()
        session.add(
            TransactionAttempt(
                transaction_id=transaction.id,
                attempt_number=1,
                rail="paypal_sandbox_payouts",
                rail_request_id=f"pactra-{transaction.id}-a1",
                status="submitting",
            )
        )
        session.commit()
        transaction_id = transaction.id

    first_claimed = Event()
    release_first = Event()

    def hold_first_claim() -> bool:
        with Session(engine, expire_on_commit=False) as session:
            claimed = claim_paypal_transaction(
                session,
                transaction_id=transaction_id,
            )
            first_claimed.set()
            assert release_first.wait(timeout=10)
            session.rollback()
            return claimed is not None

    def competing_claim() -> bool:
        assert first_claimed.wait(timeout=10)
        with Session(engine, expire_on_commit=False) as session:
            claimed = claim_paypal_transaction(
                session,
                transaction_id=transaction_id,
            )
            session.rollback()
        release_first.set()
        return claimed is not None

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(hold_first_claim)
        second = executor.submit(competing_claim)
        assert [first.result(timeout=15), second.result(timeout=15)] == [True, False]


def test_shared_rate_limit_is_atomic_across_independent_process_state() -> None:
    key = f"postgres-shared-rate-limit-{uuid4()}"
    barrier = Barrier(10)

    def attempt(index: int) -> int:
        limiter = FixedWindowRateLimiter()
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                limiter.check(
                    session,
                    key,
                    limit=5,
                    window=timedelta(minutes=5),
                )
            except ApiError as exc:
                assert exc.status_code == 429
                assert exc.details is not None
                assert int(exc.details["retry_after_seconds"]) > 0
                return exc.status_code
        return 200

    with ThreadPoolExecutor(max_workers=10) as executor:
        statuses = list(executor.map(attempt, range(10)))

    assert statuses.count(200) == 5
    assert statuses.count(429) == 5

    with Session(engine) as session:
        with pytest.raises(ApiError) as blocked:
            FixedWindowRateLimiter().check(
                session,
                key,
                limit=5,
                window=timedelta(minutes=5),
            )
    assert blocked.value.status_code == 429


def test_posted_ledger_journal_and_entry_set_are_immutable() -> None:
    user_id = create_postgres_account()
    with Session(engine) as session:
        journal = session.exec(
            select(LedgerJournal).where(
                LedgerJournal.user_id == user_id,
                LedgerJournal.journal_type == "initial_issuance",
            )
        ).one()
        entry = session.exec(
            select(LedgerEntry).where(LedgerEntry.journal_id == journal.id)
        ).first()
        assert entry is not None
        journal_id = journal.id
        account_id = entry.account_id

    with Session(engine) as session:
        with pytest.raises(DBAPIError, match="posted ledger journals are immutable"):
            session.exec(
                text(
                    "UPDATE ledger_journals SET journal_type = 'tampered' "
                    "WHERE id = CAST(:journal_id AS uuid)"
                ),
                params={"journal_id": journal_id},
            )
            session.commit()
        session.rollback()

    with Session(engine) as session:
        with pytest.raises(
            DBAPIError,
            match="posted ledger journal entry sets are immutable",
        ):
            session.exec(
                text(
                    "INSERT INTO ledger_entries "
                    "(id, journal_id, account_id, direction, amount_cents, currency, created_at) "
                    "VALUES (CAST(:entry_id AS uuid), CAST(:journal_id AS uuid), "
                    "CAST(:account_id AS uuid), 'debit', 1, 'USD', CURRENT_TIMESTAMP)"
                ),
                params={
                    "entry_id": str(uuid4()),
                    "journal_id": journal_id,
                    "account_id": account_id,
                },
            )
            session.commit()
        session.rollback()


def test_audit_events_are_immutable() -> None:
    user_id = create_postgres_account()
    with Session(engine) as session:
        event = session.exec(
            select(AuditEvent).where(AuditEvent.user_id == user_id)
        ).first()
        assert event is not None
        event_id = event.id

    with Session(engine) as session:
        with pytest.raises(DBAPIError, match="audit events are immutable"):
            session.exec(
                text(
                    "UPDATE audit_events SET event_type = 'tampered' "
                    "WHERE id = CAST(:event_id AS uuid)"
                ),
                params={"event_id": event_id},
            )
            session.commit()
        session.rollback()

    with Session(engine) as session:
        with pytest.raises(DBAPIError, match="audit events are immutable"):
            session.exec(
                text(
                    "DELETE FROM audit_events WHERE id = CAST(:event_id AS uuid)"
                ),
                params={"event_id": event_id},
            )
            session.commit()
        session.rollback()

def test_concurrent_requests_cannot_overreserve_one_wallet() -> None:
    user_id = create_postgres_account()
    with Session(engine, expire_on_commit=False) as session:
        policy = default_policy()
        policy["daily_limit_cents"] = 200_000
        policy["per_transaction_limit_cents"] = 100_000
        policy["approval_threshold_cents"] = 0
        policy["category_budgets_cents"]["software"] = 200_000
        save_policy(session, user_id=user_id, policy_json=policy)
        session.commit()

    barrier = Barrier(2)

    def request_payment(index: int) -> tuple[str, str | None]:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait(timeout=10)
            try:
                result = create_payment_request(
                    session,
                    user=user,
                    payload={
                        "type": "vendor_payment",
                        "vendor": f"Concurrent Vendor {index}",
                        "recipient": None,
                        "amount_cents": 70_000,
                        "currency": "USD",
                        "category": "software",
                        "reason": "Concurrent balance pressure",
                        "rail": "internal_sandbox",
                        "idempotency_key": f"postgres-wallet-race-{uuid4()}",
                        "source": "test",
                    },
                )
                session.commit()
                return result.transaction.status, result.transaction.failure_code
            except PolicyBlocked as exc:
                session.commit()
                return exc.transaction.status, exc.transaction.failure_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(request_payment, [1, 2]))

    assert sorted(status for status, _code in outcomes) == [
        "blocked",
        "pending_approval",
    ]
    assert [code for status, code in outcomes if status == "blocked"] == [
        "INSUFFICIENT_FUNDS"
    ]
    with Session(engine) as session:
        balance = wallet_balance(session, get_wallet_for_user(session, user_id))
        assert balance.posted_cents == 100_000
        assert balance.reserved_cents == 70_000
        assert balance.available_cents == 30_000
        active_reservations = session.exec(
            select(FundReservation).where(
                FundReservation.user_id == user_id,
                FundReservation.status == "active",
            )
        ).all()
        assert len(active_reservations) == 1


def test_concurrent_duplicate_payment_key_posts_once() -> None:
    user_id = create_postgres_account()
    barrier = Barrier(2)
    idempotency_key = f"postgres-duplicate-{uuid4()}"

    def submit_duplicate() -> str:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, user_id)
            assert user is not None
            barrier.wait(timeout=10)
            result = create_payment_request(
                session,
                user=user,
                payload={
                    "type": "vendor_payment",
                    "vendor": "Concurrent Linear",
                    "recipient": None,
                    "amount_cents": 4_900,
                    "currency": "USD",
                    "category": "software",
                    "reason": "Duplicate idempotency race",
                    "rail": "internal_sandbox",
                    "idempotency_key": idempotency_key,
                    "source": "test",
                },
            )
            session.commit()
            return result.transaction.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        transaction_ids = list(executor.map(lambda _index: submit_duplicate(), [1, 2]))

    assert len(set(transaction_ids)) == 1
    with Session(engine) as session:
        transaction_id = transaction_ids[0]
        captures = session.exec(
            select(LedgerJournal).where(
                LedgerJournal.transaction_id == transaction_id,
                LedgerJournal.journal_type == "payment_capture",
            )
        ).all()
        transactions = session.exec(
            select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
        ).all()
        assert len(captures) == 1
        assert len(transactions) == 1
        balance = wallet_balance(session, get_wallet_for_user(session, user_id))
        assert balance.posted_cents == 95_100
        assert balance.reserved_cents == 0


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
