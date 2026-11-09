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
from backend.config import settings
from backend.database import get_session
from backend.main import app
from backend.paypal_client import PayPalClient


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


def paypal_payout(*, key: str, amount_cents: int = 100) -> dict[str, object]:
    return {
        "type": "payout",
        "vendor": "US Personal Sandbox recipient",
        "recipient": None,
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": "freelance",
        "reason": "Worker-only payout regression",
        "rail": "paypal_sandbox_payouts",
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
    assert {
        entry["account_label"] for entry in receipt.json()["ledger_entries"]
    } == {"Your sandbox wallet", "Sandbox clearing"}
    assert {
        entry["counter_account_label"]
        for entry in receipt.json()["ledger_entries"]
    } == {"Your sandbox wallet", "Sandbox clearing"}
    assert sum(
        entry["amount_cents"]
        for entry in receipt.json()["ledger_entries"]
        if entry["direction"] == "debit"
    ) == sum(
        entry["amount_cents"]
        for entry in receipt.json()["ledger_entries"]
        if entry["direction"] == "credit"
    )
    assert all(event["actor_label"] for event in receipt.json()["events"])
    assert all(event["summary"] for event in receipt.json()["events"])
    assert "password" not in json.dumps(receipt.json()["events"]).casefold()
    assert "token" not in json.dumps(receipt.json()["events"]).casefold()
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
    approval_items = api.get("/api/approvals").json()["items"]
    assert len(approval_items) == 1
    approval = approval_items[0]
    assert approval["transaction"]["id"] == pending_id
    assert approval["requester"]["email"] == "api@example.com"
    assert approval["current_policy_decision"] == "approval_required"
    assert approval["current_policy_reason_code"] == "APPROVAL_REQUIRED"
    assert approval["current_policy_version"] == 1
    assert approval["available_balance"]["reserved_cents"] == 12_500
    assert {check["code"] for check in approval["policy_checks"]} >= {
        "AVAILABLE_FUNDS",
        "APPROVAL_THRESHOLD",
    }

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


def test_paypal_api_uses_configured_recipient_and_never_submits_directly(
    api: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "paypal_payouts_enabled", True)
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")
    monkeypatch.setattr(
        settings,
        "paypal_test_recipient_email",
        "configured-recipient@example.com",
    )
    monkeypatch.setattr(settings, "paypal_mock_mode", False)
    monkeypatch.setattr(
        settings,
        "paypal_base_url",
        "https://api-m.sandbox.paypal.com",
    )

    provider_calls = 0

    async def forbidden_submission(_client, **_kwargs):
        nonlocal provider_calls
        provider_calls += 1
        raise AssertionError("The transaction API must not call PayPal")

    monkeypatch.setattr(PayPalClient, "create_payout", forbidden_submission)

    current = api.get("/api/policy").json()["policy"]
    current["approval_threshold_cents"] = 99
    assert api.put(
        "/api/policy",
        headers=mutation_headers(api),
        json=current,
    ).status_code == 200

    payload = paypal_payout(key="api-paypal-worker-only-0001")
    created = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payload,
    )
    assert created.status_code == 201
    transaction = created.json()["transaction"]
    assert transaction["status"] == "pending_approval"
    assert transaction["recipient"] == "configured-recipient@example.com"
    assert provider_calls == 0

    approved = api.post(
        f"/api/approvals/{transaction['id']}/approve",
        headers=mutation_headers(api),
        json={"idempotency_key": "api-paypal-worker-only-approval-0001"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "executing"
    assert provider_calls == 0

    replay = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=payload,
    )
    assert replay.status_code == 201
    assert replay.json()["transaction"]["id"] == transaction["id"]
    assert provider_calls == 0

    freeform = paypal_payout(key="api-paypal-freeform-recipient-0001")
    freeform["recipient"] = "alternate-recipient@example.com"
    freeform_created = api.post(
        "/api/transactions",
        headers=mutation_headers(api),
        json=freeform,
    )
    assert freeform_created.status_code == 201
    assert (
        freeform_created.json()["transaction"]["recipient"]
        == "alternate-recipient@example.com"
    )
    assert provider_calls == 0

    receipt = api.get(f"/api/transactions/{transaction['id']}").json()
    assert len(receipt["attempts"]) == 1
    assert receipt["attempts"][0]["status"] == "submitting"
    assert receipt["transaction"]["provider_batch_id"] is None

    reconcile = api.post(
        f"/api/transactions/{transaction['id']}/reconcile",
        headers=mutation_headers(api),
    )
    assert reconcile.status_code == 409
    assert reconcile.json()["error"]["code"] == "PROVIDER_OUTCOME_UNKNOWN"
    assert provider_calls == 0


def test_paypal_status_masks_the_global_sandbox_recipient(
    api: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "paypal_payouts_enabled", True)
    monkeypatch.setattr(settings, "paypal_client_id", "sandbox-client")
    monkeypatch.setattr(settings, "paypal_client_secret", "sandbox-secret")
    monkeypatch.setattr(settings, "paypal_mock_mode", False)
    monkeypatch.setattr(
        settings,
        "paypal_base_url",
        "https://api-m.sandbox.paypal.com",
    )
    monkeypatch.setattr(
        settings,
        "paypal_test_recipient_email",
        "recipient@example.com",
    )

    response = api.get("/api/integrations/paypal/status")

    assert response.status_code == 200
    assert response.json()["configured"] is True
    assert response.json()["test_recipient_email"] == "r***@e***.com"
    assert "recipient@example.com" not in response.text

    monkeypatch.setattr(settings, "paypal_test_recipient_email", "")
    missing_recipient = api.get("/api/integrations/paypal/status")

    assert missing_recipient.status_code == 200
    assert missing_recipient.json()["configured"] is False
    assert missing_recipient.json()["test_recipient_email"] is None


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
    blocked_error = blocked.json()["error"]
    assert blocked_error["code"] == "POLICY_BLOCKED"
    assert blocked_error["message"] == "This request is blocked by your spending policy."
    assert blocked_error["details"]["policy_result"]["decision"] == "blocked"
    transaction = blocked_error["details"]["transaction"]
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
    receipt = api.get(f"/api/transactions/{transaction['id']}")
    assert receipt.status_code == 200
    assert receipt.json()["ledger_entries"] == []
    assert any(
        event["event_type"] == "payment.blocked"
        for event in receipt.json()["events"]
    )


def test_insufficient_funds_returns_persisted_402_without_ledger_movement(
    api: TestClient,
) -> None:
    policy = api.get("/api/policy").json()["policy"]
    policy.update(
        {
            "daily_limit_cents": 100_000_000,
            "per_transaction_limit_cents": 100_000_000,
            "approval_threshold_cents": 100_000_000,
        }
    )
    policy["category_budgets_cents"]["software"] = 100_000_000
    assert api.put(
        "/api/policy", headers=mutation_headers(api), json=policy
    ).status_code == 200

    payload = payment(amount_cents=100_001, key="api-insufficient-payment-0001")
    response = api.post(
        "/api/transactions", headers=mutation_headers(api), json=payload
    )
    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "INSUFFICIENT_FUNDS"
    assert error["message"] == "Your available sandbox balance is too low."
    transaction = error["details"]["transaction"]
    assert transaction["status"] == "blocked"
    assert transaction["failure_code"] == "INSUFFICIENT_FUNDS"
    assert error["details"]["balance"]["posted_cents"] == 100_000
    assert error["details"]["balance"]["reserved_cents"] == 0

    replay = api.post(
        "/api/transactions", headers=mutation_headers(api), json=payload
    )
    assert replay.status_code == 402
    assert replay.json()["error"]["details"]["transaction"]["id"] == transaction["id"]
    receipt = api.get(f"/api/transactions/{transaction['id']}").json()
    assert receipt["ledger_entries"] == []
    assert len(api.get("/api/transactions").json()["items"]) == 1


def test_policy_preview_is_authoritative_and_side_effect_free(api: TestClient) -> None:
    before = api.get("/api/transactions").json()["items"]
    approved = api.post(
        "/api/transactions/preview",
        headers=mutation_headers(api),
        json={
            "vendor": "Linear",
            "amount_cents": 4_900,
            "currency": "USD",
            "category": "software",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["decision"] == "approved"
    assert approved.json()["reason_code"] is None

    approval = api.post(
        "/api/transactions/preview",
        headers=mutation_headers(api),
        json={
            "vendor": "Ada Contractor",
            "amount_cents": 12_500,
            "currency": "USD",
            "category": "freelance",
        },
    )
    assert approval.json()["decision"] == "approval_required"
    assert approval.json()["reason_code"] == "APPROVAL_REQUIRED"

    blocked = api.post(
        "/api/transactions/preview",
        headers=mutation_headers(api),
        json={
            "vendor": "AWS",
            "amount_cents": 18_500,
            "currency": "USD",
            "category": "cloud",
        },
    )
    assert blocked.json()["decision"] == "blocked"
    assert blocked.json()["reason_code"] == "TRANSACTION_LIMIT_EXCEEDED"
    assert api.get("/api/transactions").json()["items"] == before
    assert api.get("/api/wallet").json() == {
        "posted_cents": 100_000,
        "reserved_cents": 0,
        "available_cents": 100_000,
        "currency": "USD",
        "sandbox_generation": 1,
    }


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
