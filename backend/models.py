"""Database entities and API schemas used throughout Pactra."""

from datetime import datetime, timezone
import math
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field as PydanticField, field_validator
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


TransactionStatus = Literal["approved", "blocked", "pending_approval"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Transaction(SQLModel, table=True):
    """Immutable request details plus the evolving PayPal execution state."""

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    timestamp: datetime = Field(default_factory=utc_now, index=True)
    vendor: str = Field(index=True)
    amount: float
    currency: str = "USD"
    category: str = Field(index=True)
    reason: str
    # SQLModel cannot map typing.Literal directly to a SQLAlchemy column. The
    # policy layer remains Literal-validated and is the only writer here.
    status: str = Field(index=True)
    block_reason: str | None = None
    paypal_order_id: str | None = None
    paypal_status: str | None = None
    initiated_by: str = "pactra-agent"
    transaction_type: str = "payment"


class PolicySnapshot(SQLModel, table=True):
    """Per-category daily spend ledger, reset naturally by the date key."""

    __table_args__ = (
        UniqueConstraint("date", "category", name="uq_policy_snapshot_date_category"),
    )

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    date: str = Field(index=True)
    category: str = Field(index=True)
    total_spent: float = 0.0


class ChatMessage(BaseModel):
    role: Literal["user", "agent"]
    content: str = PydanticField(min_length=1, max_length=8_000)


class ChatRequest(BaseModel):
    message: str = PydanticField(min_length=1, max_length=8_000)
    history: list[ChatMessage] = PydanticField(default_factory=list, max_length=100)


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = PydanticField(default_factory=list)
    transactions_created: list[str] = PydanticField(default_factory=list)


class PolicyCheckResult(BaseModel):
    approved: bool
    status: TransactionStatus
    reason: str | None = None
    rule_triggered: str | None = None


class SpendSummary(BaseModel):
    category: str
    budget: float
    spent_today: float
    remaining: float
    utilisation_pct: float


class PayPalOrderResult(BaseModel):
    order_id: str
    status: str
    amount: float
    currency: str
    approve_link: str | None = None


class PolicyConfig(BaseModel):
    """Validated on-disk policy shape."""

    model_config = ConfigDict(extra="forbid")

    daily_limit: float = PydanticField(gt=0)
    per_transaction_limit: float = PydanticField(gt=0)
    require_approval_above: float = PydanticField(ge=0)
    approved_categories: list[str] = PydanticField(min_length=1)
    blocked_vendors: list[str] = PydanticField(default_factory=list)
    budgets: dict[str, float]
    currency: str = PydanticField(min_length=3, max_length=3)

    @field_validator(
        "daily_limit", "per_transaction_limit", "require_approval_above"
    )
    @classmethod
    def require_finite_limit(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Policy limits must be finite")
        return value

    @field_validator("approved_categories")
    @classmethod
    def normalise_categories(cls, value: list[str]) -> list[str]:
        categories = [item.strip().casefold() for item in value if item.strip()]
        if not categories or len(categories) != len(set(categories)):
            raise ValueError("Approved categories must be non-empty and unique")
        return categories

    @field_validator("blocked_vendors")
    @classmethod
    def normalise_blocked_vendors(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("budgets")
    @classmethod
    def validate_budgets(cls, value: dict[str, float]) -> dict[str, float]:
        budgets = {key.strip().casefold(): amount for key, amount in value.items()}
        if any(not math.isfinite(amount) or amount <= 0 for amount in budgets.values()):
            raise ValueError("Category budgets must be positive finite numbers")
        return budgets

    @field_validator("currency")
    @classmethod
    def normalise_currency(cls, value: str) -> str:
        return value.upper()
