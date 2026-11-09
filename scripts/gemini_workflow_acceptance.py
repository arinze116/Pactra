#!/usr/bin/env python3
"""Exercise a live Gemini model through Pactra's isolated governed workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=12.0)
    return parser.parse_args()


def _load_api_key(env_file: Path) -> str:
    api_key = dotenv_values(env_file).get("GEMINI_API_KEY")
    if not isinstance(api_key, str) or not api_key.strip():
        raise RuntimeError("GEMINI_API_KEY is missing from the supplied environment file")
    return api_key.strip()


def _payment_call(result: Any) -> dict[str, Any]:
    calls = [
        call
        for call in result.tool_calls
        if call.get("name") == "create_payment_request"
    ]
    if len(calls) != 1:
        raise AssertionError(f"expected one payment tool call, received {len(calls)}")
    return calls[0]


async def _main() -> int:
    args = _parse_args()
    api_key = _load_api_key(args.env_file)
    os.environ["AI_ENABLED"] = "false"
    os.environ["GEMINI_API_KEY"] = api_key

    from sqlalchemy import event
    from sqlalchemy.pool import StaticPool
    from sqlmodel import Session, SQLModel, create_engine, select

    from backend.config import settings
    from backend.models import (
        AuditEvent,
        FundReservation,
        PaymentTransaction,
        TransactionAttempt,
    )
    from backend.services.accounts import create_account
    from backend.services.assistant import run_assistant
    from backend.services.ledger import get_wallet_for_user, wallet_balance
    from backend.services.transactions import transaction_detail

    settings.ai_enabled = True
    settings.gemini_api_key = api_key
    settings.gemini_model = args.model
    settings.gemini_request_timeout_seconds = args.timeout_seconds
    settings.paypal_payouts_enabled = False
    settings.paypal_mock_mode = True

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    report: dict[str, Any] = {
        "model": args.model,
        "database": "isolated in-memory SQLite",
        "paypal_enabled": False,
    }
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email="gemini-acceptance@example.com",
            password_hash="unused-isolated-test-hash",
        )
        user = account.user

        completed_result = await run_assistant(
            session,
            user=user,
            message=(
                "Create an internal sandbox payout of $49 USD to "
                "ai-acceptance-recipient@example.com for monthly software "
                "subscription in category software. Use the payment creation tool now."
            ),
            conversation_id=None,
            request_id="gemini-live-completed-0001",
        )
        completed_call = _payment_call(completed_result)
        completed_transaction = session.get(
            PaymentTransaction, completed_result.transaction_ids[0]
        )
        if completed_transaction is None:
            raise AssertionError("completed workflow transaction was not persisted")
        completed_args = completed_call["arguments"]
        expected_completed = {
            "type": "payout",
            "amount_cents": 4_900,
            "currency": "USD",
            "recipient": "ai-acceptance-recipient@example.com",
            "category": "software",
            "rail": "internal_sandbox",
        }
        for name, expected in expected_completed.items():
            if completed_args.get(name) != expected:
                raise AssertionError(
                    f"completed workflow argument {name!r} did not match"
                )
        if completed_transaction.status != "completed":
            raise AssertionError("internal sandbox payment did not complete")
        if completed_transaction.rail != "internal_sandbox":
            raise AssertionError("live acceptance attempted a provider rail")
        if completed_transaction.recipient != "ai-acceptance-recipient@example.com":
            raise AssertionError("live acceptance recipient was not persisted")
        if completed_transaction.policy_result.get("decision") != "approved":
            raise AssertionError("policy approval was not persisted")
        completed_receipt = transaction_detail(
            session,
            user_id=user.id,
            transaction_id=completed_transaction.id,
        )
        if len(completed_receipt["ledger_entries"]) != 2:
            raise AssertionError("completed receipt lacks balanced ledger entries")
        if len(completed_receipt["attempts"]) != 1:
            raise AssertionError("completed receipt lacks one execution attempt")
        report["completed_payment"] = {
            "status": completed_transaction.status,
            "tool": completed_call["name"],
            "arguments": completed_args,
            "policy_decision": completed_transaction.policy_result.get("decision"),
            "ledger_entry_count": len(completed_receipt["ledger_entries"]),
            "receipt_event_count": len(completed_receipt["events"]),
            "attempt_count": len(completed_receipt["attempts"]),
        }

        approval_result = await run_assistant(
            session,
            user=user,
            message=(
                "Create an internal sandbox vendor payment to Ada Contractor for "
                "$120 USD in category freelance, reason contract work. Use the "
                "payment creation tool now."
            ),
            conversation_id=None,
            request_id="gemini-live-approval-0001",
        )
        approval_call = _payment_call(approval_result)
        if len(approval_result.transaction_ids) != 1:
            raise AssertionError(
                "approval workflow did not persist one transaction: "
                f"{approval_call}"
            )
        approval_transaction = session.get(
            PaymentTransaction, approval_result.transaction_ids[0]
        )
        if approval_transaction is None:
            raise AssertionError("approval workflow transaction was not persisted")
        if approval_transaction.status != "pending_approval":
            raise AssertionError("approval threshold was not enforced")
        if approval_transaction.policy_result.get("decision") != "approval_required":
            raise AssertionError("approval-required policy decision was not persisted")
        active_reservations = session.exec(
            select(FundReservation).where(
                FundReservation.transaction_id == approval_transaction.id,
                FundReservation.status == "active",
            )
        ).all()
        approval_attempts = session.exec(
            select(TransactionAttempt).where(
                TransactionAttempt.transaction_id == approval_transaction.id
            )
        ).all()
        if len(active_reservations) != 1 or approval_attempts:
            raise AssertionError("pending approval did not remain reserved and unexecuted")
        report["approval_threshold"] = {
            "status": approval_transaction.status,
            "tool": approval_call["name"],
            "amount_cents": approval_call["arguments"].get("amount_cents"),
            "policy_decision": approval_transaction.policy_result.get("decision"),
            "active_reservation_count": len(active_reservations),
            "attempt_count": len(approval_attempts),
        }

        count_before_missing = len(session.exec(select(PaymentTransaction)).all())
        missing_result = await run_assistant(
            session,
            user=user,
            message=(
                "Pay Linear for our monthly software subscription using internal "
                "sandbox."
            ),
            conversation_id=None,
            request_id="gemini-live-missing-amount-0001",
        )
        count_after_missing = len(session.exec(select(PaymentTransaction)).all())
        if count_after_missing != count_before_missing:
            raise AssertionError("missing amount unexpectedly created a transaction")
        report["missing_information"] = {
            "transaction_created": False,
            "tool_call_count": len(missing_result.tool_calls),
            "reply_present": bool(missing_result.reply.strip()),
        }

        transactions = session.exec(select(PaymentTransaction)).all()
        if any(transaction.rail != "internal_sandbox" for transaction in transactions):
            raise AssertionError("acceptance test created a provider-rail transaction")
        wallet = get_wallet_for_user(session, user.id)
        balance = wallet_balance(session, wallet)
        audit_types = {
            event.event_type for event in session.exec(select(AuditEvent)).all()
        }
        required_audits = {
            "assistant.message_sent",
            "assistant.tool_called",
            "payment.requested",
            "transaction.completed",
            "payment.pending_approval",
        }
        if not required_audits.issubset(audit_types):
            raise AssertionError("required assistant and payment audit events are missing")
        report["governance"] = {
            "all_rails_internal_sandbox": True,
            "transaction_count": len(transactions),
            "required_audits_present": True,
            "posted_cents": balance.posted_cents,
            "reserved_cents": balance.reserved_cents,
            "available_cents": balance.available_cents,
        }
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    report["passed"] = True
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
