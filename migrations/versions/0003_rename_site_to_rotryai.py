"""rename site to Rotryai

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.execute(
        settings.update()
        .where(settings.c.key == "site_name")
        .values(value="Rotryai")
    )


def downgrade() -> None:
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.execute(
        settings.update()
        .where(settings.c.key == "site_name")
        .values(value="NotrieAI")
    )
