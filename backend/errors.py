"""Consistent public API errors without leaking internal details."""

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    """An expected API failure with a stable machine-readable code."""

    status_code: int
    code: str
    message: str

