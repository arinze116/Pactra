"""Instant-demo isolation, lifecycle, reset, and provider-boundary tests."""

import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.auth import (
    CSRF_HEADER,
    DEMO_CSRF_COOKIE,
    DEMO_SESSION_COOKIE,
    SESSION_COOKIE,
    auth_rate_limiter,
    hash_password,
)
from backend.config import settings
from backend.database import get_session
from backend.main import app
from backend.models import (
    DemoWorkspace,
    PaymentTransaction,
    PolicyVersion,
    RateLimitBucket,
    TransactionAttempt,
    User,
    utc_now,
)
from backend.services.demo import (
    DemoCleanupSafetyError,
    cleanup_expired_demo_workspaces,
)
from backend.services.paypal import ProviderUnavailable, submit_or_reconcile_payout
from backend.worker import claim_paypal_transaction, reconcile_pending_payouts


ORIGIN = "http://testserver"


@pytest.fixture
def demo_api() -> Generator[tuple[TestClient, object], None, None]:
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

    def test_session() -> Generator[Session, None, None]:
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    auth_rate_limiter.clear()
    client = TestClient(app, base_url=ORIGIN)
    try:
        yield client, engine
    finally:
        client.close()
        app.dependency_overrides.clear()
        auth_rate_limiter.clear()
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def start_demo(client: TestClient):
    return client.post("/api/demo/sessions", headers={"Origin": ORIGIN})


def demo_headers(client: TestClient) -> dict[str, str]:
    return {
        "Origin": ORIGIN,
        CSRF_HEADER: client.cookies.get(DEMO_CSRF_COOKIE),
    }


def test_demo_creation_seeds_real_workspace_and_secure_cookie(demo_api) -> None:
    client, engine = demo_api
    response = start_demo(client)

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["is_demo"] is True
    assert user["display_name"] == "Northstar Studio"
    assert user["demo_expires_at"] is not None
    assert client.cookies.get(DEMO_SESSION_COOKIE)
    assert client.cookies.get(DEMO_CSRF_COOKIE)
    assert client.cookies.get(SESSION_COOKIE) is None
    assert any(
        DEMO_SESSION_COOKIE in value and "HttpOnly" in value and "SameSite=lax" in value
        for value in response.headers.get_list("set-cookie")
    )

    restored = client.get("/api/auth/session")
    assert restored.status_code == 200
    assert restored.json()["user"]["id"] == user["id"]
    demo_status = client.get("/api/demo/session")
    assert demo_status.status_code == 200
    assert demo_status.json()["active"] is True
    assert demo_status.json()["seed_version"] == 1

    wallet = client.get("/api/wallet").json()
    assert wallet == {
        "currency": "USD",
        "available_cents": 82_500,
        "reserved_cents": 14_000,
        "posted_cents": 96_500,
        "sandbox_generation": 1,
    }
    transactions = client.get("/api/transactions?limit=100").json()["items"]
    assert {item["status"] for item in transactions} == {
        "blocked",
        "completed",
        "pending_approval",
        "rejected",
    }
    completed = next(item for item in transactions if item["status"] == "completed")
    receipt = client.get(f"/api/transactions/{completed['id']}")
    assert receipt.status_code == 200
    assert len(receipt.json()["ledger_entries"]) == 2
    assert receipt.json()["attempts"][0]["rail"] == "internal_sandbox"

    policy = client.get("/api/policy").json()
    assert policy["policy"]["daily_limit_cents"] == 50_000
    assert policy["policy"]["per_transaction_limit_cents"] == 75_000
    assert policy["policy"]["approval_threshold_cents"] == 10_000
    assert policy["policy"]["blocked_vendors"] == ["Restricted Supply Co"]

    with Session(engine) as session:
        stored_user = session.get(User, user["id"])
        workspace = session.exec(
            select(DemoWorkspace).where(DemoWorkspace.user_id == user["id"])
        ).one()
        assert stored_user is not None and stored_user.is_demo is True
        assert workspace.status == "active"
        assert len(
            session.exec(
                select(PolicyVersion).where(PolicyVersion.user_id == user["id"])
            ).all()
        ) == 2


def test_demo_principals_cannot_use_normal_login(demo_api) -> None:
    client, engine = demo_api
    with Session(engine) as session:
        session.add(
            User(
                email="known-demo@example.com",
                password_hash=hash_password("KnownDemoPassword2026!"),
                is_demo=True,
            )
        )
        session.commit()

    response = client.post(
        "/api/auth/login",
        headers={"Origin": ORIGIN},
        json={
            "email": "known-demo@example.com",
            "password": "KnownDemoPassword2026!",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert client.cookies.get(SESSION_COOKIE) is None


def test_two_demo_sessions_are_isolated_and_use_real_policy_flows(demo_api) -> None:
    first, engine = demo_api
    second = TestClient(app, base_url=ORIGIN)
    try:
        assert start_demo(first).status_code == 201
        assert start_demo(second).status_code == 201
        first_user = first.get("/api/auth/me").json()["user"]
        second_user = second.get("/api/auth/me").json()["user"]
        assert first_user["id"] != second_user["id"]

        created = first.post(
            "/api/transactions",
            headers=demo_headers(first),
            json={
                "type": "vendor_payment",
                "vendor": "Linear",
                "recipient": None,
                "amount_cents": 4_900,
                "currency": "USD",
                "category": "software",
                "reason": "Judge walkthrough software payment",
                "rail": "internal_sandbox",
                "idempotency_key": "demo-linear-payment-0001",
            },
        )
        assert created.status_code == 201
        transaction_id = created.json()["transaction"]["id"]
        assert created.json()["transaction"]["status"] == "completed"
        assert second.get(f"/api/transactions/{transaction_id}").status_code == 404

        approval = first.post(
            "/api/transactions",
            headers=demo_headers(first),
            json={
                "type": "vendor_payment",
                "vendor": "Figma Teams",
                "recipient": None,
                "amount_cents": 12_000,
                "currency": "USD",
                "category": "software",
                "reason": "Judge walkthrough approval request",
                "rail": "internal_sandbox",
                "idempotency_key": "demo-figma-approval-0001",
            },
        )
        assert approval.status_code == 201
        approval_id = approval.json()["transaction"]["id"]
        assert approval.json()["transaction"]["status"] == "pending_approval"
        approved = first.post(
            f"/api/approvals/{approval_id}/approve",
            headers=demo_headers(first),
            json={"idempotency_key": "demo-figma-approve-0001"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "completed"

        blocked = first.post(
            "/api/transactions",
            headers=demo_headers(first),
            json={
                "type": "vendor_payment",
                "vendor": "Restricted Supply Co",
                "recipient": None,
                "amount_cents": 7_500,
                "currency": "USD",
                "category": "vendor_payments",
                "reason": "Restricted demo request",
                "rail": "internal_sandbox",
                "idempotency_key": "demo-restricted-payment-0001",
            },
        )
        assert blocked.status_code == 422
        assert blocked.json()["error"]["details"]["policy_result"]["reason_code"] == "VENDOR_BLOCKED"

        with Session(engine) as session:
            first_count = len(
                session.exec(
                    select(PaymentTransaction).where(
                        PaymentTransaction.user_id == first_user["id"]
                    )
                ).all()
            )
            second_count = len(
                session.exec(
                    select(PaymentTransaction).where(
                        PaymentTransaction.user_id == second_user["id"]
                    )
                ).all()
            )
        assert first_count > second_count
        assert second_count == 4
    finally:
        second.close()


def test_demo_reset_is_idempotent_and_exit_preserves_normal_session(demo_api) -> None:
    client, _engine = demo_api
    registered = client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": "owner@example.com", "password": "StrongPassword2026!"},
    )
    assert registered.status_code == 201
    normal_session_cookie = client.cookies.get(SESSION_COOKIE)
    assert start_demo(client).status_code == 201

    reset_payload = {"idempotency_key": "demo-reset-idempotent-0001"}
    first_reset = client.post(
        "/api/demo/reset",
        headers=demo_headers(client),
        json=reset_payload,
    )
    second_reset = client.post(
        "/api/demo/reset",
        headers=demo_headers(client),
        json=reset_payload,
    )
    assert first_reset.status_code == second_reset.status_code == 200
    assert first_reset.json()["wallet"] == second_reset.json()["wallet"]
    assert first_reset.json()["transaction_ids"] == second_reset.json()["transaction_ids"]
    assert first_reset.json()["wallet"]["sandbox_generation"] == 2
    assert second_reset.json()["replayed"] is True

    demo_session_cookie = client.cookies.get(DEMO_SESSION_COOKIE)
    exited = client.post("/api/demo/exit", headers=demo_headers(client))
    assert exited.status_code == 204
    assert client.cookies.get(DEMO_SESSION_COOKIE) is None
    assert client.cookies.get(SESSION_COOKIE) == normal_session_cookie
    restored = client.get("/api/auth/session")
    assert restored.status_code == 200
    assert restored.json()["user"]["email"] == "owner@example.com"
    assert restored.json()["user"]["is_demo"] is False

    revoked_client = TestClient(app, base_url=ORIGIN)
    try:
        revoked_client.cookies.set(DEMO_SESSION_COOKIE, demo_session_cookie)
        revoked = revoked_client.get("/api/wallet")
        assert revoked.status_code == 401
        assert revoked.json()["error"]["code"] == "DEMO_SESSION_EXPIRED"
    finally:
        revoked_client.close()


def test_expiry_cleanup_and_provider_block_never_touch_normal_data(demo_api) -> None:
    client, engine = demo_api
    normal = client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": "normal@example.com", "password": "StrongPassword2026!"},
    )
    assert normal.status_code == 201
    normal_user_id = normal.json()["user"]["id"]
    client.cookies.clear()
    demo = start_demo(client)
    assert demo.status_code == 201
    demo_user_id = demo.json()["user"]["id"]

    provider_attempt = client.post(
        "/api/transactions",
        headers=demo_headers(client),
        json={
            "type": "payout",
            "vendor": "Provider test",
            "recipient": "recipient@example.com",
            "amount_cents": 2_500,
            "currency": "USD",
            "category": "vendor_payments",
            "reason": "Must remain internal",
            "rail": "paypal_sandbox_payouts",
            "idempotency_key": "demo-provider-block-0001",
        },
    )
    assert provider_attempt.status_code == 403
    assert provider_attempt.json()["error"]["code"] == "DEMO_SANDBOX_ONLY"

    with Session(engine) as session:
        workspace = session.exec(
            select(DemoWorkspace).where(DemoWorkspace.user_id == demo_user_id)
        ).one()
        workspace.expires_at = utc_now() - timedelta(seconds=1)
        session.add(workspace)
        session.commit()

    expired = client.get("/api/wallet")
    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "DEMO_SESSION_EXPIRED"
    state = client.get("/api/auth/session")
    assert state.status_code == 200
    assert state.json() == {"user": None, "demo_expired": True}

    with Session(engine) as session:
        assert cleanup_expired_demo_workspaces(session) == 1
        session.commit()
        assert session.get(User, demo_user_id) is None
        normal_user = session.get(User, normal_user_id)
        assert normal_user is not None
        assert normal_user.email == "normal@example.com"


def test_cleanup_refuses_a_workspace_without_an_explicit_demo_owner(demo_api) -> None:
    client, engine = demo_api
    normal = client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": "cleanup-guard@example.com", "password": "StrongPassword2026!"},
    )
    assert normal.status_code == 201
    normal_user_id = normal.json()["user"]["id"]

    with Session(engine) as session:
        session.add(
            DemoWorkspace(
                user_id=normal_user_id,
                status="revoked",
                expires_at=utc_now() - timedelta(seconds=1),
            )
        )
        session.commit()

    with Session(engine) as session:
        with pytest.raises(DemoCleanupSafetyError):
            cleanup_expired_demo_workspaces(session)
        session.rollback()
        assert session.get(User, normal_user_id) is not None


def test_demo_creation_is_rate_limited(demo_api, monkeypatch) -> None:
    client, _engine = demo_api
    monkeypatch.setattr(settings, "demo_creation_global_rate_limit_per_hour", 1)
    assert start_demo(client).status_code == 201
    second = TestClient(app, base_url=ORIGIN)
    try:
        limited = start_demo(second)
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"
    finally:
        second.close()


def test_per_client_limit_does_not_exhaust_global_demo_capacity(
    demo_api,
    monkeypatch,
) -> None:
    client, engine = demo_api
    monkeypatch.setattr(settings, "demo_creation_rate_limit_per_hour", 1)
    monkeypatch.setattr(settings, "demo_creation_global_rate_limit_per_hour", 100)

    assert start_demo(client).status_code == 201
    assert start_demo(client).status_code == 429

    global_key = hashlib.sha256(b"demo:create:global").hexdigest()
    with Session(engine) as session:
        bucket = session.get(RateLimitBucket, global_key)
        assert bucket is not None
        assert bucket.event_count == 1


def test_demo_transaction_count_is_bounded(demo_api, monkeypatch) -> None:
    client, _engine = demo_api
    monkeypatch.setattr(settings, "demo_max_transactions", 4)
    assert start_demo(client).status_code == 201

    limited = client.post(
        "/api/transactions",
        headers=demo_headers(client),
        json={
            "type": "vendor_payment",
            "vendor": "Linear",
            "recipient": None,
            "amount_cents": 4_900,
            "currency": "USD",
            "category": "software",
            "reason": "Bounded demo activity",
            "rail": "internal_sandbox",
            "idempotency_key": "demo-resource-limit-0001",
        },
    )

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "DEMO_RESOURCE_LIMIT"


@pytest.mark.asyncio
async def test_demo_provider_rows_are_rejected_by_service_and_worker(demo_api) -> None:
    client, engine = demo_api
    demo = start_demo(client)
    assert demo.status_code == 201
    demo_user_id = demo.json()["user"]["id"]

    with Session(engine, expire_on_commit=False) as session:
        transaction = PaymentTransaction(
            user_id=demo_user_id,
            idempotency_key=f"demo-provider-bypass-{uuid4()}",
            type="payout",
            vendor="Unsafe provider bypass test",
            recipient="recipient@example.com",
            amount_cents=2_500,
            currency="USD",
            category="vendor_payments",
            reason="Direct-row provider isolation regression",
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

    class ProviderMustNotRun:
        def __getattr__(self, name: str):
            raise AssertionError(f"provider method {name} must not run for demo data")

    with Session(engine, expire_on_commit=False) as session:
        transaction = session.get(PaymentTransaction, transaction_id)
        assert transaction is not None
        assert claim_paypal_transaction(
            session,
            transaction_id=transaction_id,
        ) is None
        with pytest.raises(
            ProviderUnavailable,
            match="disabled for demo principals",
        ):
            await submit_or_reconcile_payout(
                session,
                client=ProviderMustNotRun(),
                transaction=transaction,
            )

    @contextmanager
    def session_factory():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    assert await reconcile_pending_payouts(
        client=ProviderMustNotRun(),
        session_factory=session_factory,
    ) == 0
