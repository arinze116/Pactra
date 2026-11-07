"""Prevent mutation of posted ledger journals and their entry sets.

Revision ID: 20261107_0003
Revises: 20261103_0002
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20261107_0003"
down_revision: Union[str, None] = "20261103_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

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
        CREATE TRIGGER trg_ledger_journals_immutable
        BEFORE UPDATE OR DELETE ON ledger_journals
        FOR EACH ROW EXECUTE FUNCTION reject_ledger_journal_mutation()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION reject_extra_ledger_entry() RETURNS trigger AS $$
        DECLARE
          existing_entry_count INTEGER;
        BEGIN
          SELECT COUNT(*)
          INTO existing_entry_count
          FROM ledger_entries
          WHERE journal_id = NEW.journal_id;

          IF existing_entry_count >= 2 THEN
            RAISE EXCEPTION 'posted ledger journal entry sets are immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_ledger_entries_append_window
        BEFORE INSERT ON ledger_entries
        FOR EACH ROW EXECUTE FUNCTION reject_extra_ledger_entry()
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute(
        "DROP TRIGGER IF EXISTS trg_ledger_entries_append_window ON ledger_entries"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_extra_ledger_entry")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_ledger_journals_immutable ON ledger_journals"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_ledger_journal_mutation")
