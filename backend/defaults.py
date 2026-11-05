"""Canonical defaults shared by account bootstrap, policy and reset flows."""

from copy import deepcopy
from typing import Any


INITIAL_SANDBOX_CENTS = 100_000
TOP_UP_PRESETS_CENTS = {10_000, 50_000, 100_000}
MAX_TOP_UP_CENTS_PER_ACCOUNT = 1_000_000

DEFAULT_POLICY: dict[str, Any] = {
    "daily_limit_cents": 50_000,
    "per_transaction_limit_cents": 15_000,
    "approval_threshold_cents": 10_000,
    "allowed_categories": ["ops", "software", "cloud", "freelance"],
    "category_budgets_cents": {
        "ops": 15_000,
        "software": 20_000,
        "cloud": 10_000,
        "freelance": 15_000,
    },
    "blocked_vendors": [],
    "currency": "USD",
}


def default_policy() -> dict[str, Any]:
    """Return an isolated copy safe to store as a version snapshot."""
    return deepcopy(DEFAULT_POLICY)
