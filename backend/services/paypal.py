"""PayPal Sandbox payout submission and item-level reconciliation orchestration."""

from sqlmodel import Session

from backend.models import PaymentTransaction, User
from backend.paypal_client import (
    PayPalClient,
    PayPalConfigurationError,
    PayPalError,
    PayPalRejected,
    PayPalUnknownOutcome,
)
from backend.services.transactions import (
    apply_paypal_reconciliation,
    fail_paypal_attempt,
    get_active_paypal_attempt,
    record_paypal_submission,
    record_paypal_unknown,
)


class ProviderUnavailable(RuntimeError):
    """Provider status could not be obtained without changing local truth."""


async def submit_or_reconcile_payout(
    session: Session,
    *,
    client: PayPalClient,
    transaction: PaymentTransaction,
) -> PaymentTransaction:
    """Run one worker-owned submission or reconciliation phase."""
    owner = session.get(User, transaction.user_id)
    if owner is None or owner.is_demo:
        raise ProviderUnavailable("Provider execution is disabled for demo principals")
    attempt = get_active_paypal_attempt(session, transaction_id=transaction.id)
    if attempt.provider_batch_id is None:
        if attempt.status == "unknown":
            raise ProviderUnavailable(
                "PayPal submission outcome is unknown and requires a known batch reference"
            )
        if attempt.status != "claimed":
            raise ProviderUnavailable("PayPal payout has not been claimed by the worker")
        try:
            submission = await client.create_payout(
                transaction_id=transaction.id,
                attempt_number=attempt.attempt_number,
                recipient_email=transaction.recipient or "",
                amount_cents=transaction.amount_cents,
                currency=transaction.currency,
                note=transaction.reason,
            )
        except PayPalUnknownOutcome as exc:
            record_paypal_unknown(
                session,
                transaction=transaction,
                attempt=attempt,
                code="PAYPAL_OUTCOME_UNKNOWN",
            )
            raise ProviderUnavailable(str(exc)) from exc
        except (PayPalRejected, PayPalConfigurationError) as exc:
            fail_paypal_attempt(
                session,
                transaction=transaction,
                attempt=attempt,
                code="PAYPAL_SUBMISSION_REJECTED",
            )
            return transaction
        except PayPalError as exc:
            fail_paypal_attempt(
                session,
                transaction=transaction,
                attempt=attempt,
                code="PAYPAL_AUTH_OR_SUBMISSION_FAILED",
            )
            raise ProviderUnavailable(str(exc)) from exc
        record_paypal_submission(
            session,
            transaction=transaction,
            attempt=attempt,
            batch_id=submission.batch_id,
            batch_status=submission.batch_status,
        )
        # Submission and item-level capture are deliberately separate worker
        # cycles so the provider reference commits before reconciliation.
        return transaction

    try:
        status = await client.get_payout(attempt.provider_batch_id)
    except PayPalError as exc:
        raise ProviderUnavailable(str(exc)) from exc
    apply_paypal_reconciliation(
        session,
        transaction=transaction,
        attempt=attempt,
        batch_status=status.batch_status,
        item_id=status.item_id,
        item_status=status.item_status,
    )
    return transaction
