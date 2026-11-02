"""Decision-tree and accounting tests for the policy engine."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from backend.models import PolicySnapshot
from backend.policy_engine import PolicyEngine


@pytest.fixture
def policy_path(tmp_path: Path) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(
        json.dumps(
            {
                "daily_limit": 500.0,
                "per_transaction_limit": 150.0,
                "require_approval_above": 100.0,
                "approved_categories": [
                    "ops",
                    "software",
                    "cloud",
                    "freelance",
                ],
                "blocked_vendors": ["Risky Vendor"],
                "budgets": {
                    "ops": 1000.0,
                    "software": 500.0,
                    "cloud": 800.0,
                    "freelance": 600.0,
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


def test_approves_payment_at_threshold(
    policy_path: Path, session: Session
) -> None:
    result = PolicyEngine(policy_path).check("Linear", 100, "software", session)
    assert result.approved is True
    assert result.status == "approved"


@pytest.mark.parametrize(
    ("vendor", "amount", "category", "rule"),
    [
        ("Linear", 20, "travel", "category_not_approved"),
        ("risky vendor", 20, "ops", "vendor_blocked"),
        ("AWS", 151, "cloud", "exceeds_per_transaction_limit"),
    ],
)
def test_blocks_first_matching_rule(
    policy_path: Path,
    session: Session,
    vendor: str,
    amount: float,
    category: str,
    rule: str,
) -> None:
    result = PolicyEngine(policy_path).check(vendor, amount, category, session)
    assert result.status == "blocked"
    assert result.rule_triggered == rule


def test_blocks_daily_limit(policy_path: Path, session: Session) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    session.add(PolicySnapshot(date=today, category="ops", total_spent=450))
    session.commit()

    result = PolicyEngine(policy_path).check("Notion", 60, "software", session)
    assert result.rule_triggered == "exceeds_daily_limit"


def test_blocks_category_budget(policy_path: Path, session: Session) -> None:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["budgets"]["software"] = 100
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    today = datetime.now(timezone.utc).date().isoformat()
    session.add(
        PolicySnapshot(date=today, category="software", total_spent=75)
    )
    session.commit()

    result = PolicyEngine(policy_path).check("Linear", 30, "software", session)
    assert result.rule_triggered == "exceeds_category_budget"


def test_requires_approval_above_threshold(
    policy_path: Path, session: Session
) -> None:
    result = PolicyEngine(policy_path).check("AWS", 120, "cloud", session)
    assert result.status == "pending_approval"
    assert result.rule_triggered == "requires_human_approval"


def test_records_and_summarises_spend(
    policy_path: Path, session: Session
) -> None:
    engine = PolicyEngine(policy_path)
    engine.record_spend("software", 75, session)
    engine.record_spend("software", 25, session)
    session.commit()

    software = next(
        item for item in engine.get_summary(session) if item.category == "software"
    )
    assert software.spent_today == 100
    assert software.remaining == 400
    assert software.utilisation_pct == 20
