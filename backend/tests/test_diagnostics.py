"""Read-only operational diagnostics catch financial inconsistencies."""

import json
import logging
from types import SimpleNamespace
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from backend.diagnostics.invariants import collect_financial_invariants
from backend.diagnostics.backups import sha256_file, verify_backup
from backend.diagnostics.http_health import check_endpoint, check_frontend, validate_base_url
from backend.models import (
    FundReservation,
    LedgerEntry,
    LedgerJournal,
    PaymentTransaction,
    TransactionAttempt,
)
from backend.observability import log_event, operation_from_scope, safe_request_id
from backend.services.accounts import create_account
from backend.services.ledger import get_wallet_for_user
from backend.services.transactions import PolicyBlocked, create_payment_request


@pytest.fixture
def diagnostic_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        account = create_account(
            session,
            email="diagnostics@example.com",
            password_hash="unused-test-hash",
        )
        yield session, account.user
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


def payment_payload(*, amount_cents: int, key: str) -> dict[str, object]:
    return {
        "type": "vendor_payment",
        "vendor": "Linear",
        "recipient": None,
        "amount_cents": amount_cents,
        "currency": "USD",
        "category": "software",
        "reason": "Diagnostic transaction",
        "rail": "internal_sandbox",
        "idempotency_key": key,
        "source": "test",
    }


def test_clean_financial_state_passes_every_invariant(diagnostic_db) -> None:
    session, user = diagnostic_db
    create_payment_request(
        session,
        user=user,
        payload=payment_payload(amount_cents=4_900, key="diagnostic-auto-0001"),
    )
    create_payment_request(
        session,
        user=user,
        payload={
            **payment_payload(
                amount_cents=12_500,
                key="diagnostic-pending-0001",
            ),
            "category": "freelance",
        },
    )
    with pytest.raises(PolicyBlocked):
        create_payment_request(
            session,
            user=user,
            payload=payment_payload(
                amount_cents=20_000,
                key="diagnostic-blocked-0001",
            ),
        )
    session.commit()

    report = collect_financial_invariants(session)

    assert report.passed is True
    assert report.violation_count == 0


def test_unbalanced_journal_and_invalid_completion_are_reported(diagnostic_db) -> None:
    session, user = diagnostic_db
    wallet = get_wallet_for_user(session, user.id)
    transaction = PaymentTransaction(
        user_id=user.id,
        idempotency_key="diagnostic-invalid-completion-0001",
        type="vendor_payment",
        vendor="Broken state fixture",
        recipient=None,
        amount_cents=100,
        currency="USD",
        category="software",
        reason="Intentional diagnostic fixture",
        status="completed",
        sandbox_generation=wallet.sandbox_generation,
        policy_version=1,
        policy_result={"decision": "approved"},
        rail="internal_sandbox",
    )
    session.add(transaction)
    session.flush()
    journal = LedgerJournal(
        user_id=user.id,
        transaction_id=transaction.id,
        journal_type="payment_capture",
        idempotency_key="diagnostic-invalid-journal-0001",
        status="posted",
    )
    session.add(journal)
    session.flush()
    session.add(
        LedgerEntry(
            journal_id=journal.id,
            account_id=wallet.ledger_account_id,
            direction="debit",
            amount_cents=99,
            currency="USD",
        )
    )
    session.commit()

    report = collect_financial_invariants(session)
    checks = {check.code: check for check in report.checks}

    assert report.passed is False
    assert checks["LEDGER_JOURNALS_BALANCED"].violation_count == 1
    assert checks["CAPTURE_LINKAGE_VALID"].violation_count == 1
    assert checks["RESERVATION_STATE_VALID"].violation_count == 1


def test_diagnostics_do_not_mutate_financial_rows(diagnostic_db) -> None:
    session, _user = diagnostic_db
    before = (
        len(session.exec(select(LedgerJournal)).all()),
        len(session.exec(select(LedgerEntry)).all()),
        len(session.exec(select(PaymentTransaction)).all()),
    )

    collect_financial_invariants(session)

    after = (
        len(session.exec(select(LedgerJournal)).all()),
        len(session.exec(select(LedgerEntry)).all()),
        len(session.exec(select(PaymentTransaction)).all()),
    )
    assert after == before


def test_provider_reversal_before_capture_is_a_valid_terminal_state(
    diagnostic_db,
) -> None:
    session, user = diagnostic_db
    wallet = get_wallet_for_user(session, user.id)
    transaction = PaymentTransaction(
        user_id=user.id,
        idempotency_key="diagnostic-pre-capture-reversal-0001",
        type="payout",
        vendor="Fictional contractor",
        recipient="contractor@example.test",
        amount_cents=2_500,
        currency="USD",
        category="freelance",
        reason="Intentional provider reversal fixture",
        status="reversed",
        sandbox_generation=wallet.sandbox_generation,
        policy_version=1,
        policy_result={"decision": "approved"},
        rail="paypal_sandbox_payouts",
        provider_batch_id="diagnostic-batch-0001",
        provider_item_id="diagnostic-item-0001",
        provider_status="RETURNED",
        failure_code="PAYPAL_ITEM_RETURNED",
    )
    session.add(transaction)
    session.flush()
    session.add_all(
        [
            FundReservation(
                user_id=user.id,
                wallet_id=wallet.id,
                transaction_id=transaction.id,
                amount_cents=transaction.amount_cents,
                status="released",
            ),
            TransactionAttempt(
                transaction_id=transaction.id,
                attempt_number=1,
                rail="paypal_sandbox_payouts",
                rail_request_id="diagnostic-request-0001",
                provider_batch_id=transaction.provider_batch_id,
                provider_item_id=transaction.provider_item_id,
                provider_status="RETURNED",
                status="reversed",
            ),
        ]
    )
    session.commit()

    report = collect_financial_invariants(session)

    assert report.passed is True


def test_request_ids_are_bounded_and_log_fields_are_sanitised(caplog) -> None:
    assert safe_request_id("demo-request-0001") == "demo-request-0001"
    assert safe_request_id("bad request id") != "bad request id"
    assert len(safe_request_id("x" * 500)) == 36

    logger = logging.getLogger("pactra.tests.observability")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(
            logger,
            "diagnostic_complete",
            service="test",
            request_id="demo-request-0001",
            outcome="pass",
            violation_count=0,
        )
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "diagnostic_complete"
    assert payload["request_id"] == "demo-request-0001"
    assert payload["violation_count"] == 0
    assert "password" not in payload

    with pytest.raises(ValueError, match="Sensitive log field"):
        log_event(logger, "unsafe", service="test", session_token="forbidden")


def test_log_operation_uses_route_template_not_request_identifier() -> None:
    operation = operation_from_scope(
        {
            "path": "/api/transactions/4f62066e-718e-4e01-97ac-e7afe44daf6a",
            "route": SimpleNamespace(path_format="/api/transactions/{transaction_id}"),
        }
    )

    assert operation == "/api/transactions/{transaction_id}"
    assert "4f62066e" not in operation
    assert operation_from_scope({"path": "/unmatched/private-value"}) == "unmatched_route"


def test_backup_verification_checks_checksum_age_size_and_archive(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "pactra-demo.dump"
    archive.write_bytes(b"pactra-backup-fixture" * 100)
    fake_restore = tmp_path / "pg_restore"
    fake_restore.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_restore.chmod(0o700)

    report = verify_backup(
        archive,
        expected_sha256=sha256_file(archive),
        require_checksum=True,
        min_size_bytes=100,
        max_age_hours=1,
        pg_restore_binary=str(fake_restore),
    )

    assert report.passed is True
    assert report.archive_list_valid is True
    assert report.checks == ()


def test_backup_verification_reports_missing_checksum_and_bad_archive(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "pactra-demo.dump"
    archive.write_bytes(b"invalid")

    report = verify_backup(
        archive,
        require_checksum=True,
        min_size_bytes=100,
        pg_restore_binary=str(tmp_path / "missing-pg-restore"),
    )

    assert report.passed is False
    assert set(report.checks) == {
        "archive_list_failed",
        "backup_too_small",
        "checksum_missing",
    }


def test_backup_verification_rejects_symbolic_links(tmp_path: Path) -> None:
    archive = tmp_path / "pactra-demo.dump"
    archive.write_bytes(b"archive")
    link = tmp_path / "linked.dump"
    link.symlink_to(archive)

    with pytest.raises(ValueError, match="symbolic link"):
        verify_backup(link)


def test_public_health_checks_validate_payloads_and_latency() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
            if self.path == "/":
                body = b"<!doctype html><title>Pactra</title>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            payload = (
                {"status": "ok"}
                if self.path == "/api/health"
                else {
                    "status": "ready",
                    "database": "ok",
                    "sandbox_mode": True,
                    "internal_sandbox_available": True,
                }
            )
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = validate_base_url(
            f"http://127.0.0.1:{server.server_port}", allow_http=True
        )
        health = check_endpoint(origin, "/api/health", max_latency_ms=2_000)
        readiness = check_endpoint(origin, "/api/ready", max_latency_ms=2_000)
        frontend = check_frontend(origin, max_latency_ms=2_000)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert health.passed is True
    assert readiness.passed is True
    assert frontend.passed is True


def test_public_health_origin_rejects_credentials_and_non_https() -> None:
    with pytest.raises(ValueError):
        validate_base_url("http://pactra.example")
    with pytest.raises(ValueError):
        validate_base_url("https://user:password@pactra.example")
