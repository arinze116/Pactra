"""Validated API contracts for the judge-ready Pactra endpoints."""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def validate_password_strength(value: str) -> str:
    """Apply the PRD password length and character-class requirements."""
    if not 12 <= len(value) <= 128:
        raise ValueError("Password must be between 12 and 128 characters")
    classes = (
        bool(re.search(r"[a-z]", value)),
        bool(re.search(r"[A-Z]", value)),
        bool(re.search(r"\d", value)),
        bool(re.search(r"[^A-Za-z0-9]", value)),
    )
    if sum(classes) < 3:
        raise ValueError("Password must use at least three character types")
    return value


class RegistrationRequest(StrictModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserResponse(StrictModel):
    id: str
    email: str


class WalletBalanceResponse(StrictModel):
    currency: str
    available_cents: int
    reserved_cents: int
    posted_cents: int
    sandbox_generation: int


class RegistrationResponse(StrictModel):
    user: UserResponse
    wallet: WalletBalanceResponse
    sandbox_funds_cents: int
    message: str


class AuthResponse(StrictModel):
    user: UserResponse
    message: str | None = None


class TopUpRequest(StrictModel):
    amount_cents: int
    idempotency_key: str = Field(
        min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"
    )


class TopUpResponse(StrictModel):
    topup_id: str
    amount_cents: int
    balance: WalletBalanceResponse
    message: str


class LedgerItemResponse(StrictModel):
    journal_id: str
    journal_type: str
    transaction_id: str | None
    wallet_delta_cents: int
    counter_account_label: str
    created_at: datetime


class LedgerPageResponse(StrictModel):
    items: list[LedgerItemResponse]
    next_cursor: str | None


class PolicyInput(StrictModel):
    daily_limit_cents: int = Field(gt=0, le=100_000_000)
    per_transaction_limit_cents: int = Field(gt=0, le=100_000_000)
    approval_threshold_cents: int = Field(ge=0, le=100_000_000)
    allowed_categories: list[str] = Field(min_length=1, max_length=50)
    category_budgets_cents: dict[str, int]
    blocked_vendors: list[str] = Field(default_factory=list, max_length=200)
    currency: Literal["USD"] = "USD"

    @field_validator("allowed_categories")
    @classmethod
    def validate_categories(cls, values: list[str]) -> list[str]:
        categories = [value.strip().casefold() for value in values]
        if len(set(categories)) != len(categories):
            raise ValueError("Categories must be unique")
        if any(not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", value) for value in categories):
            raise ValueError("Category names must use valid slugs")
        return categories

    @field_validator("category_budgets_cents")
    @classmethod
    def validate_category_budgets(cls, values: dict[str, int]) -> dict[str, int]:
        normalised = {key.strip().casefold(): value for key, value in values.items()}
        if any(value <= 0 or value > 100_000_000 for value in normalised.values()):
            raise ValueError("Category budget must be greater than zero")
        return normalised

    @field_validator("blocked_vendors")
    @classmethod
    def validate_blocked_vendors(cls, values: list[str]) -> list[str]:
        vendors = [value.strip() for value in values]
        if any(not 1 <= len(value) <= 100 for value in vendors):
            raise ValueError("Blocked vendor names must be between 1 and 100 characters")
        if len({value.casefold() for value in vendors}) != len(vendors):
            raise ValueError("Blocked vendors must be unique")
        return vendors

    @field_validator("category_budgets_cents")
    @classmethod
    def ensure_budget_keys_are_valid(cls, values: dict[str, int]) -> dict[str, int]:
        if any(not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", key) for key in values):
            raise ValueError("Category budget keys must use valid slugs")
        return values

    def validated_policy(self) -> dict[str, object]:
        missing = set(self.allowed_categories) - set(self.category_budgets_cents)
        extras = set(self.category_budgets_cents) - set(self.allowed_categories)
        if missing or extras:
            raise ValueError("Every allowed category must have exactly one budget")
        return self.model_dump()


class PolicyResponse(StrictModel):
    id: str
    version: int
    policy: dict[str, object]


class PolicyVersionSummary(StrictModel):
    id: str
    version: int
    policy: dict[str, object]
    created_at: datetime


class PolicyVersionListResponse(StrictModel):
    items: list[PolicyVersionSummary]


class PaymentRequest(StrictModel):
    type: Literal["vendor_payment", "payout", "sandbox_transfer"]
    vendor: str = Field(min_length=1, max_length=100)
    recipient: EmailStr | None = None
    amount_cents: int = Field(ge=1, le=10_000_000)
    currency: Literal["USD"] = "USD"
    category: str = Field(min_length=2, max_length=32, pattern=r"^[a-z][a-z0-9_-]{1,31}$")
    reason: str = Field(min_length=1, max_length=500)
    rail: Literal["internal_sandbox", "paypal_sandbox_payouts"] = "internal_sandbox"
    idempotency_key: str = Field(
        min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"
    )

    @field_validator("vendor", "reason")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be blank")
        return value

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        return value.strip().casefold()


class TransactionResponse(StrictModel):
    id: str
    type: str
    vendor: str
    recipient: str | None
    amount_cents: int
    currency: str
    category: str
    reason: str
    status: str
    sandbox_generation: int
    policy_version: int
    rail: str
    rail_reference: str | None
    provider_batch_id: str | None
    provider_item_id: str | None
    provider_status: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class PaymentResponse(StrictModel):
    transaction: TransactionResponse
    policy_result: dict[str, object]
    balance: WalletBalanceResponse


class TransactionPageResponse(StrictModel):
    items: list[TransactionResponse]
    next_cursor: str | None


class ApprovalRequest(StrictModel):
    idempotency_key: str = Field(
        min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"
    )


class RejectionRequest(ApprovalRequest):
    reason: str | None = Field(default=None, max_length=300)


class ReversalRequest(ApprovalRequest):
    reason: str = Field(min_length=1, max_length=300)


class ApprovalListResponse(StrictModel):
    items: list[TransactionResponse]


class SpendCategoryResponse(StrictModel):
    category: str
    budget_cents: int
    committed_cents: int
    reserved_cents: int
    remaining_cents: int
    utilisation_percent: float


class SpendSummaryResponse(StrictModel):
    date: str
    daily_limit_cents: int
    daily_committed_cents: int
    daily_reserved_cents: int
    categories: list[SpendCategoryResponse]


class TransactionDetailResponse(StrictModel):
    transaction: TransactionResponse
    policy_checks: list[dict[str, object]]
    ledger_entries: list[dict[str, object]]
    events: list[dict[str, object]]
    attempts: list[dict[str, object]]


class ResetRequest(StrictModel):
    confirmation: str
    idempotency_key: str = Field(
        min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"
    )


class ResetResponse(StrictModel):
    reset: bool
    balance_cents: int
    sandbox_generation: int
    history_preserved: bool


class AssistantRequest(StrictModel):
    conversation_id: str | None = Field(default=None, max_length=36)
    message: str = Field(min_length=1, max_length=8000)
    request_id: str = Field(
        min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._~-]+$"
    )

    @field_validator("message")
    @classmethod
    def trim_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class AssistantResponse(StrictModel):
    conversation_id: str
    reply: str
    tool_calls: list[dict[str, object]]
    transactions_created: list[str]


class ConversationMessageResponse(StrictModel):
    id: str
    role: str
    content: str
    tool_calls: list[dict[str, object]] | None
    created_at: datetime


class ConversationMessagesResponse(StrictModel):
    items: list[ConversationMessageResponse]


class ConversationSummaryResponse(StrictModel):
    id: str
    title: str
    message_count: int
    preview: str | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class ConversationListResponse(StrictModel):
    items: list[ConversationSummaryResponse]


class ConversationCreateRequest(StrictModel):
    title: str | None = Field(default=None, max_length=120)

    @field_validator("title")
    @classmethod
    def trim_optional_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Conversation title cannot be blank")
        return value


class ConversationUpdateRequest(StrictModel):
    title: str | None = Field(default=None, max_length=120)
    archived: bool | None = None

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        if not value:
            raise ValueError("Conversation title cannot be blank")
        return value

    @model_validator(mode="after")
    def require_change(self) -> "ConversationUpdateRequest":
        if self.title is None and self.archived is None:
            raise ValueError("Provide a title or archive state")
        return self
