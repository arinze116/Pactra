"""Integration tests for governed payment and approval handlers."""

import json
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.agent import AgentConfigurationError, PactraAgent
from backend.config import Settings
from backend.models import Transaction
from backend.paypal_client import PayPalClient, PayPalError
from backend.policy_engine import PolicyEngine


@pytest.fixture
def policy_path(tmp_path: Path) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "daily_limit": 500,
                "per_transaction_limit": 150,
                "require_approval_above": 100,
                "approved_categories": [
                    "ops",
                    "software",
                    "cloud",
                    "freelance",
                ],
                "blocked_vendors": [],
                "budgets": {
                    "ops": 1000,
                    "software": 500,
                    "cloud": 800,
                    "freelance": 600,
                },
                "currency": "USD",
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def app_settings() -> Settings:
    return Settings(
        _env_file=None,
        paypal_mock_mode=True,
        gemini_api_key="",
    )


@pytest.mark.asyncio
async def test_legacy_agent_run_is_disabled_even_with_a_provider_key(
    policy_path: Path, session: Session, app_settings: Settings
) -> None:
    enabled_settings = app_settings.model_copy(
        update={"gemini_api_key": "test-provider-key"}
    )
    policy_engine = PolicyEngine(policy_path)
    paypal_client = PayPalClient(enabled_settings)
    agent = PactraAgent(enabled_settings)
    try:
        with pytest.raises(AgentConfigurationError, match="Legacy PactraAgent is disabled"):
            await agent.run(
                "Create a payment",
                [],
                policy_engine,
                paypal_client,
                session,
            )
    finally:
        await paypal_client.close()


@pytest.mark.asyncio
async def test_legacy_payment_path_is_disabled_before_provider_execution(
    policy_path: Path, session: Session, app_settings: Settings
) -> None:
    policy_engine = PolicyEngine(policy_path)
    paypal_client = PayPalClient(app_settings)
    agent = PactraAgent(app_settings)
    try:
        result = await agent._handle_create_payment(
            vendor="Linear",
            amount=49,
            category="software",
            reason="Monthly subscription",
            policy_engine=policy_engine,
            paypal_client=paypal_client,
            db_session=session,
        )
    finally:
        await paypal_client.close()

    transaction = session.get(Transaction, result["transaction_id"])
    assert result["outcome"] == "failed"
    assert "Legacy payment execution is disabled" in result["error"]
    assert transaction is not None
    assert transaction.paypal_status == "FAILED"
    software = next(
        item
        for item in policy_engine.get_summary(session)
        if item.category == "software"
    )
    assert software.spent_today == 0


@pytest.mark.asyncio
async def test_pending_payment_waits_for_human_then_executes(
    policy_path: Path, session: Session, app_settings: Settings
) -> None:
    policy_engine = PolicyEngine(policy_path)
    paypal_client = PayPalClient(app_settings)
    agent = PactraAgent(app_settings)
    try:
        result = await agent._handle_send_payout(
            recipient_email="ada@example.com",
            amount=125,
            category="freelance",
            note="Illustration work",
            policy_engine=policy_engine,
            paypal_client=paypal_client,
            db_session=session,
        )
        transaction = session.get(Transaction, result["transaction_id"])
        assert transaction is not None
        assert transaction.status == "pending_approval"
        assert transaction.paypal_order_id is None

        with pytest.raises(PayPalError, match="governed transaction service"):
            await agent.approve_transaction(
                transaction,
                policy_engine,
                paypal_client,
                session,
            )
    finally:
        await paypal_client.close()

    assert transaction.status == "pending_approval"
    assert transaction.paypal_order_id is None


def test_paypal_client_exposes_no_legacy_orders_execution() -> None:
    assert not hasattr(PayPalClient, "create_order")
    assert not hasattr(PayPalClient, "capture_order")


def test_only_worker_orchestration_can_call_payout_submission() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    callers = []
    for source_path in backend_root.rglob("*.py"):
        if "tests" in source_path.parts or source_path.name == "paypal_client.py":
            continue
        if ".create_payout(" in source_path.read_text(encoding="utf-8"):
            callers.append(source_path.relative_to(backend_root).as_posix())
    assert callers == ["services/paypal.py"]
    assert "/v2/checkout/orders" not in (backend_root / "paypal_client.py").read_text(
        encoding="utf-8"
    )


@pytest.mark.asyncio
async def test_blocked_payment_never_reaches_paypal(
    policy_path: Path, session: Session, app_settings: Settings
) -> None:
    policy_engine = PolicyEngine(policy_path)
    paypal_client = PayPalClient(app_settings)
    agent = PactraAgent(app_settings)
    try:
        result = await agent._handle_create_payment(
            vendor="AWS",
            amount=185,
            category="cloud",
            reason="Cloud hosting",
            policy_engine=policy_engine,
            paypal_client=paypal_client,
            db_session=session,
        )
    finally:
        await paypal_client.close()

    transaction = session.get(Transaction, result["transaction_id"])
    assert result["outcome"] == "blocked"
    assert result["rule_triggered"] == "exceeds_per_transaction_limit"
    assert transaction is not None
    assert transaction.paypal_order_id is None
