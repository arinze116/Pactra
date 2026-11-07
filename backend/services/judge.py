"""Persisted judge-walkthrough controls built on normal product services."""

from sqlmodel import Session, select

from backend.models import AuditEvent, PaymentTransaction, User
from backend.services.audit import record_audit_event
from backend.services.ledger import WalletBalance, get_wallet_for_user, wallet_balance
from backend.services.policies import PolicyDecision, get_current_policy, save_policy
from backend.services.transactions import PolicyBlocked, create_payment_request


def start_guided_test(session: Session, *, user: User) -> int:
    """Record one safe guided-test start event per sandbox generation."""
    wallet = get_wallet_for_user(session, user.id)
    events = session.exec(
        select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.entity_type == "wallet",
            AuditEvent.entity_id == wallet.id,
            AuditEvent.event_type == "judge.guided_test_started",
        )
    ).all()
    if not any(
        int(event.payload.get("sandbox_generation", 0)) == wallet.sandbox_generation
        for event in events
    ):
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="user",
            actor_id=user.id,
            entity_type="wallet",
            entity_id=wallet.id,
            event_type="judge.guided_test_started",
            payload={"sandbox_generation": wallet.sandbox_generation},
        )
    session.flush()
    return wallet.sandbox_generation


def run_insufficient_funds_scenario(
    session: Session,
    *,
    user: User,
    idempotency_key: str,
) -> tuple[PaymentTransaction, PolicyDecision, WalletBalance]:
    """Create a real insufficient-funds outcome without moving posted funds."""
    existing = session.exec(
        select(PaymentTransaction).where(
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    if existing is not None:
        if existing.failure_code != "INSUFFICIENT_FUNDS":
            raise RuntimeError("Guided scenario key belongs to another outcome")
        wallet = get_wallet_for_user(session, user.id)
        return (
            existing,
            PolicyDecision.from_snapshot(existing.policy_result),
            wallet_balance(session, wallet),
        )

    wallet = get_wallet_for_user(session, user.id, for_update=True)
    balance = wallet_balance(session, wallet)
    amount_cents = balance.available_cents + 1
    original_policy = get_current_policy(session, user.id).policy_json
    allowed_categories = list(original_policy["allowed_categories"])
    if "ops" not in allowed_categories:
        allowed_categories.append("ops")
    scenario_policy = {
        **original_policy,
        "daily_limit_cents": 100_000_000,
        "per_transaction_limit_cents": 100_000_000,
        "approval_threshold_cents": 100_000_000,
        "allowed_categories": allowed_categories,
        "category_budgets_cents": {
            **original_policy["category_budgets_cents"],
            "ops": 100_000_000,
        },
        "blocked_vendors": [
            vendor
            for vendor in original_policy["blocked_vendors"]
            if vendor.strip().casefold() != "guided insufficient funds test"
        ],
    }
    policy_was_changed = scenario_policy != original_policy
    if policy_was_changed:
        save_policy(
            session,
            user_id=user.id,
            policy_json=scenario_policy,
            event_type="judge.insufficient_policy_prepared",
        )
    try:
        create_payment_request(
            session,
            user=user,
            payload={
                "type": "vendor_payment",
                "vendor": "Guided insufficient funds test",
                "recipient": None,
                "amount_cents": amount_cents,
                "currency": "USD",
                "category": "ops",
                "reason": "Verify that unavailable sandbox funds cannot be spent",
                "rail": "internal_sandbox",
                "idempotency_key": idempotency_key,
                "source": "guided_test",
            },
        )
    except PolicyBlocked as blocked:
        if blocked.decision.reason_code != "INSUFFICIENT_FUNDS":
            raise RuntimeError(
                f"Guided scenario stopped at {blocked.decision.reason_code}"
            ) from blocked
        transaction = blocked.transaction
        decision = blocked.decision
    else:  # pragma: no cover - safety guard against moving funds unexpectedly.
        raise RuntimeError("Guided insufficient-funds scenario unexpectedly executed")
    finally:
        if policy_was_changed:
            save_policy(
                session,
                user_id=user.id,
                policy_json=original_policy,
                event_type="judge.insufficient_policy_restored",
            )

    record_audit_event(
        session,
        user_id=user.id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="judge.insufficient_funds_verified",
        payload={"sandbox_generation": wallet.sandbox_generation},
    )
    session.flush()
    return transaction, decision, wallet_balance(session, wallet)
