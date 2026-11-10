"""Single-authority PayPal Sandbox reconciliation worker."""

import asyncio
import logging
import signal
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager
from time import monotonic

from sqlalchemy import and_, or_, text, update
from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine, session_scope
from backend.models import PaymentTransaction, TransactionAttempt, User
from backend.observability import log_event
from backend.paypal_client import PayPalClient
from backend.services.paypal import ProviderUnavailable, submit_or_reconcile_payout
from backend.services.demo import cleanup_expired_demo_workspaces


logger = logging.getLogger(__name__)

RECONCILIATION_INTERVAL_SECONDS = 20.0
RECONCILIATION_BATCH_SIZE = 50
RECONCILIATION_LEASE_KEY = 0x504143545241

SessionFactory = Callable[[], AbstractContextManager[Session]]


@contextmanager
def reconciliation_lease():
    """Hold one PostgreSQL advisory lock for the worker process lifetime."""
    if settings.is_sqlite:
        yield True
        return

    with engine.connect() as connection:
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"),
                {"key": RECONCILIATION_LEASE_KEY},
            ).scalar_one()
        )
        try:
            yield acquired
        finally:
            if acquired:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:key)"),
                    {"key": RECONCILIATION_LEASE_KEY},
                )


def claim_paypal_transaction(
    session: Session, *, transaction_id: str
) -> PaymentTransaction | None:
    """Atomically claim one payout row while this database transaction is open."""
    transaction = session.exec(
        select(PaymentTransaction)
        .join(User, User.id == PaymentTransaction.user_id)
        .where(
            PaymentTransaction.id == transaction_id,
            User.is_demo.is_(False),
            PaymentTransaction.rail == "paypal_sandbox_payouts",
            PaymentTransaction.status.in_(["executing", "completed"]),
        )
        .with_for_update(skip_locked=True)
    ).one_or_none()
    if transaction is None:
        return None

    attempt = session.exec(
        select(TransactionAttempt)
        .where(TransactionAttempt.transaction_id == transaction.id)
        .order_by(TransactionAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update(skip_locked=True)
    ).one_or_none()
    if attempt is None or attempt.rail != "paypal_sandbox_payouts":
        return None

    if attempt.provider_batch_id:
        if attempt.status not in {"processing", "unknown"}:
            return None
        return transaction

    if transaction.status != "executing" or attempt.status != "submitting":
        return None
    claimed = session.exec(
        update(TransactionAttempt)
        .where(
            TransactionAttempt.id == attempt.id,
            TransactionAttempt.status == "submitting",
            TransactionAttempt.provider_batch_id.is_(None),
        )
        .values(status="claimed")
    )
    if claimed.rowcount != 1:
        return None
    session.flush()
    return transaction


async def reconcile_pending_payouts(
    *,
    client: PayPalClient,
    session_factory: SessionFactory = session_scope,
    limit: int = RECONCILIATION_BATCH_SIZE,
) -> int:
    """Process one bounded payout batch while preserving stable provider attempts."""
    with session_factory() as session:
        transaction_ids = list(
            session.exec(
                select(TransactionAttempt.transaction_id)
                .join(
                    PaymentTransaction,
                    PaymentTransaction.id == TransactionAttempt.transaction_id,
                )
                .join(User, User.id == PaymentTransaction.user_id)
                .where(
                    User.is_demo.is_(False),
                    PaymentTransaction.rail == "paypal_sandbox_payouts",
                    PaymentTransaction.status.in_(["executing", "completed"]),
                    or_(
                        and_(
                            PaymentTransaction.status == "executing",
                            TransactionAttempt.status == "submitting",
                            TransactionAttempt.provider_batch_id.is_(None),
                        ),
                        and_(
                            TransactionAttempt.status.in_(["processing", "unknown"]),
                            TransactionAttempt.provider_batch_id.is_not(None),
                        ),
                    ),
                )
                .order_by(TransactionAttempt.started_at.asc())
                .limit(limit)
            ).all()
        )

    processed = 0
    for transaction_id in transaction_ids:
        try:
            with session_factory() as session:
                transaction = claim_paypal_transaction(
                    session,
                    transaction_id=transaction_id,
                )
                if transaction is None:
                    continue
                try:
                    await submit_or_reconcile_payout(
                        session,
                        client=client,
                        transaction=transaction,
                    )
                except ProviderUnavailable:
                    # Unknown/transient provider state is local truth and must commit.
                    pass
                processed += 1
        except Exception as exc:
            log_event(
                logger,
                "paypal_reconciliation_failed",
                service="worker",
                level=logging.ERROR,
                operation="paypal.reconcile",
                outcome="error",
                error_class=type(exc).__name__,
                transaction_id=transaction_id,
            )
    return processed


async def _wait_for_stop(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def run_reconciliation_worker(stop_event: asyncio.Event) -> None:
    """Run provider reconciliation and bounded demo cleanup under one lease."""
    provider_enabled = settings.paypal_payouts_enabled and not settings.paypal_mock_mode
    client = PayPalClient() if provider_enabled else None
    next_demo_cleanup_at = 0.0
    try:
        if not provider_enabled:
            log_event(
                logger,
                "worker_standby",
                service="worker",
                operation="paypal.reconcile",
                outcome="disabled",
            )

        while not stop_event.is_set():
            with reconciliation_lease() as acquired:
                if not acquired:
                    log_event(
                        logger,
                        "worker_lease_unavailable",
                        service="worker",
                        level=logging.WARNING,
                        operation="worker.lease",
                        outcome="standby",
                    )
                    await _wait_for_stop(
                        stop_event, RECONCILIATION_INTERVAL_SECONDS
                    )
                    continue

                log_event(
                    logger,
                    "worker_lease_acquired",
                    service="worker",
                    operation="worker.lease",
                    outcome="ready",
                )
                while not stop_event.is_set():
                    try:
                        if monotonic() >= next_demo_cleanup_at:
                            with session_scope() as session:
                                cleaned = cleanup_expired_demo_workspaces(session)
                            next_demo_cleanup_at = (
                                monotonic() + settings.demo_cleanup_interval_seconds
                            )
                            if cleaned:
                                log_event(
                                    logger,
                                    "demo_cleanup_completed",
                                    service="worker",
                                    operation="demo.cleanup",
                                    outcome="processed",
                                    processed_count=cleaned,
                                )
                        count = (
                            await reconcile_pending_payouts(client=client)
                            if client is not None
                            else 0
                        )
                        if count:
                            log_event(
                                logger,
                                "worker_batch_processed",
                                service="worker",
                                operation="paypal.reconcile",
                                outcome="processed",
                                processed_count=count,
                            )
                    except Exception as exc:
                        log_event(
                            logger,
                            "worker_scan_failed",
                            service="worker",
                            level=logging.ERROR,
                            operation="paypal.scan",
                            outcome="error",
                            error_class=type(exc).__name__,
                        )
                    await _wait_for_stop(
                        stop_event, RECONCILIATION_INTERVAL_SECONDS
                    )
    finally:
        if client is not None:
            await client.close()


async def _main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signal_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signal_name, stop_event.set)
        except NotImplementedError:
            pass
    await run_reconciliation_worker(stop_event)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(_main())


if __name__ == "__main__":
    main()
