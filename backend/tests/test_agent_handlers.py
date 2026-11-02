"""Integration tests for governed payment and approval handlers."""

import json
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.agent import PactraAgent
from backend.config import Settings
from backend.models import Transaction
from backend.paypal_client import PayPalClient
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
async def test_approved_payment_executes_and_records_spend(
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
    assert result["outcome"] == "approved"
    assert result["paypal_order_id"].startswith("DEMO-ORDER-")
    assert transaction is not None
    assert transaction.paypal_status == "COMPLETED"
    software = next(
        item
        for item in policy_engine.get_summary(session)
        if item.category == "software"
    )
    assert software.spent_today == 49


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

        approved = await agent.approve_transaction(
            transaction,
            policy_engine,
            paypal_client,
            session,
        )
    finally:
        await paypal_client.close()

    assert approved.status == "approved"
    assert approved.paypal_order_id is not None
    assert approved.paypal_order_id.startswith("DEMO-PAYOUT-")


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
