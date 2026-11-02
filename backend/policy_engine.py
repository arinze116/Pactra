"""Deterministic spending-policy evaluation and budget accounting."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import ValidationError
from sqlmodel import Session, select

from .models import PolicyCheckResult, PolicyConfig, PolicySnapshot, SpendSummary


class PolicyConfigurationError(RuntimeError):
    """Raised when the configured policy cannot be loaded safely."""


class PolicyEngine:
    """Evaluate payment requests against owner-controlled, on-disk rules."""

    def __init__(self, policy_path: str | Path):
        self.policy_path = Path(policy_path)
        self._lock = RLock()
        self.policy: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """Atomically replace the active policy after full validation."""
        try:
            raw_policy = json.loads(self.policy_path.read_text(encoding="utf-8"))
            validated = PolicyConfig.model_validate(raw_policy)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise PolicyConfigurationError(
                f"Unable to load a valid policy from {self.policy_path}"
            ) from exc

        if validated.require_approval_above > validated.per_transaction_limit:
            raise PolicyConfigurationError(
                "require_approval_above cannot exceed per_transaction_limit"
            )

        approved = {category.casefold() for category in validated.approved_categories}
        unknown_budgets = set(validated.budgets) - approved
        if unknown_budgets:
            raise PolicyConfigurationError(
                f"Budgets contain unapproved categories: {sorted(unknown_budgets)}"
            )

        with self._lock:
            self.policy = validated.model_dump()
            self.policy["approved_categories"] = [
                category.casefold() for category in validated.approved_categories
            ]
            self.policy["currency"] = validated.currency.upper()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _today_spend(self, db_session: Session) -> tuple[float, dict[str, float]]:
        snapshots = db_session.exec(
            select(PolicySnapshot).where(PolicySnapshot.date == self._today())
        ).all()
        by_category = {
            snapshot.category: round(snapshot.total_spent, 2) for snapshot in snapshots
        }
        return round(sum(by_category.values()), 2), by_category

    def check(
        self,
        vendor: str,
        amount: float,
        category: str,
        db_session: Session,
    ) -> PolicyCheckResult:
        """Run the PRD decision tree in strict order and return its first match."""
        vendor = vendor.strip()
        category = category.strip().casefold()
        if not vendor:
            raise ValueError("Vendor is required")
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be a positive finite number")

        with self._lock:
            policy = dict(self.policy)

        daily_spent, category_totals = self._today_spend(db_session)
        category_spent = category_totals.get(category, 0.0)

        if category not in policy["approved_categories"]:
            return self._blocked(
                "This spending category is not approved.", "category_not_approved"
            )

        blocked_vendors = {item.strip().casefold() for item in policy["blocked_vendors"]}
        if vendor.casefold() in blocked_vendors:
            return self._blocked("This vendor is blocked.", "vendor_blocked")

        if amount > policy["per_transaction_limit"]:
            return self._blocked(
                "The payment exceeds the per-transaction limit.",
                "exceeds_per_transaction_limit",
            )

        if daily_spent + amount > policy["daily_limit"]:
            return self._blocked(
                "The payment would exceed today's spending limit.",
                "exceeds_daily_limit",
            )

        if category in policy["budgets"]:
            if category_spent + amount > policy["budgets"][category]:
                return self._blocked(
                    "The payment would exceed this category's budget.",
                    "exceeds_category_budget",
                )

        if amount > policy["require_approval_above"]:
            return PolicyCheckResult(
                approved=False,
                status="pending_approval",
                reason="This payment requires human approval.",
                rule_triggered="requires_human_approval",
            )

        return PolicyCheckResult(approved=True, status="approved")

    @staticmethod
    def _blocked(reason: str, rule: str) -> PolicyCheckResult:
        return PolicyCheckResult(
            approved=False,
            status="blocked",
            reason=reason,
            rule_triggered=rule,
        )

    def record_spend(self, category: str, amount: float, db_session: Session) -> None:
        """Upsert the current UTC day's category ledger entry."""
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Amount must be a positive finite number")

        category = category.strip().casefold()
        snapshot = db_session.exec(
            select(PolicySnapshot).where(
                PolicySnapshot.date == self._today(),
                PolicySnapshot.category == category,
            )
        ).one_or_none()

        if snapshot is None:
            snapshot = PolicySnapshot(
                date=self._today(), category=category, total_spent=round(amount, 2)
            )
            db_session.add(snapshot)
        else:
            snapshot.total_spent = round(snapshot.total_spent + amount, 2)
            db_session.add(snapshot)
        db_session.flush()

    def get_summary(self, db_session: Session) -> list[SpendSummary]:
        """Return today's utilisation for every configured category budget."""
        _, category_totals = self._today_spend(db_session)
        with self._lock:
            budgets = dict(self.policy["budgets"])

        summaries: list[SpendSummary] = []
        for category, budget in budgets.items():
            spent = round(category_totals.get(category, 0.0), 2)
            remaining = round(max(budget - spent, 0.0), 2)
            utilisation = round((spent / budget) * 100, 1) if budget else 0.0
            summaries.append(
                SpendSummary(
                    category=category,
                    budget=budget,
                    spent_today=spent,
                    remaining=remaining,
                    utilisation_pct=utilisation,
                )
            )
        return summaries
