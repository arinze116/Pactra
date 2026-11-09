"""Deprecated pre-account agent retained only as a fail-closed compatibility shim.

The active product uses ``backend.services.assistant`` and the governed
transaction service. This module must never perform provider I/O.
"""

import asyncio
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator
from sqlmodel import Session

from .config import Settings, settings
from .models import ChatMessage, ChatResponse, Transaction
from .paypal_client import PayPalClient, PayPalError
from .policy_engine import PolicyEngine


Category = Literal["ops", "software", "cloud", "freelance"]


class PaymentToolInput(BaseModel):
    vendor: str = Field(min_length=1, max_length=200)
    amount: float = Field(gt=0, le=1_000_000)
    category: Category
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("vendor", "reason")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value.strip()


class PayoutToolInput(BaseModel):
    recipient_email: EmailStr
    amount: float = Field(gt=0, le=1_000_000)
    category: Category
    note: str = Field(min_length=1, max_length=500)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Note cannot be blank")
        return value.strip()


class BalanceToolInput(BaseModel):
    category: Category


class AgentConfigurationError(RuntimeError):
    """Raised when the retired compatibility agent is invoked."""


class PactraAgent:
    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self._approval_lock = asyncio.Lock()

    async def run(
        self,
        user_message: str,
        history: list[ChatMessage],
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> ChatResponse:
        del user_message, history, policy_engine, paypal_client, db_session
        raise AgentConfigurationError(
            "Legacy PactraAgent is disabled; use backend.services.assistant"
        )

    async def _execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> dict[str, Any]:
        try:
            if name == "create_payment":
                data = PaymentToolInput.model_validate(arguments)
                return await self._handle_create_payment(
                    **data.model_dump(),
                    policy_engine=policy_engine,
                    paypal_client=paypal_client,
                    db_session=db_session,
                )
            if name == "send_payout":
                data = PayoutToolInput.model_validate(arguments)
                return await self._handle_send_payout(
                    **data.model_dump(mode="json"),
                    policy_engine=policy_engine,
                    paypal_client=paypal_client,
                    db_session=db_session,
                )
            if name == "get_spend_summary":
                return self._handle_get_spend_summary(policy_engine, db_session)
            if name == "check_balance":
                data = BalanceToolInput.model_validate(arguments)
                return self._handle_check_balance(
                    data.category, policy_engine, db_session
                )
            return {"outcome": "error", "error": f"Unknown tool: {name}"}
        except (ValidationError, ValueError) as exc:
            return {"outcome": "error", "error": str(exc)}

    async def _handle_create_payment(
        self,
        vendor: str,
        amount: float,
        category: Category,
        reason: str,
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> dict[str, Any]:
        policy_result = policy_engine.check(
            vendor, amount, category, db_session
        )
        transaction = Transaction(
            vendor=vendor,
            amount=amount,
            currency=policy_engine.policy["currency"],
            category=category,
            reason=reason,
            status=policy_result.status,
            block_reason=policy_result.rule_triggered,
            transaction_type="payment",
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)

        if policy_result.status == "blocked":
            return self._policy_result(transaction, policy_result.reason)
        if policy_result.status == "pending_approval":
            return self._policy_result(transaction, policy_result.reason)

        try:
            await self._execute_approved_transaction(
                transaction, policy_engine, paypal_client, db_session
            )
        except PayPalError as exc:
            return {
                "outcome": "failed",
                "status": "approved",
                "transaction_id": transaction.id,
                "vendor": vendor,
                "amount": amount,
                "category": category,
                "error": str(exc),
            }
        return self._success_result(transaction)

    async def _handle_send_payout(
        self,
        recipient_email: str,
        amount: float,
        category: Category,
        note: str,
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> dict[str, Any]:
        policy_result = policy_engine.check(
            recipient_email, amount, category, db_session
        )
        transaction = Transaction(
            vendor=recipient_email,
            amount=amount,
            currency=policy_engine.policy["currency"],
            category=category,
            reason=note,
            status=policy_result.status,
            block_reason=policy_result.rule_triggered,
            transaction_type="payout",
        )
        db_session.add(transaction)
        db_session.commit()
        db_session.refresh(transaction)

        if policy_result.status in {"blocked", "pending_approval"}:
            return self._policy_result(transaction, policy_result.reason)

        try:
            await self._execute_approved_transaction(
                transaction, policy_engine, paypal_client, db_session
            )
        except PayPalError as exc:
            return {
                "outcome": "failed",
                "status": "approved",
                "transaction_id": transaction.id,
                "vendor": recipient_email,
                "amount": amount,
                "category": category,
                "error": str(exc),
            }
        return self._success_result(transaction)

    async def _execute_approved_transaction(
        self,
        transaction: Transaction,
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> None:
        """Fail closed; active execution belongs to the transaction service/worker."""
        del policy_engine, paypal_client
        db_session.rollback()
        transaction.paypal_status = "FAILED"
        db_session.add(transaction)
        db_session.commit()
        raise PayPalError(
            "Legacy payment execution is disabled; use the governed transaction service"
        )

    async def approve_transaction(
        self,
        transaction: Transaction,
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> Transaction:
        """Revalidate a legacy request, then fail closed before provider I/O."""
        # Retain the lock so simultaneous legacy calls cannot race before the
        # compatibility path rejects execution.
        async with self._approval_lock:
            db_session.refresh(transaction)
            if transaction.status != "pending_approval":
                raise ValueError("Only pending transactions can be approved")

            policy_result = policy_engine.check(
                transaction.vendor,
                transaction.amount,
                transaction.category,
                db_session,
            )
            if policy_result.status == "blocked":
                transaction.status = "blocked"
                transaction.block_reason = policy_result.rule_triggered
                db_session.add(transaction)
                db_session.commit()
                db_session.refresh(transaction)
                return transaction

            await self._execute_approved_transaction(
                transaction, policy_engine, paypal_client, db_session
            )
            return transaction

    @staticmethod
    def _policy_result(
        transaction: Transaction, reason: str | None
    ) -> dict[str, Any]:
        return {
            "outcome": transaction.status,
            "status": transaction.status,
            "transaction_id": transaction.id,
            "vendor": transaction.vendor,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "category": transaction.category,
            "reason": reason,
            "rule_triggered": transaction.block_reason,
        }

    @staticmethod
    def _success_result(transaction: Transaction) -> dict[str, Any]:
        return {
            "outcome": "approved",
            "status": "approved",
            "transaction_id": transaction.id,
            "vendor": transaction.vendor,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "category": transaction.category,
            "paypal_order_id": transaction.paypal_order_id,
            "paypal_status": transaction.paypal_status,
        }

    @staticmethod
    def _handle_get_spend_summary(
        policy_engine: PolicyEngine, db_session: Session
    ) -> dict[str, Any]:
        return {
            "outcome": "success",
            "categories": [
                item.model_dump() for item in policy_engine.get_summary(db_session)
            ],
        }

    @staticmethod
    def _handle_check_balance(
        category: Category,
        policy_engine: PolicyEngine,
        db_session: Session,
    ) -> dict[str, Any]:
        summary = next(
            (
                item
                for item in policy_engine.get_summary(db_session)
                if item.category == category
            ),
            None,
        )
        if summary is None:
            return {"outcome": "error", "error": "Category budget not found"}
        return {"outcome": "success", "category": summary.model_dump()}
