"""Unified governed transaction lifecycle for every request source and rail."""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, update
from sqlmodel import Session, select

from backend.config import settings
from backend.models import (
    ApprovalAction,
    AuditEvent,
    FundReservation,
    LedgerAccount,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
    User,
    utc_now,
)
from backend.services.audit import record_audit_event
from backend.services.ledger import (
    IdempotencyConflict,
    LedgerError,
    WalletBalance,
    capture_reservation,
    get_wallet_for_user,
    release_reservation,
    reserve_funds,
    reverse_capture,
    wallet_balance,
)
from backend.services.policies import PolicyDecision, evaluate_policy, get_current_policy


class TransactionServiceError(RuntimeError):
    code = "TRANSACTION_ERROR"


class TransactionNotFound(TransactionServiceError):
    code = "NOT_FOUND"


class TransactionIdempotencyConflict(TransactionServiceError):
    code = "IDEMPOTENCY_CONFLICT"


class PolicyBlocked(TransactionServiceError):
    code = "POLICY_BLOCKED"

    def __init__(self, transaction: PaymentTransaction, decision: PolicyDecision):
        super().__init__(decision.reason_code or self.code)
        self.transaction = transaction
        self.decision = decision


class IntegrationUnavailable(TransactionServiceError):
    code = "PAYPAL_UNAVAILABLE"


class DemoProviderDisabled(IntegrationUnavailable):
    code = "DEMO_SANDBOX_ONLY"


class DemoResourceLimit(TransactionServiceError):
    code = "DEMO_RESOURCE_LIMIT"


class AlreadyActioned(TransactionServiceError):
    code = "ALREADY_ACTIONED"


class PolicyChanged(TransactionServiceError):
    code = "POLICY_CHANGED"

    def __init__(
        self,
        transaction: PaymentTransaction,
        *,
        code: str = "POLICY_CHANGED",
    ):
        self.code = code
        message = (
            "Your available sandbox balance is too low."
            if code == "INSUFFICIENT_FUNDS"
            else "Policy changed. Review the updated decision before approving."
        )
        super().__init__(message)
        self.transaction = transaction


class NotReversible(TransactionServiceError):
    code = "NOT_REVERSIBLE"


class TransactionInProgress(TransactionServiceError):
    code = "TRANSACTION_IN_PROGRESS"


@dataclass(frozen=True)
class TransactionResult:
    transaction: PaymentTransaction
    policy_result: dict[str, Any]
    balance: WalletBalance
    replayed: bool = False


@dataclass(frozen=True)
class ApprovalContext:
    transaction: PaymentTransaction
    requester: User
    policy_decision: PolicyDecision
    balance: WalletBalance


def _canonical_matches(transaction: PaymentTransaction, payload: dict[str, Any]) -> bool:
    return all(
        (
            transaction.type == payload["type"],
            transaction.vendor == payload["vendor"],
            transaction.recipient == payload.get("recipient"),
            transaction.amount_cents == payload["amount_cents"],
            transaction.currency == payload["currency"],
            transaction.category == payload["category"],
            transaction.reason == payload["reason"],
            transaction.rail == payload["rail"],
        )
    )


def get_owned_transaction(
    session: Session,
    *,
    user_id: str,
    transaction_id: str,
    for_update: bool = False,
) -> PaymentTransaction:
    statement = select(PaymentTransaction).where(
        PaymentTransaction.id == transaction_id,
        PaymentTransaction.user_id == user_id,
    )
    if for_update:
        statement = statement.with_for_update()
    transaction = session.exec(statement).one_or_none()
    if transaction is None:
        raise TransactionNotFound("Transaction not found")
    return transaction


def _record_state(
    session: Session,
    *,
    transaction: PaymentTransaction,
    previous: str,
    event_type: str = "transaction.state_changed",
) -> None:
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type=event_type,
        payload={"from": previous, "to": transaction.status},
    )


def _record_approval_revalidation_block(
    session: Session,
    *,
    transaction: PaymentTransaction,
    previous_policy_version: int,
) -> None:
    _record_state(session, transaction=transaction, previous="pending_approval")
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="user",
        actor_id=transaction.user_id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="payment.blocked",
        payload={
            "source": "approval_revalidation",
            "reason_code": transaction.failure_code,
            "previous_policy_version": previous_policy_version,
            "policy_version": transaction.policy_version,
        },
    )


def _execute_internal(
    session: Session,
    *,
    transaction: PaymentTransaction,
    rail_request_id: str | None = None,
) -> TransactionAttempt:
    attempt_count = session.exec(
        select(func.count(TransactionAttempt.id)).where(
            TransactionAttempt.transaction_id == transaction.id
        )
    ).one()
    attempt_number = int(attempt_count or 0) + 1
    attempt = TransactionAttempt(
        transaction_id=transaction.id,
        attempt_number=attempt_number,
        rail="internal_sandbox",
        rail_request_id=rail_request_id or f"internal:{transaction.id}:{attempt_number}",
        status="completed",
        response_code="INTERNAL_LEDGER_CAPTURED",
        finished_at=utc_now(),
    )
    session.add(attempt)
    capture_reservation(session, user_id=transaction.user_id, transaction=transaction)
    previous = transaction.status
    transaction.status = "completed"
    transaction.rail_reference = attempt.rail_request_id
    transaction.completed_at = utc_now()
    transaction.updated_at = transaction.completed_at
    session.add(transaction)
    _record_state(session, transaction=transaction, previous=previous)
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="transaction.completed",
        payload={"rail": "internal_sandbox", "sandbox_only": True},
    )
    session.flush()
    return attempt


def prepare_paypal_attempt(
    session: Session, *, transaction: PaymentTransaction
) -> TransactionAttempt:
    """Persist the stable provider attempt before any network request."""
    existing = session.exec(
        select(TransactionAttempt)
        .where(
            TransactionAttempt.transaction_id == transaction.id,
            TransactionAttempt.status.in_(["submitting", "processing", "unknown"]),
        )
        .order_by(TransactionAttempt.attempt_number.desc())
        .limit(1)
    ).one_or_none()
    if existing is not None:
        return existing
    count = session.exec(
        select(func.count(TransactionAttempt.id)).where(
            TransactionAttempt.transaction_id == transaction.id
        )
    ).one()
    number = int(count or 0) + 1
    attempt = TransactionAttempt(
        transaction_id=transaction.id,
        attempt_number=number,
        rail="paypal_sandbox_payouts",
        rail_request_id=f"pactra-{transaction.id}-a{number}",
        status="submitting",
    )
    session.add(attempt)
    session.flush()
    return attempt


def retry_transaction(
    session: Session,
    *,
    user: User,
    transaction_id: str,
    idempotency_key: str,
) -> tuple[PaymentTransaction, TransactionAttempt]:
    """Retry a terminal internal failure with a fresh, idempotent attempt."""
    retry_events = session.exec(
        select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.event_type == "transaction.retry_requested",
        )
    ).all()
    for event in retry_events:
        if event.payload.get("idempotency_key") == idempotency_key:
            if event.entity_id != transaction_id:
                raise TransactionIdempotencyConflict(
                    "This request key was used for a different retry"
                )
            transaction = get_owned_transaction(
                session, user_id=user.id, transaction_id=transaction_id
            )
            existing_attempt = session.get(
                TransactionAttempt, str(event.payload["attempt_id"])
            )
            if existing_attempt is None:
                raise TransactionServiceError("Retry attempt was not found")
            return transaction, existing_attempt

    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id, for_update=True
    )
    if user.is_demo and transaction.rail != "internal_sandbox":
        raise DemoProviderDisabled(
            "Demo workspaces cannot submit or retry provider payments"
        )
    if transaction.status != "failed":
        raise AlreadyActioned("Only definitively failed transactions can be retried")
    if transaction.rail == "paypal_sandbox_payouts" and transaction.provider_status in {
        "UNKNOWN",
        "PENDING",
        "PROCESSING",
        "UNCLAIMED",
        "ONHOLD",
    }:
        raise IntegrationUnavailable(
            "Provider outcome is unresolved and must be reconciled"
        )
    wallet = get_wallet_for_user(session, user.id, for_update=True)
    policy = get_current_policy(session, user.id, for_update=True)
    decision = evaluate_policy(
        session,
        user=user,
        wallet=wallet,
        policy=policy,
        vendor=transaction.vendor,
        amount_cents=transaction.amount_cents,
        currency=transaction.currency,
        category=transaction.category,
    )
    if decision.decision == "blocked":
        if decision.reason_code == "INSUFFICIENT_FUNDS":
            raise LedgerError("Your available sandbox balance is too low")
        raise AlreadyActioned(decision.reason_code or "Policy blocks this retry")
    transaction.policy_version = policy.version
    transaction.policy_result = decision.snapshot()
    reserve_funds(session, user_id=user.id, transaction=transaction)
    previous = transaction.status
    transaction.status = "executing"
    transaction.failure_code = None
    transaction.updated_at = utc_now()
    session.add(transaction)
    _record_state(session, transaction=transaction, previous=previous)
    if transaction.rail == "internal_sandbox":
        request_id = f"retry:{transaction_id}:{idempotency_key}"
        attempt = _execute_internal(
            session, transaction=transaction, rail_request_id=request_id
        )
    else:
        attempt = prepare_paypal_attempt(session, transaction=transaction)
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="transaction.retry_requested",
        payload={
            "idempotency_key": idempotency_key,
            "attempt_id": attempt.id,
            "attempt_number": attempt.attempt_number,
        },
    )
    session.flush()
    return transaction, attempt


def create_payment_request(
    session: Session,
    *,
    user: User,
    payload: dict[str, Any],
) -> TransactionResult:
    """Apply policy, reserve funds and execute through the selected rail once."""
    if user.is_demo and payload["rail"] != "internal_sandbox":
        raise DemoProviderDisabled(
            "Demo workspaces use the internal sandbox only"
        )
    existing = session.exec(
        select(PaymentTransaction).where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.idempotency_key == payload["idempotency_key"],
        )
    ).one_or_none()
    if existing is not None:
        if not _canonical_matches(existing, payload):
            raise TransactionIdempotencyConflict(
                "This request key was used for a different payment"
            )
        if existing.status == "blocked":
            raise PolicyBlocked(
                existing, PolicyDecision.from_snapshot(existing.policy_result)
            )
        wallet = get_wallet_for_user(session, user.id)
        return TransactionResult(
            transaction=existing,
            policy_result=existing.policy_result,
            balance=wallet_balance(session, wallet),
            replayed=True,
        )

    if payload["rail"] == "paypal_sandbox_payouts":
        if payload["type"] != "payout":
            raise IntegrationUnavailable("PayPal Sandbox is available only for payouts")
        if not (
            settings.paypal_payouts_enabled
            and settings.paypal_client_id
            and settings.paypal_client_secret
            and settings.paypal_test_recipient_email
            and not settings.paypal_mock_mode
            and settings.paypal_base_url.rstrip("/")
            == "https://api-m.sandbox.paypal.com"
        ):
            raise IntegrationUnavailable(
                "PayPal Sandbox is not configured. Use the internal sandbox rail."
            )

    wallet = get_wallet_for_user(session, user.id, for_update=True)
    existing = session.exec(
        select(PaymentTransaction).where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.idempotency_key == payload["idempotency_key"],
        )
    ).one_or_none()
    if existing is not None:
        if not _canonical_matches(existing, payload):
            raise TransactionIdempotencyConflict(
                "This request key was used for a different payment"
            )
        if existing.status == "blocked":
            raise PolicyBlocked(
                existing, PolicyDecision.from_snapshot(existing.policy_result)
            )
        return TransactionResult(
            transaction=existing,
            policy_result=existing.policy_result,
            balance=wallet_balance(session, wallet),
            replayed=True,
        )
    if user.is_demo:
        transaction_count = int(
            session.exec(
                select(func.count(PaymentTransaction.id)).where(
                    PaymentTransaction.user_id == user.id
                )
            ).one()
            or 0
        )
        if transaction_count >= settings.demo_max_transactions:
            raise DemoResourceLimit(
                "This demo reached its activity limit. Start a fresh demo to continue."
            )
    policy = get_current_policy(session, user.id, for_update=True)
    transaction = PaymentTransaction(
        user_id=user.id,
        idempotency_key=payload["idempotency_key"],
        type=payload["type"],
        vendor=payload["vendor"],
        recipient=payload.get("recipient"),
        amount_cents=payload["amount_cents"],
        currency=payload["currency"],
        category=payload["category"],
        reason=payload["reason"],
        status="draft",
        sandbox_generation=wallet.sandbox_generation,
        policy_version=policy.version,
        policy_result={},
        rail=payload["rail"],
    )
    session.add(transaction)
    session.flush()
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="payment.requested",
        payload={"source": payload.get("source", "manual")},
    )

    decision = evaluate_policy(
        session,
        user=user,
        wallet=wallet,
        policy=policy,
        vendor=transaction.vendor,
        amount_cents=transaction.amount_cents,
        currency=transaction.currency,
        category=transaction.category,
    )
    transaction.policy_result = decision.snapshot()
    transaction.policy_version = decision.policy_version
    previous = transaction.status
    if decision.decision == "blocked":
        transaction.status = "blocked"
        transaction.failure_code = decision.reason_code
        transaction.updated_at = utc_now()
        session.add(transaction)
        _record_state(session, transaction=transaction, previous=previous)
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="system",
            actor_id=None,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="payment.blocked",
            payload={"reason_code": decision.reason_code},
        )
        session.flush()
        raise PolicyBlocked(transaction, decision)

    reserve_funds(session, user_id=user.id, transaction=transaction)
    if decision.decision == "approval_required":
        transaction.status = "pending_approval"
        transaction.updated_at = utc_now()
        session.add(transaction)
        _record_state(session, transaction=transaction, previous=previous)
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="system",
            actor_id=None,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="payment.pending_approval",
            payload={},
        )
    else:
        transaction.status = "executing"
        transaction.updated_at = utc_now()
        session.add(transaction)
        _record_state(session, transaction=transaction, previous=previous)
        if transaction.rail == "internal_sandbox":
            _execute_internal(session, transaction=transaction)
        else:
            prepare_paypal_attempt(session, transaction=transaction)
    session.flush()
    return TransactionResult(
        transaction=transaction,
        policy_result=transaction.policy_result,
        balance=wallet_balance(session, wallet),
    )


def approve_transaction(
    session: Session,
    *,
    user: User,
    transaction_id: str,
    idempotency_key: str,
) -> PaymentTransaction:
    existing_action = session.exec(
        select(ApprovalAction).where(
            ApprovalAction.user_id == user.id,
            ApprovalAction.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    if existing_action is not None:
        if existing_action.transaction_id != transaction_id or existing_action.action != "approved":
            raise TransactionIdempotencyConflict(
                "This request key was used for a different approval action"
            )
        return get_owned_transaction(
            session, user_id=user.id, transaction_id=transaction_id
        )

    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id, for_update=True
    )
    if user.is_demo and transaction.rail != "internal_sandbox":
        raise DemoProviderDisabled(
            "Demo workspaces cannot approve provider payments"
        )
    if transaction.status != "pending_approval":
        raise AlreadyActioned("This request was already actioned")
    wallet = get_wallet_for_user(session, user.id, for_update=True)
    policy = get_current_policy(session, user.id, for_update=True)
    decision = evaluate_policy(
        session,
        user=user,
        wallet=wallet,
        policy=policy,
        vendor=transaction.vendor,
        amount_cents=transaction.amount_cents,
        currency=transaction.currency,
        category=transaction.category,
        exclude_transaction_id=transaction.id,
    )
    if policy.version != transaction.policy_version:
        previous_policy_version = transaction.policy_version
        transaction.policy_version = policy.version
        transaction.policy_result = decision.snapshot()
        transaction.updated_at = utc_now()
        if decision.decision == "blocked":
            transaction.status = "blocked"
            transaction.failure_code = decision.reason_code
            release_reservation(
                session,
                user_id=user.id,
                transaction_id=transaction.id,
                reason="policy_changed",
            )
            _record_approval_revalidation_block(
                session,
                transaction=transaction,
                previous_policy_version=previous_policy_version,
            )
        session.add(transaction)
        session.flush()
        raise PolicyChanged(transaction)
    if decision.decision == "blocked":
        transaction.policy_result = decision.snapshot()
        transaction.failure_code = decision.reason_code
        transaction.status = "blocked"
        transaction.updated_at = utc_now()
        release_reservation(
            session,
            user_id=user.id,
            transaction_id=transaction.id,
            reason=decision.reason_code or "approval_revalidation_failed",
        )
        _record_approval_revalidation_block(
            session,
            transaction=transaction,
            previous_policy_version=transaction.policy_version,
        )
        session.add(transaction)
        session.flush()
        raise PolicyChanged(
            transaction,
            code=(
                "INSUFFICIENT_FUNDS"
                if decision.reason_code == "INSUFFICIENT_FUNDS"
                else "POLICY_CHANGED"
            ),
        )

    result = session.exec(
        update(PaymentTransaction)
        .where(
            PaymentTransaction.id == transaction.id,
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.status == "pending_approval",
        )
        .values(status="executing", updated_at=utc_now())
    )
    if result.rowcount != 1:
        raise AlreadyActioned("This request was already actioned")
    session.expire(transaction)
    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id, for_update=True
    )
    action = ApprovalAction(
        transaction_id=transaction.id,
        user_id=user.id,
        idempotency_key=idempotency_key,
        action="approved",
        policy_version=policy.version,
    )
    session.add(action)
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="approval.approved",
        payload={"policy_version": policy.version},
    )
    if transaction.rail == "internal_sandbox":
        _execute_internal(session, transaction=transaction)
    else:
        prepare_paypal_attempt(session, transaction=transaction)
    session.flush()
    return transaction


def reject_transaction(
    session: Session,
    *,
    user: User,
    transaction_id: str,
    idempotency_key: str,
    reason: str | None,
) -> PaymentTransaction:
    existing_action = session.exec(
        select(ApprovalAction).where(
            ApprovalAction.user_id == user.id,
            ApprovalAction.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    if existing_action is not None:
        if existing_action.transaction_id != transaction_id or existing_action.action != "rejected":
            raise TransactionIdempotencyConflict(
                "This request key was used for a different approval action"
            )
        return get_owned_transaction(
            session, user_id=user.id, transaction_id=transaction_id
        )
    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id, for_update=True
    )
    if transaction.status != "pending_approval":
        raise AlreadyActioned("This request was already actioned")
    result = session.exec(
        update(PaymentTransaction)
        .where(
            PaymentTransaction.id == transaction.id,
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.status == "pending_approval",
        )
        .values(status="rejected", updated_at=utc_now())
    )
    if result.rowcount != 1:
        raise AlreadyActioned("This request was already actioned")
    release_reservation(
        session,
        user_id=user.id,
        transaction_id=transaction.id,
        reason=reason or "rejected",
    )
    action = ApprovalAction(
        transaction_id=transaction.id,
        user_id=user.id,
        idempotency_key=idempotency_key,
        action="rejected",
        reason=reason,
        policy_version=transaction.policy_version,
    )
    session.add(action)
    session.expire(transaction)
    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id
    )
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="approval.rejected",
        payload={"reason": reason},
    )
    session.flush()
    return transaction


def reverse_transaction(
    session: Session,
    *,
    user: User,
    transaction_id: str,
    idempotency_key: str,
    reason: str,
) -> tuple[PaymentTransaction, LedgerJournal]:
    transaction = get_owned_transaction(
        session, user_id=user.id, transaction_id=transaction_id, for_update=True
    )
    journal_key = f"reverse:{idempotency_key}"
    existing = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.user_id == user.id,
            LedgerJournal.idempotency_key == journal_key,
        )
    ).one_or_none()
    if existing is not None:
        if existing.transaction_id != transaction.id:
            raise TransactionIdempotencyConflict(
                "This request key was used for a different reversal"
            )
        return transaction, existing
    if transaction.rail != "internal_sandbox":
        raise NotReversible("Provider payouts cannot be manually reversed")
    if transaction.status != "completed":
        raise NotReversible("Only completed internal transactions can be reversed")
    journal = reverse_capture(
        session,
        user_id=user.id,
        transaction=transaction,
        idempotency_key=journal_key,
    )
    previous = transaction.status
    transaction.status = "reversed"
    transaction.updated_at = utc_now()
    session.add(transaction)
    _record_state(session, transaction=transaction, previous=previous)
    record_audit_event(
        session,
        user_id=user.id,
        actor_type="user",
        actor_id=user.id,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="transaction.reversed",
        payload={"reason": reason, "journal_id": journal.id},
    )
    session.flush()
    return transaction, journal


def get_active_paypal_attempt(
    session: Session, *, transaction_id: str
) -> TransactionAttempt:
    attempt = session.exec(
        select(TransactionAttempt)
        .where(TransactionAttempt.transaction_id == transaction_id)
        .order_by(TransactionAttempt.attempt_number.desc())
        .limit(1)
    ).one_or_none()
    if attempt is None or attempt.rail != "paypal_sandbox_payouts":
        raise TransactionServiceError("PayPal payout attempt was not found")
    return attempt


def enqueue_paypal_reconciliation(
    session: Session,
    *,
    user: User,
    transaction_id: str,
) -> PaymentTransaction:
    """Queue provider recovery while preserving the original payout attempt.

    Known batches are refreshed with a read-only provider lookup. An ambiguous
    submission without a batch reference is replayed only after this explicit
    user action, using the same attempt number and stable provider identifiers.
    Automatic worker scans never make this transition.
    """
    transaction = get_owned_transaction(
        session,
        user_id=user.id,
        transaction_id=transaction_id,
        for_update=True,
    )
    if user.is_demo:
        raise DemoProviderDisabled(
            "Demo workspaces cannot access provider reconciliation"
        )
    if transaction.rail != "paypal_sandbox_payouts" or transaction.status not in {
        "executing",
        "completed",
    }:
        raise AlreadyActioned("This transaction cannot be reconciled")
    attempt = session.exec(
        select(TransactionAttempt)
        .where(TransactionAttempt.transaction_id == transaction.id)
        .order_by(TransactionAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
    ).one_or_none()
    if attempt is None or attempt.rail != "paypal_sandbox_payouts":
        raise TransactionServiceError("PayPal payout attempt was not found")
    if not attempt.provider_batch_id and attempt.status == "unknown":
        attempt.status = "submitting"
        attempt.finished_at = None
        transaction.updated_at = utc_now()
        session.add_all([attempt, transaction])
        record_audit_event(
            session,
            user_id=transaction.user_id,
            actor_type="user",
            actor_id=user.id,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="paypal.ambiguous_submission_recovery_queued",
            payload={
                "attempt": attempt.attempt_number,
                "rail_request_id": attempt.rail_request_id,
            },
        )
        session.flush()
        return transaction
    if not attempt.provider_batch_id:
        raise IntegrationUnavailable(
            "Provider submission has not reached an ambiguous state that can be recovered"
        )
    if attempt.status != "processing":
        attempt.status = "processing"
        attempt.finished_at = None
        transaction.updated_at = utc_now()
        session.add_all([attempt, transaction])
        record_audit_event(
            session,
            user_id=transaction.user_id,
            actor_type="user",
            actor_id=user.id,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="paypal.reconciliation_queued",
            payload={"attempt": attempt.attempt_number},
        )
    session.flush()
    return transaction


def record_paypal_submission(
    session: Session,
    *,
    transaction: PaymentTransaction,
    attempt: TransactionAttempt,
    batch_id: str,
    batch_status: str,
) -> None:
    attempt.provider_batch_id = batch_id
    attempt.provider_status = batch_status
    attempt.status = "processing"
    attempt.response_code = None
    transaction.provider_batch_id = batch_id
    transaction.provider_status = batch_status
    transaction.failure_code = None
    transaction.updated_at = utc_now()
    session.add_all([attempt, transaction])
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="paypal.payout_submitted",
        payload={"batch_id": batch_id, "batch_status": batch_status},
    )
    session.flush()


def record_paypal_unknown(
    session: Session,
    *,
    transaction: PaymentTransaction,
    attempt: TransactionAttempt,
    code: str,
) -> None:
    attempt.status = "unknown"
    attempt.response_code = code
    attempt.provider_status = "UNKNOWN"
    transaction.provider_status = "UNKNOWN"
    transaction.failure_code = code
    transaction.updated_at = utc_now()
    session.add_all([attempt, transaction])
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="paypal.outcome_unknown",
        payload={"attempt": attempt.attempt_number, "code": code},
    )
    session.flush()


def fail_paypal_attempt(
    session: Session,
    *,
    transaction: PaymentTransaction,
    attempt: TransactionAttempt,
    code: str,
    provider_status: str = "FAILED",
) -> None:
    if transaction.status == "failed":
        return
    if transaction.status != "executing":
        raise AlreadyActioned("PayPal payout is no longer executing")
    release_reservation(
        session,
        user_id=transaction.user_id,
        transaction_id=transaction.id,
        reason=code,
    )
    previous = transaction.status
    transaction.status = "failed"
    transaction.failure_code = code
    transaction.provider_status = provider_status
    transaction.updated_at = utc_now()
    attempt.status = "failed"
    attempt.provider_status = provider_status
    attempt.response_code = code
    attempt.finished_at = utc_now()
    session.add_all([attempt, transaction])
    _record_state(session, transaction=transaction, previous=previous)
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="paypal.payout_failed",
        payload={"provider_status": provider_status, "failure_code": code},
    )
    session.flush()


def apply_paypal_reconciliation(
    session: Session,
    *,
    transaction: PaymentTransaction,
    attempt: TransactionAttempt,
    batch_status: str,
    item_id: str | None,
    item_status: str | None,
) -> None:
    """Apply item-level provider truth without inferring success from a batch."""
    batch_status = batch_status.upper()
    item_status = item_status.upper() if item_status else None
    attempt.provider_status = item_status or batch_status
    attempt.provider_item_id = item_id
    transaction.provider_status = item_status or batch_status
    transaction.provider_item_id = item_id
    transaction.updated_at = utc_now()
    session.add_all([attempt, transaction])
    record_audit_event(
        session,
        user_id=transaction.user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="paypal.payout_reconciled",
        payload={
            "batch_status": batch_status,
            "item_status": item_status,
            "item_id": item_id,
        },
    )

    if item_status == "SUCCESS":
        if transaction.status == "executing":
            capture_reservation(
                session, user_id=transaction.user_id, transaction=transaction
            )
            previous = transaction.status
            transaction.status = "completed"
            transaction.failure_code = None
            transaction.completed_at = utc_now()
            transaction.updated_at = transaction.completed_at
            _record_state(session, transaction=transaction, previous=previous)
        attempt.status = "completed"
        attempt.response_code = "PAYPAL_ITEM_SUCCESS"
        attempt.finished_at = utc_now()
        session.add_all([attempt, transaction])
        session.flush()
        return

    if item_status in {"RETURNED", "REVERSED", "REFUNDED"}:
        if transaction.status == "completed":
            reverse_capture(
                session,
                user_id=transaction.user_id,
                transaction=transaction,
                idempotency_key=f"provider-reversal:{transaction.id}",
            )
        elif transaction.status == "executing":
            release_reservation(
                session,
                user_id=transaction.user_id,
                transaction_id=transaction.id,
                reason=f"paypal_{item_status.casefold()}",
            )
        previous = transaction.status
        transaction.status = "reversed"
        transaction.failure_code = f"PAYPAL_ITEM_{item_status}"
        transaction.updated_at = utc_now()
        attempt.status = "reversed"
        attempt.response_code = f"PAYPAL_ITEM_{item_status}"
        attempt.finished_at = utc_now()
        session.add_all([attempt, transaction])
        if previous != transaction.status:
            _record_state(session, transaction=transaction, previous=previous)
            record_audit_event(
                session,
                user_id=transaction.user_id,
                actor_type="system",
                actor_id=None,
                entity_type="transaction",
                entity_id=transaction.id,
                event_type="paypal.payout_reversed",
                payload={"provider_status": item_status},
            )
        session.flush()
        return

    if item_status in {"FAILED", "BLOCKED", "CANCELED", "DENIED"} or (
        item_status is None and batch_status in {"DENIED", "CANCELED"}
    ):
        fail_paypal_attempt(
            session,
            transaction=transaction,
            attempt=attempt,
            code="PAYPAL_TERMINAL_FAILURE",
            provider_status=item_status or batch_status,
        )
        return

    # PENDING, PROCESSING, UNCLAIMED, ONHOLD, a batch-only SUCCESS and
    # unknown values all retain the reservation and executing state.
    attempt.status = "processing"
    session.add(attempt)
    session.flush()


def list_pending_approvals(session: Session, *, user: User) -> list[ApprovalContext]:
    transactions = list(
        session.exec(
            select(PaymentTransaction)
            .where(
                PaymentTransaction.user_id == user.id,
                PaymentTransaction.status == "pending_approval",
            )
            .order_by(PaymentTransaction.created_at.asc())
        ).all()
    )
    if not transactions:
        return []
    wallet = get_wallet_for_user(session, user.id)
    policy = get_current_policy(session, user.id)
    balance = wallet_balance(session, wallet)
    return [
        ApprovalContext(
            transaction=transaction,
            requester=user,
            policy_decision=evaluate_policy(
                session,
                user=user,
                wallet=wallet,
                policy=policy,
                vendor=transaction.vendor,
                amount_cents=transaction.amount_cents,
                currency=transaction.currency,
                category=transaction.category,
                exclude_transaction_id=transaction.id,
            ),
            balance=balance,
        )
        for transaction in transactions
    ]


def _encode_cursor(transaction: PaymentTransaction) -> str:
    payload = json.dumps(
        {"created_at": transaction.created_at.isoformat(), "id": transaction.id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        created_at = datetime.fromisoformat(data["created_at"])
        if created_at.tzinfo is None:
            raise ValueError("Cursor timestamp must include a timezone")
        return created_at, str(UUID(str(data["id"])))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise TransactionServiceError("Transaction cursor is invalid") from exc


def list_transactions(
    session: Session,
    *,
    user_id: str,
    generation: int | None,
    status: str | None = None,
    category: str | None = None,
    transaction_type: str | None = None,
    vendor: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = 25,
) -> tuple[list[PaymentTransaction], str | None]:
    statement = select(PaymentTransaction).where(PaymentTransaction.user_id == user_id)
    if generation is not None:
        statement = statement.where(PaymentTransaction.sandbox_generation == generation)
    if status:
        statement = statement.where(PaymentTransaction.status == status)
    if category:
        statement = statement.where(PaymentTransaction.category == category.casefold())
    if transaction_type:
        statement = statement.where(PaymentTransaction.type == transaction_type)
    if vendor:
        statement = statement.where(PaymentTransaction.vendor.ilike(f"%{vendor.strip()}%"))
    if created_from:
        statement = statement.where(PaymentTransaction.created_at >= created_from)
    if created_to:
        statement = statement.where(PaymentTransaction.created_at < created_to)
    if cursor:
        created_at, transaction_id = _decode_cursor(cursor)
        statement = statement.where(
            (PaymentTransaction.created_at < created_at)
            | (
                (PaymentTransaction.created_at == created_at)
                & (PaymentTransaction.id < transaction_id)
            )
        )
    items = list(
        session.exec(
            statement.order_by(
                PaymentTransaction.created_at.desc(), PaymentTransaction.id.desc()
            ).limit(limit + 1)
        ).all()
    )
    has_more = len(items) > limit
    items = items[:limit]
    return items, _encode_cursor(items[-1]) if has_more and items else None


def transaction_detail(
    session: Session, *, user_id: str, transaction_id: str
) -> dict[str, Any]:
    transaction = get_owned_transaction(
        session, user_id=user_id, transaction_id=transaction_id
    )
    ledger_entries = session.exec(
        select(LedgerEntry, LedgerJournal, LedgerAccount)
        .join(LedgerJournal, LedgerJournal.id == LedgerEntry.journal_id)
        .join(LedgerAccount, LedgerAccount.id == LedgerEntry.account_id)
        .where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.transaction_id == transaction.id,
        )
        .order_by(LedgerEntry.created_at.asc())
    ).all()
    events = session.exec(
        select(AuditEvent)
        .where(
            AuditEvent.user_id == user_id,
            AuditEvent.entity_type == "transaction",
            AuditEvent.entity_id == transaction.id,
        )
        .order_by(AuditEvent.created_at.asc())
    ).all()
    attempts = session.exec(
        select(TransactionAttempt)
        .where(TransactionAttempt.transaction_id == transaction.id)
        .order_by(TransactionAttempt.attempt_number.asc())
    ).all()
    entries_by_journal: dict[str, list[tuple[LedgerEntry, LedgerAccount]]] = {}
    for entry, journal, account in ledger_entries:
        entries_by_journal.setdefault(journal.id, []).append((entry, account))

    def account_label(account: LedgerAccount) -> str:
        if account.account_type == "user_wallet":
            return "Your sandbox wallet"
        if account.account_type == "sandbox_issuance":
            return "Sandbox issuance"
        if account.account_type == "sandbox_clearing":
            return "Sandbox clearing"
        return "Protected ledger account"

    def event_summary(event: AuditEvent) -> str:
        payload = event.payload
        if event.event_type == "payment.requested":
            source = payload.get("source")
            return "Payment request created" + (
                f" from {source}" if source in {"manual", "assistant"} else ""
            )
        if event.event_type == "transaction.state_changed":
            previous = str(payload.get("from", "unknown")).replace("_", " ")
            current = str(payload.get("to", "unknown")).replace("_", " ")
            return f"State changed from {previous} to {current}"
        if event.event_type == "payment.blocked":
            code = str(payload.get("reason_code", "policy rule")).replace("_", " ")
            return f"Stopped by {code}"
        if event.event_type == "payment.pending_approval":
            return "Funds reserved pending owner review"
        if event.event_type == "approval.approved":
            version = payload.get("policy_version")
            return f"Approved using policy v{version}" if isinstance(version, int) else "Approved by the owner"
        if event.event_type == "approval.rejected":
            return "Rejected by the owner; the reservation was released"
        if event.event_type == "transaction.retry_requested":
            attempt = payload.get("attempt_number")
            return f"Retry attempt {attempt} requested" if isinstance(attempt, int) else "Retry requested"
        if event.event_type == "transaction.reversed":
            return "Compensating sandbox reversal posted"
        if event.event_type == "transaction.cancelled":
            return "Cancelled during sandbox reset"
        if event.event_type == "funds.reserved":
            amount = payload.get("amount_cents")
            return f"Reserved {amount} cents" if isinstance(amount, int) else "Funds reserved"
        if event.event_type == "funds.released":
            return "Reservation released"
        if event.event_type.startswith("paypal."):
            provider_status = payload.get("provider_status") or payload.get("batch_status")
            return (
                f"PayPal Sandbox status: {provider_status}"
                if isinstance(provider_status, str)
                else "PayPal Sandbox lifecycle updated"
            )
        return "Durable lifecycle event recorded"

    return {
        "transaction": transaction,
        "policy_checks": transaction.policy_result.get("checks", []),
        "ledger_entries": [
            {
                "journal_id": journal.id,
                "journal_type": journal.journal_type,
                "entry_id": entry.id,
                "direction": entry.direction,
                "amount_cents": entry.amount_cents,
                "currency": entry.currency,
                "account_label": account_label(account),
                "counter_account_label": next(
                    (
                        account_label(other_account)
                        for other_entry, other_account in entries_by_journal[journal.id]
                        if other_entry.id != entry.id
                    ),
                    "Balanced counter-account",
                ),
                "created_at": entry.created_at,
            }
            for entry, journal, account in ledger_entries
        ],
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "actor_label": (
                    "You" if event.actor_type == "user" else "Pactra system"
                ),
                "summary": event_summary(event),
                "created_at": event.created_at,
            }
            for event in events
        ],
        "attempts": [
            {
                "id": attempt.id,
                "attempt_number": attempt.attempt_number,
                "rail": attempt.rail,
                "status": attempt.status,
                "provider_status": attempt.provider_status,
                "response_code": attempt.response_code,
                "started_at": attempt.started_at,
                "finished_at": attempt.finished_at,
            }
            for attempt in attempts
        ],
    }
