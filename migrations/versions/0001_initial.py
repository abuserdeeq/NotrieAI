"""initial schema: users + app_settings

Revision ID: 0001
Revises:
Create Date: 2026-08-18

"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_SETTINGS = {
    # AI provider toggles - read by app/providers.py at request time.
    "provider_openai_enabled": "true",
    "provider_gemini_enabled": "true",
    # Theme colors - copied from the frontend's current index.css defaults
    # (light mode) so switching to DB-driven theming doesn't change the
    # look of the app on day one. Admin can edit these afterwards.
    "theme_light": json.dumps(
        {
            "background": "42 42% 96%",
            "foreground": "213 28% 18%",
            "primary": "202 34% 20%",
            "primary_foreground": "42 42% 96%",
            "secondary": "38 36% 91%",
            "secondary_foreground": "213 28% 24%",
            "accent": "39 93% 62%",
            "accent_foreground": "213 28% 18%",
        }
    ),
    "theme_dark": json.dumps(
        {
            "background": "205 33% 13%",
            "foreground": "42 42% 96%",
            "primary": "39 93% 62%",
            "primary_foreground": "213 28% 18%",
            "secondary": "202 28% 25%",
            "secondary_foreground": "42 42% 96%",
            "accent": "161 31% 42%",
            "accent_foreground": "42 42% 96%",
        }
    ),
}


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.Text),
    )
    op.bulk_insert(
        settings_table,
        [{"key": k, "value": v} for k, v in DEFAULT_SETTINGS.items()],
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
