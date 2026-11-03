"""Consistent public API errors without leaking internal details."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ApiError(Exception):
    """An expected API failure with a stable machine-readable code."""

    status_code: int
    code: str
    message: str
    details: dict[str, Any] | None = None

