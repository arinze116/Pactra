"""Deprecated pre-account agent retained only as a fail-closed compatibility shim.

The active product uses ``backend.services.assistant`` and the governed
transaction service. This module must never perform provider I/O.
"""

import asyncio
import logging
from typing import Any, Literal

from google import genai
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator
from sqlmodel import Session

from .config import Settings, settings
from .models import ChatMessage, ChatResponse, Transaction
from .paypal_client import PayPalClient, PayPalError
from .policy_engine import PolicyEngine


logger = logging.getLogger(__name__)


TOOLS = [
    {
        "name": "create_payment",
        "description": (
            "Create a payment to a vendor through PayPal. The policy engine will "
            "evaluate and approve, block, or flag for approval. Use this for paying "
            "invoices, subscriptions, or vendor services."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "vendor": {
                    "type": "string",
                    "description": "Vendor name or PayPal email of the recipient",
                },
                "amount": {
                    "type": "number",
                    "description": "Payment amount in USD",
                },
                "category": {
                    "type": "string",
                    "enum": ["ops", "software", "cloud", "freelance"],
                    "description": "Spending category for budget tracking",
                },
                "reason": {
                    "type": "string",
                    "description": "Business justification for this payment",
                },
            },
            "required": ["vendor", "amount", "category", "reason"],
        },
    },
    {
        "name": "send_payout",
        "description": (
            "Send a payout to an individual via their PayPal email. Use for contractor "
            "payments, freelancer fees, or team disbursements. The policy engine will "
            "evaluate before sending."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recipient_email": {
                    "type": "string",
                    "description": "PayPal email of the recipient",
                },
                "amount": {
                    "type": "number",
                    "description": "Payout amount in USD",
                },
                "category": {
                    "type": "string",
                    "enum": ["ops", "software", "cloud", "freelance"],
                    "description": "Spending category for budget tracking",
                },
                "note": {
                    "type": "string",
                    "description": "Payment note or description shown to recipient",
                },
            },
            "required": ["recipient_email", "amount", "category", "note"],
        },
    },
    {
        "name": "get_spend_summary",
        "description": (
            "Get current spending vs budget for all categories today. Use when asked "
            "about budget, remaining funds, or spend status."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "check_balance",
        "description": "Check remaining budget for a specific spending category.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["ops", "software", "cloud", "freelance"],
                    "description": "The category to check",
                }
            },
            "required": ["category"],
        },
    },
]


SYSTEM_PROMPT = """
You are the deprecated Pactra compatibility agent.

You help businesses make vendor payments and payouts through PayPal,
within pre-configured spending policies set by the business owner.

Your capabilities:
- Create payments to vendors via PayPal
- Send payouts to contractors or team members
- Check current budget status and remaining spend
- Report on spending by category

Your rules:
- Always use a tool when a payment or budget action is requested
- Before any payment, identify the correct category from: ops, software, cloud, freelance
- If a payment is blocked by policy, explain clearly which rule was triggered
- If a payment requires approval, say so and log it as pending
- Always confirm the outcome: approved, blocked, or pending
- Be concise and professional — you are a business tool, not a chatbot
- Never fabricate PayPal transaction IDs or invent outcomes
- If unsure of category, ask before proceeding

This compatibility path cannot execute payments. Direct all active requests to
the authenticated governed transaction service.
When a payment is blocked, confirm: vendor, amount, and the exact rule that blocked it.
""".strip()


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
    """Raised when the Gemini integration has not been configured."""


class PactraAgent:
    def __init__(self, app_settings: Settings = settings):
        self.settings = app_settings
        self._approval_lock = asyncio.Lock()
        self.model: Any | None = None
        if app_settings.gemini_api_key:
            genai.configure(api_key=app_settings.gemini_api_key)
            self.model = genai.GenerativeModel(
                model_name=app_settings.gemini_model,
                system_instruction=SYSTEM_PROMPT,
                tools=[{"function_declarations": TOOLS}],
            )

    async def run(
        self,
        user_message: str,
        history: list[ChatMessage],
        policy_engine: PolicyEngine,
        paypal_client: PayPalClient,
        db_session: Session,
    ) -> ChatResponse:
        if self.model is None:
            raise AgentConfigurationError(
                "GEMINI_API_KEY is not configured. Add it to .env and restart the API."
            )

        trimmed_history = history[-self.settings.max_chat_history :]
        gemini_history = [
            {
                "role": "user" if message.role == "user" else "model",
                "parts": [message.content],
            }
            for message in trimmed_history
        ]
        chat = self.model.start_chat(history=gemini_history)
        response = await asyncio.to_thread(chat.send_message, user_message)

        tool_log: list[dict[str, Any]] = []
        transaction_ids: list[str] = []

        for _ in range(8):
            function_calls = self._extract_function_calls(response)
            if not function_calls:
                reply = self._extract_text(response)
                if not reply:
                    reply = "The request completed, but Gemini returned no text response."
                return ChatResponse(
                    reply=reply,
                    tool_calls=tool_log,
                    transactions_created=transaction_ids,
                )

            function_parts = []
            for name, arguments in function_calls:
                result = await self._execute_tool(
                    name,
                    arguments,
                    policy_engine,
                    paypal_client,
                    db_session,
                )
                tool_log.append(
                    {"name": name, "arguments": arguments, "result": result}
                )
                transaction_id = result.get("transaction_id")
                if transaction_id:
                    transaction_ids.append(str(transaction_id))
                function_parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result},
                        )
                    )
                )

            response = await asyncio.to_thread(chat.send_message, function_parts)

        logger.warning("Gemini exceeded Pactra's tool-call round limit")
        return ChatResponse(
            reply="I stopped because the request required too many consecutive actions.",
            tool_calls=tool_log,
            transactions_created=transaction_ids,
        )

    @staticmethod
    def _extract_function_calls(response: Any) -> list[tuple[str, dict[str, Any]]]:
        calls: list[tuple[str, dict[str, Any]]] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                call = getattr(part, "function_call", None)
                name = getattr(call, "name", "") if call else ""
                if name:
                    calls.append((name, dict(call.args)))
        return calls

    @staticmethod
    def _extract_text(response: Any) -> str:
        text_parts: list[str] = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                text = getattr(part, "text", None)
                if text:
                    text_parts.append(str(text))
        return "\n".join(text_parts).strip()

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
        """Revalidate non-approval rules, then execute a human-approved request."""
        # One process-level lock prevents duplicate execution from simultaneous
        # approval clicks. Stable PayPal request IDs protect network retries.
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
