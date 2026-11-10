"""Deterministic fictional data for an explicitly isolated demo database."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import secrets
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, select

from backend.auth import hash_password
from backend.models import AuditEvent, PaymentTransaction, User
from backend.services.accounts import create_account
from backend.services.audit import record_audit_event
from backend.services.ledger import get_wallet_for_user, wallet_balance
from backend.services.transactions import (
    PolicyBlocked,
    create_payment_request,
    reject_transaction,
)


DEMO_EMAIL = "demo@pactra-demo.example.com"
DEMO_DATABASE_PREFIX = "pactra-demo-"
DEMO_SCHEMA_REVISION = "20261110_0006"


@dataclass(frozen=True)
class DemoDataset:
    user_id: str
    email: str
    transaction_ids: dict[str, str]
    posted_cents: int
    reserved_cents: int
    available_cents: int
    replayed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validated_demo_database_path(database_url: str, app_env: str) -> Path:
    """Resolve a deliberately named local SQLite demo target or refuse it."""
    if app_env != "demo":
        raise ValueError("Demo data commands require APP_ENV=demo")
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database:
        raise ValueError("Demo data commands require a file-backed SQLite database")
    candidate = Path(url.database).expanduser()
    if not candidate.is_absolute():
        raise ValueError("Demo database path must be absolute")
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("Demo database must not be a symbolic link")
    resolved = candidate.resolve(strict=False)
    if not (
        resolved.name.startswith(DEMO_DATABASE_PREFIX)
        and resolved.suffix == ".db"
    ):
        raise ValueError(
            f"Demo database filename must match {DEMO_DATABASE_PREFIX}*.db"
        )
    forbidden_roots = (Path("/etc/pactra"), Path("/opt/pactra"))
    if any(resolved.is_relative_to(root) for root in forbidden_roots):
        raise ValueError("Demo database cannot be stored in a production path")
    project_database = Path(__file__).resolve().parent.parent / "pactra.db"
    if resolved == project_database.resolve(strict=False):
        raise ValueError("The default development database is not a demo target")
    return resolved


def verify_demo_schema(engine: Engine) -> None:
    """Require the exact current schema before inserting demo records."""
    required_tables = {
        "alembic_version",
        "audit_events",
        "ledger_entries",
        "ledger_journals",
        "policies",
        "transactions",
        "users",
        "wallets",
    }
    present = set(inspect(engine).get_table_names())
    missing = required_tables - present
    if missing:
        raise RuntimeError(
            "Demo database is not migrated; missing tables: " + ", ".join(sorted(missing))
        )
    with engine.connect() as connection:
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    if revision != DEMO_SCHEMA_REVISION:
        raise RuntimeError(
            f"Demo database revision {revision!r} does not match {DEMO_SCHEMA_REVISION}"
        )


def _payment(
    *,
    key: str,
    vendor: str,
    amount_cents: int,
    category: str,
    reason: str,
    payment_type: str = "vendor_payment",
    recipient: str | None = None,
) -> dict[str, Any]:
    return {
        "type": payment_type,
        "vendor": vendor,
        "recipient": recipient,
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": category,
        "reason": reason,
        "rail": "internal_sandbox",
        "idempotency_key": key,
        "source": "demo_seed",
    }


def _ensure_payment(
    session: Session,
    *,
    user: User,
    payload: dict[str, Any],
) -> PaymentTransaction:
    try:
        result = create_payment_request(session, user=user, payload=payload)
        transaction = result.transaction
    except PolicyBlocked as exc:
        transaction = exc.transaction
    session.commit()
    session.refresh(transaction)
    return transaction


def seed_demo_dataset(session: Session) -> DemoDataset:
    """Create the same governed dataset on every safe invocation."""
    users = list(session.exec(select(User)).all())
    unexpected = [user.email for user in users if user.email != DEMO_EMAIL]
    if unexpected:
        raise RuntimeError("Demo seed refused because non-demo users exist")

    user = next((item for item in users if item.email == DEMO_EMAIL), None)
    created = user is None
    if user is None:
        user = create_account(
            session,
            email=DEMO_EMAIL,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            is_demo=True,
            display_name="Pactra local demo fixture",
        ).user
    else:
        user.password_hash = hash_password(secrets.token_urlsafe(48))
        user.is_demo = True
        user.display_name = "Pactra local demo fixture"
        session.add(user)
        session.commit()
        session.refresh(user)

    completed = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            key="demo-completed-linear-0001",
            vendor="Linear",
            amount_cents=4_900,
            category="software",
            reason="Monthly project-management subscription",
        ),
    )
    pending = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            key="demo-pending-contractor-0001",
            vendor="Ada Contractor",
            recipient="ada.contractor@example.com",
            amount_cents=12_500,
            category="freelance",
            reason="Fictional design contract milestone",
            payment_type="payout",
        ),
    )
    rejected = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            key="demo-rejected-ops-0001",
            vendor="Northwind Office Supply",
            amount_cents=12_000,
            category="ops",
            reason="Fictional office equipment order",
        ),
    )
    if rejected.status == "pending_approval":
        rejected = reject_transaction(
            session,
            user=user,
            transaction_id=rejected.id,
            idempotency_key="demo-reject-action-0001",
            reason="Invoice needs an itemised breakdown",
        )
        session.commit()
        session.refresh(rejected)
    blocked = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            key="demo-blocked-cloud-0001",
            vendor="Mega Cloud Renewal",
            amount_cents=20_000,
            category="cloud",
            reason="Fictional annual cloud renewal",
        ),
    )

    marker = session.exec(
        select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.event_type == "demo.dataset_seeded",
        )
    ).first()
    if marker is None:
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="system",
            actor_id=None,
            entity_type="user",
            entity_id=user.id,
            event_type="demo.dataset_seeded",
            payload={"dataset_version": 1, "fictional": True},
        )
        session.commit()

    wallet = get_wallet_for_user(session, user.id)
    balance = wallet_balance(session, wallet)
    return DemoDataset(
        user_id=user.id,
        email=user.email,
        transaction_ids={
            "completed": completed.id,
            "pending_approval": pending.id,
            "rejected": rejected.id,
            "blocked": blocked.id,
        },
        posted_cents=balance.posted_cents,
        reserved_cents=balance.reserved_cents,
        available_cents=balance.available_cents,
        replayed=not created,
    )
