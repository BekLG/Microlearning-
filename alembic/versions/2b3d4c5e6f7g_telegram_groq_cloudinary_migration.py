"""Telegram auth and hosted provider migration

Revision ID: 2b3d4c5e6f7g
Revises: 5e69e77be9df
Create Date: 2026-04-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2b3d4c5e6f7g"
down_revision: Union[str, Sequence[str], None] = "5e69e77be9df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    op.add_column("users", sa.Column("first_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("photo_url", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_telegram_id", "users", ["telegram_id"])

    # Preserve existing users so their related documents remain intact.
    # Legacy rows will keep a NULL telegram_id until the user re-authenticates
    # through Telegram and a new account is created or linked manually.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_column("users", "email")
    op.drop_column("users", "password_hash")


def downgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.drop_constraint("uq_users_telegram_id", "users", type_="unique")
    op.drop_column("users", "photo_url")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
    op.drop_column("users", "username")
    op.drop_column("users", "telegram_id")
    op.alter_column("users", "email", nullable=False)
    op.alter_column("users", "password_hash", nullable=False)
