"""add card color to theme_light/theme_dark

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-21
"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches index.css's current --card default for each mode.
CARD_DEFAULTS = {
    "theme_light": "42 50% 99%",
    "theme_dark": "202 31% 18%",
}


def _merge_card(connection, table, key: str, card_value: str) -> None:
    row = connection.execute(
        sa.select(table.c.value).where(table.c.key == key)
    ).first()
    if row is None:
        return
    try:
        data = json.loads(row[0])
    except (TypeError, ValueError):
        return
    if "card" in data:
        return
    data["card"] = card_value
    connection.execute(
        table.update().where(table.c.key == key).values(value=json.dumps(data))
    )


def upgrade() -> None:
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    connection = op.get_bind()
    for key, card_value in CARD_DEFAULTS.items():
        _merge_card(connection, settings, key, card_value)


def downgrade() -> None:
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    connection = op.get_bind()
    for key in CARD_DEFAULTS:
        row = connection.execute(
            sa.select(settings.c.value).where(settings.c.key == key)
        ).first()
        if row is None:
            continue
        try:
            data = json.loads(row[0])
        except (TypeError, ValueError):
            continue
        data.pop("card", None)
        connection.execute(
            settings.update().where(settings.c.key == key).values(value=json.dumps(data))
        )
