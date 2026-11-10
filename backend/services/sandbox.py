"""Safe user-scoped sandbox reset without deleting immutable history."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from backend.defaults import INITIAL_SANDBOX_CENTS
from backend.models import (
    AuditEvent,
    FundReservation,
    PaymentTransaction,
    SYSTEM_ISSUANCE_ACCOUNT_ID,
    User,
    utc_now,
)
from backend.services.audit import record_audit_event
from backend.services.ledger import (
    ensure_system_accounts,
    get_wallet_for_user,
    post_journal,
    release_reservation,
    wallet_balance,
)
from backend.services.policies import reset_policy
from backend.services.transactions import TransactionInProgress


class ResetRateLimited(RuntimeError):
    """The account has used the allowed reset attempts for this hour."""


@dataclass(frozen=True)
class ResetResult:
    balance_cents: int
    sandbox_generation: int
    replayed: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def reset_sandbox(
    session: Session,
    *,
    user: User,
    idempotency_key: str,
    max_resets_per_hour: int = 2,
    reset_policy_json: dict[str, Any] | None = None,
) -> ResetResult:
    wallet = get_wallet_for_user(session, user.id, for_update=True)
    prior_resets = session.exec(
        select(AuditEvent)
        .where(
            AuditEvent.user_id == user.id,
            AuditEvent.event_type == "sandbox.reset",
        )
        .order_by(AuditEvent.created_at.desc())
    ).all()
    for event in prior_resets:
        if event.payload.get("idempotency_key") == idempotency_key:
            return ResetResult(
                balance_cents=int(event.payload["balance_cents"]),
                sandbox_generation=int(event.payload["sandbox_generation"]),
                replayed=True,
            )
    hour_ago = utc_now() - timedelta(hours=1)
    if (
        sum(1 for event in prior_resets if _as_utc(event.created_at) >= hour_ago)
        >= max_resets_per_hour
    ):
        raise ResetRateLimited("Reset limit reached. Try again later")

    in_progress = session.exec(
        select(PaymentTransaction.id).where(
            PaymentTransaction.user_id == user.id,
            (
                (PaymentTransaction.status == "executing")
                | (
                    PaymentTransaction.provider_status.in_(
                        ["PENDING", "PROCESSING", "UNCLAIMED", "ONHOLD"]
                    )
                )
            ),
        )
    ).first()
    if in_progress is not None:
        raise TransactionInProgress(
            "Reset is unavailable while a transaction is still processing"
        )

    pending = session.exec(
        select(PaymentTransaction).where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.sandbox_generation == wallet.sandbox_generation,
            PaymentTransaction.status == "pending_approval",
        )
    ).all()
    for transaction in pending:
        active_hold = session.exec(
            select(FundReservation.id).where(
                FundReservation.transaction_id == transaction.id,
                FundReservation.status == "active",
            )
        ).first()
        if active_hold is not None:
            release_reservation(
                session,
                user_id=user.id,
                transaction_id=transaction.id,
                reason="sandbox_reset",
            )
        transaction.status = "cancelled"
        transaction.updated_at = utc_now()
        session.add(transaction)
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="system",
            actor_id=None,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="transaction.cancelled",
            payload={"reason": "sandbox_reset"},
        )

    ensure_system_accounts(session)
    current_balance = wallet_balance(session, wallet).posted_cents
    adjustment = INITIAL_SANDBOX_CENTS - current_balance
    journal_id: str | None = None
    if adjustment != 0:
        journal = post_journal(
            session,
            user_id=user.id,
            journal_type="reset_adjustment",
            idempotency_key=f"reset:{idempotency_key}",
            amount_cents=abs(adjustment),
            debit_account_id=(
                SYSTEM_ISSUANCE_ACCOUNT_ID
                if adjustment > 0
                else wallet.ledger_account_id
            ),
            credit_account_id=(
                wallet.ledger_account_id
                if adjustment > 0
                else SYSTEM_ISSUANCE_ACCOUNT_ID
            ),
        )
        journal_id = journal.id

    wallet.sandbox_generation += 1
    session.add(wallet)
    reset_policy(
        session,
        user_id=user.id,
        policy_json=reset_policy_json,
    )
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="wallet",
        entity_id=wallet.id,
        event_type="sandbox.reset",
        payload={
            "idempotency_key": idempotency_key,
            "balance_cents": INITIAL_SANDBOX_CENTS,
            "sandbox_generation": wallet.sandbox_generation,
            "journal_id": journal_id,
            "history_preserved": True,
        },
    )
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="wallet",
        entity_id=wallet.id,
        event_type="judge.reset_confirmed",
        payload={"sandbox_generation": wallet.sandbox_generation},
    )
    session.flush()
    return ResetResult(
        balance_cents=INITIAL_SANDBOX_CENTS,
        sandbox_generation=wallet.sandbox_generation,
        replayed=False,
    )
