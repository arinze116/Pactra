"""Isolated instant-demo lifecycle built on Pactra's normal ownership model."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from sqlalchemy import delete, func, or_, text
from sqlmodel import Session, select

from backend.auth import hash_password
from backend.config import settings
from backend.models import (
    ApprovalAction,
    AuditEvent,
    AuthSession,
    Conversation,
    ConversationMessage,
    DemoWorkspace,
    FundReservation,
    LedgerAccount,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    PolicyVersion,
    TransactionAttempt,
    User,
    Wallet,
    utc_now,
)
from backend.services.accounts import create_account
from backend.services.audit import record_audit_event
from backend.services.ledger import WalletBalance, get_wallet_for_user, wallet_balance
from backend.services.policies import save_policy
from backend.services.sandbox import ResetResult, reset_sandbox
from backend.services.transactions import (
    PolicyBlocked,
    create_payment_request,
    reject_transaction,
)


DEMO_WORKSPACE_NAME = "Northstar Studio"
DEMO_SEED_VERSION = 1
DEMO_CREATION_LOCK_KEY = 0x5041435444454D4F
DEMO_POLICY: dict[str, Any] = {
    "daily_limit_cents": 50_000,
    "per_transaction_limit_cents": 75_000,
    "approval_threshold_cents": 10_000,
    "allowed_categories": ["software", "vendor_payments", "operations"],
    "category_budgets_cents": {
        "software": 25_000,
        "vendor_payments": 40_000,
        "operations": 20_000,
    },
    "blocked_vendors": ["Restricted Supply Co"],
    "currency": "USD",
}


class DemoCapacityExceeded(RuntimeError):
    """The bounded pool of active demo sessions is currently full."""


class DemoWorkspaceUnavailable(RuntimeError):
    """The demo workspace is expired, revoked, or not owned by this principal."""


class DemoCleanupSafetyError(RuntimeError):
    """Cleanup encountered a record that was not explicitly demo-owned."""


@dataclass(frozen=True)
class DemoSeedResult:
    transaction_ids: dict[str, str]
    balance: WalletBalance


@dataclass(frozen=True)
class DemoBootstrap:
    user: User
    workspace: DemoWorkspace
    seed: DemoSeedResult


@dataclass(frozen=True)
class DemoResetResult:
    seed: DemoSeedResult
    reset: ResetResult


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def demo_policy() -> dict[str, Any]:
    return deepcopy(DEMO_POLICY)


def _payment(
    *,
    generation: int,
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
        "idempotency_key": f"demo-g{generation}-{key}",
        "source": "demo_seed",
    }


def _ensure_payment(
    session: Session,
    *,
    user: User,
    payload: dict[str, Any],
) -> PaymentTransaction:
    try:
        return create_payment_request(
            session,
            user=user,
            payload=payload,
        ).transaction
    except PolicyBlocked as exc:
        return exc.transaction


def seed_demo_workspace(
    session: Session,
    *,
    user: User,
    workspace: DemoWorkspace,
) -> DemoSeedResult:
    """Seed one current sandbox generation through real product services."""
    if not user.is_demo or workspace.user_id != user.id:
        raise DemoWorkspaceUnavailable("Demo workspace ownership could not be verified")

    wallet = get_wallet_for_user(session, user.id)
    generation = wallet.sandbox_generation
    completed = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            generation=generation,
            key="completed-frameio-0001",
            vendor="Frame.io",
            amount_cents=3_500,
            category="software",
            reason="Fictional monthly creative-review subscription",
        ),
    )
    pending = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            generation=generation,
            key="pending-print-0001",
            vendor="Northstar Print House",
            amount_cents=14_000,
            category="vendor_payments",
            reason="Fictional campaign print production",
        ),
    )
    rejected = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            generation=generation,
            key="rejected-contractor-0001",
            vendor="Ridgeway Contractor",
            amount_cents=13_000,
            category="vendor_payments",
            reason="Fictional contractor invoice requiring clarification",
            payment_type="payout",
            recipient="ridgeway.contractor@example.com",
        ),
    )
    if rejected.status == "pending_approval":
        rejected = reject_transaction(
            session,
            user=user,
            transaction_id=rejected.id,
            idempotency_key=f"demo-g{generation}-reject-contractor-0001",
            reason="Invoice needs an itemised scope before approval",
        )
    blocked = _ensure_payment(
        session,
        user=user,
        payload=_payment(
            generation=generation,
            key="blocked-restricted-vendor-0001",
            vendor="Restricted Supply Co",
            amount_cents=7_500,
            category="vendor_payments",
            reason="Fictional restricted-vendor purchase",
        ),
    )

    marker = session.exec(
        select(AuditEvent).where(
            AuditEvent.user_id == user.id,
            AuditEvent.event_type == "demo.dataset_seeded",
            AuditEvent.payload["sandbox_generation"].as_integer() == generation,
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
            payload={
                "dataset_version": workspace.seed_version,
                "sandbox_generation": generation,
                "fictional": True,
                "sandbox_only": True,
            },
        )
    session.flush()
    return DemoSeedResult(
        transaction_ids={
            "completed": completed.id,
            "pending_approval": pending.id,
            "rejected": rejected.id,
            "blocked": blocked.id,
        },
        balance=wallet_balance(session, wallet),
    )


def create_demo_workspace(session: Session) -> DemoBootstrap:
    """Create one temporary demo principal, wallet, policy, and seeded history."""
    now = utc_now()
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": DEMO_CREATION_LOCK_KEY},
        )
    active_count = int(
        session.exec(
            select(func.count(DemoWorkspace.id)).where(
                DemoWorkspace.status == "active",
                DemoWorkspace.expires_at > now,
            )
        ).one()
        or 0
    )
    if active_count >= settings.demo_max_active_sessions:
        raise DemoCapacityExceeded("Demo capacity is temporarily full")

    suffix = secrets.token_hex(12)
    account = create_account(
        session,
        email=f"demo-{suffix}@demo.pactra.invalid",
        password_hash=hash_password(secrets.token_urlsafe(48)),
        is_demo=True,
        display_name=DEMO_WORKSPACE_NAME,
        commit=False,
    )
    workspace = DemoWorkspace(
        user_id=account.user.id,
        status="active",
        seed_version=DEMO_SEED_VERSION,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.demo_session_ttl_minutes),
    )
    session.add(workspace)
    session.flush()
    save_policy(
        session,
        user_id=account.user.id,
        policy_json=demo_policy(),
        event_type="demo.policy_seeded",
    )
    seed = seed_demo_workspace(
        session,
        user=account.user,
        workspace=workspace,
    )
    record_audit_event(
        session,
        user_id=account.user.id,
        actor_type="system",
        actor_id=None,
        entity_type="user",
        entity_id=account.user.id,
        event_type="demo.workspace_created",
        payload={
            "workspace_id": workspace.id,
            "expires_at": workspace.expires_at.isoformat(),
            "sandbox_only": True,
        },
    )
    session.flush()
    return DemoBootstrap(user=account.user, workspace=workspace, seed=seed)


def reset_demo_workspace(
    session: Session,
    *,
    user: User,
    workspace_id: str,
    idempotency_key: str,
) -> DemoResetResult:
    """Serialize and restore only the current demo principal's workspace."""
    workspace = session.exec(
        select(DemoWorkspace)
        .where(
            DemoWorkspace.id == workspace_id,
            DemoWorkspace.user_id == user.id,
        )
        .with_for_update()
    ).one_or_none()
    now = utc_now()
    if (
        workspace is None
        or not user.is_demo
        or workspace.status != "active"
        or _as_utc(workspace.expires_at) <= now
    ):
        raise DemoWorkspaceUnavailable("This demo workspace is no longer active")

    reset = reset_sandbox(
        session,
        user=user,
        idempotency_key=idempotency_key,
        max_resets_per_hour=settings.demo_reset_rate_limit_per_hour,
        reset_policy_json=demo_policy(),
    )
    seed = seed_demo_workspace(session, user=user, workspace=workspace)
    if not reset.replayed:
        workspace.last_reset_at = now
        session.add(workspace)
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="user",
            actor_id=user.id,
            entity_type="user",
            entity_id=user.id,
            event_type="demo.workspace_reset",
            payload={
                "workspace_id": workspace.id,
                "sandbox_generation": reset.sandbox_generation,
            },
        )
    session.flush()
    return DemoResetResult(seed=seed, reset=reset)


def revoke_demo_workspace(
    session: Session,
    *,
    user: User,
    workspace_id: str,
) -> None:
    workspace = session.exec(
        select(DemoWorkspace)
        .where(
            DemoWorkspace.id == workspace_id,
            DemoWorkspace.user_id == user.id,
        )
        .with_for_update()
    ).one_or_none()
    if workspace is None or not user.is_demo:
        raise DemoWorkspaceUnavailable("Demo workspace not found")
    if workspace.status == "active":
        workspace.status = "revoked"
        session.add(workspace)
    now = utc_now()
    active_sessions = session.exec(
        select(AuthSession).where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
    ).all()
    for auth_session in active_sessions:
        auth_session.revoked_at = now
        session.add(auth_session)
    session.flush()


def cleanup_expired_demo_workspaces(
    session: Session,
    *,
    limit: int | None = None,
) -> int:
    """Delete only principals proven to be expired or revoked demo workspaces."""
    now = utc_now()
    batch_size = limit or settings.demo_cleanup_batch_size
    statement = (
        select(DemoWorkspace)
        .where(
            or_(
                DemoWorkspace.status != "active",
                DemoWorkspace.expires_at <= now,
            )
        )
        .order_by(DemoWorkspace.expires_at.asc())
        .limit(batch_size)
    )
    if session.get_bind().dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    workspaces = list(session.exec(statement).all())
    cleaned = 0
    for workspace in workspaces:
        user = session.get(User, workspace.user_id)
        if user is None or not user.is_demo:
            raise DemoCleanupSafetyError(
                "Cleanup refused a workspace without an explicit demo owner"
            )
        if workspace.status == "active":
            workspace.status = "expired"
            session.add(workspace)
            session.flush()
        _delete_demo_principal(session, user_id=user.id)
        cleaned += 1
    session.flush()
    return cleaned


def _delete_demo_principal(session: Session, *, user_id: str) -> None:
    conversation_ids = select(Conversation.id).where(Conversation.user_id == user_id)
    transaction_ids = select(PaymentTransaction.id).where(
        PaymentTransaction.user_id == user_id
    )
    journal_ids = select(LedgerJournal.id).where(LedgerJournal.user_id == user_id)

    session.exec(
        delete(ConversationMessage).where(
            ConversationMessage.conversation_id.in_(conversation_ids)
        )
    )
    session.exec(delete(Conversation).where(Conversation.user_id == user_id))
    session.exec(
        delete(ApprovalAction).where(ApprovalAction.transaction_id.in_(transaction_ids))
    )
    session.exec(
        delete(TransactionAttempt).where(
            TransactionAttempt.transaction_id.in_(transaction_ids)
        )
    )
    session.exec(delete(FundReservation).where(FundReservation.user_id == user_id))
    session.exec(delete(LedgerEntry).where(LedgerEntry.journal_id.in_(journal_ids)))
    session.exec(delete(LedgerJournal).where(LedgerJournal.user_id == user_id))
    session.exec(
        delete(PaymentTransaction).where(PaymentTransaction.user_id == user_id)
    )
    session.exec(delete(PolicyVersion).where(PolicyVersion.user_id == user_id))
    session.exec(delete(Wallet).where(Wallet.user_id == user_id))
    session.exec(delete(AuditEvent).where(AuditEvent.user_id == user_id))
    session.exec(delete(AuthSession).where(AuthSession.user_id == user_id))
    session.exec(delete(DemoWorkspace).where(DemoWorkspace.user_id == user_id))
    session.exec(delete(LedgerAccount).where(LedgerAccount.user_id == user_id))
    session.exec(delete(User).where(User.id == user_id, User.is_demo.is_(True)))
