"""Append-only double-entry sandbox ledger and fund reservations."""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from sqlalchemy import case, func
from sqlmodel import Session, select

from backend.defaults import MAX_TOP_UP_CENTS_PER_ACCOUNT, TOP_UP_PRESETS_CENTS
from backend.models import (
    FundReservation,
    LedgerAccount,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    SYSTEM_CLEARING_ACCOUNT_ID,
    SYSTEM_ISSUANCE_ACCOUNT_ID,
    Wallet,
    utc_now,
)
from backend.services.audit import record_audit_event


class LedgerError(RuntimeError):
    """Base class for safe ledger service failures."""


class IdempotencyConflict(LedgerError):
    """The same key was reused for a different canonical action."""


class InsufficientFunds(LedgerError):
    """The wallet cannot satisfy a requested reservation or capture."""


class ReservationConflict(LedgerError):
    """A transaction reservation is missing or already finalised."""


class TopUpLimitReached(LedgerError):
    """The account has exceeded its sandbox top-up allowance."""


@dataclass(frozen=True)
class WalletBalance:
    currency: str
    available_cents: int
    reserved_cents: int
    posted_cents: int
    sandbox_generation: int


@dataclass(frozen=True)
class WalletLedgerItem:
    journal_id: str
    journal_type: str
    transaction_id: str | None
    wallet_delta_cents: int
    counter_account_label: str
    created_at: datetime


def ensure_system_accounts(session: Session) -> None:
    """Create deterministic sandbox counter-accounts when absent."""
    accounts = (
        (
            SYSTEM_ISSUANCE_ACCOUNT_ID,
            "sandbox_issuance_usd",
            "sandbox_issuance",
        ),
        (
            SYSTEM_CLEARING_ACCOUNT_ID,
            "sandbox_clearing_usd",
            "sandbox_clearing",
        ),
    )
    for account_id, code, account_type in accounts:
        if session.get(LedgerAccount, account_id) is None:
            session.add(
                LedgerAccount(
                    id=account_id,
                    user_id=None,
                    code=code,
                    account_type=account_type,
                    currency="USD",
                )
            )
    session.flush()


def get_wallet_for_user(
    session: Session, user_id: str, *, for_update: bool = False
) -> Wallet:
    statement = select(Wallet).where(Wallet.user_id == user_id)
    if for_update:
        statement = statement.with_for_update()
    wallet = session.exec(statement).one_or_none()
    if wallet is None:
        raise LedgerError("Sandbox wallet was not found")
    return wallet


def wallet_balance(session: Session, wallet: Wallet) -> WalletBalance:
    posted = session.exec(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (LedgerEntry.direction == "credit", LedgerEntry.amount_cents),
                        else_=-LedgerEntry.amount_cents,
                    )
                ),
                0,
            )
        ).where(LedgerEntry.account_id == wallet.ledger_account_id)
    ).one()
    reserved = session.exec(
        select(func.coalesce(func.sum(FundReservation.amount_cents), 0)).where(
            FundReservation.wallet_id == wallet.id,
            FundReservation.status == "active",
        )
    ).one()
    posted_cents = int(posted or 0)
    reserved_cents = int(reserved or 0)
    return WalletBalance(
        currency=wallet.currency,
        available_cents=posted_cents - reserved_cents,
        reserved_cents=reserved_cents,
        posted_cents=posted_cents,
        sandbox_generation=wallet.sandbox_generation,
    )


def post_journal(
    session: Session,
    *,
    user_id: str,
    journal_type: str,
    idempotency_key: str,
    amount_cents: int,
    debit_account_id: str,
    credit_account_id: str,
    transaction_id: str | None = None,
) -> LedgerJournal:
    """Post a balanced two-entry journal or return its idempotent replay."""
    if amount_cents <= 0:
        raise LedgerError("Ledger amount must be positive")
    existing = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    if existing is not None:
        entries = session.exec(
            select(LedgerEntry).where(LedgerEntry.journal_id == existing.id)
        ).all()
        signature = {
            (entry.account_id, entry.direction, entry.amount_cents)
            for entry in entries
        }
        expected = {
            (debit_account_id, "debit", amount_cents),
            (credit_account_id, "credit", amount_cents),
        }
        if (
            existing.journal_type != journal_type
            or existing.transaction_id != transaction_id
            or signature != expected
        ):
            raise IdempotencyConflict(
                "This request key was already used for a different ledger action"
            )
        return existing

    debit_account = session.get(LedgerAccount, debit_account_id)
    credit_account = session.get(LedgerAccount, credit_account_id)
    if debit_account is None or credit_account is None:
        raise LedgerError("Ledger account was not found")
    if debit_account.currency != "USD" or credit_account.currency != "USD":
        raise LedgerError("Only USD sandbox ledger postings are supported")
    for account in (debit_account, credit_account):
        if account.account_type == "user_wallet" and account.user_id != user_id:
            raise LedgerError("Wallet account does not belong to this user")

    journal = LedgerJournal(
        user_id=user_id,
        transaction_id=transaction_id,
        journal_type=journal_type,
        idempotency_key=idempotency_key,
        status="posted",
    )
    session.add(journal)
    session.flush()
    session.add_all(
        [
            LedgerEntry(
                journal_id=journal.id,
                account_id=debit_account_id,
                direction="debit",
                amount_cents=amount_cents,
                currency="USD",
            ),
            LedgerEntry(
                journal_id=journal.id,
                account_id=credit_account_id,
                direction="credit",
                amount_cents=amount_cents,
                currency="USD",
            ),
        ]
    )
    session.flush()
    return journal


def issue_sandbox_funds(
    session: Session,
    *,
    user_id: str,
    wallet: Wallet,
    amount_cents: int,
    journal_type: str,
    idempotency_key: str,
) -> LedgerJournal:
    ensure_system_accounts(session)
    existing = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    journal = post_journal(
        session,
        user_id=user_id,
        journal_type=journal_type,
        idempotency_key=idempotency_key,
        amount_cents=amount_cents,
        debit_account_id=SYSTEM_ISSUANCE_ACCOUNT_ID,
        credit_account_id=wallet.ledger_account_id,
    )
    if existing is None:
        record_audit_event(
            session,
            user_id=user_id,
            actor_type="user" if journal_type == "topup" else "system",
            actor_id=user_id if journal_type == "topup" else None,
            entity_type="ledger_journal",
            entity_id=journal.id,
            event_type=f"wallet.{journal_type}",
            payload={"amount_cents": amount_cents, "sandbox_only": True},
        )
    return journal


def top_up_wallet(
    session: Session,
    *,
    user_id: str,
    amount_cents: int,
    idempotency_key: str,
) -> tuple[LedgerJournal, WalletBalance]:
    if amount_cents not in TOP_UP_PRESETS_CENTS:
        raise LedgerError("Top-up amount is not an allowed preset")
    wallet = get_wallet_for_user(session, user_id, for_update=True)

    existing = session.exec(
        select(LedgerJournal).where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.idempotency_key == idempotency_key,
        )
    ).one_or_none()
    if existing is not None:
        journal = issue_sandbox_funds(
            session,
            user_id=user_id,
            wallet=wallet,
            amount_cents=amount_cents,
            journal_type="topup",
            idempotency_key=idempotency_key,
        )
        return journal, wallet_balance(session, wallet)

    hour_ago = utc_now() - timedelta(hours=1)
    top_up_count = session.exec(
        select(func.count(LedgerJournal.id)).where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.journal_type == "topup",
            LedgerJournal.created_at >= hour_ago,
        )
    ).one()
    total_top_ups = session.exec(
        select(func.coalesce(func.sum(LedgerEntry.amount_cents), 0))
        .join(LedgerJournal, LedgerJournal.id == LedgerEntry.journal_id)
        .where(
            LedgerJournal.user_id == user_id,
            LedgerJournal.journal_type == "topup",
            LedgerEntry.account_id == wallet.ledger_account_id,
            LedgerEntry.direction == "credit",
        )
    ).one()
    if int(top_up_count or 0) >= 5 or int(total_top_ups or 0) + amount_cents > MAX_TOP_UP_CENTS_PER_ACCOUNT:
        raise TopUpLimitReached("Top-up limit reached. Try again later")

    journal = issue_sandbox_funds(
        session,
        user_id=user_id,
        wallet=wallet,
        amount_cents=amount_cents,
        journal_type="topup",
        idempotency_key=idempotency_key,
    )
    return journal, wallet_balance(session, wallet)


def reserve_funds(
    session: Session,
    *,
    user_id: str,
    transaction: PaymentTransaction,
) -> FundReservation:
    if transaction.user_id != user_id:
        raise ReservationConflict("Transaction does not belong to this user")
    wallet = get_wallet_for_user(session, user_id, for_update=True)
    if transaction.sandbox_generation != wallet.sandbox_generation:
        raise ReservationConflict("Transaction belongs to a previous sandbox generation")
    existing = session.exec(
        select(FundReservation).where(
            FundReservation.transaction_id == transaction.id,
            FundReservation.status == "active",
        )
    ).one_or_none()
    if existing is not None:
        if existing.amount_cents != transaction.amount_cents:
            raise ReservationConflict("Reservation amount does not match transaction")
        return existing

    balance = wallet_balance(session, wallet)
    if balance.available_cents < transaction.amount_cents:
        raise InsufficientFunds("Your available sandbox balance is too low")

    reservation = FundReservation(
        user_id=user_id,
        wallet_id=wallet.id,
        transaction_id=transaction.id,
        amount_cents=transaction.amount_cents,
        status="active",
    )
    session.add(reservation)
    session.flush()
    record_audit_event(
        session,
        user_id=user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="funds.reserved",
        payload={"amount_cents": transaction.amount_cents},
    )
    return reservation


def release_reservation(
    session: Session,
    *,
    user_id: str,
    transaction_id: str,
    reason: str,
) -> FundReservation:
    reservation = session.exec(
        select(FundReservation)
        .where(
            FundReservation.user_id == user_id,
            FundReservation.transaction_id == transaction_id,
            FundReservation.status == "active",
        )
        .with_for_update()
    ).one_or_none()
    if reservation is None:
        raise ReservationConflict("No active reservation exists")
    reservation.status = "released"
    reservation.released_at = utc_now()
    session.add(reservation)
    record_audit_event(
        session,
        user_id=user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction_id,
        event_type="funds.released",
        payload={"amount_cents": reservation.amount_cents, "reason": reason},
    )
    session.flush()
    return reservation


def capture_reservation(
    session: Session,
    *,
    user_id: str,
    transaction: PaymentTransaction,
) -> LedgerJournal:
    if transaction.user_id != user_id:
        raise ReservationConflict("Transaction does not belong to this user")
    wallet = get_wallet_for_user(session, user_id, for_update=True)
    reservation = session.exec(
        select(FundReservation)
        .where(
            FundReservation.user_id == user_id,
            FundReservation.transaction_id == transaction.id,
            FundReservation.status == "active",
        )
        .with_for_update()
    ).one_or_none()
    if reservation is None:
        existing = session.exec(
            select(LedgerJournal).where(
                LedgerJournal.user_id == user_id,
                LedgerJournal.transaction_id == transaction.id,
                LedgerJournal.journal_type == "payment_capture",
            )
        ).one_or_none()
        if existing is not None:
            return existing
        raise ReservationConflict("No active reservation exists")

    posted = wallet_balance(session, wallet).posted_cents
    if posted < reservation.amount_cents:
        raise InsufficientFunds("Posted sandbox balance is too low")
    journal = post_journal(
        session,
        user_id=user_id,
        transaction_id=transaction.id,
        journal_type="payment_capture",
        idempotency_key=f"capture:{transaction.id}",
        amount_cents=reservation.amount_cents,
        debit_account_id=wallet.ledger_account_id,
        credit_account_id=SYSTEM_CLEARING_ACCOUNT_ID,
    )
    reservation.status = "captured"
    reservation.released_at = utc_now()
    session.add(reservation)
    record_audit_event(
        session,
        user_id=user_id,
        actor_type="system",
        actor_id=None,
        entity_type="transaction",
        entity_id=transaction.id,
        event_type="ledger.posted",
        payload={"journal_id": journal.id, "amount_cents": reservation.amount_cents},
    )
    session.flush()
    return journal


def _encode_cursor(created_at: datetime, journal_id: str) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "journal_id": journal_id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        return datetime.fromisoformat(payload["created_at"]), str(payload["journal_id"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise LedgerError("Ledger cursor is invalid") from exc


def list_wallet_ledger(
    session: Session,
    *,
    user_id: str,
    cursor: str | None = None,
    limit: int = 25,
) -> tuple[list[WalletLedgerItem], str | None]:
    """Return only the authenticated user's wallet-side posting summaries."""
    wallet = get_wallet_for_user(session, user_id)
    statement = (
        select(LedgerJournal, LedgerEntry)
        .join(LedgerEntry, LedgerEntry.journal_id == LedgerJournal.id)
        .where(
            LedgerJournal.user_id == user_id,
            LedgerEntry.account_id == wallet.ledger_account_id,
        )
    )
    if cursor:
        created_at, journal_id = _decode_cursor(cursor)
        statement = statement.where(
            (LedgerJournal.created_at < created_at)
            | (
                (LedgerJournal.created_at == created_at)
                & (LedgerJournal.id < journal_id)
            )
        )
    rows = session.exec(
        statement.order_by(LedgerJournal.created_at.desc(), LedgerJournal.id.desc()).limit(
            limit + 1
        )
    ).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        WalletLedgerItem(
            journal_id=journal.id,
            journal_type=journal.journal_type,
            transaction_id=journal.transaction_id,
            wallet_delta_cents=(
                entry.amount_cents if entry.direction == "credit" else -entry.amount_cents
            ),
            counter_account_label=(
                "Sandbox clearing"
                if journal.journal_type in {"payment_capture", "reversal"}
                else "Sandbox issuance"
            ),
            created_at=journal.created_at,
        )
        for journal, entry in rows
    ]
    next_cursor = None
    if has_more and items:
        next_cursor = _encode_cursor(items[-1].created_at, items[-1].journal_id)
    return items, next_cursor
