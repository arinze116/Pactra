"""PayPal Sandbox payout submission and item-level reconciliation orchestration."""

from sqlmodel import Session

from backend.models import PaymentTransaction
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
    """Submit once using stable IDs, then reconcile the payout item when possible."""
    attempt = get_active_paypal_attempt(session, transaction_id=transaction.id)
    if attempt.provider_batch_id is None:
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
        # Preserve the accepted provider reference before local capture. If a
        # later commit fails, reconciliation can query this exact batch rather
        # than submitting a second payout.
        session.commit()
        session.refresh(transaction)
        session.refresh(attempt)

    try:
        status = await client.get_payout(attempt.provider_batch_id or transaction.provider_batch_id or "")
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
