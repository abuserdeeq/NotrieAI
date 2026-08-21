"""per-account daily/monthly analysis quota

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_type", sa.String(length=10), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id", "period_type", "period_start",
            name="uq_usage_user_period",
        ),
    )
    op.create_index("ix_usage_counters_user_id", "usage_counters", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_usage_counters_user_id", table_name="usage_counters")
    op.drop_table("usage_counters")
