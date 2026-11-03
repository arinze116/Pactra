"""User account creation and its atomic sandbox-resource bootstrap."""

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.defaults import INITIAL_SANDBOX_CENTS, default_policy
from backend.models import LedgerAccount, PolicyVersion, User, Wallet
from backend.services.audit import record_audit_event
from backend.services.ledger import WalletBalance, issue_sandbox_funds, wallet_balance


class EmailAlreadyExists(RuntimeError):
    """Raised when an email is already associated with an account."""


@dataclass(frozen=True)
class AccountBootstrap:
    user: User
    wallet: Wallet
    balance: WalletBalance


def create_account(
    session: Session, *, email: str, password_hash: str
) -> AccountBootstrap:
    """Create the user, wallet, default policy and issuance atomically."""
    normalised_email = email.strip().casefold()
    if session.exec(select(User.id).where(User.email == normalised_email)).first():
        raise EmailAlreadyExists("An account with this email already exists")

    user = User(email=normalised_email, password_hash=password_hash)
    session.add(user)
    try:
        session.flush()
        account = LedgerAccount(
            user_id=user.id,
            code=f"wallet_{user.id}_usd",
            account_type="user_wallet",
            currency="USD",
        )
        session.add(account)
        session.flush()

        wallet = Wallet(
            user_id=user.id,
            ledger_account_id=account.id,
            currency="USD",
            status="active",
            sandbox_generation=1,
        )
        policy = PolicyVersion(
            user_id=user.id,
            version=1,
            policy_json=default_policy(),
            created_by=user.id,
        )
        session.add_all([wallet, policy])
        session.flush()

        issue_sandbox_funds(
            session,
            user_id=user.id,
            wallet=wallet,
            amount_cents=INITIAL_SANDBOX_CENTS,
            journal_type="initial_issuance",
            idempotency_key=f"initial:{user.id}",
        )
        record_audit_event(
            session,
            user_id=user.id,
            actor_type="user",
            actor_id=user.id,
            entity_type="user",
            entity_id=user.id,
            event_type="auth.registered",
            payload={"sandbox_only": True},
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmailAlreadyExists("An account with this email already exists") from exc
    except Exception:
        session.rollback()
        raise

    session.refresh(user)
    session.refresh(wallet)
    return AccountBootstrap(
        user=user,
        wallet=wallet,
        balance=wallet_balance(session, wallet),
    )

