"""Create an isolated failed internal transaction for browser retry tests."""

import sys

from sqlmodel import Session, select

from backend.config import settings
from backend.database import engine
from backend.models import PaymentTransaction, User
from backend.services.audit import record_audit_event
from backend.services.ledger import get_wallet_for_user
from backend.services.policies import get_current_policy


def main() -> None:
    if settings.app_env != "test":
        raise RuntimeError("E2E fixtures are available only in APP_ENV=test")
    if len(sys.argv) != 2:
        raise RuntimeError("Usage: seed_e2e_failed_transaction.py <email>")

    email = sys.argv[1].strip().casefold()
    with Session(engine, expire_on_commit=False) as session:
        user = session.exec(select(User).where(User.email == email)).one()
        wallet = get_wallet_for_user(session, user.id)
        policy = get_current_policy(session, user.id)
        transaction = PaymentTransaction(
            user_id=user.id,
            idempotency_key=f"e2e-failed-{user.id}",
            type="vendor_payment",
            vendor="Retry Fixture",
            recipient=None,
            amount_cents=4_900,
            currency="USD",
            category="software",
            reason="Isolated browser retry verification",
            status="failed",
            sandbox_generation=wallet.sandbox_generation,
            policy_version=policy.version,
            policy_result={"decision": "approved", "checks": []},
            rail="internal_sandbox",
            failure_code="TEMPORARY_INTERNAL_FAILURE",
        )
        session.add(transaction)
        session.flush()
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="system",
            actor_id=None,
            entity_type="transaction",
            entity_id=transaction.id,
            event_type="transaction.state_changed",
            payload={"from": "executing", "to": "failed"},
        )
        session.commit()
        print(transaction.id)


if __name__ == "__main__":
    main()
