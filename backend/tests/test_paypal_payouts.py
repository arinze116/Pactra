"""PayPal Sandbox submission and item-level reconciliation safety tests."""

import json
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
    AuditEvent,
    FundReservation,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
)
from backend.paypal_client import (
    PayPalClient,
    PayPalError,
    PayPalRejected,
    PayPalUnknownOutcome,
    PayoutStatus,
    PayoutSubmission,
)
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.defaults import default_policy
from backend.services.paypal import submit_or_reconcile_payout
from backend.services.policies import save_policy
from backend.services.transactions import (
    apply_paypal_reconciliation,
    approve_transaction,
    create_payment_request,
    enqueue_paypal_reconciliation,
    reject_transaction,
    transaction_detail,
)
from backend.worker import claim_paypal_transaction, reconcile_pending_payouts


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
    transaction_id = "550e8400-e29b-41d4-a716-446655440000"
    sender_batch_id = f"pactra-{transaction_id}-a1"

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.headers["PayPal-Request-Id"] == sender_batch_id
        assert payload["sender_batch_header"]["sender_batch_id"] == sender_batch_id
        assert payload["items"][0]["sender_item_id"] == f"pactra-{transaction_id}"
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
            transaction_id=transaction_id,
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


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["timeout", "reset", "http-408", "http-429", "http-500", "malformed-201"])
async def test_ambiguous_submission_failures_require_same_id_recovery(
    outcome: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if outcome == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if outcome == "reset":
            raise httpx.ReadError("connection reset", request=request)
        if outcome == "malformed-201":
            return httpx.Response(201, json={})
        return httpx.Response(int(outcome.removeprefix("http-")), json={})

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
@pytest.mark.parametrize("status_code", [400, 401, 403, 422])
async def test_definitive_submission_rejection_is_not_ambiguous(
    status_code: int,
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"name": "REQUEST_REJECTED"})

    client = PayPalClient(paypal_settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )
    client._token = "test-token"
    client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    try:
        with pytest.raises(PayPalRejected):
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
@pytest.mark.parametrize("outcome", ["http-429", "http-503", "malformed-200"])
async def test_reconciliation_provider_errors_do_not_invent_item_truth(
    outcome: str,
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        if outcome == "malformed-200":
            return httpx.Response(200, json={})
        return httpx.Response(int(outcome.removeprefix("http-")), json={})

    client = PayPalClient(paypal_settings())
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )
    client._token = "test-token"
    client._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
    try:
        with pytest.raises(PayPalError):
            await client.get_payout("BATCH-123")
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
    monkeypatch.setattr(
        settings,
        "paypal_test_recipient_email",
        "configured-recipient@example.com",
    )
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


def worker_session_factory(session: Session):
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

    return worker_session


async def run_worker_cycles(
    session: Session,
    client: FakePayPalClient,
    count: int,
) -> list[int]:
    worker_session = worker_session_factory(session)
    results = [
        await reconcile_pending_payouts(
            client=client,
            session_factory=worker_session,
        )
        for _ in range(count)
    ]
    session.expire_all()
    return results


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
    assert await run_worker_cycles(session, client, 2) == [1, 1]
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None

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
    client = FakePayPalClient([success, success, returned])

    assert await run_worker_cycles(session, client, 2) == [1, 1]
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "completed"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 95_100

    enqueue_paypal_reconciliation(
        session,
        user=user,
        transaction_id=result.transaction.id,
    )
    session.commit()
    assert await run_worker_cycles(session, client, 1) == [1]
    captures = session.exec(
        select(LedgerJournal).where(LedgerJournal.journal_type == "payment_capture")
    ).all()
    assert len(captures) == 1
    receipt = transaction_detail(
        session,
        user_id=user.id,
        transaction_id=result.transaction.id,
    )
    assert receipt["transaction"].status == "completed"
    assert receipt["transaction"].provider_batch_id == "BATCH-123"
    assert receipt["transaction"].provider_item_id == "ITEM-1"
    assert receipt["transaction"].provider_status == "SUCCESS"
    assert len(receipt["attempts"]) == 1
    receipt_attempt = receipt["attempts"][0]
    assert receipt_attempt["attempt_number"] == 1
    assert receipt_attempt["rail"] == "paypal_sandbox_payouts"
    assert receipt_attempt["status"] == "completed"
    assert receipt_attempt["provider_status"] == "SUCCESS"
    assert receipt_attempt["response_code"] == "PAYPAL_ITEM_SUCCESS"
    capture_entries = [
        entry
        for entry in receipt["ledger_entries"]
        if entry["journal_type"] == "payment_capture"
    ]
    assert len(capture_entries) == 2
    assert sum(
        entry["amount_cents"]
        for entry in capture_entries
        if entry["direction"] == "debit"
    ) == 4_900
    assert sum(
        entry["amount_cents"]
        for entry in capture_entries
        if entry["direction"] == "credit"
    ) == 4_900
    event_types = {event["event_type"] for event in receipt["events"]}
    assert {
        "funds.reserved",
        "paypal.payout_submitted",
        "paypal.payout_reconciled",
        "ledger.posted",
    } <= event_types

    enqueue_paypal_reconciliation(
        session,
        user=user,
        transaction_id=result.transaction.id,
    )
    session.commit()
    assert await run_worker_cycles(session, client, 1) == [1]
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "reversed"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).posted_cents == 100_000

    attempt = session.exec(select(TransactionAttempt)).one()
    apply_paypal_reconciliation(
        session,
        transaction=transaction,
        attempt=attempt,
        batch_status="SUCCESS",
        item_id="ITEM-1",
        item_status="RETURNED",
    )
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
    assert await run_worker_cycles(session, client, 2) == [1, 1]
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "failed"
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

    assert await run_worker_cycles(session, client, 2) == [1, 1]
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "reversed"
    assert transaction.provider_status == provider_status
    assert transaction.failure_code == f"PAYPAL_ITEM_{provider_status}"
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

    attempt = session.exec(select(TransactionAttempt)).one()
    apply_paypal_reconciliation(
        session,
        transaction=transaction,
        attempt=attempt,
        batch_status="SUCCESS",
        item_id="ITEM-1",
        item_status=provider_status,
    )
    session.commit()
    assert session.exec(
        select(LedgerJournal).where(
            LedgerJournal.journal_type.in_(["payment_capture", "payment_reversal"])
        )
    ).all() == []


@pytest.mark.asyncio
async def test_unknown_submission_is_not_blindly_retried(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-unknown-0001")
    )
    session.commit()
    client = FakePayPalClient(
        [PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "ONHOLD")],
        submission_error=PayPalUnknownOutcome("timeout"),
    )
    assert await run_worker_cycles(session, client, 1) == [1]
    attempt = session.exec(select(TransactionAttempt)).one()
    assert attempt.status == "unknown"
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert transaction.status == "executing"

    assert await run_worker_cycles(session, client, 1) == [0]
    assert client.create_calls == [(result.transaction.id, 1)]
    attempts = session.exec(select(TransactionAttempt)).all()
    assert len(attempts) == 1
    assert transaction.provider_status == "UNKNOWN"
    assert wallet_balance(
        session, get_wallet_for_user(session, user.id)
    ).reserved_cents == 4_900


@pytest.mark.asyncio
async def test_unknown_submission_recovery_reuses_the_same_stable_attempt(
    payout_db,
) -> None:
    session, user = payout_db
    result = create_payment_request(
        session, user=user, payload=payout_payload("paypal-unknown-recovery-0001")
    )
    session.commit()
    client = FakePayPalClient(
        [PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "ONHOLD")],
        submission_error=PayPalUnknownOutcome("timeout"),
    )

    assert await run_worker_cycles(session, client, 1) == [1]
    attempt = session.exec(select(TransactionAttempt)).one()
    stable_request_id = attempt.rail_request_id
    assert attempt.status == "unknown"

    assert await run_worker_cycles(session, client, 1) == [0]
    enqueue_paypal_reconciliation(
        session,
        user=user,
        transaction_id=result.transaction.id,
    )
    session.commit()

    attempt = session.get(TransactionAttempt, attempt.id)
    assert attempt is not None
    assert attempt.status == "submitting"
    assert attempt.attempt_number == 1
    assert attempt.rail_request_id == stable_request_id

    assert await run_worker_cycles(session, client, 1) == [1]
    session.expire_all()
    attempt = session.exec(select(TransactionAttempt)).one()
    transaction = session.get(PaymentTransaction, result.transaction.id)
    assert transaction is not None
    assert attempt.status == "processing"
    assert attempt.provider_batch_id == "BATCH-123"
    assert attempt.response_code is None
    assert transaction.provider_batch_id == "BATCH-123"
    assert transaction.failure_code is None
    assert client.create_calls == [
        (result.transaction.id, 1),
        (result.transaction.id, 1),
    ]
    assert len(session.exec(select(TransactionAttempt)).all()) == 1
    recovery_event = session.exec(
        select(AuditEvent).where(
            AuditEvent.event_type
            == "paypal.ambiguous_submission_recovery_queued"
        )
    ).one()
    assert recovery_event.payload == {
        "attempt": 1,
        "rail_request_id": stable_request_id,
    }
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

    assert await run_worker_cycles(session, client, 1) == [1]

    recovered = session.get(PaymentTransaction, result.transaction.id)
    assert recovered is not None
    assert recovered.status == "executing"
    assert recovered.provider_batch_id == "BATCH-123"
    assert client.create_calls == [(result.transaction.id, 1)]

    with Session(session.get_bind(), expire_on_commit=False) as worker_db:
        claimed = claim_paypal_transaction(
            worker_db,
            transaction_id=result.transaction.id,
        )
        assert claimed is not None
        await submit_or_reconcile_payout(
            worker_db,
            client=client,
            transaction=claimed,
        )
        worker_db.rollback()

    client.statuses.append(PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS"))
    assert await run_worker_cycles(session, client, 1) == [1]

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
async def test_worker_crash_after_provider_acceptance_reuses_stable_attempt(
    payout_db,
) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-crash-after-acceptance-0001"),
    )
    session.commit()
    client = FakePayPalClient([])

    with Session(session.get_bind(), expire_on_commit=False) as worker_db:
        claimed = claim_paypal_transaction(
            worker_db,
            transaction_id=result.transaction.id,
        )
        assert claimed is not None
        await submit_or_reconcile_payout(
            worker_db,
            client=client,
            transaction=claimed,
        )
        worker_db.rollback()

    session.expire_all()
    attempt = session.exec(select(TransactionAttempt)).one()
    assert attempt.status == "submitting"
    assert attempt.provider_batch_id is None

    assert await run_worker_cycles(session, client, 1) == [1]
    session.expire_all()
    attempt = session.exec(select(TransactionAttempt)).one()
    assert attempt.provider_batch_id == "BATCH-123"
    assert client.create_calls == [
        (result.transaction.id, 1),
        (result.transaction.id, 1),
    ]
    assert len(session.exec(select(TransactionAttempt)).all()) == 1


@pytest.mark.asyncio
async def test_worker_crash_before_submission_leaves_one_claimable_attempt(
    payout_db,
) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-crash-before-submission-0001"),
    )
    session.commit()

    with Session(session.get_bind(), expire_on_commit=False) as worker_db:
        claimed = claim_paypal_transaction(
            worker_db,
            transaction_id=result.transaction.id,
        )
        assert claimed is not None
        worker_db.rollback()

    client = FakePayPalClient([])
    assert await run_worker_cycles(session, client, 1) == [1]
    assert client.create_calls == [(result.transaction.id, 1)]
    assert len(session.exec(select(TransactionAttempt)).all()) == 1


@pytest.mark.asyncio
async def test_worker_restart_reuses_persisted_provider_batch(payout_db) -> None:
    session, user = payout_db
    result = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-worker-restart-0001"),
    )
    session.commit()
    pending = PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "PENDING")
    success = PayoutStatus("BATCH-123", "SUCCESS", "ITEM-1", "SUCCESS")
    client = FakePayPalClient([pending, success])

    assert await run_worker_cycles(session, client, 3) == [1, 1, 1]

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


@pytest.mark.asyncio
async def test_api_replay_and_duplicate_worker_delivery_submit_once(payout_db) -> None:
    session, user = payout_db
    payload = payout_payload("paypal-api-replay-0001")
    first = create_payment_request(session, user=user, payload=payload)
    replay = create_payment_request(session, user=user, payload=payload)
    session.commit()

    assert replay.replayed is True
    assert replay.transaction.id == first.transaction.id
    assert len(session.exec(select(TransactionAttempt)).all()) == 1

    pending = PayoutStatus("BATCH-123", "PENDING", "ITEM-1", "PENDING")
    client = FakePayPalClient([pending, pending])
    assert await run_worker_cycles(session, client, 3) == [1, 1, 1]
    assert client.create_calls == [(first.transaction.id, 1)]


@pytest.mark.asyncio
async def test_one_dollar_payout_requires_approval_before_worker_submission(
    payout_db,
) -> None:
    session, user = payout_db
    policy = default_policy()
    policy["approval_threshold_cents"] = 99
    save_policy(session, user_id=user.id, policy_json=policy)
    session.commit()

    rejected = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-one-dollar-reject-0001", amount_cents=100),
    )
    session.commit()
    assert rejected.transaction.status == "pending_approval"
    assert session.exec(select(TransactionAttempt)).all() == []

    reject_transaction(
        session,
        user=user,
        transaction_id=rejected.transaction.id,
        idempotency_key="paypal-one-dollar-rejection-0001",
        reason="Isolated approval rejection test",
    )
    session.commit()
    client = FakePayPalClient([])
    assert await run_worker_cycles(session, client, 1) == [0]
    assert client.create_calls == []

    approved = create_payment_request(
        session,
        user=user,
        payload=payout_payload("paypal-one-dollar-approve-0001", amount_cents=100),
    )
    session.commit()
    assert approved.transaction.status == "pending_approval"
    approve_transaction(
        session,
        user=user,
        transaction_id=approved.transaction.id,
        idempotency_key="paypal-one-dollar-approval-0001",
    )
    session.commit()

    queued_attempts = session.exec(
        select(TransactionAttempt).where(
            TransactionAttempt.transaction_id == approved.transaction.id
        )
    ).all()
    assert len(queued_attempts) == 1
    assert queued_attempts[0].status == "submitting"
    assert await run_worker_cycles(session, client, 1) == [1]
    assert client.create_calls == [(approved.transaction.id, 1)]
