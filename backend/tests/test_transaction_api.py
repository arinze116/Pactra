"""Authenticated policy, payment, approval and receipt API integration tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.auth import CSRF_COOKIE, CSRF_HEADER, auth_rate_limiter
from backend.database import get_session
from backend.main import app


ORIGIN = "http://testserver"


@pytest.fixture
def api() -> Generator[TestClient, None, None]:
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

    def test_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = test_session
    auth_rate_limiter.clear()
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        "/api/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": "api@example.com", "password": "StrongPassword2026!"},
    )
    assert response.status_code == 201
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()
        auth_rate_limiter.clear()
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def mutation_headers(client: TestClient) -> dict[str, str]:
    return {"Origin": ORIGIN, CSRF_HEADER: client.cookies.get(CSRF_COOKIE)}


def payment(
    *, amount_cents: int, key: str, category: str = "software"
) -> dict[str, object]:
    return {
        "type": "vendor_payment",
        "vendor": "Linear",
        "recipient": None,
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": category,
        "reason": "Monthly subscription",
        "rail": "internal_sandbox",
        "idempotency_key": key,
    }


def test_auto_payment_receipt_and_reversal(api: TestClient) -> None:
    created = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=4_900, key="api-auto-payment-0001"),
    )
    assert created.status_code == 201
    transaction = created.json()["transaction"]
    assert transaction["status"] == "completed"
    assert created.json()["balance"]["posted_cents"] == 95_100

    receipt = api.get(f"/api/transactions/{transaction['id']}")
    assert receipt.status_code == 200
    assert len(receipt.json()["ledger_entries"]) == 2
    assert receipt.json()["attempts"][0]["status"] == "completed"

    reversed_response = api.post(
        f"/api/transactions/{transaction['id']}/reverse",
        headers=mutation_headers(api),
        json={
            "idempotency_key": "api-reversal-payment-0001",
            "reason": "Duplicate invoice",
        },
    )
    assert reversed_response.status_code == 200
    assert reversed_response.json()["transaction"]["status"] == "reversed"
    assert api.get("/api/wallet").json()["posted_cents"] == 100_000


def test_pending_approval_and_rejection_flows(api: TestClient) -> None:
    pending = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(
            amount_cents=12_500,
            key="api-pending-payment-0001",
            category="freelance",
        ),
    )
    assert pending.status_code == 201
    pending_id = pending.json()["transaction"]["id"]
    assert pending.json()["transaction"]["status"] == "pending_approval"
    assert pending.json()["balance"]["reserved_cents"] == 12_500
    assert len(api.get("/api/approvals").json()["items"]) == 1

    approved = api.post(
        f"/api/approvals/{pending_id}/approve",
        headers=mutation_headers(api),
        json={"idempotency_key": "api-approve-payment-0001"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "completed"

    second = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(
            amount_cents=11_000,
            key="api-reject-payment-0001",
            category="ops",
        ),
    )
    assert second.status_code == 201
    second_id = second.json()["transaction"]["id"]
    rejected = api.post(
        f"/api/approvals/{second_id}/reject",
        headers=mutation_headers(api),
        json={
            "idempotency_key": "api-reject-action-0001",
            "reason": "Needs a corrected invoice",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert api.get("/api/wallet").json()["reserved_cents"] == 0


def test_policy_update_changes_decision_and_blocked_transaction_is_persisted(
    api: TestClient,
) -> None:
    current = api.get("/api/policy")
    assert current.status_code == 200
    policy = current.json()["policy"]
    policy["blocked_vendors"] = ["Linear"]
    updated = api.put(
        "/api/policy", headers=mutation_headers(api), json=policy
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    blocked = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=1_000, key="api-blocked-payment-0001"),
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "POLICY_BLOCKED"
    transaction = blocked.json()["error"]["details"]["transaction"]
    assert transaction["status"] == "blocked"
    assert transaction["failure_code"] == "VENDOR_BLOCKED"
    replay = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=1_000, key="api-blocked-payment-0001"),
    )
    assert replay.status_code == 422
    assert replay.json()["error"]["details"]["transaction"]["id"] == transaction["id"]

    history = api.get("/api/transactions").json()["items"]
    assert len(history) == 1
    assert history[0]["id"] == transaction["id"]


def test_transaction_history_date_filters_and_range_validation(api: TestClient) -> None:
    created = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=4_900, key="api-date-filter-payment-0001"),
    )
    assert created.status_code == 201

    today = created.json()["transaction"]["created_at"][:10]
    assert len(api.get(f"/api/transactions?from={today}&to={today}").json()["items"]) == 1
    assert api.get("/api/transactions?from=2099-01-01").json()["items"] == []

    reversed_range = api.get("/api/transactions?from=2026-11-03&to=2026-11-02")
    assert reversed_range.status_code == 400
    assert reversed_range.json()["error"]["code"] == "INVALID_DATE_RANGE"

    excessive_range = api.get("/api/transactions?from=2026-01-01&to=2026-05-01")
    assert excessive_range.status_code == 400
    assert excessive_range.json()["error"]["code"] == "INVALID_DATE_RANGE"


def test_another_user_cannot_read_or_action_transaction(api: TestClient) -> None:
    pending = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(
            amount_cents=12_000,
            key="api-private-payment-0001",
            category="freelance",
        ),
    )
    transaction_id = pending.json()["transaction"]["id"]

    other = TestClient(app, base_url=ORIGIN)
    try:
        registered = other.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={"email": "other-api@example.com", "password": "StrongPassword2026!"},
        )
        assert registered.status_code == 201
        assert other.get(f"/api/transactions/{transaction_id}").status_code == 404
        approval = other.post(
            f"/api/approvals/{transaction_id}/approve",
            headers=mutation_headers(other),
            json={"idempotency_key": "api-cross-user-approve-01"},
        )
        assert approval.status_code == 404
    finally:
        other.close()


def test_reset_restores_balance_cancels_holds_and_preserves_history(
    api: TestClient,
) -> None:
    completed = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=4_900, key="api-reset-completed-0001"),
    ).json()["transaction"]
    pending = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(
            amount_cents=11_000,
            key="api-reset-pending-0001",
            category="freelance",
        ),
    ).json()["transaction"]

    reset_body = {
        "confirmation": "RESET",
        "idempotency_key": "api-sandbox-reset-0001",
    }
    reset = api.post(
        "/api/wallet/reset", headers=mutation_headers(api), json=reset_body
    )
    assert reset.status_code == 200
    assert reset.json() == {
        "reset": True,
        "balance_cents": 100_000,
        "sandbox_generation": 2,
        "history_preserved": True,
    }
    replay = api.post(
        "/api/wallet/reset", headers=mutation_headers(api), json=reset_body
    )
    assert replay.status_code == 200
    assert replay.json()["sandbox_generation"] == 2

    wallet = api.get("/api/wallet").json()
    assert wallet["posted_cents"] == wallet["available_cents"] == 100_000
    assert wallet["reserved_cents"] == 0
    assert api.get("/api/transactions").json()["items"] == []
    all_history = api.get("/api/transactions?generation=all").json()["items"]
    assert {item["id"] for item in all_history} == {completed["id"], pending["id"]}
    pending_receipt = api.get(f"/api/transactions/{pending['id']}").json()
    assert pending_receipt["transaction"]["status"] == "cancelled"
    assert api.get(f"/api/transactions/{completed['id']}").status_code == 200
    assert api.get("/api/policy").json()["version"] == 2

