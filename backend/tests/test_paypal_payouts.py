"""PayPal Sandbox submission and item-level reconciliation safety tests."""

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.config import Settings, settings
from backend.models import (
    FundReservation,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
)
from backend.paypal_client import (
    PayPalClient,
    PayPalRejected,
    PayPalUnknownOutcome,
    PayoutStatus,
    PayoutSubmission,
)
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.services.paypal import ProviderUnavailable, submit_or_reconcile_payout
from backend.services.transactions import create_payment_request
from backend.worker import reconcile_pending_payouts


class FakePayPalClient:
    def __init__(self, statuses, *, submission_error: Exception | None = None):
        self.statuses = deque(statuses)
        self.submission_error = submission_error
        self.create_calls: list[tuple[str, int]] = []

    async def create_payout(self, **kwargs):
        self.create_calls.append((kwargs["transaction_id"], kwargs["attempt_number"]))
        if self.submission_error is not None:
            error = self.submission_error
            self.submission_error = None
            raise error
        return PayoutSubmission(batch_id="BATCH-123", batch_status="PENDING")

    async def get_payout(self, batch_id: str):
        assert batch_id == "BATCH-123"
        return self.statuses.popleft()


def paypal_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        paypal_payouts_enabled=True,
        paypal_client_id="sandbox-client",
        paypal_client_secret="sandbox-secret",
        paypal_test_recipient_email="recipient@example.com",
        paypal_mock_mode=False,
    )


@pytest.mark.asyncio
async def test_duplicate_batch_response_recovers_original_batch_reference() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "name": "DUPLICATE_BATCH_ID",
                "links": [
                    {
                        "href": (
                            "https://api-m.sandbox.paypal.com/"
                            "v1/payments/payouts/BATCH-ORIGINAL"
                        ),
                        "rel": "self",
                        "method": "GET",
                    }
                ],
            },
        )

    client = PayPalClient(paypal_settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )
    client._token = "test-token"
    client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    try:
        submission = await client.create_payout(
            transaction_id="550e8400-e29b-41d4-a716-446655440000",
            attempt_number=1,
            recipient_email="recipient@example.com",
            amount_cents=2_500,
            currency="USD",
            note="Sandbox test",
        )
    finally:
        await client.close()

    assert submission == PayoutSubmission(
        batch_id="BATCH-ORIGINAL",
        batch_status="PENDING",
    )


@pytest.mark.asyncio
async def test_duplicate_batch_without_safe_reference_remains_unknown() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"name": "DUPLICATE_BATCH_ID", "links": []},
        )

    client = PayPalClient(paypal_settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )
    client._token = "test-token"
    client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    try:
        with pytest.raises(PayPalUnknownOutcome):
            await client.create_payout(
                transaction_id="550e8400-e29b-41d4-a716-446655440000",
                attempt_number=1,
                recipient_email="recipient@example.com",
                amount_cents=2_500,
                currency="USD",
                note="Sandbox test",
            )
    finally:
        await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected_error"),
    [
        ([], PayPalRejected),
        (
            {"name": "DUPLICATE_BATCH_ID", "links": "not-a-list"},
            PayPalUnknownOutcome,
        ),
        (
            {
                "name": "DUPLICATE_BATCH_ID",
                "links": [
                    {
                        "href": "https://example.com/v1/payments/payouts/BATCH-OTHER",
                        "rel": "self",
                    }
                ],
            },
            PayPalUnknownOutcome,
        ),
        (
            {
                "name": "DUPLICATE_BATCH_ID",
                "links": [
                    {
                        "href": (
                            "https://api-m.sandbox.paypal.com/"
                            "v1/payments/payouts/BATCH-WRONG-REL"
                        ),
                        "rel": "next",
                    }
                ],
            },
            PayPalUnknownOutcome,
        ),
    ],
)
async def test_duplicate_batch_rejects_malformed_or_untrusted_links(
    payload: object,
    expected_error: type[Exception],
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json=payload)

    client = PayPalClient(paypal_settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )
    client._token = "test-token"
    client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    try:
        with pytest.raises(expected_error):
            await client.create_payout(
                transaction_id="550e8400-e29b-41d4-a716-446655440000",
                attempt_number=1,
                recipient_email="recipient@example.com",
                amount_cents=2_500,
                currency="USD",
                note="Sandbox test",
            )
    finally:
        await client.close()


@pytest.fixture
def payout_db(monkeypatch):
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
    monkeypatch.setattr(settings, "paypal_payouts_enabled", True)
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")
    monkeypatch.setattr(settings, "paypal_mock_mode", False)
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email="paypal@example.com",
            password_hash="unused-test-hash",
        )
        yield session, account.user
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def payout_payload(key: str, amount_cents: int = 4_900) -> dict[str, object]:
    return {
        "type": "payout",
        "vendor": "Ada Contractor",
        "recipient": "sandbox-recipient@example.com",
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": "software",
        "reason": "Contract work",
        "rail": "paypal_sandbox_payouts",
        "idempotency_key": key,
        "source": "manual",
    }


@pytest.mark.asyncio
async def test_batch_success_without_item_success_keeps_hold(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-pending-0001")
    )
    session.commit()
    client = FakePayPalClient(
        [
            PayoutStatus(
                batch_id="BATCH-123",
                batch_status="SUCCESS",
                item_id="ITEM-1",
                item_status="PENDING",
            )
        ]
    )
    transaction = await submit_or_reconcile_payout(
        session, client=client, transaction=result.transaction
    )
    session.commit()

    assert transaction.status == "executing"
    assert transaction.provider_status == "PENDING"
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert balance.posted_cents == 100_000
    assert balance.reserved_cents == 4_900


@pytest.mark.asyncio
async def test_item_success_captures_once_and_later_return_compensates(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-success-0001")
    )
    session.commit()
    success = PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS")
    returned = PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "RETURNED")
    client = FakePayPalClient([success, success, returned, returned])

    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    assert result.transaction.status == "completed"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 95_100

    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    captures = session.exec(
        select(LedgerJournal).where(LedgerJournal.journal_type == "payment_capture")
    ).all()
    assert len(captures) == 1

    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    assert result.transaction.status == "reversed"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 100_000
    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    reversals = session.exec(
        select(LedgerJournal).where(LedgerJournal.journal_type == "payment_reversal")
    ).all()
    assert len(reversals) == 1


@pytest.mark.asyncio
async def test_terminal_item_failure_releases_hold(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-failure-0001")
    )
    session.commit()
    client = FakePayPalClient(
        [PayoutStatus("BATCH-123", "DENIED", "ITEM-1", "FAILED")]
    )
    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    assert result.transaction.status == "failed"
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert balance.posted_cents == balance.available_cents == 100_000
    reservation = session.exec(select(FundReservation)).one()
    assert reservation.status == "released"


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_status", ["RETURNED", "REVERSED", "REFUNDED"])
async def test_pre_capture_provider_return_releases_hold_without_posting(
    payout_db,
    provider_status: str,
) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload(f"paypal-pre-capture-{provider_status.casefold()}-0001"),
    )
    session.commit()
    provider_result = PayoutStatus(
        "BATCH-123",
        "SUCCESS",
        "ITEM-1",
        provider_status,
    )
    client = FakePayPalClient([provider_result, provider_result])

    await submit_or_reconcile_payout(
        session,
        client=client,
        transaction=result.transaction,
    )
    session.commit()
    assert result.transaction.status == "reversed"
    assert result.transaction.provider_status == provider_status
    assert result.transaction.failure_code == f"PAYPAL_ITEM_{provider_status}"
    balance = wallet_balance(session, get_wallet_for_user(session, user.id))
    assert balance.posted_cents == balance.available_cents == 100_000
    assert balance.reserved_cents == 0
    reservation = session.exec(select(FundReservation)).one()
    assert reservation.status == "released"
    assert session.exec(
        select(LedgerJournal).where(
            LedgerJournal.journal_type.in_(["payment_capture", "payment_reversal"])
        )
    ).all() == []

    await submit_or_reconcile_payout(
        session,
        client=client,
        transaction=result.transaction,
    )
    session.commit()
    assert session.exec(
        select(LedgerJournal).where(
            LedgerJournal.journal_type.in_(["payment_capture", "payment_reversal"])
        )
    ).all() == []


@pytest.mark.asyncio
async def test_unknown_submission_reuses_same_attempt(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-unknown-0001")
    )
    session.commit()
    client = FakePayPalClient(
        [PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "ONHOLD")],
        submission_error=PayPalUnknownOutcome("timeout"),
    )
    with pytest.raises(ProviderUnavailable):
        await submit_or_reconcile_payout(
            session, client=client, transaction=result.transaction
        )
    session.commit()
    attempt = session.exec(select(TransactionAttempt)).one()
    assert attempt.status == "unknown"
    assert result.transaction.status == "executing"

    await submit_or_reconcile_payout(session, client=client, transaction=result.transaction)
    session.commit()
    assert client.create_calls == [
        (result.transaction.id, 1),
        (result.transaction.id, 1),
    ]
    attempts = session.exec(select(TransactionAttempt)).all()
    assert len(attempts) == 1
    assert result.transaction.provider_status == "ONHOLD"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).reserved_cents == 4_900


@pytest.mark.asyncio
async def test_provider_batch_survives_local_capture_rollback(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-capture-recovery-0001"),
    )
    session.commit()
    client = FakePayPalClient(
        [PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS")]
    )

    await submit_or_reconcile_payout(
        session, client=client, transaction=result.transaction
    )
    # Simulate failure of the caller's final commit after provider success.
    session.rollback()

    recovered = session.get(PaymentTransaction, result.transaction.id)
    assert recovered is not None
    assert recovered.status == "executing"
    assert recovered.provider_batch_id == "BATCH-123"
    assert client.create_calls == [(result.transaction.id, 1)]

    client.statuses.append(
        PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS")
    )
    await submit_or_reconcile_payout(
        session, client=client, transaction=recovered
    )
    session.commit()

    completed = session.get(PaymentTransaction, result.transaction.id)
    assert completed is not None
    assert completed.status == "completed"
    assert client.create_calls == [(result.transaction.id, 1)]
    captures = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.transaction_id == result.transaction.id,
            LedgerJournal.journal_type == "payment_capture",
        )
    ).all()
    assert len(captures) == 1


@pytest.mark.asyncio
async def test_worker_restart_reuses_persisted_provider_batch(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-worker-restart-0001"),
    )
    session.commit()
    engine = session.get_bind()

    @contextmanager
    def worker_session():
        with Session(engine, expire_on_commit=False) as worker_db:
            try:
                yield worker_db
                worker_db.commit()
            except Exception:
                worker_db.rollback()
                raise

    pending = PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "PENDING")
    success = PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS")
    client = FakePayPalClient([pending, success])

    assert await reconcile_pending_payouts(
        client=client,
        session_factory=worker_session,
    ) == 1
    assert await reconcile_pending_payouts(
        client=client,
        session_factory=worker_session,
    ) == 1

    session.expire_all()
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "completed"
    assert client.create_calls == [(result.transaction.id, 1)]
    captures = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.transaction_id == result.transaction.id,
            LedgerJournal.journal_type == "payment_capture",
        )
    ).all()
    assert len(captures) == 1
