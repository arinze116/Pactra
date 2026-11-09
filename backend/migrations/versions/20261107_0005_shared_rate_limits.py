"""Persist API rate-limit windows across processes and restarts.

Revision ID: 20261107_0005
Revises: 20261107_0004
Create Date: 2026-11-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261107_0005"
down_revision: str | None = "20261107_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("key_hash", name="pk_rate_limit_buckets"),
    )
    op.create_index(
        "ix_rate_limit_buckets_expires",
        "rate_limit_buckets",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rate_limit_buckets_expires",
        table_name="rate_limit_buckets",
    )
    op.drop_table("rate_limit_buckets")
