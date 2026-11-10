"""Add isolated instant-demo principals and safe expired-data cleanup.

Revision ID: 20261110_0006
Revises: 20261107_0005
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261110_0006"
down_revision: Union[str, None] = "20261107_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ID = sa.String(36).with_variant(postgresql.UUID(as_uuid=False), "postgresql")
NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("display_name", sa.String(100), nullable=True),
    )
    op.create_index("ix_users_is_demo", "users", ["is_demo"])

    op.create_table(
        "demo_workspaces",
        sa.Column("id", ID, primary_key=True),
        sa.Column(
            "user_id",
            ID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "seed_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active','revoked','expired')",
            name="ck_demo_workspaces_status_valid",
        ),
        sa.CheckConstraint(
            "seed_version > 0",
            name="ck_demo_workspaces_seed_version_positive",
        ),
        sa.UniqueConstraint("user_id", name="uq_demo_workspaces_user_id"),
    )
    op.create_index(
        "ix_demo_workspaces_status_expiry",
        "demo_workspaces",
        ["status", "expires_at"],
    )

    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE OR REPLACE FUNCTION is_cleanup_eligible_demo_user(target_user UUID)
        RETURNS BOOLEAN AS $$
          SELECT EXISTS (
            SELECT 1
            FROM users AS u
            JOIN demo_workspaces AS d ON d.user_id = u.id
            WHERE u.id = target_user
              AND u.is_demo = TRUE
              AND (d.status <> 'active' OR d.expires_at <= CURRENT_TIMESTAMP)
          )
        $$ LANGUAGE sql STABLE
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_ledger_journal_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND is_cleanup_eligible_demo_user(OLD.user_id) THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'posted ledger journals are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_ledger_entry_mutation() RETURNS trigger AS $$
        DECLARE
          owner_id UUID;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            SELECT user_id INTO owner_id
            FROM ledger_journals
            WHERE id = OLD.journal_id;
            IF owner_id IS NOT NULL AND is_cleanup_eligible_demo_user(owner_id) THEN
              RETURN OLD;
            END IF;
          END IF;
          RAISE EXCEPTION 'posted ledger entries are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND is_cleanup_eligible_demo_user(OLD.user_id) THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'audit events are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_balanced_ledger_journal() RETURNS trigger AS $$
        DECLARE
          target_journal UUID;
          owner_id UUID;
          debit_total BIGINT;
          credit_total BIGINT;
          posting_count INTEGER;
        BEGIN
          target_journal := COALESCE(NEW.journal_id, OLD.journal_id);
          SELECT user_id INTO owner_id
          FROM ledger_journals
          WHERE id = target_journal;

          IF owner_id IS NULL OR is_cleanup_eligible_demo_user(owner_id) THEN
            RETURN NULL;
          END IF;

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


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_ledger_journal_mutation() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'posted ledger journals are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
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
            CREATE OR REPLACE FUNCTION reject_audit_event_mutation() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'audit events are immutable';
            END;
            $$ LANGUAGE plpgsql
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
        op.execute("DROP FUNCTION IF EXISTS is_cleanup_eligible_demo_user")

    op.drop_index(
        "ix_demo_workspaces_status_expiry",
        table_name="demo_workspaces",
    )
    op.drop_table("demo_workspaces")
    op.drop_index("ix_users_is_demo", table_name="users")
    op.drop_column("users", "display_name")
    op.drop_column("users", "is_demo")
