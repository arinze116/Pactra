"""Read-only financial and payment-state invariant checks."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from sqlmodel import Session, select

from backend.models import (
    AuditEvent,
    FundReservation,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
    Wallet,
)


ALLOWED_STATE_TRANSITIONS = frozenset(
    {
        ("draft", "blocked"),
        ("draft", "executing"),
        ("draft", "pending_approval"),
        ("pending_approval", "blocked"),
        ("pending_approval", "cancelled"),
        ("pending_approval", "executing"),
        ("pending_approval", "rejected"),
        ("executing", "completed"),
        ("executing", "failed"),
        ("executing", "reversed"),
        ("failed", "executing"),
        ("completed", "reversed"),
    }
)


@dataclass(frozen=True)
class InvariantResult:
    code: str
    severity: str
    passed: bool
    violation_count: int
    description: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class InvariantReport:
    passed: bool
    checks: tuple[InvariantResult, ...]

    @property
    def violation_count(self) -> int:
        return sum(check.violation_count for check in self.checks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violation_count": self.violation_count,
            "checks": [check.as_dict() for check in self.checks],
        }


def _result(
    code: str,
    severity: str,
    violations: int,
    description: str,
) -> InvariantResult:
    return InvariantResult(
        code=code,
        severity=severity,
        passed=violations == 0,
        violation_count=violations,
        description=description,
    )


def collect_financial_invariants(session: Session) -> InvariantReport:
    """Evaluate accounting and provider invariants without changing data."""
    transactions = list(session.exec(select(PaymentTransaction)).all())
    transaction_by_id = {transaction.id: transaction for transaction in transactions}
    journals = list(session.exec(select(LedgerJournal)).all())
    entries = list(session.exec(select(LedgerEntry)).all())
    reservations = list(session.exec(select(FundReservation)).all())
    attempts = list(session.exec(select(TransactionAttempt)).all())
    wallets = list(session.exec(select(Wallet)).all())
    wallet_by_user = {wallet.user_id: wallet for wallet in wallets}
    state_events = list(
        session.exec(
            select(AuditEvent).where(
                AuditEvent.entity_type == "transaction",
                AuditEvent.event_type == "transaction.state_changed",
            )
        ).all()
    )

    entries_by_journal: dict[str, list[LedgerEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_journal[entry.journal_id].append(entry)
    journals_by_transaction: dict[str, list[LedgerJournal]] = defaultdict(list)
    for journal in journals:
        if journal.transaction_id:
            journals_by_transaction[journal.transaction_id].append(journal)
    reservations_by_transaction: dict[str, list[FundReservation]] = defaultdict(list)
    for reservation in reservations:
        reservations_by_transaction[reservation.transaction_id].append(reservation)
    attempts_by_transaction: dict[str, list[TransactionAttempt]] = defaultdict(list)
    for attempt in attempts:
        attempts_by_transaction[attempt.transaction_id].append(attempt)

    unbalanced_journals = 0
    for journal in journals:
        journal_entries = entries_by_journal[journal.id]
        debit = sum(
            entry.amount_cents
            for entry in journal_entries
            if entry.direction == "debit"
        )
        credit = sum(
            entry.amount_cents
            for entry in journal_entries
            if entry.direction == "credit"
        )
        currencies = {entry.currency for entry in journal_entries}
        if len(journal_entries) != 2 or debit != credit or currencies != {"USD"}:
            unbalanced_journals += 1

    duplicate_captures = 0
    invalid_capture_linkage = 0
    reservation_state_violations = 0
    paypal_success_violations = 0
    unknown_outcome_violations = 0
    for transaction in transactions:
        transaction_journals = journals_by_transaction[transaction.id]
        captures = [
            journal
            for journal in transaction_journals
            if journal.journal_type == "payment_capture"
        ]
        reversals = [
            journal
            for journal in transaction_journals
            if journal.journal_type == "payment_reversal"
        ]
        if len(captures) > 1 or len(reversals) > 1:
            duplicate_captures += 1
        for journal in captures + reversals:
            journal_entries = entries_by_journal[journal.id]
            amounts = {entry.amount_cents for entry in journal_entries}
            if journal.user_id != transaction.user_id or amounts != {
                transaction.amount_cents
            }:
                invalid_capture_linkage += 1

        transaction_reservations = reservations_by_transaction[transaction.id]
        active = [item for item in transaction_reservations if item.status == "active"]
        captured = [
            item for item in transaction_reservations if item.status == "captured"
        ]
        if any(
            item.user_id != transaction.user_id
            or wallet_by_user.get(transaction.user_id) is None
            or item.wallet_id != wallet_by_user[transaction.user_id].id
            or item.amount_cents != transaction.amount_cents
            for item in transaction_reservations
        ):
            reservation_state_violations += 1
        if transaction.status in {"pending_approval", "executing"}:
            if len(active) != 1:
                reservation_state_violations += 1
        elif active:
            reservation_state_violations += 1
        if transaction.status == "completed":
            if len(captured) != 1 or len(captures) != 1:
                reservation_state_violations += 1
            if reversals:
                reservation_state_violations += 1
        elif transaction.status == "reversed":
            compensated_capture = (
                len(captured) == 1
                and len(captures) == 1
                and len(reversals) == 1
            )
            reversed_before_capture = (
                not captured and not captures and not reversals
            )
            if not (compensated_capture or reversed_before_capture):
                reservation_state_violations += 1
        elif transaction.status in {"blocked", "rejected", "failed", "cancelled"}:
            if captured or captures or reversals:
                reservation_state_violations += 1

        transaction_attempts = attempts_by_transaction[transaction.id]
        if transaction.rail == "paypal_sandbox_payouts" and transaction.status == "completed":
            successful_attempts = [
                attempt
                for attempt in transaction_attempts
                if attempt.status == "completed"
                and attempt.provider_status == "SUCCESS"
            ]
            if transaction.provider_status != "SUCCESS" or len(successful_attempts) != 1:
                paypal_success_violations += 1
        unknown_attempts = [
            attempt for attempt in transaction_attempts if attempt.status == "unknown"
        ]
        if unknown_attempts and (
            transaction.status != "executing" or len(active) != 1 or captures
        ):
            unknown_outcome_violations += 1

    wallet_balance_violations = 0
    entries_by_account: dict[str, list[LedgerEntry]] = defaultdict(list)
    reservations_by_wallet: dict[str, list[FundReservation]] = defaultdict(list)
    for entry in entries:
        entries_by_account[entry.account_id].append(entry)
    for reservation in reservations:
        reservations_by_wallet[reservation.wallet_id].append(reservation)
    for wallet in wallets:
        posted = sum(
            entry.amount_cents if entry.direction == "credit" else -entry.amount_cents
            for entry in entries_by_account[wallet.ledger_account_id]
        )
        reserved = sum(
            item.amount_cents
            for item in reservations_by_wallet[wallet.id]
            if item.status == "active"
        )
        if posted < 0 or reserved < 0 or posted - reserved < 0:
            wallet_balance_violations += 1

    provider_identifier_violations = 0
    identifier_sets = (
        [item.provider_batch_id for item in transactions if item.provider_batch_id],
        [item.provider_item_id for item in transactions if item.provider_item_id],
        [item.rail_request_id for item in attempts],
        [item.provider_batch_id for item in attempts if item.provider_batch_id],
        [item.provider_item_id for item in attempts if item.provider_item_id],
    )
    for values in identifier_sets:
        provider_identifier_violations += sum(
            1 for count in Counter(values).values() if count > 1
        )

    attempt_state_violations = 0
    for attempt in attempts:
        transaction = transaction_by_id.get(attempt.transaction_id)
        if transaction is None or attempt.rail != transaction.rail:
            attempt_state_violations += 1
            continue
        if attempt.rail == "paypal_sandbox_payouts" and transaction.rail != attempt.rail:
            attempt_state_violations += 1
        if attempt.status in {"submitting", "claimed", "processing", "unknown"} and (
            transaction.status not in {"executing", "completed"}
        ):
            attempt_state_violations += 1
        if attempt.status == "completed" and transaction.status not in {
            "completed",
            "reversed",
        }:
            attempt_state_violations += 1

    journal_owner_violations = sum(
        1
        for journal in journals
        if journal.transaction_id
        and (
            journal.transaction_id not in transaction_by_id
            or transaction_by_id[journal.transaction_id].user_id != journal.user_id
        )
    )
    transition_violations = sum(
        1
        for event in state_events
        if (
            str(event.payload.get("from")),
            str(event.payload.get("to")),
        )
        not in ALLOWED_STATE_TRANSITIONS
    )

    checks = (
        _result(
            "LEDGER_JOURNALS_BALANCED",
            "P0",
            unbalanced_journals,
            "Every posted journal has exactly two equal USD debit and credit entries.",
        ),
        _result(
            "CAPTURE_JOURNALS_EXACTLY_ONCE",
            "P0",
            duplicate_captures,
            "Each transaction has at most one capture and one compensating reversal.",
        ),
        _result(
            "CAPTURE_LINKAGE_VALID",
            "P0",
            invalid_capture_linkage + journal_owner_violations,
            "Transaction journals belong to the same tenant and match the payment amount.",
        ),
        _result(
            "RESERVATION_STATE_VALID",
            "P0",
            reservation_state_violations,
            "Reservations match transaction ownership, amount and terminal state.",
        ),
        _result(
            "WALLET_BALANCES_NONNEGATIVE",
            "P0",
            wallet_balance_violations,
            "Derived posted, reserved and available wallet balances are non-negative.",
        ),
        _result(
            "PROVIDER_IDENTIFIERS_UNIQUE",
            "P0",
            provider_identifier_violations,
            "Stable provider and rail identifiers are not reused across attempts.",
        ),
        _result(
            "PAYPAL_ITEM_SUCCESS_AUTHORITATIVE",
            "P0",
            paypal_success_violations,
            "Completed PayPal payouts have exactly one item-level SUCCESS attempt.",
        ),
        _result(
            "UNKNOWN_OUTCOMES_REMAIN_RESERVED",
            "P0",
            unknown_outcome_violations,
            "Unknown PayPal outcomes remain executing, reserved and uncaptured.",
        ),
        _result(
            "ATTEMPT_STATE_LINKAGE_VALID",
            "P1",
            attempt_state_violations,
            "Execution attempts correspond to a compatible transaction rail and state.",
        ),
        _result(
            "STATE_TRANSITIONS_VALID",
            "P1",
            transition_violations,
            "Recorded transaction state transitions belong to the allowed lifecycle.",
        ),
    )
    return InvariantReport(
        passed=all(check.passed for check in checks),
        checks=checks,
    )
