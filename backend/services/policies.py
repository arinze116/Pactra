"""Versioned policy persistence and deterministic cents-based evaluation."""

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from backend.defaults import default_policy
from backend.models import (
    FundReservation,
    PaymentTransaction,
    PolicyVersion,
    User,
    Wallet,
)
from backend.services.audit import record_audit_event
from backend.services.ledger import WalletBalance, wallet_balance


class PolicyError(RuntimeError):
    """Raised when a user policy is missing or invalid."""


class PolicyUnchanged(PolicyError):
    """The submitted policy is identical to the current version."""


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    reason_code: str | None
    policy_version: int
    checks: list[dict[str, Any]]
    daily_committed_cents: int
    daily_reserved_cents: int
    category_committed_cents: int
    category_reserved_cents: int

    def snapshot(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason_code": self.reason_code,
            "policy_version": self.policy_version,
            "checks": self.checks,
            "daily_committed_cents": self.daily_committed_cents,
            "daily_reserved_cents": self.daily_reserved_cents,
            "category_committed_cents": self.category_committed_cents,
            "category_reserved_cents": self.category_reserved_cents,
        }

    @classmethod
    def from_snapshot(cls, value: dict[str, Any]) -> "PolicyDecision":
        return cls(
            decision=str(value["decision"]),
            reason_code=value.get("reason_code"),
            policy_version=int(value["policy_version"]),
            checks=list(value.get("checks", [])),
            daily_committed_cents=int(value.get("daily_committed_cents", 0)),
            daily_reserved_cents=int(value.get("daily_reserved_cents", 0)),
            category_committed_cents=int(value.get("category_committed_cents", 0)),
            category_reserved_cents=int(value.get("category_reserved_cents", 0)),
        )


def get_current_policy(
    session: Session, user_id: str, *, for_update: bool = False
) -> PolicyVersion:
    statement = (
        select(PolicyVersion)
        .where(PolicyVersion.user_id == user_id)
        .order_by(PolicyVersion.version.desc())
        .limit(1)
    )
    if for_update:
        statement = statement.with_for_update()
    policy = session.exec(statement).one_or_none()
    if policy is None:
        raise PolicyError("Account policy was not found")
    return policy


def save_policy(
    session: Session,
    *,
    user_id: str,
    policy_json: dict[str, Any],
    event_type: str = "policy.updated",
    allow_unchanged: bool = False,
) -> PolicyVersion:
    # Lock a stable per-user row. Locking only the latest policy version does
    # not serialize two inserts that both calculate the same next version.
    owner = session.exec(
        select(User).where(User.id == user_id).with_for_update()
    ).one_or_none()
    if owner is None:
        raise PolicyError("Account was not found")
    current = get_current_policy(session, user_id)
    if current.policy_json == policy_json and not allow_unchanged:
        raise PolicyUnchanged("Change at least one policy field before saving")
    policy = PolicyVersion(
        user_id=user_id,
        version=current.version + 1,
        policy_json=policy_json,
        created_by=user_id,
    )
    session.add(policy)
    session.flush()
    record_audit_event(
        session,
        user_id=user_id,
        actor_type="user",
        actor_id=user_id,
        entity_type="policy",
        entity_id=policy.id,
        event_type=event_type,
        payload={
            "old_version": current.version,
            "new_version": policy.version,
            "old_policy": current.policy_json,
            "new_policy": policy.policy_json,
        },
    )
    return policy


def reset_policy(session: Session, *, user_id: str) -> PolicyVersion:
    return save_policy(
        session,
        user_id=user_id,
        policy_json=default_policy(),
        event_type="policy.reset",
        allow_unchanged=True,
    )


def list_policy_versions(session: Session, *, user_id: str) -> list[PolicyVersion]:
    return list(
        session.exec(
            select(PolicyVersion)
            .where(PolicyVersion.user_id == user_id)
            .order_by(PolicyVersion.version.desc())
            .limit(100)
        ).all()
    )


def _today_start() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def _committed_spend(
    session: Session,
    *,
    user_id: str,
    generation: int,
    category: str | None = None,
) -> int:
    statement = select(func.coalesce(func.sum(PaymentTransaction.amount_cents), 0)).where(
        PaymentTransaction.user_id == user_id,
        PaymentTransaction.sandbox_generation == generation,
        PaymentTransaction.status == "completed",
        PaymentTransaction.completed_at >= _today_start(),
    )
    if category is not None:
        statement = statement.where(PaymentTransaction.category == category)
    return int(session.exec(statement).one() or 0)


def _reserved_spend(
    session: Session,
    *,
    user_id: str,
    generation: int,
    category: str | None = None,
    exclude_transaction_id: str | None = None,
) -> int:
    statement = (
        select(func.coalesce(func.sum(FundReservation.amount_cents), 0))
        .join(PaymentTransaction, PaymentTransaction.id == FundReservation.transaction_id)
        .where(
            FundReservation.user_id == user_id,
            FundReservation.status == "active",
            PaymentTransaction.sandbox_generation == generation,
        )
    )
    if category is not None:
        statement = statement.where(PaymentTransaction.category == category)
    if exclude_transaction_id is not None:
        statement = statement.where(FundReservation.transaction_id != exclude_transaction_id)
    return int(session.exec(statement).one() or 0)


def evaluate_policy(
    session: Session,
    *,
    user: User,
    wallet: Wallet,
    policy: PolicyVersion,
    vendor: str,
    amount_cents: int,
    currency: str,
    category: str,
    exclude_transaction_id: str | None = None,
) -> PolicyDecision:
    """Evaluate policy in the exact PRD order and return an audit snapshot."""
    data = policy.policy_json
    checks: list[dict[str, Any]] = []

    daily_committed = _committed_spend(
        session, user_id=user.id, generation=wallet.sandbox_generation
    )
    daily_reserved = _reserved_spend(
        session,
        user_id=user.id,
        generation=wallet.sandbox_generation,
        exclude_transaction_id=exclude_transaction_id,
    )
    category_committed = _committed_spend(
        session,
        user_id=user.id,
        generation=wallet.sandbox_generation,
        category=category,
    )
    category_reserved = _reserved_spend(
        session,
        user_id=user.id,
        generation=wallet.sandbox_generation,
        category=category,
        exclude_transaction_id=exclude_transaction_id,
    )

    def decision(reason: str) -> PolicyDecision:
        return PolicyDecision(
            decision="blocked",
            reason_code=reason,
            policy_version=policy.version,
            checks=checks,
            daily_committed_cents=daily_committed,
            daily_reserved_cents=daily_reserved,
            category_committed_cents=category_committed,
            category_reserved_cents=category_reserved,
        )

    account_ok = user.status == "active" and wallet.status == "active"
    checks.append({"code": "ACCOUNT_ACTIVE", "passed": account_ok})
    if not account_ok:
        return decision("ACCOUNT_INACTIVE")
    currency_ok = currency == "USD" and wallet.currency == "USD"
    checks.append({"code": "CURRENCY_SUPPORTED", "passed": currency_ok})
    if not currency_ok:
        return decision("CURRENCY_UNSUPPORTED")

    allowed = category in data["allowed_categories"]
    checks.append({"code": "CATEGORY_ALLOWED", "passed": allowed, "category": category})
    if not allowed:
        return decision("CATEGORY_NOT_ALLOWED")

    vendor_blocked = vendor.strip().casefold() in {
        item.strip().casefold() for item in data["blocked_vendors"]
    }
    checks.append({"code": "VENDOR_ALLOWED", "passed": not vendor_blocked})
    if vendor_blocked:
        return decision("VENDOR_BLOCKED")

    transaction_limit = int(data["per_transaction_limit_cents"])
    transaction_ok = amount_cents <= transaction_limit
    checks.append(
        {
            "code": "TRANSACTION_LIMIT",
            "passed": transaction_ok,
            "limit_cents": transaction_limit,
        }
    )
    if not transaction_ok:
        return decision("TRANSACTION_LIMIT_EXCEEDED")

    daily_limit = int(data["daily_limit_cents"])
    daily_ok = daily_committed + daily_reserved + amount_cents <= daily_limit
    checks.append(
        {
            "code": "DAILY_LIMIT",
            "passed": daily_ok,
            "limit_cents": daily_limit,
            "committed_cents": daily_committed,
            "reserved_cents": daily_reserved,
        }
    )
    if not daily_ok:
        return decision("DAILY_LIMIT_EXCEEDED")

    category_limit = int(data["category_budgets_cents"][category])
    category_ok = category_committed + category_reserved + amount_cents <= category_limit
    checks.append(
        {
            "code": "CATEGORY_BUDGET",
            "passed": category_ok,
            "limit_cents": category_limit,
            "committed_cents": category_committed,
            "reserved_cents": category_reserved,
        }
    )
    if not category_ok:
        return decision("CATEGORY_BUDGET_EXCEEDED")

    balance: WalletBalance = wallet_balance(session, wallet)
    available = balance.available_cents
    if exclude_transaction_id is not None:
        own_hold = session.exec(
            select(func.coalesce(func.sum(FundReservation.amount_cents), 0)).where(
                FundReservation.transaction_id == exclude_transaction_id,
                FundReservation.status == "active",
            )
        ).one()
        available += int(own_hold or 0)
    funds_ok = available >= amount_cents
    checks.append(
        {
            "code": "AVAILABLE_FUNDS",
            "passed": funds_ok,
            "available_cents": available,
        }
    )
    if not funds_ok:
        return decision("INSUFFICIENT_FUNDS")

    threshold = int(data["approval_threshold_cents"])
    requires_approval = amount_cents > threshold
    checks.append(
        {
            "code": "APPROVAL_THRESHOLD",
            "passed": not requires_approval,
            "threshold_cents": threshold,
        }
    )
    return PolicyDecision(
        decision="approval_required" if requires_approval else "approved",
        reason_code="APPROVAL_REQUIRED" if requires_approval else None,
        policy_version=policy.version,
        checks=checks,
        daily_committed_cents=daily_committed,
        daily_reserved_cents=daily_reserved,
        category_committed_cents=category_committed,
        category_reserved_cents=category_reserved,
    )


def spend_summary(session: Session, *, user_id: str, wallet: Wallet) -> dict[str, Any]:
    policy = get_current_policy(session, user_id)
    data = policy.policy_json
    categories: list[dict[str, Any]] = []
    for category in data["allowed_categories"]:
        committed = _committed_spend(
            session,
            user_id=user_id,
            generation=wallet.sandbox_generation,
            category=category,
        )
        reserved = _reserved_spend(
            session,
            user_id=user_id,
            generation=wallet.sandbox_generation,
            category=category,
        )
        budget = int(data["category_budgets_cents"][category])
        categories.append(
            {
                "category": category,
                "budget_cents": budget,
                "committed_cents": committed,
                "reserved_cents": reserved,
                "remaining_cents": max(0, budget - committed - reserved),
                "utilisation_percent": round(
                    ((committed + reserved) / budget) * 100, 1
                ),
            }
        )
    return {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "daily_limit_cents": int(data["daily_limit_cents"]),
        "daily_committed_cents": _committed_spend(
            session, user_id=user_id, generation=wallet.sandbox_generation
        ),
        "daily_reserved_cents": _reserved_spend(
            session, user_id=user_id, generation=wallet.sandbox_generation
        ),
        "categories": categories,
    }
