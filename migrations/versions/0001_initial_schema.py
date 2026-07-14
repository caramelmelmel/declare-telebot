"""initial schema: user, prompt

Revision ID: 0001
Revises:
Create Date: 2026-07-13

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("telegram_user_id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "prompt",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("user.telegram_user_id"),
            nullable=False,
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_update_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("raw_payload_object_key", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("telegram_update_id", name="uq_prompt_telegram_update_id"),
    )
    op.create_index("ix_prompt_expires_at", "prompt", ["expires_at"])
    op.create_index("ix_prompt_user_id", "prompt", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_prompt_user_id", table_name="prompt")
    op.drop_index("ix_prompt_expires_at", table_name="prompt")
    op.drop_table("prompt")
    op.drop_table("user")
