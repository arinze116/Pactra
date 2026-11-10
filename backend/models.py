"""Database entities and API schemas used throughout Pactra."""

from datetime import datetime, timezone
import math
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field as PydanticField, field_validator
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlmodel import Field, SQLModel


TransactionStatus = Literal["approved", "blocked", "pending_approval"]


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """Return a UUID string suitable for SQLite and PostgreSQL storage."""
    return str(uuid4())


JSON_VALUE = JSON().with_variant(JSONB(), "postgresql")
UUID_STRING = String(36).with_variant(PostgresUUID(as_uuid=False), "postgresql")
SYSTEM_ISSUANCE_ACCOUNT_ID = "00000000-0000-4000-8000-000000000001"
SYSTEM_CLEARING_ACCOUNT_ID = "00000000-0000-4000-8000-000000000002"


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


# Judge-ready persistence models. The legacy Transaction and PolicySnapshot
# tables above remain temporarily so the existing demo API stays runnable while
# services are migrated in verified slices.


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','disabled')", name="users_status_valid"
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    email: str = Field(max_length=254, unique=True, index=True)
    password_hash: str
    status: str = Field(default="active", max_length=16)
    is_demo: bool = Field(default=False, index=True)
    display_name: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AuthSession(SQLModel, table=True):
    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_expiry", "user_id", "expires_at"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    token_hash: bytes = Field(
        sa_column=Column(LargeBinary, nullable=False, unique=True)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    last_seen_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class DemoWorkspace(SQLModel, table=True):
    """Lifecycle record for one isolated, temporary demo principal."""

    __tablename__ = "demo_workspaces"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','revoked','expired')",
            name="demo_workspaces_status_valid",
        ),
        CheckConstraint(
            "seed_version > 0",
            name="demo_workspaces_seed_version_positive",
        ),
        Index("ix_demo_workspaces_status_expiry", "status", "expires_at"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )
    status: str = Field(default="active", max_length=16)
    seed_version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    last_reset_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class RateLimitBucket(SQLModel, table=True):
    """Shared fixed-window counters for API processes using one database."""

    __tablename__ = "rate_limit_buckets"
    __table_args__ = (Index("ix_rate_limit_buckets_expires", "expires_at"),)

    key_hash: str = Field(primary_key=True, max_length=64)
    window_started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    event_count: int = Field(default=1)


class LedgerAccount(SQLModel, table=True):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('user_wallet','sandbox_issuance','sandbox_clearing')",
            name="ledger_accounts_type_valid",
        ),
        CheckConstraint("currency = 'USD'", name="ledger_accounts_currency_usd"),
        CheckConstraint(
            "(account_type = 'user_wallet' AND user_id IS NOT NULL) OR "
            "(account_type IN ('sandbox_issuance','sandbox_clearing') AND user_id IS NULL)",
            name="ledger_accounts_owner_valid",
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str | None = Field(
        default=None,
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
    )
    code: str = Field(max_length=64, unique=True)
    account_type: str = Field(max_length=24)
    currency: str = Field(default="USD", max_length=3)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("currency = 'USD'", name="wallets_currency_usd"),
        CheckConstraint(
            "status IN ('active','locked')", name="wallets_status_valid"
        ),
        CheckConstraint(
            "sandbox_generation > 0", name="wallets_generation_positive"
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )
    ledger_account_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        )
    )
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(default="active", max_length=16)
    sandbox_generation: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PolicyVersion(SQLModel, table=True):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_policies_user_version"),
        CheckConstraint("version > 0", name="policies_version_positive"),
        Index("ix_policies_user_version", "user_id", "version"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    version: int
    policy_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON_VALUE, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    created_by: str | None = Field(
        default=None,
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
    )


class PaymentTransaction(SQLModel, table=True):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_transactions_user_idempotency"
        ),
        CheckConstraint(
            "type IN ('vendor_payment','payout','sandbox_transfer')",
            name="transactions_type_valid",
        ),
        CheckConstraint("amount_cents > 0", name="transactions_amount_positive"),
        CheckConstraint("currency = 'USD'", name="transactions_currency_usd"),
        CheckConstraint(
            "status IN ('draft','pending_approval','executing','completed','blocked',"
            "'rejected','failed','cancelled','reversed')",
            name="transactions_status_valid",
        ),
        CheckConstraint(
            "sandbox_generation > 0", name="transactions_generation_positive"
        ),
        CheckConstraint(
            "rail IN ('internal_sandbox','paypal_sandbox_payouts')",
            name="transactions_rail_valid",
        ),
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index("ix_transactions_user_status", "user_id", "status"),
        Index("ix_transactions_user_category", "user_id", "category"),
        Index("ix_transactions_provider_batch", "provider_batch_id"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    idempotency_key: str = Field(max_length=128)
    type: str = Field(max_length=24)
    vendor: str = Field(max_length=100)
    recipient: str | None = Field(default=None, max_length=254)
    amount_cents: int = Field(sa_column=Column(BigInteger, nullable=False))
    currency: str = Field(default="USD", max_length=3)
    category: str = Field(max_length=32)
    reason: str = Field(sa_column=Column(String(500), nullable=False))
    status: str = Field(max_length=24, index=True)
    sandbox_generation: int
    policy_version: int
    policy_result: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON_VALUE, nullable=False),
    )
    rail: str = Field(max_length=32)
    rail_reference: str | None = Field(default=None, max_length=128)
    provider_batch_id: str | None = Field(
        default=None, max_length=128, unique=True
    )
    provider_item_id: str | None = Field(default=None, max_length=128)
    provider_status: str | None = Field(default=None, max_length=32)
    failure_code: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class LedgerJournal(SQLModel, table=True):
    __tablename__ = "ledger_journals"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_journals_user_idempotency"
        ),
        CheckConstraint("status = 'posted'", name="journals_status_posted"),
        Index("ix_journals_user_created", "user_id", "created_at"),
        Index("ix_journals_transaction", "transaction_id"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    transaction_id: str | None = Field(
        default=None,
        sa_column=Column(
            UUID_STRING,
            ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    journal_type: str = Field(max_length=32)
    idempotency_key: str = Field(max_length=128)
    status: str = Field(default="posted", max_length=16)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class LedgerEntry(SQLModel, table=True):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('debit','credit')", name="ledger_entries_direction_valid"
        ),
        CheckConstraint("amount_cents > 0", name="ledger_entries_amount_positive"),
        CheckConstraint("currency = 'USD'", name="ledger_entries_currency_usd"),
        Index("ix_ledger_account_created", "account_id", "created_at"),
        Index("ix_ledger_journal", "journal_id"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    journal_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("ledger_journals.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    account_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    direction: str = Field(max_length=8)
    amount_cents: int = Field(sa_column=Column(BigInteger, nullable=False))
    currency: str = Field(default="USD", max_length=3)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class FundReservation(SQLModel, table=True):
    __tablename__ = "fund_reservations"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="reservations_amount_positive"),
        CheckConstraint(
            "status IN ('active','captured','released')",
            name="reservations_status_valid",
        ),
        Index("ix_reservations_user_status", "user_id", "status"),
        Index(
            "uq_active_reservation_transaction",
            "transaction_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    wallet_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False
        )
    )
    transaction_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    amount_cents: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: str = Field(max_length=16)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    released_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class TransactionAttempt(SQLModel, table=True):
    __tablename__ = "transaction_attempts"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id", "attempt_number", name="uq_attempts_transaction_number"
        ),
        UniqueConstraint("rail_request_id", name="uq_attempts_rail_request"),
        CheckConstraint("attempt_number > 0", name="attempts_number_positive"),
        Index("ix_attempts_provider_batch", "provider_batch_id"),
        Index("ix_attempts_status_started", "status", "started_at"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    transaction_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    attempt_number: int
    rail: str = Field(max_length=32)
    rail_request_id: str = Field(max_length=128)
    provider_batch_id: str | None = Field(default=None, max_length=128)
    provider_item_id: str | None = Field(default=None, max_length=128)
    provider_status: str | None = Field(default=None, max_length=32)
    status: str = Field(max_length=24)
    response_code: str | None = Field(default=None, max_length=64)
    started_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    finished_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class ApprovalAction(SQLModel, table=True):
    __tablename__ = "approval_actions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_approvals_user_idempotency"
        ),
        CheckConstraint(
            "action IN ('approved','rejected')", name="approvals_action_valid"
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    transaction_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    idempotency_key: str = Field(max_length=128)
    action: str = Field(max_length=16)
    reason: str | None = Field(default=None, max_length=300)
    policy_version: int
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    actor_type: str = Field(max_length=16)
    actor_id: str | None = Field(
        default=None,
        sa_column=Column(UUID_STRING, nullable=True),
    )
    entity_type: str = Field(max_length=32)
    entity_id: str = Field(sa_column=Column(UUID_STRING, nullable=False))
    event_type: str = Field(max_length=64)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON_VALUE, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_user_updated", "user_id", "updated_at"),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    user_id: str = Field(
        sa_column=Column(
            UUID_STRING, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    title: str = Field(default="New conversation", max_length=120)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


class ConversationMessage(SQLModel, table=True):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant','tool')", name="messages_role_valid"
        ),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
        Index(
            "uq_messages_request_role",
            "conversation_id",
            "request_id",
            "role",
            unique=True,
        ),
    )

    id: str = Field(
        default_factory=new_id,
        sa_column=Column(UUID_STRING, primary_key=True, nullable=False),
    )
    conversation_id: str = Field(
        sa_column=Column(
            UUID_STRING,
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    role: str = Field(max_length=16)
    request_id: str | None = Field(default=None, max_length=128)
    content: str = Field(sa_column=Column(Text, nullable=False))
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        sa_column=Column(JSON_VALUE, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
