"""Append-only audit event helpers."""

from typing import Any

from sqlmodel import Session

from backend.models import AuditEvent


def record_audit_event(
    session: Session,
    *,
    user_id: str,
    actor_type: str,
    actor_id: str | None,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Create an audit event inside the caller's database transaction."""
    event = AuditEvent(
        user_id=user_id,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload=payload or {},
    )
    session.add(event)
    session.flush()
    return event
