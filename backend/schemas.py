"""Validated API contracts for the judge-ready Pactra endpoints."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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
    idempotency_key: str = Field(min_length=8, max_length=128)


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

