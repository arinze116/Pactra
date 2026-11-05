"""Add conversation history metadata and message request idempotency.

Revision ID: 20261103_0002
Revises: 20261103_0001
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20261103_0002"
down_revision: str | None = "20261103_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "title",
            sa.String(length=120),
            nullable=False,
            server_default="New conversation",
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_conversations_user_updated",
        "conversations",
        ["user_id", "updated_at"],
    )
    op.add_column(
        "conversation_messages",
        sa.Column("request_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_messages_request_role",
        "conversation_messages",
        ["conversation_id", "request_id", "role"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_messages_request_role", table_name="conversation_messages")
    op.drop_column("conversation_messages", "request_id")
    op.drop_index("ix_conversations_user_updated", table_name="conversations")
    op.drop_column("conversations", "archived_at")
    op.drop_column("conversations", "title")
