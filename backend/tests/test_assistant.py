"""Persisted assistant fallback and owner-isolation tests."""

from types import SimpleNamespace

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.config import settings
from backend.models import AuditEvent, ConversationMessage, PaymentTransaction
from backend.services.accounts import create_account
from backend.services import assistant
from backend.services.assistant import (
    ConversationNotFound,
    list_messages,
    refresh_assistant_payment_state,
    run_assistant,
)


class FakeGeminiClient:
    def __init__(self, responses: list[object] | None = None, *, error: Exception | None = None):
        self._responses = list(responses or [])
        self._error = error
        self.aio = self
        self.models = self

    async def generate_content(self, **_kwargs):
        if self._error is not None:
            raise self._error
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def aclose(self) -> None:
        return None


def gemini_tool_response(name: str, arguments: dict[str, object]) -> object:
    call = SimpleNamespace(name=name, args=arguments)
    content = SimpleNamespace(parts=[SimpleNamespace(function_call=call)])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)], text="")


def gemini_text_response(text: str) -> object:
    content = SimpleNamespace(parts=[])
    return SimpleNamespace(candidates=[SimpleNamespace(content=content)], text=text)


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
        request_id="assistant-test-payment-0001",
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
    assert "completed after backend policy and ledger confirmation" in result.reply


@pytest.mark.asyncio
async def test_gemini_tool_call_uses_governed_service_and_persists_tool_message(
    assistant_db,
    monkeypatch,
) -> None:
    session, user, _other = assistant_db
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    fake = FakeGeminiClient(
        [
            gemini_tool_response(
                "create_payment_request",
                {
                    "type": "vendor_payment",
                    "vendor": "Linear",
                    "recipient": None,
                    "amount_cents": 4_900,
                    "currency": "USD",
                    "category": "software",
                    "reason": "Monthly subscription",
                    "rail": "internal_sandbox",
                },
            ),
            gemini_text_response("The payment was created."),
        ]
    )
    monkeypatch.setattr(assistant.genai, "Client", lambda **_kwargs: fake)

    result = await run_assistant(
        session,
        user=user,
        message="Pay Linear $49 for our monthly software subscription",
        conversation_id=None,
        request_id="assistant-gemini-tool-0001",
    )

    assert len(result.transaction_ids) == 1
    transaction = session.get(PaymentTransaction, result.transaction_ids[0])
    assert transaction is not None
    assert transaction.status == "completed"
    messages = list_messages(
        session, user_id=user.id, conversation_id=result.conversation_id
    )
    assert [message.role for message in messages] == ["user", "tool", "assistant"]
    assert messages[1].tool_calls[0]["name"] == "create_payment_request"
    assert "completed after backend policy and ledger confirmation" in result.reply


@pytest.mark.asyncio
async def test_gemini_failure_is_audited_and_disclosed_before_fallback(
    assistant_db,
    monkeypatch,
) -> None:
    session, user, _other = assistant_db
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    monkeypatch.setattr(
        assistant.genai,
        "Client",
        lambda **_kwargs: FakeGeminiClient(error=RuntimeError("provider unavailable")),
    )

    result = await run_assistant(
        session,
        user=user,
        message="Pay Linear $49 for our monthly software subscription",
        conversation_id=None,
        request_id="assistant-gemini-failure-0001",
    )

    assert "Gemini is temporarily unavailable" in result.reply
    assert len(result.transaction_ids) == 1
    audit = session.exec(
        select(AuditEvent).where(AuditEvent.event_type == "assistant.error")
    ).one()
    assert audit.payload == {
        "code": "AI_UNAVAILABLE",
        "model": settings.gemini_model,
    }


@pytest.mark.asyncio
async def test_gemini_failure_after_payment_preserves_committed_tool_state(
    assistant_db,
    monkeypatch,
) -> None:
    session, user, _other = assistant_db
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")
    fake = FakeGeminiClient(
        [
            gemini_tool_response(
                "create_payment_request",
                {
                    "type": "vendor_payment",
                    "vendor": "Linear",
                    "recipient": None,
                    "amount_cents": 4_900,
                    "currency": "USD",
                    "category": "software",
                    "reason": "Monthly subscription",
                    "rail": "internal_sandbox",
                },
            ),
            RuntimeError("provider failed after tool execution"),
        ]
    )
    monkeypatch.setattr(assistant.genai, "Client", lambda **_kwargs: fake)

    result = await run_assistant(
        session,
        user=user,
        message="Handle the approved supplier obligation now.",
        conversation_id=None,
        request_id="assistant-gemini-partial-failure-0001",
    )

    assert len(result.transaction_ids) == 1
    assert len(session.exec(select(PaymentTransaction)).all()) == 1
    transaction = session.get(PaymentTransaction, result.transaction_ids[0])
    assert transaction is not None
    assert transaction.status == "completed"
    assert "Gemini became unavailable" in result.reply
    assert "completed after backend policy and ledger confirmation" in result.reply
    messages = list_messages(
        session, user_id=user.id, conversation_id=result.conversation_id
    )
    assert [message.role for message in messages] == ["user", "tool", "assistant"]
    assert messages[-1].tool_calls == result.tool_calls
    assert messages[-1].tool_calls[0]["result"]["id"] == transaction.id


@pytest.mark.asyncio
async def test_provider_status_refresh_updates_returned_and_persisted_reply(
    assistant_db,
) -> None:
    session, user, _other = assistant_db
    request_id = "assistant-provider-refresh-0001"
    result = await run_assistant(
        session,
        user=user,
        message="Pay Linear $49 for our monthly software subscription",
        conversation_id=None,
        request_id=request_id,
    )
    transaction = session.get(PaymentTransaction, result.transaction_ids[0])
    assert transaction is not None
    transaction.status = "failed"
    transaction.failure_code = "PAYPAL_SUBMISSION_REJECTED"
    session.add(transaction)
    session.commit()

    refreshed = refresh_assistant_payment_state(
        session,
        user_id=user.id,
        request_id=request_id,
        result=result,
    )
    session.commit()

    assert "failed" in refreshed.reply
    assistant_message = session.exec(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == result.conversation_id,
            ConversationMessage.role == "assistant",
        )
    ).one()
    assert assistant_message.content == refreshed.reply
    assert assistant_message.tool_calls[0]["result"]["status"] == "failed"


@pytest.mark.asyncio
async def test_ambiguous_fallback_does_not_create_transaction(assistant_db) -> None:
    session, user, _other = assistant_db
    result = await run_assistant(
        session,
        user=user,
        message="Please take care of the invoice",
        conversation_id=None,
        request_id="assistant-test-ambiguous-0001",
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
        request_id="assistant-test-owner-0001",
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
        request_id="assistant-test-paypal-0001",
    )
    assert result.transaction_ids == []
    assert "PayPal Sandbox is not configured" in result.reply
    assert session.exec(select(PaymentTransaction)).all() == []


@pytest.mark.asyncio
async def test_request_id_replay_does_not_duplicate_messages_or_payment(
    assistant_db,
) -> None:
    session, user, _other = assistant_db
    request_id = "assistant-test-replay-0001"
    first = await run_assistant(
        session,
        user=user,
        message="Pay Linear $49 for our monthly software subscription",
        conversation_id=None,
        request_id=request_id,
    )
    replay = await run_assistant(
        session,
        user=user,
        message="This changed text must not create another payment",
        conversation_id=first.conversation_id,
        request_id=request_id,
    )

    assert replay == first
    messages = list_messages(
        session, user_id=user.id, conversation_id=first.conversation_id
    )
    assert [message.role for message in messages] == ["user", "assistant"]
    assert len(session.exec(select(PaymentTransaction)).all()) == 1


@pytest.mark.asyncio
async def test_request_ids_are_isolated_between_users(assistant_db) -> None:
    session, user, other = assistant_db
    request_id = "assistant-cross-user-request-0001"
    first = await run_assistant(
        session,
        user=user,
        message="Please take care of the first invoice",
        conversation_id=None,
        request_id=request_id,
    )
    second = await run_assistant(
        session,
        user=other,
        message="Please take care of the second invoice",
        conversation_id=None,
        request_id=request_id,
    )

    assert first.conversation_id != second.conversation_id
    assert "first invoice" in list_messages(
        session, user_id=user.id, conversation_id=first.conversation_id
    )[0].content
    assert "second invoice" in list_messages(
        session, user_id=other.id, conversation_id=second.conversation_id
    )[0].content
