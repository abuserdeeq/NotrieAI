"""site branding seed + per-user analysis history

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.bulk_insert(
        settings,
        [
            {"key": "site_name", "value": "Rotryai"},
            {"key": "site_tagline", "value": "Understand anything in seconds."},
        ],
    )

    op.create_table(
        "analysis_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_analysis_history_user_id", "analysis_history", ["user_id"])
    op.create_index(
        "ix_analysis_history_user_created_at",
        "analysis_history",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_history_user_created_at", table_name="analysis_history")
    op.drop_index("ix_analysis_history_user_id", table_name="analysis_history")
    op.drop_table("analysis_history")
    op.execute("DELETE FROM app_settings WHERE key IN ('site_name', 'site_tagline')")
