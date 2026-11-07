"""Authenticated policy, payment, approval and receipt API integration tests."""

import base64
from collections.abc import Generator
import json

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
    assert receipt.json()["attempts"][0]["rail"] == "internal_sandbox"
    assert receipt.json()["attempts"][0]["provider_status"] is None
    assert (
        receipt.json()["attempts"][0]["response_code"]
        == "INTERNAL_LEDGER_CAPTURED"
    )

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
    assert blocked.status_code == 201
    assert blocked.json()["policy_result"]["decision"] == "blocked"
    transaction = blocked.json()["transaction"]
    assert transaction["status"] == "blocked"
    assert transaction["failure_code"] == "VENDOR_BLOCKED"
    replay = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=1_000, key="api-blocked-payment-0001"),
    )
    assert replay.status_code == 201
    assert replay.json()["transaction"]["id"] == transaction["id"]

    history = api.get("/api/transactions").json()["items"]
    assert len(history) == 1
    assert history[0]["id"] == transaction["id"]


def test_policy_validation_unchanged_save_and_version_history(api: TestClient) -> None:
    empty = api.put("/api/policy", headers=mutation_headers(api), json={})
    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "VALIDATION_ERROR"

    current = api.get("/api/policy").json()
    invalid = {**current["policy"], "allowed_categories": []}
    invalid["category_budgets_cents"] = {}
    rejected = api.put("/api/policy", headers=mutation_headers(api), json=invalid)
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"

    unchanged = api.put(
        "/api/policy", headers=mutation_headers(api), json=current["policy"]
    )
    assert unchanged.status_code == 409
    assert unchanged.json()["error"]["code"] == "POLICY_UNCHANGED"

    changed_policy = {**current["policy"], "approval_threshold_cents": 7_500}
    saved = api.put(
        "/api/policy", headers=mutation_headers(api), json=changed_policy
    )
    assert saved.status_code == 200
    assert saved.json()["version"] == 2
    assert api.get("/api/policy").json() == saved.json()

    history = api.get("/api/policies")
    assert history.status_code == 200
    assert [item["version"] for item in history.json()["items"]] == [2, 1]


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
    completed = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment(amount_cents=4_900, key="api-private-completed-0001"),
    )
    assert completed.status_code == 201
    completed_id = completed.json()["transaction"]["id"]
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
    owner_policy_id = api.get("/api/policy").json()["id"]
    owner_conversation = api.post(
        "/api/conversations",
        headers=mutation_headers(api),
        json={"title": "Private owner conversation"},
    )
    assert owner_conversation.status_code == 201
    owner_conversation_id = owner_conversation.json()["id"]

    other = TestClient(app, base_url=ORIGIN)
    try:
        registered = other.post(
            "/api/auth/register",
            headers={"Origin": ORIGIN},
            json={"email": "other-api@example.com", "password": "StrongPassword2026!"},
        )
        assert registered.status_code == 201
        assert other.get("/api/transactions").json()["items"] == []
        assert other.get("/api/approvals").json()["items"] == []
        assert owner_policy_id not in {
            item["id"] for item in other.get("/api/policies").json()["items"]
        }
        assert other.get(f"/api/transactions/{transaction_id}").status_code == 404
        approval = other.post(
            f"/api/approvals/{transaction_id}/approve",
            headers=mutation_headers(other),
            json={"idempotency_key": "api-cross-user-approve-01"},
        )
        assert approval.status_code == 404
        rejection = other.post(
            f"/api/approvals/{transaction_id}/reject",
            headers=mutation_headers(other),
            json={
                "idempotency_key": "api-cross-user-reject-0001",
                "reason": "Unauthorized",
            },
        )
        assert rejection.status_code == 404
        reversal = other.post(
            f"/api/transactions/{completed_id}/reverse",
            headers=mutation_headers(other),
            json={
                "idempotency_key": "api-cross-user-reverse-0001",
                "reason": "Unauthorized",
            },
        )
        assert reversal.status_code == 404
        retry = other.post(
            f"/api/transactions/{completed_id}/retry",
            headers=mutation_headers(other),
            json={"idempotency_key": "api-cross-user-retry-0001"},
        )
        assert retry.status_code == 404
        reconcile = other.post(
            f"/api/transactions/{transaction_id}/reconcile",
            headers=mutation_headers(other),
        )
        assert reconcile.status_code == 404
        assert other.get(
            f"/api/conversations/{owner_conversation_id}/messages"
        ).status_code == 404
        conversation_update = other.patch(
            f"/api/conversations/{owner_conversation_id}",
            headers=mutation_headers(other),
            json={"title": "Stolen conversation"},
        )
        assert conversation_update.status_code == 404
    finally:
        other.close()


def test_payment_and_policy_payloads_reject_owner_mass_assignment(
    api: TestClient,
) -> None:
    payment_payload = payment(
        amount_cents=4_900,
        key="api-mass-assignment-payment-0001",
    )
    payment_payload["user_id"] = "00000000-0000-4000-8000-000000000000"
    created = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payment_payload,
    )
    assert created.status_code == 400
    assert created.json()["error"]["code"] == "VALIDATION_ERROR"

    policy = api.get("/api/policy").json()["policy"]
    policy["user_id"] = "00000000-0000-4000-8000-000000000000"
    updated = api.put(
        "/api/policy",
        headers=mutation_headers(api),
        json=policy,
    )
    assert updated.status_code == 400
    assert updated.json()["error"]["code"] == "VALIDATION_ERROR"


def test_malformed_resource_ids_and_cursors_never_reach_postgresql(
    api: TestClient,
) -> None:
    invalid_id = "not-a-uuid"
    mutation_cases = [
        (f"/api/transactions/{invalid_id}/reverse", {
            "idempotency_key": "invalid-id-reverse-0001",
            "reason": "Invalid resource identifier",
        }),
        (f"/api/transactions/{invalid_id}/retry", {
            "idempotency_key": "invalid-id-retry-0001",
        }),
        (f"/api/transactions/{invalid_id}/reconcile", None),
        (f"/api/approvals/{invalid_id}/approve", {
            "idempotency_key": "invalid-id-approve-0001",
        }),
        (f"/api/approvals/{invalid_id}/reject", {
            "idempotency_key": "invalid-id-reject-0001",
            "reason": "Invalid resource identifier",
        }),
    ]
    assert api.get(f"/api/transactions/{invalid_id}").status_code == 400
    assert api.get(f"/api/conversations/{invalid_id}/messages").status_code == 400
    assert api.patch(
        f"/api/conversations/{invalid_id}",
        headers=mutation_headers(api),
        json={"title": "Invalid resource identifier"},
    ).status_code == 400
    for path, body in mutation_cases:
        response = api.post(
            path,
            headers=mutation_headers(api),
            json=body,
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    invalid_conversation = api.post(
        "/api/chat",
        headers=mutation_headers(api),
        json={
            "conversation_id": invalid_id,
            "message": "Show my balance",
            "request_id": "invalid-conversation-id-0001",
        },
    )
    assert invalid_conversation.status_code == 400

    transaction_cursor = base64.urlsafe_b64encode(
        json.dumps(
            {
                "created_at": "2026-11-07T00:00:00+00:00",
                "id": invalid_id,
            }
        ).encode()
    ).decode().rstrip("=")
    ledger_cursor = base64.urlsafe_b64encode(
        json.dumps(
            {
                "created_at": "2026-11-07T00:00:00+00:00",
                "journal_id": invalid_id,
            }
        ).encode()
    ).decode().rstrip("=")
    transaction_response = api.get(
        "/api/transactions", params={"cursor": transaction_cursor}
    )
    ledger_response = api.get(
        "/api/wallet/ledger", params={"cursor": ledger_cursor}
    )
    assert transaction_response.status_code == 400
    assert transaction_response.json()["error"]["code"] == "INVALID_CURSOR"
    assert ledger_response.status_code == 400
    assert ledger_response.json()["error"]["code"] == "INVALID_CURSOR"


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
