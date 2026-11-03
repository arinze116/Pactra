"""Persisted assistant fallback and owner-isolation tests."""

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.config import settings
from backend.models import ConversationMessage, PaymentTransaction
from backend.services.accounts import create_account
from backend.services.assistant import ConversationNotFound, list_messages, run_assistant


@pytest.fixture
def assistant_db(monkeypatch):
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
    monkeypatch.setattr(settings, "ai_enabled", False)
    with Session(engine, expire_on_commit=False) as session:
        first = create_account(
            session,
            email="assistant@example.com",
            password_hash="unused-test-hash",
        )
        second = create_account(
            session,
            email="other-assistant@example.com",
            password_hash="unused-test-hash",
        )
        yield session, first.user, second.user
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.asyncio
async def test_fallback_creates_governed_transaction_and_persists_messages(
    assistant_db,
) -> None:
    session, user, _other = assistant_db
    result = await run_assistant(
        session,
        user=user,
        message="Pay Linear $49 for our monthly software subscription",
        conversation_id=None,
    )
    assert len(result.transaction_ids) == 1
    transaction = session.get(PaymentTransaction, result.transaction_ids[0])
    assert transaction is not None
    assert transaction.status == "completed"
    assert transaction.amount_cents == 4_900
    assert transaction.category == "software"
    assert transaction.rail == "internal_sandbox"

    messages = list_messages(
        session, user_id=user.id, conversation_id=result.conversation_id
    )
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[1].tool_calls[0]["name"] == "create_payment_request"


@pytest.mark.asyncio
async def test_ambiguous_fallback_does_not_create_transaction(assistant_db) -> None:
    session, user, _other = assistant_db
    result = await run_assistant(
        session,
        user=user,
        message="Please take care of the invoice",
        conversation_id=None,
    )
    assert result.transaction_ids == []
    assert "couldn't identify" in result.reply
    assert session.exec(select(PaymentTransaction)).all() == []


@pytest.mark.asyncio
async def test_conversation_is_owner_scoped(assistant_db) -> None:
    session, user, other = assistant_db
    result = await run_assistant(
        session,
        user=user,
        message="What is my current balance?",
        conversation_id=None,
    )
    with pytest.raises(ConversationNotFound):
        list_messages(
            session, user_id=other.id, conversation_id=result.conversation_id
        )


@pytest.mark.asyncio
async def test_paypal_fallback_does_not_silently_switch_rails(assistant_db) -> None:
    session, user, _other = assistant_db
    result = await run_assistant(
        session,
        user=user,
        message=(
            "Send $49 to sandbox-recipient@example.com for PayPal Sandbox "
            "contract work"
        ),
        conversation_id=None,
    )
    assert result.transaction_ids == []
    assert "PayPal Sandbox is not configured" in result.reply
    assert session.exec(select(PaymentTransaction)).all() == []
