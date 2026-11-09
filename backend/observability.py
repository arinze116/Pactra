"""Privacy-safe structured operational logging helpers."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from backend.config import settings


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{8,128}$")
SENSITIVE_FIELD_FRAGMENTS = frozenset(
    {
        "authorization",
        "cookie",
        "credential",
        "password",
        "prompt",
        "recipient",
        "request_body",
        "response_body",
        "secret",
        "session",
        "token",
    }
)


def safe_request_id(value: str | None) -> str:
    """Accept a bounded correlation ID or replace it with a server UUID."""
    candidate = (value or "").strip()
    if REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid4())


def operation_from_scope(scope: Mapping[str, Any]) -> str:
    """Return a low-cardinality route template without logging path values."""
    route = scope.get("route")
    route_template = getattr(route, "path_format", None) or getattr(route, "path", None)
    if isinstance(route_template, str) and route_template.startswith("/"):
        return route_template[:240]
    return "unmatched_route"


def _safe_value(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, str):
            return value[:240]
        return value
    return type(value).__name__


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    service: str,
    level: int = logging.INFO,
    exc_info: bool = False,
    **fields: Any,
) -> None:
    """Write one JSON event while rejecting sensitive field names.

    Callers supply only low-cardinality operational metadata. Prompts, request
    bodies, provider payloads, credentials and recipient data are forbidden.
    """
    for key in fields:
        lowered = key.casefold()
        if any(fragment in lowered for fragment in SENSITIVE_FIELD_FRAGMENTS):
            raise ValueError(f"Sensitive log field is not permitted: {key}")
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severity": logging.getLevelName(level),
        "service": service,
        "environment": settings.app_env,
        "event": event,
        **{key: _safe_value(value) for key, value in fields.items()},
    }
    logger.log(
        level,
        json.dumps(payload, separators=(",", ":"), sort_keys=True),
        exc_info=exc_info,
    )
