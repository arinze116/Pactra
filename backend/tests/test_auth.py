"""Authentication, session security and owner-scoped wallet API tests."""

from collections.abc import Generator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.auth import CSRF_COOKIE, CSRF_HEADER, auth_rate_limiter
from backend.database import get_session
from backend.main import app
from backend.models import AuditEvent, AuthSession, LedgerJournal, PolicyVersion, User, Wallet, utc_now


ORIGIN_HEADERS = {"Origin": "http://testserver"}


@pytest.fixture
def api() -> Generator[tuple[TestClient, object], None, None]:
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
    client = TestClient(app, base_url="http://testserver")
    try:
        yield client, engine
    finally:
        client.close()
        app.dependency_overrides.clear()
        auth_rate_limiter.clear()
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def register(client: TestClient, email: str = "judge@example.com"):
    return client.post(
        "/api/auth/register",
        headers=ORIGIN_HEADERS,
        json={"email": email, "password": "StrongPassword2026!"},
    )


def csrf_headers(client: TestClient) -> dict[str, str]:
    return {
        **ORIGIN_HEADERS,
        CSRF_HEADER: client.cookies.get(CSRF_COOKIE),
    }


def test_registration_bootstraps_isolated_sandbox_account(api) -> None:
    client, engine = api
    response = register(client, "  Judge@Example.com ")

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["email"] == "judge@example.com"
    assert payload["wallet"]["available_cents"] == 100_000
    assert payload["wallet"]["reserved_cents"] == 0
    assert payload["sandbox_funds_cents"] == 100_000
    assert "pactra_session" in client.cookies
    assert CSRF_COOKIE in client.cookies
    assert response.headers[CSRF_HEADER] == client.cookies.get(CSRF_COOKIE)
    assert any(
        CSRF_COOKIE in value and "HttpOnly" in value
        for value in response.headers.get_list("set-cookie")
    )

    current = client.get("/api/auth/me", headers=ORIGIN_HEADERS)
    assert current.status_code == 200
    assert current.headers[CSRF_HEADER] == client.cookies.get(CSRF_COOKIE)
    assert CSRF_HEADER.lower() in current.headers["access-control-expose-headers"].lower()

    with Session(engine) as session:
        user = session.exec(select(User)).one()
        assert user.password_hash != "StrongPassword2026!"
        assert user.password_hash.startswith("$argon2id$")
        assert session.exec(select(Wallet).where(Wallet.user_id == user.id)).one()
        policy = session.exec(
            select(PolicyVersion).where(PolicyVersion.user_id == user.id)
        ).one()
        assert policy.version == 1
        assert session.exec(select(LedgerJournal)).one().journal_type == "initial_issuance"


def test_duplicate_registration_and_login_use_safe_errors(api) -> None:
    client, _engine = api
    assert register(client).status_code == 201
    duplicate = register(client)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_EXISTS"

    client.cookies.clear()
    wrong = client.post(
        "/api/auth/login",
        headers=ORIGIN_HEADERS,
        json={"email": "judge@example.com", "password": "not-the-password"},
    )
    missing = client.post(
        "/api/auth/login",
        headers=ORIGIN_HEADERS,
        json={"email": "missing@example.com", "password": "not-the-password"},
    )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json()["error"]["message"] == missing.json()["error"]["message"]


def test_csrf_logout_and_expired_sessions_are_enforced(api) -> None:
    client, engine = api
    registered = register(client)
    assert registered.status_code == 201

    missing_csrf = client.post(
        "/api/wallet/topups",
        headers=ORIGIN_HEADERS,
        json={"amount_cents": 10_000, "idempotency_key": "topup-no-csrf-01"},
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_INVALID"

    header_token = registered.headers[CSRF_HEADER]
    valid = client.post(
        "/api/wallet/topups",
        headers={**ORIGIN_HEADERS, CSRF_HEADER: header_token},
        json={"amount_cents": 10_000, "idempotency_key": "topup-header-csrf-01"},
    )
    assert valid.status_code == 201

    with Session(engine) as session:
        auth_session = session.exec(select(AuthSession)).one()
        auth_session.last_seen_at = utc_now() - timedelta(hours=25)
        session.add(auth_session)
        session.commit()
    expired = client.get("/api/auth/me")
    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "UNAUTHENTICATED"


def test_topup_is_idempotent_and_owner_scoped(api) -> None:
    client_a, engine = api
    assert register(client_a, "a@example.com").status_code == 201
    client_b = TestClient(app, base_url="http://testserver")
    try:
        assert register(client_b, "b@example.com").status_code == 201

        request_body = {"amount_cents": 10_000, "idempotency_key": "topup-account-a-0001"}
        first = client_a.post(
            "/api/wallet/topups", headers=csrf_headers(client_a), json=request_body
        )
        replay = client_a.post(
            "/api/wallet/topups", headers=csrf_headers(client_a), json=request_body
        )
        assert first.status_code == replay.status_code == 201
        assert first.json()["topup_id"] == replay.json()["topup_id"]
        assert first.json()["balance"]["posted_cents"] == 110_000
        assert replay.json()["balance"]["posted_cents"] == 110_000

        conflict = client_a.post(
            "/api/wallet/topups",
            headers=csrf_headers(client_a),
            json={"amount_cents": 50_000, "idempotency_key": "topup-account-a-0001"},
        )
        assert conflict.status_code == 409

        wallet_b = client_b.get("/api/wallet").json()
        assert wallet_b["posted_cents"] == 100_000
        ledger_a = client_a.get("/api/wallet/ledger").json()["items"]
        ledger_b = client_b.get("/api/wallet/ledger").json()["items"]
        assert [item["wallet_delta_cents"] for item in ledger_a] == [10_000, 100_000]
        assert [item["wallet_delta_cents"] for item in ledger_b] == [100_000]

        with Session(engine) as session:
            topup_audits = session.exec(
                select(AuditEvent).where(AuditEvent.event_type == "wallet.topup")
            ).all()
            assert len(topup_audits) == 1
    finally:
        client_b.close()


def test_password_change_revokes_other_sessions_and_logout_revokes_current(api) -> None:
    client_a, _engine = api
    assert register(client_a).status_code == 201
    client_b = TestClient(app, base_url="http://testserver")
    try:
        login = client_b.post(
            "/api/auth/login",
            headers=ORIGIN_HEADERS,
            json={"email": "judge@example.com", "password": "StrongPassword2026!"},
        )
        assert login.status_code == 200

        old_token = client_a.cookies.get(CSRF_COOKIE)
        changed = client_a.post(
            "/api/auth/change-password",
            headers=csrf_headers(client_a),
            json={
                "current_password": "StrongPassword2026!",
                "new_password": "NewStrongPassword2027!",
            },
        )
        assert changed.status_code == 204
        assert changed.headers[CSRF_HEADER] == client_a.cookies.get(CSRF_COOKIE)
        assert changed.headers[CSRF_HEADER] != old_token
        current = client_a.get("/api/auth/me")
        assert current.status_code == 200
        assert current.headers[CSRF_HEADER] == changed.headers[CSRF_HEADER]
        assert client_b.get("/api/auth/me").status_code == 401

        logout = client_a.post("/api/auth/logout", headers=csrf_headers(client_a))
        assert logout.status_code == 204
        assert client_a.get("/api/auth/me").status_code == 401
    finally:
        client_b.close()


def test_conversation_history_persists_and_is_owner_scoped(api) -> None:
    client, _engine = api
    assert register(client, "conversation-owner@example.com").status_code == 201

    created = client.post(
        "/api/conversations",
        headers=csrf_headers(client),
        json={"title": "Quarterly vendors"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    request = {
        "conversation_id": conversation_id,
        "message": "Please take care of the invoice",
        "request_id": "conversation-api-request-0001",
    }
    first = client.post("/api/chat", headers=csrf_headers(client), json=request)
    replay = client.post("/api/chat", headers=csrf_headers(client), json=request)
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()

    messages = client.get(f"/api/conversations/{conversation_id}/messages")
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()["items"]] == [
        "user",
        "assistant",
    ]
    assert messages.json()["items"][0]["content"] == request["message"]

    renamed = client.patch(
        f"/api/conversations/{conversation_id}",
        headers=csrf_headers(client),
        json={"title": "Approved vendors"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Approved vendors"
    assert renamed.json()["message_count"] == 2

    other = TestClient(app, base_url="http://testserver")
    try:
        assert register(other, "conversation-other@example.com").status_code == 201
        assert other.get(f"/api/conversations/{conversation_id}/messages").status_code == 404
        denied = other.patch(
            f"/api/conversations/{conversation_id}",
            headers=csrf_headers(other),
            json={"title": "Stolen"},
        )
        assert denied.status_code == 404
    finally:
        other.close()

    archived = client.patch(
        f"/api/conversations/{conversation_id}",
        headers=csrf_headers(client),
        json={"archived": True},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert client.get("/api/conversations").json()["items"] == []
    assert len(client.get("/api/conversations?include_archived=true").json()["items"]) == 1

    blocked_reply = client.post(
        "/api/chat",
        headers=csrf_headers(client),
        json={**request, "request_id": "conversation-api-request-0002"},
    )
    assert blocked_reply.status_code == 409
    assert blocked_reply.json()["error"]["code"] == "CONVERSATION_ARCHIVED"

    restored = client.patch(
        f"/api/conversations/{conversation_id}",
        headers=csrf_headers(client),
        json={"archived": False},
    )
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None

