"""Create the judge-ready user, ledger and transaction schema.

Revision ID: 20261103_0001
Revises: None
Create Date: 2026-11-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261103_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ID = sa.String(36).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
JSON_VALUE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", ID, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_users_status_valid"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "sessions",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_user_expiry", "sessions", ["user_id", "expires_at"])

    op.create_table(
        "ledger_accounts",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("account_type", sa.String(24), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "account_type IN ('user_wallet','sandbox_issuance','sandbox_clearing')",
            name="ck_ledger_accounts_type_valid",
        ),
        sa.CheckConstraint("currency = 'USD'", name="ck_ledger_accounts_currency_usd"),
        sa.CheckConstraint(
            "(account_type = 'user_wallet' AND user_id IS NOT NULL) OR "
            "(account_type IN ('sandbox_issuance','sandbox_clearing') AND user_id IS NULL)",
            name="ck_ledger_accounts_owner_valid",
        ),
        sa.UniqueConstraint("code", name="uq_ledger_accounts_code"),
    )

    account_table = sa.table(
        "ledger_accounts",
        sa.column("id", ID),
        sa.column("user_id", ID),
        sa.column("code", sa.String),
        sa.column("account_type", sa.String),
        sa.column("currency", sa.String),
    )
    op.bulk_insert(
        account_table,
        [
            {
                "id": "00000000-0000-4000-8000-000000000001",
                "user_id": None,
                "code": "sandbox_issuance_usd",
                "account_type": "sandbox_issuance",
                "currency": "USD",
            },
            {
                "id": "00000000-0000-4000-8000-000000000002",
                "user_id": None,
                "code": "sandbox_clearing_usd",
                "account_type": "sandbox_clearing",
                "currency": "USD",
            },
        ],
    )

    op.create_table(
        "wallets",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "ledger_account_id",
            ID,
            sa.ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("sandbox_generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("currency = 'USD'", name="ck_wallets_currency_usd"),
        sa.CheckConstraint("status IN ('active','locked')", name="ck_wallets_status_valid"),
        sa.CheckConstraint("sandbox_generation > 0", name="ck_wallets_generation_positive"),
        sa.UniqueConstraint("user_id", name="uq_wallets_user_id"),
        sa.UniqueConstraint("ledger_account_id", name="uq_wallets_ledger_account_id"),
    )

    op.create_table(
        "policies",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("policy_json", JSON_VALUE, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("created_by", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("version > 0", name="ck_policies_version_positive"),
        sa.UniqueConstraint("user_id", "version", name="uq_policies_user_version"),
    )
    op.create_index("ix_policies_user_version", "policies", ["user_id", "version"])

    op.create_table(
        "transactions",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("vendor", sa.String(100), nullable=False),
        sa.Column("recipient", sa.String(254), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("sandbox_generation", sa.Integer(), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("policy_result", JSON_VALUE, nullable=False),
        sa.Column("rail", sa.String(32), nullable=False),
        sa.Column("rail_reference", sa.String(128), nullable=True),
        sa.Column("provider_batch_id", sa.String(128), nullable=True),
        sa.Column("provider_item_id", sa.String(128), nullable=True),
        sa.Column("provider_status", sa.String(32), nullable=True),
        sa.Column("failure_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('vendor_payment','payout','sandbox_transfer')",
            name="ck_transactions_type_valid",
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint("currency = 'USD'", name="ck_transactions_currency_usd"),
        sa.CheckConstraint(
            "status IN ('draft','pending_approval','executing','completed','blocked',"
            "'rejected','failed','cancelled','reversed')",
            name="ck_transactions_status_valid",
        ),
        sa.CheckConstraint(
            "sandbox_generation > 0", name="ck_transactions_generation_positive"
        ),
        sa.CheckConstraint(
            "rail IN ('internal_sandbox','paypal_sandbox_payouts')",
            name="ck_transactions_rail_valid",
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_transactions_user_idempotency"
        ),
        sa.UniqueConstraint("provider_batch_id", name="uq_transactions_provider_batch"),
    )
    op.create_index("ix_transactions_user_created", "transactions", ["user_id", "created_at"])
    op.create_index("ix_transactions_user_status", "transactions", ["user_id", "status"])
    op.create_index("ix_transactions_user_category", "transactions", ["user_id", "category"])
    op.create_index("ix_transactions_provider_batch", "transactions", ["provider_batch_id"])

    op.create_table(
        "ledger_journals",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "transaction_id",
            ID,
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("journal_type", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="posted"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("status = 'posted'", name="ck_journals_status_posted"),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_journals_user_idempotency"
        ),
    )
    op.create_index("ix_journals_user_created", "ledger_journals", ["user_id", "created_at"])
    op.create_index("ix_journals_transaction", "ledger_journals", ["transaction_id"])

    op.create_table(
        "ledger_entries",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "journal_id",
            ID,
            sa.ForeignKey("ledger_journals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            ID,
            sa.ForeignKey("ledger_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "direction IN ('debit','credit')", name="ck_ledger_entries_direction_valid"
        ),
        sa.CheckConstraint("amount_cents > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("currency = 'USD'", name="ck_ledger_entries_currency_usd"),
    )
    op.create_index("ix_ledger_account_created", "ledger_entries", ["account_id", "created_at"])
    op.create_index("ix_ledger_journal", "ledger_entries", ["journal_id"])

    op.create_table(
        "fund_reservations",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wallet_id", ID, sa.ForeignKey("wallets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column(
            "transaction_id",
            ID,
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("amount_cents > 0", name="ck_reservations_amount_positive"),
        sa.CheckConstraint(
            "status IN ('active','captured','released')",
            name="ck_reservations_status_valid",
        ),
    )
    op.create_index("ix_reservations_user_status", "fund_reservations", ["user_id", "status"])
    op.create_index(
        "uq_active_reservation_transaction",
        "fund_reservations",
        ["transaction_id"],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "transaction_attempts",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "transaction_id",
            ID,
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("rail", sa.String(32), nullable=False),
        sa.Column("rail_request_id", sa.String(128), nullable=False),
        sa.Column("provider_batch_id", sa.String(128), nullable=True),
        sa.Column("provider_item_id", sa.String(128), nullable=True),
        sa.Column("provider_status", sa.String(32), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("response_code", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_attempts_number_positive"),
        sa.UniqueConstraint(
            "transaction_id", "attempt_number", name="uq_attempts_transaction_number"
        ),
        sa.UniqueConstraint("rail_request_id", name="uq_attempts_rail_request"),
        sa.UniqueConstraint("provider_batch_id", name="uq_attempts_provider_batch"),
    )
    op.create_index("ix_attempts_provider_batch", "transaction_attempts", ["provider_batch_id"])
    op.create_index("ix_attempts_status_started", "transaction_attempts", ["status", "started_at"])

    op.create_table(
        "approval_actions",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "transaction_id",
            ID,
            sa.ForeignKey("transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(300), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "action IN ('approved','rejected')", name="ck_approvals_action_valid"
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_approvals_user_idempotency"
        ),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", ID, nullable=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", ID, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", JSON_VALUE, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index("ix_audit_user_created", "audit_events", ["user_id", "created_at"])
    op.create_index("ix_audit_entity", "audit_events", ["entity_type", "entity_id"])

    op.create_table(
        "conversations",
        sa.Column("id", ID, primary_key=True),
        sa.Column("user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )

    op.create_table(
        "conversation_messages",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "conversation_id",
            ID,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", JSON_VALUE, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "role IN ('user','assistant','tool')", name="ck_messages_role_valid"
        ),
    )
    op.create_index(
        "ix_messages_conversation_created",
        "conversation_messages",
        ["conversation_id", "created_at"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_ledger_entry_mutation() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'posted ledger entries are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_ledger_entries_immutable
            BEFORE UPDATE OR DELETE ON ledger_entries
            FOR EACH ROW EXECUTE FUNCTION reject_ledger_entry_mutation()
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION enforce_balanced_ledger_journal() RETURNS trigger AS $$
            DECLARE
              target_journal UUID;
              debit_total BIGINT;
              credit_total BIGINT;
              posting_count INTEGER;
            BEGIN
              target_journal := COALESCE(NEW.journal_id, OLD.journal_id);
              SELECT
                COALESCE(SUM(CASE WHEN direction = 'debit' THEN amount_cents ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN direction = 'credit' THEN amount_cents ELSE 0 END), 0),
                COUNT(*)
              INTO debit_total, credit_total, posting_count
              FROM ledger_entries
              WHERE journal_id = target_journal;
              IF posting_count < 2 OR debit_total <> credit_total THEN
                RAISE EXCEPTION 'ledger journal % is unbalanced', target_journal;
              END IF;
              RETURN NULL;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE CONSTRAINT TRIGGER trg_ledger_journal_balanced
            AFTER INSERT OR UPDATE OR DELETE ON ledger_entries
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION enforce_balanced_ledger_journal()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_ledger_journal_balanced ON ledger_entries")
        op.execute("DROP FUNCTION IF EXISTS enforce_balanced_ledger_journal")
        op.execute("DROP TRIGGER IF EXISTS trg_ledger_entries_immutable ON ledger_entries")
        op.execute("DROP FUNCTION IF EXISTS reject_ledger_entry_mutation")

    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_table("audit_events")
    op.drop_table("approval_actions")
    op.drop_table("transaction_attempts")
    op.drop_table("fund_reservations")
    op.drop_table("ledger_entries")
    op.drop_table("ledger_journals")
    op.drop_table("transactions")
    op.drop_table("policies")
    op.drop_table("wallets")
    op.drop_table("ledger_accounts")
    op.drop_table("sessions")
    op.drop_table("users")
