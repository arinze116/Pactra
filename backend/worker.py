"""Single-authority PayPal Sandbox reconciliation worker."""

import asyncio
import logging
import signal
from collections.abc import Callable
from contextlib import AbstractContextManager, contextmanager

from sqlalchemy import text
from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine, session_scope
from backend.models import PaymentTransaction
from backend.paypal_client import PayPalClient
from backend.services.paypal import ProviderUnavailable, submit_or_reconcile_payout


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


async def reconcile_pending_payouts(
    *,
    client: PayPalClient,
    session_factory: SessionFactory = session_scope,
    limit: int = RECONCILIATION_BATCH_SIZE,
) -> int:
    """Reconcile one bounded batch while preserving stable provider attempts."""
    with session_factory() as session:
        transaction_ids = list(
            session.exec(
                select(PaymentTransaction.id)
                .where(
                    PaymentTransaction.rail == "paypal_sandbox_payouts",
                    PaymentTransaction.status == "executing",
                )
                .order_by(PaymentTransaction.updated_at.asc())
                .limit(limit)
            ).all()
        )

    reconciled = 0
    for transaction_id in transaction_ids:
        try:
            with session_factory() as session:
                transaction = session.exec(
                    select(PaymentTransaction)
                    .where(
                        PaymentTransaction.id == transaction_id,
                        PaymentTransaction.status == "executing",
                    )
                    .with_for_update()
                ).one_or_none()
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
                reconciled += 1
        except Exception:
            logger.exception(
                "PayPal reconciliation failed for transaction %s",
                transaction_id,
            )
    return reconciled


async def _wait_for_stop(stop_event: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def run_reconciliation_worker(stop_event: asyncio.Event) -> None:
    """Run until shutdown, with a database-backed single-worker lease."""
    client = PayPalClient()
    try:
        if not settings.paypal_payouts_enabled or settings.paypal_mock_mode:
            logger.info("PayPal reconciliation is disabled; worker is standing by")
            await stop_event.wait()
            return

        while not stop_event.is_set():
            with reconciliation_lease() as acquired:
                if not acquired:
                    logger.warning(
                        "Another Pactra reconciliation worker holds the database lease"
                    )
                    await _wait_for_stop(
                        stop_event, RECONCILIATION_INTERVAL_SECONDS
                    )
                    continue

                logger.info("Pactra reconciliation worker acquired the database lease")
                while not stop_event.is_set():
                    try:
                        count = await reconcile_pending_payouts(client=client)
                        if count:
                            logger.info("Reconciled %s PayPal payout(s)", count)
                    except Exception:
                        logger.exception("PayPal reconciliation scan failed")
                    await _wait_for_stop(
                        stop_event, RECONCILIATION_INTERVAL_SECONDS
                    )
    finally:
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
