"""seed site_name / site_tagline branding settings

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# These are picked up by GET /api/settings/public (no auth needed, since
# the "site_" prefix is already whitelisted there - see app/routes.py) and
# by the generic admin settings editor (PUT /api/admin/settings), so an
# admin can change either value at any time without touching code or
# running a new migration.
DEFAULT_BRANDING = {
    "site_name": "NotrieAI",
    "site_tagline": "Understanding should not be a privilege.",
}


def upgrade() -> None:
    settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.bulk_insert(
        settings_table,
        [{"key": k, "value": v} for k, v in DEFAULT_BRANDING.items()],
    )


def downgrade() -> None:
    settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
    )
    op.execute(
        settings_table.delete().where(
            settings_table.c.key.in_(list(DEFAULT_BRANDING.keys()))
        )
    )
